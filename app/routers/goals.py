from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from app.db import get_db_dependency, insert_and_get_id
from app.models import GoalCreate, GoalOut, GoalUpdate, reais_to_centavos

router = APIRouter(prefix="/api/goals", tags=["goals"])


def _row_to_out(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "nome": row["nome"],
        "valor_alvo": row["valor_alvo_centavos"] / 100,
        "valor_atual": row["valor_atual_centavos"] / 100,
        "prazo": row["prazo"],
        "created_at": row["created_at"],
    }


@router.get("", response_model=list[GoalOut])
def list_goals(conn: sqlite3.Connection = Depends(get_db_dependency)):
    rows = conn.execute("SELECT * FROM goals ORDER BY id ASC").fetchall()
    return [_row_to_out(r) for r in rows]


@router.post("", response_model=GoalOut, status_code=201)
def create_goal(payload: GoalCreate, conn: sqlite3.Connection = Depends(get_db_dependency)):
    goal_id = insert_and_get_id(
        conn,
        "INSERT INTO goals (nome, valor_alvo_centavos, valor_atual_centavos, prazo) VALUES (?, ?, ?, ?)",
        (
            payload.nome,
            reais_to_centavos(payload.valor_alvo),
            reais_to_centavos(payload.valor_atual),
            payload.prazo.isoformat() if payload.prazo else None,
        ),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM goals WHERE id = ?", (goal_id,)).fetchone()
    return _row_to_out(row)


@router.patch("/{goal_id}", response_model=GoalOut)
def update_goal(goal_id: int, payload: GoalUpdate, conn: sqlite3.Connection = Depends(get_db_dependency)):
    row = conn.execute("SELECT * FROM goals WHERE id = ?", (goal_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Meta não encontrada")

    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        return _row_to_out(row)

    campos = []
    valores = []
    for campo, valor in updates.items():
        if campo == "valor_alvo":
            campos.append("valor_alvo_centavos = ?")
            valores.append(reais_to_centavos(valor))
        elif campo == "valor_atual":
            campos.append("valor_atual_centavos = ?")
            valores.append(reais_to_centavos(valor))
        elif campo == "prazo":
            campos.append("prazo = ?")
            valores.append(valor.isoformat() if valor else None)
        else:
            campos.append(f"{campo} = ?")
            valores.append(valor)
    valores.append(goal_id)

    conn.execute(f"UPDATE goals SET {', '.join(campos)} WHERE id = ?", valores)
    conn.commit()
    row = conn.execute("SELECT * FROM goals WHERE id = ?", (goal_id,)).fetchone()
    return _row_to_out(row)


@router.delete("/{goal_id}", status_code=204)
def delete_goal(goal_id: int, conn: sqlite3.Connection = Depends(get_db_dependency)):
    row = conn.execute("SELECT * FROM goals WHERE id = ?", (goal_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Meta não encontrada")
    conn.execute("DELETE FROM goals WHERE id = ?", (goal_id,))
    conn.commit()
    return None
