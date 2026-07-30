from __future__ import annotations

import sqlite3
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.db import get_db_dependency, insert_and_get_id
from app.models import BudgetCreate, BudgetOut, BudgetStatusItem, BudgetUpdate, reais_to_centavos
from app.services.budgets import compute_budget_status
from app.services.dates import mes_atual

router = APIRouter(prefix="/api/budgets", tags=["budgets"])


def _row_to_out(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "category_id": row["category_id"],
        "mes": row["mes"],
        "limite": row["limite_centavos"] / 100,
    }


@router.get("", response_model=list[BudgetOut])
def list_budgets(conn: sqlite3.Connection = Depends(get_db_dependency)):
    rows = conn.execute("SELECT * FROM budgets ORDER BY id ASC").fetchall()
    return [_row_to_out(r) for r in rows]


@router.get("/status", response_model=list[BudgetStatusItem])
def budget_status(
    mes: str = Query(default=None, description="YYYY-MM, padrão: mês atual"),
    conn: sqlite3.Connection = Depends(get_db_dependency),
):
    mes = mes or mes_atual()
    return compute_budget_status(conn, mes)


@router.post("", response_model=BudgetOut, status_code=201)
def create_budget(payload: BudgetCreate, conn: sqlite3.Connection = Depends(get_db_dependency)):
    cat = conn.execute("SELECT id FROM categories WHERE id = ?", (payload.category_id,)).fetchone()
    if cat is None:
        raise HTTPException(status_code=422, detail="category_id não existe")

    budget_id = insert_and_get_id(
        conn,
        "INSERT INTO budgets (category_id, mes, limite_centavos) VALUES (?, ?, ?)",
        (payload.category_id, payload.mes, reais_to_centavos(payload.limite)),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM budgets WHERE id = ?", (budget_id,)).fetchone()
    return _row_to_out(row)


@router.patch("/{budget_id}", response_model=BudgetOut)
def update_budget(budget_id: int, payload: BudgetUpdate, conn: sqlite3.Connection = Depends(get_db_dependency)):
    row = conn.execute("SELECT * FROM budgets WHERE id = ?", (budget_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Orçamento não encontrado")

    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        return _row_to_out(row)

    if "category_id" in updates:
        cat = conn.execute("SELECT id FROM categories WHERE id = ?", (updates["category_id"],)).fetchone()
        if cat is None:
            raise HTTPException(status_code=422, detail="category_id não existe")

    campos = []
    valores = []
    for campo, valor in updates.items():
        if campo == "limite":
            campos.append("limite_centavos = ?")
            valores.append(reais_to_centavos(valor))
        else:
            campos.append(f"{campo} = ?")
            valores.append(valor)
    valores.append(budget_id)

    conn.execute(f"UPDATE budgets SET {', '.join(campos)} WHERE id = ?", valores)
    conn.commit()
    row = conn.execute("SELECT * FROM budgets WHERE id = ?", (budget_id,)).fetchone()
    return _row_to_out(row)


@router.delete("/{budget_id}", status_code=204)
def delete_budget(budget_id: int, conn: sqlite3.Connection = Depends(get_db_dependency)):
    row = conn.execute("SELECT * FROM budgets WHERE id = ?", (budget_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Orçamento não encontrado")
    conn.execute("DELETE FROM budgets WHERE id = ?", (budget_id,))
    conn.commit()
    return None
