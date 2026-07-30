from __future__ import annotations

import sqlite3
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.db import get_db_dependency, insert_and_get_id
from app.models import (
    TransactionCreate,
    TransactionListOut,
    TransactionOut,
    TransactionUpdate,
    reais_to_centavos,
)
from app.services.dates import mes_bounds

router = APIRouter(prefix="/api/transactions", tags=["transactions"])

ORDENS_VALIDAS = {
    "data_desc": "data DESC, id DESC",
    "data_asc": "data ASC, id ASC",
    "valor_desc": "valor_centavos DESC",
    "valor_asc": "valor_centavos ASC",
}


def _row_to_out(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "data": row["data"],
        "descricao": row["descricao"],
        "valor": row["valor_centavos"] / 100,
        "tipo": row["tipo"],
        "category_id": row["category_id"],
        "metodo_pagamento": row["metodo_pagamento"],
        "recorrente": bool(row["recorrente"]),
        "notas": row["notas"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


@router.get("", response_model=TransactionListOut)
def list_transactions(
    mes: Optional[str] = Query(default=None, description="YYYY-MM"),
    de: Optional[date] = None,
    ate: Optional[date] = None,
    category_id: Optional[int] = None,
    tipo: Optional[str] = None,
    busca: Optional[str] = None,
    ordem: str = Query(default="data_desc"),
    limit: int = Query(default=20, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    conn: sqlite3.Connection = Depends(get_db_dependency),
):
    if ordem not in ORDENS_VALIDAS:
        raise HTTPException(status_code=400, detail=f"ordem inválida. Use uma de: {', '.join(ORDENS_VALIDAS)}")
    if tipo is not None and tipo not in ("despesa", "receita"):
        raise HTTPException(status_code=400, detail="tipo deve ser 'despesa' ou 'receita'")

    where = []
    params: list = []

    if mes is not None:
        try:
            inicio, fim = mes_bounds(mes)
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="mes deve estar no formato YYYY-MM") from None
        where.append("data BETWEEN ? AND ?")
        params.extend([inicio, fim])
    if de is not None:
        where.append("data >= ?")
        params.append(de.isoformat())
    if ate is not None:
        where.append("data <= ?")
        params.append(ate.isoformat())
    if category_id is not None:
        where.append("category_id = ?")
        params.append(category_id)
    if tipo is not None:
        where.append("tipo = ?")
        params.append(tipo)
    if busca:
        where.append("(descricao LIKE ? OR notas LIKE ?)")
        termo = f"%{busca}%"
        params.extend([termo, termo])

    where_sql = f"WHERE {' AND '.join(where)}" if where else ""

    total = conn.execute(f"SELECT COUNT(*) AS total FROM transactions {where_sql}", params).fetchone()["total"]

    rows = conn.execute(
        f"SELECT * FROM transactions {where_sql} ORDER BY {ORDENS_VALIDAS[ordem]} LIMIT ? OFFSET ?",
        [*params, limit, offset],
    ).fetchall()

    return {
        "items": [_row_to_out(r) for r in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.post("", response_model=TransactionOut, status_code=201)
def create_transaction(payload: TransactionCreate, conn: sqlite3.Connection = Depends(get_db_dependency)):
    if payload.category_id is not None:
        cat = conn.execute("SELECT id FROM categories WHERE id = ?", (payload.category_id,)).fetchone()
        if cat is None:
            raise HTTPException(status_code=422, detail="category_id não existe")

    valor_centavos = reais_to_centavos(payload.valor)
    transaction_id = insert_and_get_id(
        conn,
        """
        INSERT INTO transactions (data, descricao, valor_centavos, tipo, category_id, metodo_pagamento, recorrente, notas)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            payload.data.isoformat(),
            payload.descricao,
            valor_centavos,
            payload.tipo,
            payload.category_id,
            payload.metodo_pagamento,
            int(payload.recorrente),
            payload.notas,
        ),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM transactions WHERE id = ?", (transaction_id,)).fetchone()
    return _row_to_out(row)


@router.patch("/{transaction_id}", response_model=TransactionOut)
def update_transaction(transaction_id: int, payload: TransactionUpdate, conn: sqlite3.Connection = Depends(get_db_dependency)):
    row = conn.execute("SELECT * FROM transactions WHERE id = ?", (transaction_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Transação não encontrada")

    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        return _row_to_out(row)

    if "category_id" in updates and updates["category_id"] is not None:
        cat = conn.execute("SELECT id FROM categories WHERE id = ?", (updates["category_id"],)).fetchone()
        if cat is None:
            raise HTTPException(status_code=422, detail="category_id não existe")

    campos = []
    valores = []
    for campo, valor in updates.items():
        if campo == "valor":
            campos.append("valor_centavos = ?")
            valores.append(reais_to_centavos(valor))
        elif campo == "data":
            campos.append("data = ?")
            valores.append(valor.isoformat())
        elif campo == "recorrente":
            campos.append("recorrente = ?")
            valores.append(int(valor))
        else:
            campos.append(f"{campo} = ?")
            valores.append(valor)

    campos.append("updated_at = datetime('now')")
    valores.append(transaction_id)

    conn.execute(f"UPDATE transactions SET {', '.join(campos)} WHERE id = ?", valores)
    conn.commit()
    row = conn.execute("SELECT * FROM transactions WHERE id = ?", (transaction_id,)).fetchone()
    return _row_to_out(row)


@router.delete("/{transaction_id}", status_code=204)
def delete_transaction(transaction_id: int, conn: sqlite3.Connection = Depends(get_db_dependency)):
    row = conn.execute("SELECT * FROM transactions WHERE id = ?", (transaction_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Transação não encontrada")
    conn.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
    conn.commit()
    return None
