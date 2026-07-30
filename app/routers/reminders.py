from __future__ import annotations

import sqlite3
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query

from app.db import get_db_dependency, insert_and_get_id
from app.models import (
    ReminderCreate,
    ReminderOut,
    ReminderUpdate,
    centavos_to_reais,
    reais_to_centavos,
)

router = APIRouter(prefix="/api/reminders", tags=["reminders"])


def _row_to_out(row: sqlite3.Row) -> dict:
    value = row["valor_centavos"]
    return {
        "id": row["id"],
        "titulo": row["titulo"],
        "data_vencimento": row["data_vencimento"],
        "valor": centavos_to_reais(value) if value is not None else None,
        "recorrente": bool(row["recorrente"]),
        "concluido": bool(row["concluido"]),
        "notas": row["notas"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


@router.get("", response_model=list[ReminderOut])
def list_reminders(
    mes: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    incluir_concluidos: bool = True,
    conn: sqlite3.Connection = Depends(get_db_dependency),
):
    conditions: list[str] = []
    values: list[object] = []
    if mes:
        conditions.append("substr(data_vencimento, 1, 7) = ?")
        values.append(mes)
    if not incluir_concluidos:
        conditions.append("concluido = 0")
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    rows = conn.execute(
        f"""
        SELECT * FROM reminders
        {where}
        ORDER BY concluido ASC, data_vencimento ASC, id DESC
        """,
        values,
    ).fetchall()
    return [_row_to_out(row) for row in rows]


@router.post("", response_model=ReminderOut, status_code=201)
def create_reminder(
    payload: ReminderCreate,
    conn: sqlite3.Connection = Depends(get_db_dependency),
):
    reminder_id = insert_and_get_id(
        conn,
        """
        INSERT INTO reminders
            (titulo, data_vencimento, valor_centavos, recorrente, concluido, notas)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            payload.titulo.strip(),
            payload.data_vencimento.isoformat(),
            reais_to_centavos(payload.valor) if payload.valor is not None else None,
            int(payload.recorrente),
            int(payload.concluido),
            payload.notas,
        ),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM reminders WHERE id = ?", (reminder_id,)).fetchone()
    return _row_to_out(row)


@router.patch("/{reminder_id}", response_model=ReminderOut)
def update_reminder(
    reminder_id: int,
    payload: ReminderUpdate,
    conn: sqlite3.Connection = Depends(get_db_dependency),
):
    row = conn.execute("SELECT * FROM reminders WHERE id = ?", (reminder_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Lembrete não encontrado.")

    updates = payload.model_dump(exclude_unset=True)
    field_map = {
        "titulo": "titulo",
        "data_vencimento": "data_vencimento",
        "valor": "valor_centavos",
        "recorrente": "recorrente",
        "concluido": "concluido",
        "notas": "notas",
    }
    fields: list[str] = []
    values: list[object] = []
    for name, value in updates.items():
        fields.append(f"{field_map[name]} = ?")
        if name == "data_vencimento" and isinstance(value, date):
            value = value.isoformat()
        elif name == "valor":
            value = reais_to_centavos(value) if value is not None else None
        elif name in {"recorrente", "concluido"}:
            value = int(value)
        elif name == "titulo" and isinstance(value, str):
            value = value.strip()
        values.append(value)

    if fields:
        fields.append("updated_at = datetime('now')")
        values.append(reminder_id)
        conn.execute(
            f"UPDATE reminders SET {', '.join(fields)} WHERE id = ?",
            values,
        )
        conn.commit()

    row = conn.execute("SELECT * FROM reminders WHERE id = ?", (reminder_id,)).fetchone()
    return _row_to_out(row)


@router.delete("/{reminder_id}", status_code=204)
def delete_reminder(
    reminder_id: int,
    conn: sqlite3.Connection = Depends(get_db_dependency),
):
    row = conn.execute("SELECT id FROM reminders WHERE id = ?", (reminder_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Lembrete não encontrado.")
    conn.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
    conn.commit()
    return None
