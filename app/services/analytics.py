"""Cálculos de summary, spending-by-category e trend."""
from __future__ import annotations

import sqlite3

from app.services.dates import mes_anterior, mes_bounds, somar_meses


def _totais_do_mes(conn: sqlite3.Connection, mes: str) -> tuple[int, int]:
    """Retorna (total_receita_centavos, total_despesa_centavos) do mês."""
    inicio, fim = mes_bounds(mes)
    row = conn.execute(
        """
        SELECT
            COALESCE(SUM(CASE WHEN tipo = 'receita' THEN valor_centavos ELSE 0 END), 0) AS receita,
            COALESCE(SUM(CASE WHEN tipo = 'despesa' THEN valor_centavos ELSE 0 END), 0) AS despesa
        FROM transactions
        WHERE data BETWEEN ? AND ?
        """,
        (inicio, fim),
    ).fetchone()
    return row["receita"], row["despesa"]


def _variacao_pct(atual: float, anterior: float) -> float | None:
    if anterior == 0:
        return None
    return round(((atual - anterior) / abs(anterior)) * 100, 2)


def compute_summary(conn: sqlite3.Connection, mes: str) -> dict:
    receita_c, despesa_c = _totais_do_mes(conn, mes)
    saldo_c = receita_c - despesa_c

    mes_ant = mes_anterior(mes)
    receita_ant_c, despesa_ant_c = _totais_do_mes(conn, mes_ant)
    saldo_ant_c = receita_ant_c - despesa_ant_c

    taxa_poupanca = round((saldo_c / receita_c) * 100, 2) if receita_c > 0 else 0.0

    return {
        "mes": mes,
        "saldo": saldo_c / 100,
        "total_receita": receita_c / 100,
        "total_despesa": despesa_c / 100,
        "taxa_poupanca": taxa_poupanca,
        "variacao_saldo_pct": _variacao_pct(saldo_c, saldo_ant_c),
        "variacao_receita_pct": _variacao_pct(receita_c, receita_ant_c),
        "variacao_despesa_pct": _variacao_pct(despesa_c, despesa_ant_c),
    }


def compute_spending_by_category(conn: sqlite3.Connection, mes: str) -> list[dict]:
    inicio, fim = mes_bounds(mes)
    rows = conn.execute(
        """
        SELECT
            COALESCE(p.id, c.id) AS category_id,
            COALESCE(p.nome, c.nome) AS category_nome,
            COALESCE(p.cor, c.cor) AS cor,
            COALESCE(SUM(t.valor_centavos), 0) AS total_centavos
        FROM transactions t
        JOIN categories c ON c.id = t.category_id
        LEFT JOIN categories p ON p.id = c.parent_id
        WHERE t.tipo = 'despesa' AND t.data BETWEEN ? AND ?
        GROUP BY
            COALESCE(p.id, c.id),
            COALESCE(p.nome, c.nome),
            COALESCE(p.cor, c.cor)
        ORDER BY total_centavos DESC
        """,
        (inicio, fim),
    ).fetchall()

    total_geral = sum(r["total_centavos"] for r in rows)

    resultado = []
    for r in rows:
        pct = round((r["total_centavos"] / total_geral) * 100, 2) if total_geral > 0 else 0.0
        resultado.append(
            {
                "category_id": r["category_id"],
                "category_nome": r["category_nome"],
                "cor": r["cor"],
                "valor": r["total_centavos"] / 100,
                "percentual": pct,
            }
        )
    return resultado


def compute_trend(conn: sqlite3.Connection, meses: int) -> list[dict]:
    from app.services.dates import mes_atual

    atual = mes_atual()
    lista_meses = [somar_meses(atual, -i) for i in range(meses - 1, -1, -1)]

    resultado = []
    for mes in lista_meses:
        receita_c, despesa_c = _totais_do_mes(conn, mes)
        resultado.append(
            {
                "mes": mes,
                "receita": receita_c / 100,
                "despesa": despesa_c / 100,
                "saldo": (receita_c - despesa_c) / 100,
            }
        )
    return resultado
