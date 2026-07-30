"""Cliente assíncrono e regras de importação da Pluggy.

As credenciais da aplicação nunca saem do servidor. O frontend recebe apenas
um Connect Token temporário, com escopo limitado, para abrir o widget oficial.
"""
from __future__ import annotations

import asyncio
import os
import sqlite3
import time
import unicodedata
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx
from app.db import insert_and_get_id

PLUGGY_API_URL = "https://api.pluggy.ai"
CONNECT_CLIENT_USER_ID = "finpilot-local"
BRASILIA_TIME = timezone(timedelta(hours=-3))


class PluggyError(RuntimeError):
    """Erro seguro para ser convertido em resposta HTTP pelo router."""


class PluggyConfigurationError(PluggyError):
    """Credenciais da Pluggy ainda não foram configuradas."""


class PluggyAPIError(PluggyError):
    """A Pluggy recusou a chamada ou ficou indisponível."""

    def __init__(self, message: str, *, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code


_api_key: str | None = None
_api_key_credentials: tuple[str, str] | None = None
_api_key_expires_at = 0.0
_api_key_lock = asyncio.Lock()


def pluggy_configured() -> bool:
    return bool(os.getenv("PLUGGY_CLIENT_ID", "").strip() and os.getenv("PLUGGY_CLIENT_SECRET", "").strip())


def _credentials() -> tuple[str, str]:
    client_id = os.getenv("PLUGGY_CLIENT_ID", "").strip()
    client_secret = os.getenv("PLUGGY_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        raise PluggyConfigurationError(
            "Integração bancária ainda não configurada. "
            "Defina PLUGGY_CLIENT_ID e PLUGGY_CLIENT_SECRET no arquivo .env."
        )
    return client_id, client_secret


def _safe_api_message(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        payload = {}
    if isinstance(payload, dict):
        code = payload.get("codeDescription") or payload.get("code")
        message = payload.get("message")
        if code and message:
            return f"{code}: {message}"
        if message:
            return str(message)
        if code:
            return str(code)
    return f"HTTP {response.status_code}"


class PluggyService:
    """Wrapper REST da Pluggy usando apenas httpx."""

    def __init__(self, client: httpx.AsyncClient | None = None):
        self._external_client = client

    async def _authenticate(self, client: httpx.AsyncClient, *, force: bool = False) -> str:
        global _api_key, _api_key_credentials, _api_key_expires_at

        credentials = _credentials()
        if (
            not force
            and _api_key
            and _api_key_credentials == credentials
            and time.monotonic() < _api_key_expires_at
        ):
            return _api_key

        async with _api_key_lock:
            if (
                not force
                and _api_key
                and _api_key_credentials == credentials
                and time.monotonic() < _api_key_expires_at
            ):
                return _api_key

            try:
                response = await client.post(
                    "/auth",
                    json={"clientId": credentials[0], "clientSecret": credentials[1]},
                )
            except httpx.RequestError as exc:
                raise PluggyAPIError("Não foi possível autenticar na Pluggy agora.") from exc

            if response.status_code >= 400:
                status = 401 if response.status_code == 401 else 502
                raise PluggyAPIError(
                    f"Falha na autenticação da Pluggy ({_safe_api_message(response)}).",
                    status_code=status,
                )

            payload = response.json()
            token = payload.get("apiKey") or payload.get("accessToken")
            if not token:
                raise PluggyAPIError("A Pluggy não retornou uma chave de API válida.")

            _api_key = str(token)
            _api_key_credentials = credentials
            # A chave oficial vale duas horas; renovar cinco minutos antes.
            _api_key_expires_at = time.monotonic() + (115 * 60)
            return _api_key

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> Any:
        owns_client = self._external_client is None
        client = self._external_client or httpx.AsyncClient(
            base_url=os.getenv("PLUGGY_API_URL", PLUGGY_API_URL).rstrip("/"),
            timeout=httpx.Timeout(30.0, connect=10.0),
        )
        try:
            api_key = await self._authenticate(client)
            for attempt in range(2):
                try:
                    response = await client.request(
                        method,
                        path,
                        params=params,
                        json=json,
                        headers={"X-API-KEY": api_key, "Accept": "application/json"},
                    )
                except httpx.RequestError as exc:
                    raise PluggyAPIError("A Pluggy está indisponível no momento. Tente novamente.") from exc

                if response.status_code == 401 and attempt == 0:
                    api_key = await self._authenticate(client, force=True)
                    continue
                if response.status_code >= 400:
                    status = response.status_code if response.status_code in (400, 401, 403, 404, 409, 429) else 502
                    raise PluggyAPIError(
                        f"Erro ao consultar a Pluggy ({_safe_api_message(response)}).",
                        status_code=status,
                    )
                if response.status_code == 204:
                    return None
                return response.json()
            raise PluggyAPIError("Não foi possível renovar a autenticação da Pluggy.", status_code=401)
        finally:
            if owns_client:
                await client.aclose()

    async def create_connect_token(
        self,
        *,
        client_user_id: str = CONNECT_CLIENT_USER_ID,
        item_id: str | None = None,
    ) -> str:
        body: dict[str, Any] = {
            "options": {
                "clientUserId": client_user_id,
                "avoidDuplicates": True,
            }
        }
        if item_id:
            body["itemId"] = item_id
        payload = await self._request("POST", "/connect_token", json=body)
        token = payload.get("accessToken") if isinstance(payload, dict) else None
        if not token:
            raise PluggyAPIError("A Pluggy não retornou um Connect Token válido.")
        return str(token)

    async def get_item(self, item_id: str) -> dict[str, Any]:
        payload = await self._request("GET", f"/items/{item_id}")
        if not isinstance(payload, dict):
            raise PluggyAPIError("Resposta inválida ao consultar a conexão bancária.")
        return payload

    async def fetch_accounts(self, item_id: str) -> list[dict[str, Any]]:
        payload = await self._request("GET", "/accounts", params={"itemId": item_id})
        results = payload.get("results", []) if isinstance(payload, dict) else []
        return [item for item in results if isinstance(item, dict)]

    async def fetch_transactions(
        self,
        account_id: str,
        *,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"accountId": account_id}
        if date_from:
            params["dateFrom"] = date_from.isoformat()
        if date_to:
            params["dateTo"] = date_to.isoformat()

        transactions: list[dict[str, Any]] = []
        seen_cursors: set[str] = set()
        for _ in range(100):
            payload = await self._request("GET", "/v2/transactions", params=params)
            if not isinstance(payload, dict):
                raise PluggyAPIError("Resposta inválida ao consultar transações.")
            transactions.extend(item for item in payload.get("results", []) if isinstance(item, dict))

            next_page = payload.get("next")
            if not next_page:
                break
            parsed = urlparse(str(next_page))
            next_params = {key: values[-1] for key, values in parse_qs(parsed.query).items() if values}
            cursor = str(next_params.get("after", ""))
            if not cursor or cursor in seen_cursors:
                break
            seen_cursors.add(cursor)
            params = next_params
        else:
            raise PluggyAPIError("A paginação de transações excedeu o limite de segurança.")
        return transactions


CATEGORY_RULES: tuple[tuple[str, str, str, tuple[str, ...]], ...] = (
    ("Alimentação", "#F2B94D", "utensils", ("food", "restaurant", "grocery", "supermarket", "mercado", "padaria", "bakery", "ifood")),
    ("Moradia", "#8B7CF6", "house", ("rent", "home", "housing", "aluguel", "condominio", "energia", "electric", "water", "agua", "gas")),
    ("Transporte", "#4C8DFF", "car", ("transport", "uber", "99app", "fuel", "gas station", "combustivel", "posto", "parking", "pedagio")),
    ("Saúde", "#F06B8A", "heart-pulse", ("health", "pharmacy", "drugstore", "hospital", "doctor", "farmacia", "drogaria", "medic")),
    ("Educação", "#5A9BD5", "graduation-cap", ("education", "school", "college", "course", "book", "escola", "faculdade", "curso", "livro")),
    ("Lazer", "#A978E8", "gamepad-2", ("entertainment", "cinema", "travel", "viagem", "hotel", "game", "lazer")),
    ("Assinaturas", "#7A69D8", "receipt", ("subscription", "streaming", "netflix", "spotify", "internet", "software", "assinatura")),
    ("Compras", "#E68A5C", "shopping-bag", ("shopping", "clothing", "electronics", "store", "roupa", "tenis", "calcado", "loja")),
    ("Transferências", "#7D8B99", "arrow-left-right", ("transfer", "pix", "ted", "doc", "bank slip", "boleto")),
)

INCOME_RULES: tuple[tuple[str, str, str, tuple[str, ...]], ...] = (
    ("Salário", "#19A974", "wallet-cards", ("salary", "payroll", "salario", "folha")),
    ("Rendimentos", "#2F9E79", "trending-up", ("income", "yield", "interest", "dividend", "rendimento", "juros", "dividendo")),
    ("Transferências recebidas", "#4C8DFF", "arrow-down-left", ("transfer", "pix", "ted", "doc")),
)


def _normalized(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    return "".join(char for char in text if not unicodedata.combining(char)).casefold()


def map_transaction_category(transaction: dict[str, Any], tipo: str) -> tuple[str, str, str]:
    """Mapeia categoria/descrição da Pluggy para uma categoria do FinPilot."""

    merchant = transaction.get("merchant")
    merchant_text = ""
    if isinstance(merchant, dict):
        merchant_text = " ".join(
            str(merchant.get(field) or "") for field in ("name", "businessName", "category")
        )
    haystack = _normalized(
        " ".join(
            str(value or "")
            for value in (
                transaction.get("category"),
                transaction.get("description"),
                transaction.get("descriptionRaw"),
                transaction.get("operationType"),
                transaction.get("operationTypeAdditionalInfo"),
                merchant_text,
            )
        )
    )

    rules = INCOME_RULES if tipo == "receita" else CATEGORY_RULES
    for name, color, icon, keywords in rules:
        if any(_normalized(keyword) in haystack for keyword in keywords):
            return name, color, icon
    if tipo == "receita":
        return "Outras receitas", "#19A974", "circle-plus"
    return "Outros", "#7D8B99", "shapes"


def resolve_category_id(
    conn: sqlite3.Connection,
    transaction: dict[str, Any],
    tipo: str,
) -> int:
    name, color, icon = map_transaction_category(transaction, tipo)
    row = conn.execute(
        "SELECT id FROM categories WHERE nome = ? AND tipo = ? ORDER BY id LIMIT 1",
        (name, tipo),
    ).fetchone()
    if row:
        return int(row["id"])
    category_id = insert_and_get_id(
        conn,
        "INSERT INTO categories (nome, tipo, cor, icone, essencial) VALUES (?, ?, ?, ?, 0)",
        (name, tipo, color, icon),
    )
    return category_id


def transaction_kind(account: dict[str, Any], transaction: dict[str, Any]) -> str | None:
    """Converte o sentido da Pluggy em despesa/receita.

    Pagamentos/créditos em fatura de cartão são ignorados: registrá-los como
    receita distorceria o fluxo de caixa e duplicaria a saída da conta bancária.
    """

    provider_type = str(transaction.get("type") or "").upper()
    account_type = str(account.get("type") or "").upper()
    if account_type == "CREDIT":
        return "despesa" if provider_type == "DEBIT" else None
    if provider_type == "DEBIT":
        return "despesa"
    if provider_type == "CREDIT":
        return "receita"
    try:
        return "despesa" if Decimal(str(transaction.get("amount"))) < 0 else "receita"
    except (InvalidOperation, TypeError):
        return None


def amount_to_centavos(value: Any) -> int:
    try:
        amount = abs(Decimal(str(value))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, TypeError, ValueError):
        return 0
    return int(amount * 100)


def signed_amount_to_centavos(value: Any) -> int:
    try:
        amount = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, TypeError, ValueError):
        return 0
    return int(amount * 100)


def transaction_date(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return date.today().isoformat()
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(BRASILIA_TIME).date().isoformat()
    except ValueError:
        try:
            return date.fromisoformat(raw[:10]).isoformat()
        except ValueError:
            return date.today().isoformat()


def masked_account_number(value: Any) -> str | None:
    raw = "".join(char for char in str(value or "") if char.isalnum())
    return f"•••• {raw[-4:]}" if raw else None


def default_sync_start(days: int = 365) -> date:
    return date.today() - timedelta(days=days)
