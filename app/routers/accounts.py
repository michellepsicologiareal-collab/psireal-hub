from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from app.db import get_db_dependency, insert_and_get_id
from app.models import FinancialAccountCreate, FinancialAccountOut, FinancialAccountUpdate, reais_to_centavos

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


def _row_to_out(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "account_type": row["account_type"],
        "nome": row["nome"],
        "instituicao": row["instituicao"],
        "valor": row["valor_centavos"] / 100,
        "limite": row["limite_centavos"] / 100 if row["limite_centavos"] is not None else None,
        "dia_fechamento": row["dia_fechamento"],
        "dia_vencimento": row["dia_vencimento"],
        "subtipo": row["subtipo"],
        "cor": row["cor"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


@router.get("", response_model=list[FinancialAccountOut])
def list_accounts(conn: sqlite3.Connection = Depends(get_db_dependency)):
    rows = conn.execute(
        """
        SELECT *
        FROM financial_accounts
        ORDER BY
            CASE account_type WHEN 'bank' THEN 1 WHEN 'credit_card' THEN 2 ELSE 3 END,
            nome ASC
        """
    ).fetchall()
    return [_row_to_out(row) for row in rows]


@router.post("", response_model=FinancialAccountOut, status_code=201)
def create_account(payload: FinancialAccountCreate, conn: sqlite3.Connection = Depends(get_db_dependency)):
    account_id = insert_and_get_id(
        conn,
        """
        INSERT INTO financial_accounts (
            account_type, nome, instituicao, valor_centavos, limite_centavos,
            dia_fechamento, dia_vencimento, subtipo, cor
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            payload.account_type,
            payload.nome,
            payload.instituicao,
            reais_to_centavos(payload.valor),
            reais_to_centavos(payload.limite) if payload.limite is not None else None,
            payload.dia_fechamento,
            payload.dia_vencimento,
            payload.subtipo,
            payload.cor,
        ),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM financial_accounts WHERE id = ?", (account_id,)).fetchone()
    return _row_to_out(row)


@router.patch("/{account_id}", response_model=FinancialAccountOut)
def update_account(
    account_id: int,
    payload: FinancialAccountUpdate,
    conn: sqlite3.Connection = Depends(get_db_dependency),
):
    row = conn.execute("SELECT * FROM financial_accounts WHERE id = ?", (account_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Conta não encontrada")

    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        return _row_to_out(row)

    fields: list[str] = []
    values: list[object] = []
    for field, value in updates.items():
        if field == "valor":
            fields.append("valor_centavos = ?")
            values.append(reais_to_centavos(value))
        elif field == "limite":
            fields.append("limite_centavos = ?")
            values.append(reais_to_centavos(value) if value is not None else None)
        else:
            fields.append(f"{field} = ?")
            values.append(value)
    fields.append("updated_at = datetime('now')")
    values.append(account_id)

    conn.execute(f"UPDATE financial_accounts SET {', '.join(fields)} WHERE id = ?", values)
    conn.commit()
    row = conn.execute("SELECT * FROM financial_accounts WHERE id = ?", (account_id,)).fetchone()
    return _row_to_out(row)


@router.delete("/{account_id}", status_code=204)
def delete_account(account_id: int, conn: sqlite3.Connection = Depends(get_db_dependency)):
    row = conn.execute("SELECT id FROM financial_accounts WHERE id = ?", (account_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Conta não encontrada")
    conn.execute("DELETE FROM financial_accounts WHERE id = ?", (account_id,))
    conn.commit()
    return None
