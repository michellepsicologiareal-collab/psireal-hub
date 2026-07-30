from __future__ import annotations

import re
from collections import defaultdict
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query

from app.db import get_db_dependency
from app.services.card_import import CARD_PAYMENT_METHOD
from app.services.dates import mes_bounds

router = APIRouter(prefix="/api/cards", tags=["cards"])


def _month_label(month: str) -> str:
    names = ("jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez")
    year, number = map(int, month.split("-"))
    return f"{names[number - 1]}/{str(year)[2:]}"


def _previous_months(month: str, count: int = 6) -> list[str]:
    year, number = map(int, month.split("-"))
    output = []
    for offset in range(count - 1, -1, -1):
        absolute = year * 12 + number - 1 - offset
        output.append(f"{absolute // 12:04d}-{absolute % 12 + 1:02d}")
    return output


def _merchant_name(description: str) -> str:
    cleaned = re.sub(
        r"\s+(?:parc(?:ela)?\s*)?\d{1,2}\s*(?:/|de)\s*\d{1,2}\b",
        "",
        description,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
    return cleaned[:48] or description[:48]


def _installment(description: str) -> dict | None:
    match = re.search(
        r"(?:parc(?:ela)?\s*)?(\d{1,2})\s*(?:/|de)\s*(\d{1,2})",
        description,
        re.IGNORECASE,
    )
    if not match:
        return None
    current, total = map(int, match.groups())
    if current < 1 or total < current or total > 99:
        return None
    return {"atual": current, "total": total, "restantes": total - current}


@router.get("/summary")
def card_summary(
    mes: str = Query(default=None, description="YYYY-MM"),
    conn=Depends(get_db_dependency),
):
    month = mes or date.today().strftime("%Y-%m")
    try:
        start, end = mes_bounds(month)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="mes deve estar no formato YYYY-MM") from None

    rows = conn.execute(
        """
        SELECT t.*, c.nome AS category_nome, c.cor AS category_cor, c.icone AS category_icon
        FROM transactions t
        LEFT JOIN categories c ON c.id = t.category_id
        WHERE t.data BETWEEN ? AND ?
          AND (
            t.metodo_pagamento = ?
            OR t.notas LIKE 'Fatura importada:%'
          )
        ORDER BY t.data DESC, t.id DESC
        """,
        (start, end, CARD_PAYMENT_METHOD),
    ).fetchall()

    expenses = [row for row in rows if row["tipo"] == "despesa"]
    refunds = [row for row in rows if row["tipo"] == "receita"]
    total_expenses = sum(int(row["valor_centavos"]) for row in expenses)
    total_refunds = sum(int(row["valor_centavos"]) for row in refunds)

    category_groups: dict[str, dict] = {}
    merchant_groups: dict[str, int] = defaultdict(int)
    installments: list[dict] = []
    for row in expenses:
        category = row["category_nome"] or "Sem categoria"
        group = category_groups.setdefault(
            category,
            {
                "nome": category,
                "cor": row["category_cor"] or "#7D8B99",
                "icone": row["category_icon"] or "💳",
                "valor_centavos": 0,
                "quantidade": 0,
            },
        )
        group["valor_centavos"] += int(row["valor_centavos"])
        group["quantidade"] += 1
        merchant_groups[_merchant_name(row["descricao"])] += int(row["valor_centavos"])
        installment = _installment(row["descricao"])
        if installment:
            installments.append(
                {
                    "descricao": row["descricao"],
                    "valor": int(row["valor_centavos"]) / 100,
                    **installment,
                }
            )

    categories = sorted(category_groups.values(), key=lambda item: item["valor_centavos"], reverse=True)
    for item in categories:
        item["valor"] = item.pop("valor_centavos") / 100
        item["percentual"] = round(item["valor"] * 10000 / total_expenses, 1) if total_expenses else 0

    merchants = [
        {"nome": name, "valor": cents / 100}
        for name, cents in sorted(merchant_groups.items(), key=lambda item: item[1], reverse=True)[:8]
    ]

    history_months = _previous_months(month)
    history_start, _ = mes_bounds(history_months[0])
    _, history_end = mes_bounds(history_months[-1])
    history_rows = conn.execute(
        """
        SELECT data, valor_centavos, tipo
        FROM transactions
        WHERE data BETWEEN ? AND ?
          AND (metodo_pagamento = ? OR notas LIKE 'Fatura importada:%')
        """,
        (history_start, history_end, CARD_PAYMENT_METHOD),
    ).fetchall()
    history_values = {item: 0 for item in history_months}
    for row in history_rows:
        if row["tipo"] == "despesa":
            history_values[str(row["data"])[:7]] += int(row["valor_centavos"])
        else:
            history_values[str(row["data"])[:7]] -= int(row["valor_centavos"])

    recent = [
        {
            "id": row["id"],
            "data": row["data"],
            "descricao": row["descricao"],
            "valor": int(row["valor_centavos"]) / 100,
            "tipo": row["tipo"],
            "category_id": row["category_id"],
            "categoria": row["category_nome"],
        }
        for row in rows[:12]
    ]
    return {
        "mes": month,
        "total_compras": total_expenses / 100,
        "total_estornos": total_refunds / 100,
        "total_liquido": (total_expenses - total_refunds) / 100,
        "quantidade": len(rows),
        "ticket_medio": total_expenses / 100 / len(expenses) if expenses else 0,
        "maior_compra": max((int(row["valor_centavos"]) for row in expenses), default=0) / 100,
        "categorias": categories,
        "estabelecimentos": merchants,
        "parcelas": installments[:12],
        "historico": [
            {"mes": item, "rotulo": _month_label(item), "valor": history_values[item] / 100}
            for item in history_months
        ],
        "recentes": recent,
    }
