"""Helpers de data/mês compartilhados pelos services."""
from __future__ import annotations

import calendar
from datetime import date, datetime


def parse_mes(mes: str) -> tuple[int, int]:
    """Recebe 'YYYY-MM' e retorna (ano, mes)."""
    ano_str, mes_str = mes.split("-")
    return int(ano_str), int(mes_str)


def mes_bounds(mes: str) -> tuple[str, str]:
    """Retorna (primeiro_dia, ultimo_dia) do mês 'YYYY-MM' como strings 'YYYY-MM-DD'."""
    ano, m = parse_mes(mes)
    ultimo_dia = calendar.monthrange(ano, m)[1]
    primeiro = f"{ano:04d}-{m:02d}-01"
    ultimo = f"{ano:04d}-{m:02d}-{ultimo_dia:02d}"
    return primeiro, ultimo


def mes_anterior(mes: str) -> str:
    ano, m = parse_mes(mes)
    if m == 1:
        return f"{ano - 1:04d}-12"
    return f"{ano:04d}-{m - 1:02d}"


def somar_meses(mes: str, delta: int) -> str:
    """Soma (ou subtrai, se delta negativo) meses a 'YYYY-MM'."""
    ano, m = parse_mes(mes)
    total = (ano * 12 + (m - 1)) + delta
    novo_ano, novo_mes = divmod(total, 12)
    return f"{novo_ano:04d}-{novo_mes + 1:02d}"


def mes_atual() -> str:
    hoje = datetime.now().date()
    return f"{hoje.year:04d}-{hoje.month:02d}"


def dias_no_mes(mes: str) -> int:
    ano, m = parse_mes(mes)
    return calendar.monthrange(ano, m)[1]


def dias_restantes_no_mes(mes: str, referencia: date | None = None) -> int:
    """Dias restantes no mês (inclusive hoje), 0 se o mês já passou completamente."""
    ano, m = parse_mes(mes)
    total_dias = calendar.monthrange(ano, m)[1]
    hoje = referencia or datetime.now().date()
    if hoje.year == ano and hoje.month == m:
        return total_dias - hoje.day + 1
    primeiro = date(ano, m, 1)
    if hoje < primeiro:
        return total_dias
    return 0
