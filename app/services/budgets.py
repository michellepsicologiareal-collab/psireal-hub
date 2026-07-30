"""Cálculo de status de orçamentos por categoria."""
from __future__ import annotations

import sqlite3

from app.services.dates import dias_no_mes, dias_restantes_no_mes, mes_bounds


def compute_budget_status(conn: sqlite3.Connection, mes: str) -> list[dict]:
    """Para cada orçamento aplicável ao mês (específico do mês OU recorrente sem
    orçamento específico que o sobrescreva), calcula gasto real, percentual,
    dias restantes e ritmo diário projetado.
    """
    inicio, fim = mes_bounds(mes)

    # Orçamentos específicos do mês têm prioridade sobre os recorrentes (mes IS NULL)
    # para a mesma categoria.
    orcamentos_mes = conn.execute(
        "SELECT id, category_id, limite_centavos FROM budgets WHERE mes = ?", (mes,)
    ).fetchall()
    categorias_com_orcamento_especifico = {r["category_id"] for r in orcamentos_mes}

    orcamentos_recorrentes = conn.execute(
        "SELECT id, category_id, limite_centavos FROM budgets WHERE mes IS NULL"
    ).fetchall()

    orcamentos_aplicaveis: dict[int, int] = {}
    for r in orcamentos_recorrentes:
        orcamentos_aplicaveis[r["category_id"]] = r["limite_centavos"]
    for r in orcamentos_mes:
        orcamentos_aplicaveis[r["category_id"]] = r["limite_centavos"]

    if not orcamentos_aplicaveis:
        return []

    total_dias = dias_no_mes(mes)
    dias_restantes = dias_restantes_no_mes(mes)
    dias_passados = max(total_dias - dias_restantes + 1, 1)

    resultado = []
    for category_id, limite_centavos in orcamentos_aplicaveis.items():
        cat_row = conn.execute(
            "SELECT nome, cor FROM categories WHERE id = ?", (category_id,)
        ).fetchone()
        if cat_row is None:
            continue

        gasto_row = conn.execute(
            """
            SELECT COALESCE(SUM(valor_centavos), 0) AS total
            FROM transactions
            WHERE (
                category_id = ?
                OR category_id IN (SELECT id FROM categories WHERE parent_id = ?)
            )
              AND tipo = 'despesa'
              AND data BETWEEN ? AND ?
            """,
            (category_id, category_id, inicio, fim),
        ).fetchone()
        gasto_centavos = gasto_row["total"]

        percentual = round((gasto_centavos / limite_centavos) * 100, 2) if limite_centavos > 0 else 0.0

        if percentual >= 100:
            estado = "estourado"
        elif percentual >= 80:
            estado = "atencao"
        else:
            estado = "normal"

        ritmo_diario = gasto_centavos / dias_passados
        ritmo_diario_projetado_centavos = ritmo_diario * total_dias

        resultado.append(
            {
                "category_id": category_id,
                "category_nome": cat_row["nome"],
                "category_cor": cat_row["cor"],
                "limite": limite_centavos / 100,
                "gasto": gasto_centavos / 100,
                "percentual": percentual,
                "dias_restantes": dias_restantes,
                "ritmo_diario_projetado": round(ritmo_diario_projetado_centavos / 100, 2),
                "estado": estado,
            }
        )

    resultado.sort(key=lambda x: x["percentual"], reverse=True)
    return resultado
