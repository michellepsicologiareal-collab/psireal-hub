from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from app.db import get_db_dependency, insert_and_get_id
from app.models import CategoryCreate, CategoryOut, CategoryUpdate

router = APIRouter(prefix="/api/categories", tags=["categories"])


def _row_to_out(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "nome": row["nome"],
        "tipo": row["tipo"],
        "cor": row["cor"],
        "icone": row["icone"],
        "essencial": bool(row["essencial"]),
        "parent_id": row["parent_id"],
        "created_at": row["created_at"],
    }


@router.get("", response_model=list[CategoryOut])
def list_categories(conn: sqlite3.Connection = Depends(get_db_dependency)):
    rows = conn.execute("SELECT * FROM categories ORDER BY nome ASC").fetchall()
    return [_row_to_out(r) for r in rows]


@router.post("", response_model=CategoryOut, status_code=201)
def create_category(payload: CategoryCreate, conn: sqlite3.Connection = Depends(get_db_dependency)):
    if payload.parent_id is not None:
        parent = conn.execute(
            "SELECT id, parent_id, tipo FROM categories WHERE id = ?",
            (payload.parent_id,),
        ).fetchone()
        if parent is None or parent["parent_id"] is not None:
            raise HTTPException(status_code=422, detail="Categoria principal inválida.")
        if parent["tipo"] != payload.tipo:
            raise HTTPException(status_code=422, detail="A subcategoria deve ter o mesmo tipo da categoria principal.")
    category_id = insert_and_get_id(
        conn,
        "INSERT INTO categories (parent_id, nome, tipo, cor, icone, essencial) VALUES (?, ?, ?, ?, ?, ?)",
        (payload.parent_id, payload.nome, payload.tipo, payload.cor, payload.icone, int(payload.essencial)),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM categories WHERE id = ?", (category_id,)).fetchone()
    return _row_to_out(row)


@router.patch("/{category_id}", response_model=CategoryOut)
def update_category(category_id: int, payload: CategoryUpdate, conn: sqlite3.Connection = Depends(get_db_dependency)):
    row = conn.execute("SELECT * FROM categories WHERE id = ?", (category_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")

    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        return _row_to_out(row)

    if "parent_id" in updates and updates["parent_id"] == category_id:
        raise HTTPException(status_code=422, detail="Uma categoria não pode ser filha dela mesma.")
    if "parent_id" in updates and updates["parent_id"] is not None:
        parent = conn.execute(
            "SELECT id, parent_id, tipo FROM categories WHERE id = ?",
            (updates["parent_id"],),
        ).fetchone()
        if parent is None or parent["parent_id"] is not None:
            raise HTTPException(status_code=422, detail="Categoria principal inválida.")
        next_type = updates.get("tipo", row["tipo"])
        if parent["tipo"] != next_type:
            raise HTTPException(status_code=422, detail="A subcategoria deve ter o mesmo tipo da categoria principal.")

    campos = []
    valores = []
    for campo, valor in updates.items():
        if campo == "essencial":
            valor = int(valor)
        campos.append(f"{campo} = ?")
        valores.append(valor)
    valores.append(category_id)

    conn.execute(f"UPDATE categories SET {', '.join(campos)} WHERE id = ?", valores)
    conn.commit()
    row = conn.execute("SELECT * FROM categories WHERE id = ?", (category_id,)).fetchone()
    return _row_to_out(row)


@router.delete("/{category_id}", status_code=204)
def delete_category(category_id: int, conn: sqlite3.Connection = Depends(get_db_dependency)):
    row = conn.execute("SELECT * FROM categories WHERE id = ?", (category_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")

    count = conn.execute(
        """
        SELECT COUNT(*) AS total
        FROM transactions
        WHERE category_id = ?
           OR category_id IN (SELECT id FROM categories WHERE parent_id = ?)
        """,
        (category_id, category_id),
    ).fetchone()["total"]
    if count > 0:
        raise HTTPException(
            status_code=409,
            detail=f"Não é possível excluir a categoria: existem {count} transação(ões) vinculada(s) a ela.",
        )

    conn.execute(
        "DELETE FROM budgets WHERE category_id = ? OR category_id IN (SELECT id FROM categories WHERE parent_id = ?)",
        (category_id, category_id),
    )
    conn.execute("DELETE FROM categories WHERE id = ?", (category_id,))
    conn.commit()
    return None
