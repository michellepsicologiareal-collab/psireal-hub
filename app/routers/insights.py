from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Query

from app.db import get_db_dependency
from app.models import InsightsOut
from app.services.dates import mes_atual
from app.services.insights import generate_insights

router = APIRouter(prefix="/api", tags=["insights"])


@router.get("/insights", response_model=InsightsOut)
def insights(
    mes: str = Query(default=None, description="YYYY-MM, padrão: mês atual"),
    usar_ia: bool = Query(default=True, description="Enriquece os textos com a Anthropic quando configurada"),
    conn: sqlite3.Connection = Depends(get_db_dependency),
):
    return generate_insights(conn, mes or mes_atual(), usar_ia=usar_ia)
