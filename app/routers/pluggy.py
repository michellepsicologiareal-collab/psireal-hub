from __future__ import annotations

import sqlite3
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel, Field

from app.db import get_db_dependency, insert_and_get_id
from app.security import get_current_user_id
from app.services.pluggy_service import (
    CONNECT_CLIENT_USER_ID,
    PluggyAPIError,
    PluggyConfigurationError,
    PluggyService,
    amount_to_centavos,
    default_sync_start,
    masked_account_number,
    pluggy_configured,
    resolve_category_id,
    signed_amount_to_centavos,
    transaction_date,
    transaction_kind,
)

router = APIRouter(prefix="/api/pluggy", tags=["pluggy"])


class ConnectRequest(BaseModel):
    item_id: str | None = Field(default=None, min_length=8, max_length=100)


class SyncRequest(BaseModel):
    item_id: str | None = Field(default=None, min_length=8, max_length=100)
    dias: int = Field(default=365, ge=1, le=365)


def _client_user_id() -> str:
    """Identificador estável que impede vincular um banco à conta errada."""

    return get_current_user_id() or CONNECT_CLIENT_USER_ID


def _http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, PluggyConfigurationError):
        return HTTPException(status_code=503, detail=str(exc))
    if isinstance(exc, PluggyAPIError):
        return HTTPException(status_code=exc.status_code, detail=str(exc))
    return HTTPException(status_code=502, detail="Falha inesperada na integração bancária.")


def _connector_details(item: dict[str, Any]) -> tuple[str | None, str | None]:
    connector = item.get("connector")
    if not isinstance(connector, dict):
        return None, None
    connector_id = connector.get("id")
    return (str(connector_id) if connector_id is not None else None, connector.get("name"))


def _save_connection(conn: sqlite3.Connection, item: dict[str, Any]) -> None:
    item_id = str(item.get("id") or "")
    if not item_id:
        raise HTTPException(status_code=422, detail="Item da Pluggy sem identificador.")
    client_user_id = item.get("clientUserId")
    if client_user_id != _client_user_id():
        raise HTTPException(status_code=403, detail="Esta conexão não pertence a este FinPilot.")

    connector_id, connector_name = _connector_details(item)
    conn.execute(
        """
        INSERT INTO pluggy_connections
            (item_id, connector_id, connector_name, status, execution_status, updated_at)
        VALUES (?, ?, ?, ?, ?, datetime('now'))
        ON CONFLICT(item_id) DO UPDATE SET
            connector_id = excluded.connector_id,
            connector_name = excluded.connector_name,
            status = excluded.status,
            execution_status = excluded.execution_status,
            updated_at = datetime('now')
        """,
        (
            item_id,
            connector_id,
            connector_name,
            item.get("status"),
            item.get("executionStatus"),
        ),
    )
    conn.commit()


@router.post("/connect")
async def connect(
    payload: ConnectRequest | None = Body(default=None),
    conn: sqlite3.Connection = Depends(get_db_dependency),
):
    """Cria Connect Token ou confirma o item retornado pelo widget."""

    service = PluggyService()
    try:
        if payload and payload.item_id:
            item = await service.get_item(payload.item_id)
            _save_connection(conn, item)
            return {
                "connected": True,
                "item_id": payload.item_id,
                "status": item.get("status"),
                "execution_status": item.get("executionStatus"),
            }

        access_token = await service.create_connect_token(client_user_id=_client_user_id())
        return {
            "accessToken": access_token,
            "expires_in_minutes": 30,
            "configured": True,
        }
    except (PluggyConfigurationError, PluggyAPIError) as exc:
        raise _http_error(exc) from exc


@router.get("/accounts")
async def accounts(conn: sqlite3.Connection = Depends(get_db_dependency)):
    """Lista contas conectadas sem expor CPF ou número bancário completo."""

    if not pluggy_configured():
        raise _http_error(PluggyConfigurationError(
            "Integração bancária ainda não configurada. "
            "Defina PLUGGY_CLIENT_ID e PLUGGY_CLIENT_SECRET no arquivo .env."
        ))

    connections = conn.execute(
        "SELECT item_id, connector_name, status, last_sync_at FROM pluggy_connections ORDER BY created_at"
    ).fetchall()
    if not connections:
        return {"items": [], "total": 0}

    service = PluggyService()
    output: list[dict[str, Any]] = []
    try:
        for connection in connections:
            item_id = connection["item_id"]
            remote_accounts = await service.fetch_accounts(item_id)
            for account in remote_accounts:
                account_id = str(account.get("id") or "")
                if not account_id:
                    continue
                credit_data = account.get("creditData") if isinstance(account.get("creditData"), dict) else {}
                conn.execute(
                    """
                    INSERT INTO pluggy_accounts
                        (account_id, item_id, type, subtype, name, number_masked,
                         balance_centavos, currency_code, credit_limit_centavos, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                    ON CONFLICT(account_id) DO UPDATE SET
                        item_id = excluded.item_id,
                        type = excluded.type,
                        subtype = excluded.subtype,
                        name = excluded.name,
                        number_masked = excluded.number_masked,
                        balance_centavos = excluded.balance_centavos,
                        currency_code = excluded.currency_code,
                        credit_limit_centavos = excluded.credit_limit_centavos,
                        updated_at = datetime('now')
                    """,
                    (
                        account_id,
                        item_id,
                        account.get("type"),
                        account.get("subtype"),
                        account.get("name") or account.get("marketingName") or "Conta bancária",
                        masked_account_number(account.get("number")),
                        signed_amount_to_centavos(account.get("balance")),
                        account.get("currencyCode") or "BRL",
                        amount_to_centavos(credit_data.get("creditLimit")) if credit_data else None,
                    ),
                )
                output.append(
                    {
                        "id": account_id,
                        "item_id": item_id,
                        "instituicao": connection["connector_name"],
                        "nome": account.get("name") or account.get("marketingName") or "Conta bancária",
                        "numero": masked_account_number(account.get("number")),
                        "tipo": account.get("type"),
                        "subtipo": account.get("subtype"),
                        "saldo": signed_amount_to_centavos(account.get("balance")) / 100,
                        "moeda": account.get("currencyCode") or "BRL",
                        "limite_credito": (
                            amount_to_centavos(credit_data.get("creditLimit")) / 100
                            if credit_data and credit_data.get("creditLimit") is not None
                            else None
                        ),
                        "ultima_sincronizacao": connection["last_sync_at"],
                    }
                )
        conn.commit()
        return {"items": output, "total": len(output)}
    except (PluggyConfigurationError, PluggyAPIError) as exc:
        conn.rollback()
        raise _http_error(exc) from exc


def _upsert_imported_transaction(
    conn: sqlite3.Connection,
    *,
    account: dict[str, Any],
    provider_transaction: dict[str, Any],
) -> str:
    provider_transaction_id = str(provider_transaction.get("id") or "")
    account_id = str(account.get("id") or "")
    if not provider_transaction_id or not account_id:
        return "ignorada"
    if str(provider_transaction.get("status") or "").upper() != "POSTED":
        return "ignorada"

    tipo = transaction_kind(account, provider_transaction)
    transaction_currency = str(provider_transaction.get("currencyCode") or "BRL").upper()
    account_currency = str(account.get("currencyCode") or "BRL").upper()
    if transaction_currency == "BRL":
        imported_amount = provider_transaction.get("amount")
    elif account_currency == "BRL" and provider_transaction.get("amountInAccountCurrency") is not None:
        imported_amount = provider_transaction.get("amountInAccountCurrency")
    else:
        # O FinPilot ainda não mantém câmbio/moeda por lançamento. Importar
        # diretamente um valor em USD/EUR como se fosse BRL seria incorreto.
        return "ignorada"
    valor_centavos = amount_to_centavos(imported_amount)
    if tipo is None or valor_centavos <= 0:
        return "ignorada"

    category_id = resolve_category_id(conn, provider_transaction, tipo)
    descricao = str(provider_transaction.get("description") or "Transação bancária")[:255]
    data = transaction_date(provider_transaction.get("date"))
    account_name = str(account.get("name") or account.get("marketingName") or "conta")
    notas = f"Importado automaticamente da Pluggy — {account_name}"[:500]

    link = conn.execute(
        "SELECT transaction_id FROM pluggy_transaction_links WHERE provider_transaction_id = ?",
        (provider_transaction_id,),
    ).fetchone()
    local_transaction_id = link["transaction_id"] if link else None
    local_exists = (
        conn.execute("SELECT id FROM transactions WHERE id = ?", (local_transaction_id,)).fetchone()
        if local_transaction_id
        else None
    )

    if local_exists:
        conn.execute(
            """
            UPDATE transactions
            SET data = ?, descricao = ?, valor_centavos = ?, tipo = ?,
                category_id = ?, metodo_pagamento = ?, notas = ?,
                updated_at = datetime('now')
            WHERE id = ?
            """,
            (data, descricao, valor_centavos, tipo, category_id, "Open Finance", notas, local_transaction_id),
        )
        action = "atualizada"
    else:
        local_transaction_id = insert_and_get_id(
            conn,
            """
            INSERT INTO transactions
                (data, descricao, valor_centavos, tipo, category_id,
                 metodo_pagamento, recorrente, notas)
            VALUES (?, ?, ?, ?, ?, 'Open Finance', 0, ?)
            """,
            (data, descricao, valor_centavos, tipo, category_id, notas),
        )
        action = "importada"

    conn.execute(
        """
        INSERT INTO pluggy_transaction_links
            (provider_transaction_id, account_id, transaction_id, provider_id,
             provider_status, raw_category, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
        ON CONFLICT(provider_transaction_id) DO UPDATE SET
            account_id = excluded.account_id,
            transaction_id = excluded.transaction_id,
            provider_id = excluded.provider_id,
            provider_status = excluded.provider_status,
            raw_category = excluded.raw_category,
            updated_at = datetime('now')
        """,
        (
            provider_transaction_id,
            account_id,
            local_transaction_id,
            provider_transaction.get("providerId"),
            provider_transaction.get("status"),
            provider_transaction.get("category"),
        ),
    )
    return action


@router.post("/sync")
async def sync(
    payload: SyncRequest | None = Body(default=None),
    conn: sqlite3.Connection = Depends(get_db_dependency),
):
    """Copia transações efetivadas da Pluggy para o diário do FinPilot."""

    request = payload or SyncRequest()
    if request.item_id:
        connections = conn.execute(
            "SELECT item_id FROM pluggy_connections WHERE item_id = ?",
            (request.item_id,),
        ).fetchall()
    else:
        connections = conn.execute("SELECT item_id FROM pluggy_connections ORDER BY created_at").fetchall()
    if not connections:
        raise HTTPException(status_code=409, detail="Conecte um banco antes de sincronizar.")

    service = PluggyService()
    counters = {"importadas": 0, "atualizadas": 0, "ignoradas": 0}
    accounts_count = 0
    try:
        for connection in connections:
            item_id = connection["item_id"]
            item = await service.get_item(item_id)
            _save_connection(conn, item)
            remote_accounts = await service.fetch_accounts(item_id)
            accounts_count += len(remote_accounts)

            for account in remote_accounts:
                account_id = str(account.get("id") or "")
                if not account_id:
                    continue
                credit_data = account.get("creditData") if isinstance(account.get("creditData"), dict) else {}
                conn.execute(
                    """
                    INSERT INTO pluggy_accounts
                        (account_id, item_id, type, subtype, name, number_masked,
                         balance_centavos, currency_code, credit_limit_centavos, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                    ON CONFLICT(account_id) DO UPDATE SET
                        type = excluded.type,
                        subtype = excluded.subtype,
                        name = excluded.name,
                        number_masked = excluded.number_masked,
                        balance_centavos = excluded.balance_centavos,
                        currency_code = excluded.currency_code,
                        credit_limit_centavos = excluded.credit_limit_centavos,
                        updated_at = datetime('now')
                    """,
                    (
                        account_id,
                        item_id,
                        account.get("type"),
                        account.get("subtype"),
                        account.get("name") or account.get("marketingName") or "Conta bancária",
                        masked_account_number(account.get("number")),
                        signed_amount_to_centavos(account.get("balance")),
                        account.get("currencyCode") or "BRL",
                        amount_to_centavos(credit_data.get("creditLimit")) if credit_data else None,
                    ),
                )
                transactions = await service.fetch_transactions(
                    account_id,
                    date_from=default_sync_start(request.dias),
                )
                for transaction in transactions:
                    action = _upsert_imported_transaction(
                        conn,
                        account=account,
                        provider_transaction=transaction,
                    )
                    counters[f"{action}s"] += 1

            conn.execute(
                """
                UPDATE pluggy_connections
                SET status = ?, execution_status = ?, last_sync_at = datetime('now'),
                    updated_at = datetime('now')
                WHERE item_id = ?
                """,
                (item.get("status"), item.get("executionStatus"), item_id),
            )
            conn.commit()

        return {
            **counters,
            "contas": accounts_count,
            "conexoes": len(connections),
            "periodo_dias": request.dias,
        }
    except (PluggyConfigurationError, PluggyAPIError) as exc:
        conn.rollback()
        raise _http_error(exc) from exc
