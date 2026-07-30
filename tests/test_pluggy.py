from __future__ import annotations

import asyncio

import httpx

from app.services.pluggy_service import (
    PluggyService,
    map_transaction_category,
    transaction_kind,
)


def test_pluggy_migrations_create_integration_tables(conn):
    names = {
        row["name"]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name LIKE 'pluggy_%'"
        ).fetchall()
    }
    assert names == {"pluggy_connections", "pluggy_accounts", "pluggy_transaction_links"}


def test_automatic_category_mapping():
    category = map_transaction_category(
        {"description": "SUPERMERCADO CENTRAL", "category": "Food - Groceries"},
        "despesa",
    )
    assert category[0] == "Alimentação"


def test_credit_card_payment_is_not_income():
    account = {"type": "CREDIT"}
    assert transaction_kind(account, {"type": "DEBIT", "amount": 95.56}) == "despesa"
    assert transaction_kind(account, {"type": "CREDIT", "amount": -1500}) is None


def test_connection_from_another_client_user_is_rejected(client, monkeypatch):
    import app.routers.pluggy as pluggy_router

    class ForeignItemService:
        async def get_item(self, item_id):
            return {"id": item_id, "clientUserId": "outro-usuario"}

    monkeypatch.setattr(pluggy_router, "PluggyService", ForeignItemService)
    response = client.post("/api/pluggy/connect", json={"item_id": "foreign-item-123"})
    assert response.status_code == 403


def test_service_authenticates_and_creates_connect_token(monkeypatch):
    monkeypatch.setenv("PLUGGY_CLIENT_ID", "client-test-connect-token")
    monkeypatch.setenv("PLUGGY_CLIENT_SECRET", "secret-test-connect-token")
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/auth":
            return httpx.Response(200, json={"apiKey": "api-key-test"})
        if request.url.path == "/connect_token":
            assert request.headers["X-API-KEY"] == "api-key-test"
            return httpx.Response(200, json={"accessToken": "connect-token-test"})
        return httpx.Response(404)

    async def run():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            base_url="https://api.pluggy.ai",
        ) as client:
            return await PluggyService(client).create_connect_token()

    token = asyncio.run(run())

    assert token == "connect-token-test"
    assert [request.url.path for request in requests] == ["/auth", "/connect_token"]
    assert b"clientSecret" in requests[0].content
    assert b"clientSecret" not in requests[1].content


def test_pluggy_endpoints_connect_list_and_sync(client, monkeypatch):
    import app.routers.pluggy as pluggy_router

    monkeypatch.setenv("PLUGGY_CLIENT_ID", "client-endpoint-test")
    monkeypatch.setenv("PLUGGY_CLIENT_SECRET", "secret-endpoint-test")

    class FakePluggyService:
        async def create_connect_token(self, *, client_user_id="finpilot-local", item_id=None):
            assert client_user_id == "finpilot-local"
            return "connect-token"

        async def get_item(self, item_id):
            return {
                "id": item_id,
                "clientUserId": "finpilot-local",
                "status": "UPDATED",
                "executionStatus": "SUCCESS",
                "connector": {"id": 42, "name": "Banco Teste"},
            }

        async def fetch_accounts(self, item_id):
            return [
                {
                    "id": "account-bank-1",
                    "itemId": item_id,
                    "type": "BANK",
                    "subtype": "CHECKING_ACCOUNT",
                    "name": "Conta Corrente",
                    "number": "0001/12345-6",
                    "balance": 1540.75,
                    "currencyCode": "BRL",
                }
            ]

        async def fetch_transactions(self, account_id, *, date_from=None, date_to=None):
            return [
                {
                    "id": "transaction-posted-1",
                    "accountId": account_id,
                    "date": "2026-07-28T15:00:00.000Z",
                    "description": "SUPERMERCADO CENTRAL",
                    "amount": -95.56,
                    "type": "DEBIT",
                    "status": "POSTED",
                    "category": "Food - Groceries",
                },
                {
                    "id": "transaction-pending-1",
                    "accountId": account_id,
                    "date": "2026-07-29T15:00:00.000Z",
                    "description": "COMPRA PENDENTE",
                    "amount": -20,
                    "type": "DEBIT",
                    "status": "PENDING",
                },
            ]

    monkeypatch.setattr(pluggy_router, "PluggyService", FakePluggyService)

    token_response = client.post("/api/pluggy/connect", json={})
    assert token_response.status_code == 200
    assert token_response.json()["accessToken"] == "connect-token"

    confirm_response = client.post("/api/pluggy/connect", json={"item_id": "item-test-123"})
    assert confirm_response.status_code == 200
    assert confirm_response.json()["connected"] is True

    accounts_response = client.get("/api/pluggy/accounts")
    assert accounts_response.status_code == 200
    assert accounts_response.json()["items"][0]["numero"] == "•••• 3456"
    assert "taxNumber" not in accounts_response.text

    first_sync = client.post("/api/pluggy/sync", json={"dias": 365})
    assert first_sync.status_code == 200
    assert first_sync.json()["importadas"] == 1
    assert first_sync.json()["ignoradas"] == 1

    second_sync = client.post("/api/pluggy/sync", json={"dias": 365})
    assert second_sync.status_code == 200
    assert second_sync.json()["importadas"] == 0
    assert second_sync.json()["atualizadas"] == 1

    transactions = client.get("/api/transactions", params={"busca": "SUPERMERCADO"}).json()
    assert transactions["total"] == 1
    assert transactions["items"][0]["valor"] == 95.56
    assert transactions["items"][0]["metodo_pagamento"] == "Open Finance"
