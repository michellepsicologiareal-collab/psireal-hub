from __future__ import annotations

import sqlite3
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query

from app.db import get_db_dependency
from app.models import (
    ConsciousReflectionCreate,
    ConsciousReflectionOut,
    ConsciousWeeklyCheckinCreate,
    ConsciousWeeklyCheckinOut,
)
from app.services.conscious import (
    build_prompts,
    build_weekly_summary,
    list_reflections,
    options,
    save_reflection,
    save_weekly_checkin,
)
from app.services.dates import mes_atual

router = APIRouter(prefix="/api/conscious", tags=["conscious"])


@router.get("/options")
def conscious_options():
    return options()


@router.post("/reflections", response_model=ConsciousReflectionOut)
def upsert_reflection(
    payload: ConsciousReflectionCreate,
    conn: sqlite3.Connection = Depends(get_db_dependency),
):
    try:
        return save_reflection(conn, payload)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/reflections")
def reflections(
    mes: str | None = Query(default=None, description="YYYY-MM"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    conn: sqlite3.Connection = Depends(get_db_dependency),
):
    try:
        return list_reflections(conn, mes=mes, limit=limit, offset=offset)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/prompts")
def prompts(
    mes: str | None = Query(default=None, description="YYYY-MM, padrão: mês atual"),
    conn: sqlite3.Connection = Depends(get_db_dependency),
):
    try:
        items = build_prompts(conn, mes or mes_atual())
        return {"items": items, "total": len(items)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/weekly-checkins", response_model=ConsciousWeeklyCheckinOut)
def weekly_checkin(
    payload: ConsciousWeeklyCheckinCreate,
    conn: sqlite3.Connection = Depends(get_db_dependency),
):
    return save_weekly_checkin(conn, payload)


@router.get("/weekly")
def weekly_summary(
    semana: date | None = Query(default=None, description="Qualquer data da semana"),
    usar_ia: bool = Query(default=False, description="Personaliza textos usando somente dados agregados"),
    conn: sqlite3.Connection = Depends(get_db_dependency),
):
    return build_weekly_summary(conn, semana or date.today(), use_ai=usar_ia)
