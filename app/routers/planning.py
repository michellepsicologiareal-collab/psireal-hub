from __future__ import annotations

import calendar
import sqlite3
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.db import get_db_dependency, insert_and_get_id
from app.models import (
    PurchasePlanCreate,
    PurchasePlanOut,
    PurchasePlanUpdate,
    ScheduledExpenseCreate,
    ScheduledExpenseOut,
    ScheduledExpenseUpdate,
    reais_to_centavos,
)
from app.services.dates import mes_bounds

router = APIRouter(tags=["planning"])


class ScheduledExpensePay(BaseModel):
    data_pagamento: date = date.today()
    metodo_pagamento: str = "outro"


def _purchase_to_out(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "nome": row["nome"],
        "valor_estimado": row["valor_estimado_centavos"] / 100,
        "prioridade": row["prioridade"],
        "data_desejada": row["data_desejada"],
        "notas": row["notas"],
        "status": row["status"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _scheduled_to_out(row: sqlite3.Row, month_start: Optional[str] = None) -> dict:
    due = date.fromisoformat(row["data_vencimento"])
    return {
        "id": row["id"],
        "titulo": row["titulo"],
        "valor": row["valor_centavos"] / 100,
        "category_id": row["category_id"],
        "data_vencimento": row["data_vencimento"],
        "recorrencia": row["recorrencia"],
        "notas": row["notas"],
        "ativo": bool(row["ativo"]),
        "atrasado": bool(row["ativo"]) and due < date.today(),
        "levado_de_outro_mes": bool(month_start and row["data_vencimento"] < month_start),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _next_month(value: date) -> date:
    year = value.year + (1 if value.month == 12 else 0)
    month = 1 if value.month == 12 else value.month + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


@router.get("/api/purchase-plans", response_model=list[PurchasePlanOut])
def list_purchase_plans(conn: sqlite3.Connection = Depends(get_db_dependency)):
    rows = conn.execute(
        """
        SELECT * FROM purchase_plans
        ORDER BY status ASC,
                 CASE prioridade WHEN 'alta' THEN 1 WHEN 'media' THEN 2 ELSE 3 END,
                 COALESCE(data_desejada, '9999-12-31') ASC,
                 id DESC
        """
    ).fetchall()
    return [_purchase_to_out(row) for row in rows]


@router.post("/api/purchase-plans", response_model=PurchasePlanOut, status_code=201)
def create_purchase_plan(payload: PurchasePlanCreate, conn: sqlite3.Connection = Depends(get_db_dependency)):
    plan_id = insert_and_get_id(
        conn,
        """
        INSERT INTO purchase_plans (nome, valor_estimado_centavos, prioridade, data_desejada, notas)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            payload.nome,
            reais_to_centavos(payload.valor_estimado),
            payload.prioridade,
            payload.data_desejada.isoformat() if payload.data_desejada else None,
            payload.notas,
        ),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM purchase_plans WHERE id = ?", (plan_id,)).fetchone()
    return _purchase_to_out(row)


@router.patch("/api/purchase-plans/{plan_id}", response_model=PurchasePlanOut)
def update_purchase_plan(
    plan_id: int,
    payload: PurchasePlanUpdate,
    conn: sqlite3.Connection = Depends(get_db_dependency),
):
    row = conn.execute("SELECT * FROM purchase_plans WHERE id = ?", (plan_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Compra futura não encontrada")
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        return _purchase_to_out(row)

    fields: list[str] = []
    values: list[object] = []
    for field, value in updates.items():
        if field == "valor_estimado":
            fields.append("valor_estimado_centavos = ?")
            values.append(reais_to_centavos(value))
        elif field == "data_desejada":
            fields.append("data_desejada = ?")
            values.append(value.isoformat() if value else None)
        else:
            fields.append(f"{field} = ?")
            values.append(value)
    fields.append("updated_at = datetime('now')")
    values.append(plan_id)
    conn.execute(f"UPDATE purchase_plans SET {', '.join(fields)} WHERE id = ?", values)
    conn.commit()
    row = conn.execute("SELECT * FROM purchase_plans WHERE id = ?", (plan_id,)).fetchone()
    return _purchase_to_out(row)


@router.delete("/api/purchase-plans/{plan_id}", status_code=204)
def delete_purchase_plan(plan_id: int, conn: sqlite3.Connection = Depends(get_db_dependency)):
    row = conn.execute("SELECT id FROM purchase_plans WHERE id = ?", (plan_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Compra futura não encontrada")
    conn.execute("DELETE FROM purchase_plans WHERE id = ?", (plan_id,))
    conn.commit()
    return None


@router.get("/api/scheduled-expenses", response_model=list[ScheduledExpenseOut])
def list_scheduled_expenses(
    mes: Optional[str] = Query(default=None, description="YYYY-MM"),
    conn: sqlite3.Connection = Depends(get_db_dependency),
):
    month_start: Optional[str] = None
    if mes:
        try:
            month_start, month_end = mes_bounds(mes)
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="mes deve estar no formato YYYY-MM") from None
        rows = conn.execute(
            """
            SELECT * FROM scheduled_expenses
            WHERE ativo = 1 AND data_vencimento <= ?
            ORDER BY data_vencimento ASC, id ASC
            """,
            (month_end,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM scheduled_expenses ORDER BY ativo DESC, data_vencimento ASC, id ASC"
        ).fetchall()
    return [_scheduled_to_out(row, month_start) for row in rows]


@router.post("/api/scheduled-expenses", response_model=ScheduledExpenseOut, status_code=201)
def create_scheduled_expense(
    payload: ScheduledExpenseCreate,
    conn: sqlite3.Connection = Depends(get_db_dependency),
):
    if payload.category_id is not None:
        category = conn.execute("SELECT id FROM categories WHERE id = ?", (payload.category_id,)).fetchone()
        if category is None:
            raise HTTPException(status_code=422, detail="category_id não existe")
    expense_id = insert_and_get_id(
        conn,
        """
        INSERT INTO scheduled_expenses (
            titulo, valor_centavos, category_id, data_vencimento, recorrencia, notas
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            payload.titulo,
            reais_to_centavos(payload.valor),
            payload.category_id,
            payload.data_vencimento.isoformat(),
            payload.recorrencia,
            payload.notas,
        ),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM scheduled_expenses WHERE id = ?", (expense_id,)).fetchone()
    return _scheduled_to_out(row)


@router.patch("/api/scheduled-expenses/{expense_id}", response_model=ScheduledExpenseOut)
def update_scheduled_expense(
    expense_id: int,
    payload: ScheduledExpenseUpdate,
    conn: sqlite3.Connection = Depends(get_db_dependency),
):
    row = conn.execute("SELECT * FROM scheduled_expenses WHERE id = ?", (expense_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Despesa prevista não encontrada")
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        return _scheduled_to_out(row)

    if "category_id" in updates and updates["category_id"] is not None:
        category = conn.execute("SELECT id FROM categories WHERE id = ?", (updates["category_id"],)).fetchone()
        if category is None:
            raise HTTPException(status_code=422, detail="category_id não existe")

    fields: list[str] = []
    values: list[object] = []
    for field, value in updates.items():
        if field == "valor":
            fields.append("valor_centavos = ?")
            values.append(reais_to_centavos(value))
        elif field == "data_vencimento":
            fields.append("data_vencimento = ?")
            values.append(value.isoformat())
        elif field == "ativo":
            fields.append("ativo = ?")
            values.append(int(value))
        else:
            fields.append(f"{field} = ?")
            values.append(value)
    fields.append("updated_at = datetime('now')")
    values.append(expense_id)
    conn.execute(f"UPDATE scheduled_expenses SET {', '.join(fields)} WHERE id = ?", values)
    conn.commit()
    row = conn.execute("SELECT * FROM scheduled_expenses WHERE id = ?", (expense_id,)).fetchone()
    return _scheduled_to_out(row)


@router.post("/api/scheduled-expenses/{expense_id}/pay", response_model=ScheduledExpenseOut)
def pay_scheduled_expense(
    expense_id: int,
    payload: ScheduledExpensePay,
    conn: sqlite3.Connection = Depends(get_db_dependency),
):
    row = conn.execute("SELECT * FROM scheduled_expenses WHERE id = ?", (expense_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Despesa prevista não encontrada")
    if not bool(row["ativo"]):
        raise HTTPException(status_code=409, detail="Essa despesa prevista já foi concluída")

    insert_and_get_id(
        conn,
        """
        INSERT INTO transactions (
            data, descricao, valor_centavos, tipo, category_id,
            metodo_pagamento, recorrente, notas
        )
        VALUES (?, ?, ?, 'despesa', ?, ?, ?, ?)
        """,
        (
            payload.data_pagamento.isoformat(),
            row["titulo"],
            row["valor_centavos"],
            row["category_id"],
            payload.metodo_pagamento,
            int(row["recorrencia"] == "mensal"),
            row["notas"],
        ),
    )

    if row["recorrencia"] == "mensal":
        next_due = _next_month(date.fromisoformat(row["data_vencimento"]))
        while next_due <= payload.data_pagamento:
            next_due = _next_month(next_due)
        conn.execute(
            """
            UPDATE scheduled_expenses
            SET data_vencimento = ?, updated_at = datetime('now')
            WHERE id = ?
            """,
            (next_due.isoformat(), expense_id),
        )
    else:
        conn.execute(
            "UPDATE scheduled_expenses SET ativo = 0, updated_at = datetime('now') WHERE id = ?",
            (expense_id,),
        )
    conn.commit()
    row = conn.execute("SELECT * FROM scheduled_expenses WHERE id = ?", (expense_id,)).fetchone()
    return _scheduled_to_out(row)


@router.delete("/api/scheduled-expenses/{expense_id}", status_code=204)
def delete_scheduled_expense(expense_id: int, conn: sqlite3.Connection = Depends(get_db_dependency)):
    row = conn.execute("SELECT id FROM scheduled_expenses WHERE id = ?", (expense_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Despesa prevista não encontrada")
    conn.execute("DELETE FROM scheduled_expenses WHERE id = ?", (expense_id,))
    conn.commit()
    return None
