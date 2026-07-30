"""Detecção determinística de gastos recorrentes/assinaturas.

Regra: mesma descrição normalizada (ou valor muito próximo, tolerância de 5%)
aparecendo em 3+ meses consecutivos é considerada recorrente.
"""
from __future__ import annotations

import re
import sqlite3
import unicodedata
from collections import defaultdict
from datetime import datetime

from app.services.dates import somar_meses

TOLERANCIA_VALOR = 0.05  # 5%


def normalizar_descricao(descricao: str) -> str:
    """Remove acentos, baixa para minúsculas, remove números/pontuação supérflua
    e espaços múltiplos, para agrupar descrições equivalentes."""
    texto = unicodedata.normalize("NFKD", descricao)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = texto.lower().strip()
    texto = re.sub(r"[^a-z0-9\s]", " ", texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


def _mes_da_data(data_str: str) -> str:
    return data_str[:7]  # 'YYYY-MM-DD' -> 'YYYY-MM'


def _meses_consecutivos(meses_ordenados: list[str]) -> list[list[str]]:
    """Agrupa uma lista ordenada de meses ('YYYY-MM') em blocos consecutivos."""
    if not meses_ordenados:
        return []
    blocos = [[meses_ordenados[0]]]
    for mes in meses_ordenados[1:]:
        anterior = blocos[-1][-1]
        if somar_meses(anterior, 1) == mes:
            blocos[-1].append(mes)
        else:
            blocos.append([mes])
    return blocos


def detect_recurring(conn: sqlite3.Connection, meses_janela: int = 12) -> list[dict]:
    """Detecta despesas recorrentes olhando os últimos `meses_janela` meses.

    Agrupamento primário: descricao_normalizada.
    Dentro de cada grupo de descrição normalizada, sub-agrupa por proximidade
    de valor (tolerância de 5%) para não misturar "Netflix R$ 39,90" com
    "Netflix R$ 55,90" (upgrade de plano) se realmente forem valores muito
    diferentes -- mas aceita pequenas variações de mês a mês.
    """
    rows = conn.execute(
        """
        SELECT t.id, t.data, t.descricao, t.valor_centavos, t.category_id, c.nome AS category_nome
        FROM transactions t
        LEFT JOIN categories c ON c.id = t.category_id
        WHERE t.tipo = 'despesa'
        ORDER BY t.data ASC
        """
    ).fetchall()

    if not rows:
        return []

    # Filtra para a janela dos últimos N meses corridos a partir da transação mais recente.
    ultima_data = max(r["data"] for r in rows)
    ultimo_mes = _mes_da_data(ultima_data)
    mes_limite = somar_meses(ultimo_mes, -(meses_janela - 1))

    por_descricao: dict[str, list[sqlite3.Row]] = defaultdict(list)
    for r in rows:
        if _mes_da_data(r["data"]) >= mes_limite:
            chave = normalizar_descricao(r["descricao"])
            por_descricao[chave].append(r)

    resultado = []

    for descricao_norm, transacoes in por_descricao.items():
        # Sub-agrupa por proximidade de valor dentro da mesma descrição.
        transacoes_ordenadas = sorted(transacoes, key=lambda r: r["valor_centavos"])
        subgrupos: list[list[sqlite3.Row]] = []
        for t in transacoes_ordenadas:
            colocado = False
            for grupo in subgrupos:
                media_grupo = sum(g["valor_centavos"] for g in grupo) / len(grupo)
                if abs(t["valor_centavos"] - media_grupo) <= media_grupo * TOLERANCIA_VALOR:
                    grupo.append(t)
                    colocado = True
                    break
            if not colocado:
                subgrupos.append([t])

        for grupo in subgrupos:
            meses_presentes = sorted({_mes_da_data(t["data"]) for t in grupo})
            blocos = _meses_consecutivos(meses_presentes)
            maior_bloco = max(blocos, key=len) if blocos else []

            if len(maior_bloco) < 3:
                continue

            # Considera apenas as transações dentro do maior bloco consecutivo
            # para calcular estatísticas de "recorrência ativa".
            transacoes_bloco = [t for t in grupo if _mes_da_data(t["data"]) in set(maior_bloco)]
            transacoes_bloco.sort(key=lambda t: t["data"])

            valor_medio_centavos = sum(t["valor_centavos"] for t in transacoes_bloco) / len(transacoes_bloco)
            total_centavos = sum(t["valor_centavos"] for t in grupo)  # já filtrado pela janela de 12 meses
            ultima_ocorrencia = transacoes_bloco[-1]["data"]
            descricao_exemplo = transacoes_bloco[-1]["descricao"]
            category_id = transacoes_bloco[-1]["category_id"]
            category_nome = transacoes_bloco[-1]["category_nome"]

            resultado.append(
                {
                    "descricao_normalizada": descricao_norm,
                    "descricao_exemplo": descricao_exemplo,
                    "valor_medio": round(valor_medio_centavos / 100, 2),
                    "periodicidade": "mensal",
                    "category_id": category_id,
                    "category_nome": category_nome,
                    "total_ultimos_12_meses": round(total_centavos / 100, 2),
                    "ocorrencias": len(transacoes_bloco),
                    "ultima_ocorrencia": ultima_ocorrencia,
                }
            )

    resultado.sort(key=lambda x: x["total_ultimos_12_meses"], reverse=True)
    return resultado
