"""Autenticação multiusuário do FinPilot usando Supabase Auth.

Tokens ficam apenas em cookies HttpOnly. Cada requisição autenticada expõe o
UUID do usuário em um ContextVar, usado pela camada PostgreSQL para ativar as
políticas RLS do Supabase.
"""
from __future__ import annotations

import contextvars
import os
import re
import time
from pathlib import Path
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel, EmailStr, Field, field_validator
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

ACCESS_COOKIE = "finpilot_access_token"
REFRESH_COOKIE = "finpilot_refresh_token"
REFRESH_MAX_AGE = 30 * 24 * 60 * 60
PUBLIC_PATHS = {"/entrar", "/termos", "/privacidade", "/api/health", "/favicon.ico"}
PUBLIC_AUTH_PATHS = {"/api/auth/login", "/api/auth/register"}
AUTH_HTML = Path(__file__).resolve().parent / "static" / "auth.html"
TERMS_HTML = Path(__file__).resolve().parent / "static" / "terms.html"
PRIVACY_HTML = Path(__file__).resolve().parent / "static" / "privacy.html"

_current_user_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "finpilot_current_user_id",
    default=None,
)
_validated_tokens: dict[str, tuple[float, dict[str, Any]]] = {}

router = APIRouter(tags=["auth"])


class LoginPayload(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class RegisterPayload(LoginPayload):
    display_name: str = Field(min_length=2, max_length=60)
    confirm_password: str = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def strong_password(cls, value: str) -> str:
        if not re.search(r"[A-Za-zÀ-ÿ]", value) or not re.search(r"\d", value):
            raise ValueError("Use pelo menos uma letra e um número.")
        return value

    @field_validator("confirm_password")
    @classmethod
    def matching_password(cls, value: str, info) -> str:
        if info.data.get("password") != value:
            raise ValueError("As senhas não coincidem.")
        return value


def get_current_user_id() -> str | None:
    return _current_user_id.get()


def auth_configured() -> bool:
    return bool(
        os.getenv("SUPABASE_URL", "").strip()
        and (
            os.getenv("SUPABASE_PUBLISHABLE_KEY", "").strip()
            or os.getenv("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY", "").strip()
            or os.getenv("SUPABASE_ANON_KEY", "").strip()
        )
    )


def _running_on_vercel() -> bool:
    return bool(os.getenv("VERCEL"))


def _protection_required() -> bool:
    return _running_on_vercel() or auth_configured()


def _publishable_key() -> str:
    return (
        os.getenv("SUPABASE_PUBLISHABLE_KEY", "").strip()
        or os.getenv("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY", "").strip()
        or os.getenv("SUPABASE_ANON_KEY", "").strip()
    )


def _safe_auth_error(payload: Any, default: str) -> str:
    raw = ""
    if isinstance(payload, dict):
        raw = str(
            payload.get("msg")
            or payload.get("message")
            or payload.get("error_description")
            or payload.get("error")
            or ""
        )
    normalized = raw.casefold()
    mappings = (
        (("invalid login", "invalid credentials"), "E-mail ou senha incorretos."),
        (("email not confirmed",), "Confirme seu e-mail antes de entrar."),
        (("already registered", "user already"), "Já existe uma conta com esse e-mail."),
        (("password", "least"), "A senha não atende aos requisitos de segurança."),
        (("rate limit", "too many"), "Muitas tentativas. Aguarde alguns minutos e tente novamente."),
        (("email", "invalid"), "Digite um endereço de e-mail válido."),
    )
    for needles, message in mappings:
        if all(needle in normalized for needle in needles):
            return message
    return default


class SupabaseAuthService:
    def __init__(self, client: httpx.AsyncClient | None = None):
        self._client = client

    def _config(self) -> tuple[str, str]:
        url = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
        key = _publishable_key()
        if not url or not key:
            raise RuntimeError("A autenticação do Supabase ainda não foi conectada à Vercel.")
        return url, key

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        url, key = self._config()
        headers = {"apikey": key, "Accept": "application/json", "Content-Type": "application/json"}
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"
        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(timeout=httpx.Timeout(20.0, connect=8.0))
        try:
            response = await client.request(method, f"{url}{path}", headers=headers, json=json)
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=503,
                detail="Não foi possível acessar o login agora. Tente novamente em instantes.",
            ) from exc
        finally:
            if owns_client:
                await client.aclose()

        try:
            payload = response.json()
        except ValueError:
            payload = {}
        if response.status_code >= 400:
            default = "Não foi possível concluir o acesso. Tente novamente."
            raise HTTPException(
                status_code=401 if response.status_code in (400, 401) else response.status_code,
                detail=_safe_auth_error(payload, default),
            )
        if not isinstance(payload, dict):
            raise HTTPException(status_code=502, detail="Resposta inválida do serviço de acesso.")
        return payload

    async def sign_up(self, *, display_name: str, email: str, password: str) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/auth/v1/signup",
            json={
                "email": email.strip().casefold(),
                "password": password,
                "data": {"display_name": display_name.strip()},
            },
        )

    async def sign_in(self, *, email: str, password: str) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/auth/v1/token?grant_type=password",
            json={"email": email.strip().casefold(), "password": password},
        )

    async def refresh(self, refresh_token: str) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/auth/v1/token?grant_type=refresh_token",
            json={"refresh_token": refresh_token},
        )

    async def get_user(self, access_token: str) -> dict[str, Any]:
        return await self._request("GET", "/auth/v1/user", access_token=access_token)

    async def sign_out(self, access_token: str) -> None:
        try:
            await self._request("POST", "/auth/v1/logout", access_token=access_token)
        except HTTPException:
            pass


def _set_auth_cookies(response: Response, session: dict[str, Any]) -> None:
    access_token = str(session.get("access_token") or "")
    refresh_token = str(session.get("refresh_token") or "")
    if not access_token or not refresh_token:
        raise HTTPException(status_code=502, detail="O serviço de acesso não retornou uma sessão válida.")
    expires_in = max(60, min(int(session.get("expires_in") or 3600), 24 * 60 * 60))
    common = {
        "httponly": True,
        "secure": _running_on_vercel(),
        "samesite": "lax",
        "path": "/",
    }
    response.set_cookie(ACCESS_COOKIE, access_token, max_age=expires_in, **common)
    response.set_cookie(REFRESH_COOKIE, refresh_token, max_age=REFRESH_MAX_AGE, **common)
    response.headers["Cache-Control"] = "no-store"


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(ACCESS_COOKIE, path="/", samesite="lax")
    response.delete_cookie(REFRESH_COOKIE, path="/", samesite="lax")
    response.headers["Cache-Control"] = "no-store"


async def _validated_user(access_token: str) -> dict[str, Any]:
    cached = _validated_tokens.get(access_token)
    now = time.monotonic()
    if cached and cached[0] > now:
        return cached[1]
    user = await SupabaseAuthService().get_user(access_token)
    user_id = str(user.get("id") or "")
    if not user_id:
        raise HTTPException(status_code=401, detail="Sessão inválida.")
    safe_user = {
        "id": user_id,
        "email": user.get("email"),
        "display_name": (user.get("user_metadata") or {}).get("display_name") or "Usuário",
    }
    _validated_tokens[access_token] = (now + 180, safe_user)
    if len(_validated_tokens) > 500:
        expired = [token for token, value in _validated_tokens.items() if value[0] <= now]
        for token in expired:
            _validated_tokens.pop(token, None)
    return safe_user


class SupabaseAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        is_public = (
            request.method == "OPTIONS"
            or path in PUBLIC_PATHS
            or path in PUBLIC_AUTH_PATHS
        )
        if is_public or not _protection_required():
            return await call_next(request)

        if not auth_configured():
            if path.startswith("/api/"):
                return JSONResponse(
                    {"detail": "Conecte o Supabase Auth à Vercel antes de usar o FinPilot."},
                    status_code=503,
                )
            return RedirectResponse(url="/entrar?config=required", status_code=303)

        access_token = request.cookies.get(ACCESS_COOKIE)
        refresh_token = request.cookies.get(REFRESH_COOKIE)
        session_to_write: dict[str, Any] | None = None
        user: dict[str, Any] | None = None
        if access_token:
            try:
                user = await _validated_user(access_token)
            except HTTPException:
                user = None
        if user is None and refresh_token:
            try:
                session_to_write = await SupabaseAuthService().refresh(refresh_token)
                access_token = str(session_to_write.get("access_token") or "")
                user = await _validated_user(access_token)
            except HTTPException:
                user = None

        if user is None:
            if path.startswith("/api/"):
                response = JSONResponse({"detail": "Entre no FinPilot para continuar."}, status_code=401)
                _clear_auth_cookies(response)
                return response
            return RedirectResponse(url="/entrar", status_code=303)

        request.state.user = user
        context_token = _current_user_id.set(str(user["id"]))
        try:
            response = await call_next(request)
        finally:
            _current_user_id.reset(context_token)
        if session_to_write:
            _set_auth_cookies(response, session_to_write)
        response.headers.setdefault("Cache-Control", "no-store")
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        return response


@router.get("/entrar", include_in_schema=False)
def auth_page():
    return FileResponse(AUTH_HTML, media_type="text/html", headers={"Cache-Control": "no-store"})


@router.get("/termos", include_in_schema=False)
def terms_page():
    return FileResponse(TERMS_HTML, media_type="text/html")


@router.get("/privacidade", include_in_schema=False)
def privacy_page():
    return FileResponse(PRIVACY_HTML, media_type="text/html")


@router.post("/api/auth/register")
async def register(payload: RegisterPayload):
    result = await SupabaseAuthService().sign_up(
        display_name=payload.display_name,
        email=str(payload.email),
        password=payload.password,
    )
    response = JSONResponse(
        {
            "ok": True,
            "confirmation_required": not bool(result.get("access_token")),
            "message": (
                "Confira seu e-mail para confirmar a conta."
                if not result.get("access_token")
                else "Conta criada com sucesso."
            ),
        },
        status_code=201,
    )
    if result.get("access_token"):
        _set_auth_cookies(response, result)
    return response


@router.post("/api/auth/login")
async def login(payload: LoginPayload):
    session = await SupabaseAuthService().sign_in(email=str(payload.email), password=payload.password)
    response = JSONResponse({"ok": True, "message": "Acesso confirmado."})
    _set_auth_cookies(response, session)
    return response


@router.get("/api/auth/me")
def me(request: Request):
    user = getattr(request.state, "user", None)
    if not user and not _protection_required():
        return {
            "id": "local-user",
            "email": "local@finpilot.app",
            "display_name": "Mi",
            "user_metadata": {"display_name": "Mi"},
            "local_mode": True,
        }
    if not user:
        raise HTTPException(status_code=401, detail="Entre no FinPilot para continuar.")
    return user


@router.post("/api/auth/logout")
async def logout(request: Request):
    access_token = request.cookies.get(ACCESS_COOKIE)
    if access_token:
        await SupabaseAuthService().sign_out(access_token)
        _validated_tokens.pop(access_token, None)
    response = JSONResponse({"ok": True})
    _clear_auth_cookies(response)
    return response
