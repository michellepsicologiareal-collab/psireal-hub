from __future__ import annotations

from uuid import UUID

from app.security import ACCESS_COOKIE, REFRESH_COOKIE, SupabaseAuthService

USER_ID = "67e55044-10b1-426f-9247-bb680e5fe0c8"


def _configure_auth(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://exemplo.supabase.co")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "chave-publicavel-de-teste")
    monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)
    monkeypatch.delenv("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY", raising=False)


def test_auth_page_matches_requested_account_screen(client):
    response = client.get("/entrar")

    assert response.status_code == 200
    assert "Entrar" in response.text
    assert "Criar conta" in response.text
    assert "Crie seu acesso" in response.text
    assert "Dados separados por usuário" in response.text
    assert "Confirmar senha" in response.text


def test_legal_pages_are_public(client, monkeypatch):
    _configure_auth(monkeypatch)

    terms = client.get("/termos")
    privacy = client.get("/privacidade")

    assert terms.status_code == 200
    assert "Termos de uso" in terms.text
    assert privacy.status_code == 200
    assert "Política de privacidade" in privacy.text


def test_health_remains_public_when_auth_is_enabled(client, monkeypatch):
    _configure_auth(monkeypatch)

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_vercel_fails_closed_without_supabase_auth(client, monkeypatch):
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_PUBLISHABLE_KEY", raising=False)
    monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)
    monkeypatch.delenv("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY", raising=False)

    api_response = client.get("/api/categories")
    assert api_response.status_code == 503
    assert "Supabase Auth" in api_response.json()["detail"]

    page_response = client.get("/", follow_redirects=False)
    assert page_response.status_code == 303
    assert page_response.headers["location"] == "/entrar?config=required"


def test_protected_api_requires_a_session(client, monkeypatch):
    _configure_auth(monkeypatch)

    response = client.get("/api/categories")

    assert response.status_code == 401
    assert "Entre no FinPilot" in response.json()["detail"]


def test_login_sets_http_only_cookies_and_opens_the_app(client, monkeypatch):
    _configure_auth(monkeypatch)

    async def fake_sign_in(self, *, email, password):
        assert email == "michelle@example.com"
        assert password == "Segura123"
        return {
            "access_token": "access-token-de-teste",
            "refresh_token": "refresh-token-de-teste",
            "expires_in": 3600,
        }

    async def fake_get_user(self, access_token):
        assert access_token == "access-token-de-teste"
        return {
            "id": USER_ID,
            "email": "michelle@example.com",
            "user_metadata": {"display_name": "Michelle"},
        }

    async def fake_sign_out(self, access_token):
        assert access_token == "access-token-de-teste"

    monkeypatch.setattr(SupabaseAuthService, "sign_in", fake_sign_in)
    monkeypatch.setattr(SupabaseAuthService, "get_user", fake_get_user)
    monkeypatch.setattr(SupabaseAuthService, "sign_out", fake_sign_out)

    response = client.post(
        "/api/auth/login",
        json={"email": "michelle@example.com", "password": "Segura123"},
    )

    assert response.status_code == 200
    cookie_headers = response.headers.get_list("set-cookie")
    assert any(ACCESS_COOKIE in value and "HttpOnly" in value for value in cookie_headers)
    assert any(REFRESH_COOKIE in value and "HttpOnly" in value for value in cookie_headers)

    authorized = client.get("/api/categories")
    assert authorized.status_code == 200

    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["id"] == str(UUID(USER_ID))
    assert me.json()["display_name"] == "Michelle"

    logout = client.post("/api/auth/logout")
    assert logout.status_code == 200
    assert client.get("/api/categories").status_code == 401


def test_register_requires_matching_strong_password(client, monkeypatch):
    _configure_auth(monkeypatch)

    mismatch = client.post(
        "/api/auth/register",
        json={
            "display_name": "Michelle",
            "email": "michelle@example.com",
            "password": "Segura123",
            "confirm_password": "Outra123",
        },
    )
    assert mismatch.status_code == 422

    weak = client.post(
        "/api/auth/register",
        json={
            "display_name": "Michelle",
            "email": "michelle@example.com",
            "password": "semsomente",
            "confirm_password": "semsomente",
        },
    )
    assert weak.status_code == 422


def test_register_can_require_email_confirmation(client, monkeypatch):
    _configure_auth(monkeypatch)

    async def fake_sign_up(self, *, display_name, email, password):
        return {"user": {"id": USER_ID}}

    monkeypatch.setattr(SupabaseAuthService, "sign_up", fake_sign_up)

    response = client.post(
        "/api/auth/register",
        json={
            "display_name": "Michelle",
            "email": "michelle@example.com",
            "password": "Segura123",
            "confirm_password": "Segura123",
        },
    )

    assert response.status_code == 201
    assert response.json()["confirmation_required"] is True
    assert "e-mail" in response.json()["message"]
