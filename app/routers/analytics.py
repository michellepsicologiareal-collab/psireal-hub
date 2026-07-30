from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Query

from app.db import get_db_dependency
from app.models import RecurringItem, SpendingByCategoryItem, SummaryOut, TrendItem
from app.services.analytics import compute_spending_by_category, compute_summary, compute_trend
from app.services.dates import mes_atual
from app.services.recurring import detect_recurring

router = APIRouter(prefix="/api", tags=["analytics"])


@router.get("/summary", response_model=SummaryOut)
def summary(mes: str = Query(default=None, description="YYYY-MM"), conn: sqlite3.Connection = Depends(get_db_dependency)):
    mes = mes or mes_atual()
    return compute_summary(conn, mes)


@router.get("/spending-by-category", response_model=list[SpendingByCategoryItem])
def spending_by_category(mes: str = Query(default=None, description="YYYY-MM"), conn: sqlite3.Connection = Depends(get_db_dependency)):
    mes = mes or mes_atual()
    return compute_spending_by_category(conn, mes)


@router.get("/trend", response_model=list[TrendItem])
def trend(meses: int = Query(default=6, ge=1, le=36), conn: sqlite3.Connection = Depends(get_db_dependency)):
    return compute_trend(conn, meses)


@router.get("/recurring", response_model=list[RecurringItem])
def recurring(conn: sqlite3.Connection = Depends(get_db_dependency)):
    return detect_recurring(conn)
