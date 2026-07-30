from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends

from app.db import get_db_dependency
from app.models import SettingItem, SettingsUpdate
from app.security import get_current_user_id

router = APIRouter(prefix="/api/settings", tags=["settings"])


def _user_id() -> str:
    return get_current_user_id() or "local-user"


@router.get("", response_model=list[SettingItem])
def get_settings(conn: sqlite3.Connection = Depends(get_db_dependency)):
    rows = conn.execute(
        "SELECT chave, valor FROM user_settings WHERE user_id = ? ORDER BY chave ASC",
        (_user_id(),),
    ).fetchall()
    return [{"chave": r["chave"], "valor": r["valor"]} for r in rows]


@router.put("", response_model=list[SettingItem])
def put_settings(payload: SettingsUpdate, conn: sqlite3.Connection = Depends(get_db_dependency)):
    for chave, valor in payload.settings.items():
        conn.execute(
            """
            INSERT INTO user_settings (user_id, chave, valor) VALUES (?, ?, ?)
            ON CONFLICT(user_id, chave) DO UPDATE SET valor = excluded.valor
            """,
            (_user_id(), chave, valor),
        )
    conn.commit()
    rows = conn.execute(
        "SELECT chave, valor FROM user_settings WHERE user_id = ? ORDER BY chave ASC",
        (_user_id(),),
    ).fetchall()
    return [{"chave": r["chave"], "valor": r["valor"]} for r in rows]
