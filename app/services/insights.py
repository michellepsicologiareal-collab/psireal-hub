"""Motor de insights financeiros determinístico com enriquecimento opcional por IA.

Os cálculos e impactos monetários são sempre feitos localmente. A Anthropic
recebe somente os achados agregados e pode reescrever título, descrição e ação;
ela nunca define ou altera os valores financeiros retornados pela API.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
from copy import deepcopy
from typing import Any, Callable

from app.services.analytics import compute_summary
from app.services.budgets import compute_budget_status
from app.services.dates import mes_anterior, mes_bounds
from app.services.recurring import detect_recurring

AVISO_FINANCEIRO = (
    "Insights educacionais baseados nos dados cadastrados; não substituem "
    "orientação financeira profissional."
)
MODELO_PADRAO = "claude-sonnet-5"
LIMITE_INSIGHTS = 8

SYSTEM_PROMPT = """Você é o redator do FinPilot, um painel brasileiro de finanças pessoais.
Receberá achados calculados por regras determinísticas. Reescreva cada conselho
em português do Brasil, de forma curta, clara, respeitosa e acionável.

Regras obrigatórias:
- responda somente com um array JSON válido;
- preserve exatamente o id de cada item;
- retorne apenas id, titulo, descricao e acao;
- não crie nem recalcule números, percentuais ou impactos;
- não recomende investimentos, crédito ou produtos financeiros;
- não use tom alarmista nem afirme que uma despesa deve ser cancelada.
"""


def _reais(centavos: int) -> float:
    return round(centavos / 100, 2)


def _formatar_brl(valor: float) -> str:
    texto = f"{valor:,.2f}"
    return "R$ " + texto.replace(",", "X").replace(".", ",").replace("X", ".")


def _gastos_por_categoria(conn: sqlite3.Connection, mes: str) -> dict[int, dict[str, Any]]:
    inicio, fim = mes_bounds(mes)
    rows = conn.execute(
        """
        SELECT c.id, c.nome, COALESCE(SUM(t.valor_centavos), 0) AS total_centavos
        FROM categories c
        JOIN transactions t ON t.category_id = c.id
        WHERE t.tipo = 'despesa' AND t.data BETWEEN ? AND ?
        GROUP BY c.id, c.nome
        """,
        (inicio, fim),
    ).fetchall()
    return {
        row["id"]: {
            "nome": row["nome"],
            "total_centavos": row["total_centavos"],
        }
        for row in rows
    }


def _insights_de_orcamento(conn: sqlite3.Connection, mes: str) -> tuple[list[dict], set[int]]:
    items: list[dict] = []
    categorias_alertadas: set[int] = set()

    for status in compute_budget_status(conn, mes):
        gasto = status["gasto"]
        limite = status["limite"]
        projetado = max(gasto, status["ritmo_diario_projetado"])
        nome = status["category_nome"]
        category_id = status["category_id"]

        if gasto > limite:
            impacto = round(gasto - limite, 2)
            categorias_alertadas.add(category_id)
            items.append(
                {
                    "id": f"orcamento-estourado-{category_id}-{mes}",
                    "tipo": "orcamento_estourado",
                    "severidade": "critico",
                    "titulo": f"{nome} passou do orçamento",
                    "descricao": (
                        f"O gasto foi de {_formatar_brl(gasto)} para um limite de "
                        f"{_formatar_brl(limite)}."
                    ),
                    "acao": "Revise os lançamentos da categoria e pause gastos não essenciais até o próximo mês.",
                    "impacto_estimado": impacto,
                    "evidencia": {
                        "categoria": nome,
                        "gasto": gasto,
                        "limite": limite,
                        "excesso": impacto,
                        "percentual_usado": status["percentual"],
                    },
                    "fonte": "local",
                }
            )
        elif projetado > limite:
            impacto = round(projetado - limite, 2)
            categorias_alertadas.add(category_id)
            items.append(
                {
                    "id": f"orcamento-risco-{category_id}-{mes}",
                    "tipo": "orcamento_em_risco",
                    "severidade": "atencao",
                    "titulo": f"{nome} pode ultrapassar o limite",
                    "descricao": (
                        f"No ritmo atual, o mês pode fechar em {_formatar_brl(projetado)}, "
                        f"acima do limite de {_formatar_brl(limite)}."
                    ),
                    "acao": "Defina um teto para os próximos gastos desta categoria.",
                    "impacto_estimado": impacto,
                    "evidencia": {
                        "categoria": nome,
                        "gasto_atual": gasto,
                        "projecao": projetado,
                        "limite": limite,
                        "excesso_projetado": impacto,
                    },
                    "fonte": "local",
                }
            )

    return items, categorias_alertadas


def _insights_de_variacao(
    conn: sqlite3.Connection,
    mes: str,
    categorias_ja_alertadas: set[int],
) -> list[dict]:
    atual = _gastos_por_categoria(conn, mes)
    anterior = _gastos_por_categoria(conn, mes_anterior(mes))
    items: list[dict] = []

    for category_id, dados in atual.items():
        if category_id in categorias_ja_alertadas or category_id not in anterior:
            continue
        atual_c = dados["total_centavos"]
        anterior_c = anterior[category_id]["total_centavos"]
        diferenca_c = atual_c - anterior_c
        if anterior_c <= 0 or diferenca_c < 5_000:
            continue
        variacao = round((diferenca_c / anterior_c) * 100, 2)
        if variacao < 20:
            continue

        diferenca = _reais(diferenca_c)
        nome = dados["nome"]
        items.append(
            {
                "id": f"aumento-gastos-{category_id}-{mes}",
                "tipo": "aumento_gastos",
                "severidade": "atencao" if variacao < 50 else "critico",
                "titulo": f"Gastos com {nome} aumentaram",
                "descricao": (
                    f"A categoria subiu {variacao:.1f}% em relação ao mês anterior, "
                    f"uma diferença de {_formatar_brl(diferenca)}."
                ),
                "acao": "Compare os lançamentos dos dois meses e identifique o que pode ser ajustado.",
                "impacto_estimado": diferenca,
                "evidencia": {
                    "categoria": nome,
                    "mes_atual": _reais(atual_c),
                    "mes_anterior": _reais(anterior_c),
                    "variacao_percentual": variacao,
                    "diferenca": diferenca,
                },
                "fonte": "local",
            }
        )
    return items


def _insight_de_poupanca(conn: sqlite3.Connection, mes: str) -> list[dict]:
    summary = compute_summary(conn, mes)
    receita = summary["total_receita"]
    taxa = summary["taxa_poupanca"]
    if receita <= 0 or taxa >= 10:
        return []

    meta_poupanca = round(receita * 0.10, 2)
    impacto = round(max(0.0, meta_poupanca - summary["saldo"]), 2)
    return [
        {
            "id": f"poupanca-baixa-{mes}",
            "tipo": "poupanca_baixa",
            "severidade": "critico" if summary["saldo"] < 0 else "atencao",
            "titulo": "Sua margem de poupança está baixa",
            "descricao": (
                f"A taxa do mês está em {taxa:.1f}%. Para chegar a 10%, "
                f"seria preciso liberar {_formatar_brl(impacto)} no orçamento."
            ),
            "acao": "Comece pelos alertas de maior impacto e defina uma transferência automática realista.",
            "impacto_estimado": impacto,
            "evidencia": {
                "receita": receita,
                "saldo": summary["saldo"],
                "taxa_poupanca": taxa,
                "meta_taxa": 10.0,
                "valor_para_meta": impacto,
            },
            "fonte": "local",
        }
    ]


def _insights_de_recorrencias(conn: sqlite3.Connection) -> list[dict]:
    recorrencias = detect_recurring(conn)
    essenciais = {
        row["id"]: bool(row["essencial"])
        for row in conn.execute("SELECT id, essencial FROM categories").fetchall()
    }
    items: list[dict] = []

    for recorrencia in recorrencias:
        if essenciais.get(recorrencia["category_id"], False):
            continue
        valor_mensal = recorrencia["valor_medio"]
        impacto_anual = round(valor_mensal * 12, 2)
        descricao = recorrencia["descricao_exemplo"]
        items.append(
            {
                "id": f"recorrencia-{recorrencia['descricao_normalizada']}",
                "tipo": "recorrencia",
                "severidade": "info",
                "titulo": f"Revise a recorrência {descricao}",
                "descricao": (
                    f"O valor médio é {_formatar_brl(valor_mensal)} por mês, "
                    f"equivalente a {_formatar_brl(impacto_anual)} em 12 meses."
                ),
                "acao": "Confirme se o serviço ainda é usado e se o plano atual continua adequado.",
                "impacto_estimado": impacto_anual,
                "evidencia": {
                    "descricao": descricao,
                    "valor_medio_mensal": valor_mensal,
                    "impacto_potencial_12_meses": impacto_anual,
                    "ocorrencias": recorrencia["ocorrencias"],
                },
                "fonte": "local",
            }
        )
    return items[:3]


def build_local_insights(conn: sqlite3.Connection, mes: str) -> list[dict]:
    """Calcula alertas reproduzíveis e ordenados sem depender de IA."""
    orcamentos, categorias_alertadas = _insights_de_orcamento(conn, mes)
    items = [
        *orcamentos,
        *_insights_de_variacao(conn, mes, categorias_alertadas),
        *_insight_de_poupanca(conn, mes),
        *_insights_de_recorrencias(conn),
    ]
    prioridade = {"critico": 0, "atencao": 1, "info": 2}
    items.sort(key=lambda item: (prioridade[item["severidade"]], -item["impacto_estimado"], item["id"]))
    return items[:LIMITE_INSIGHTS]


def _extrair_json(texto: str) -> list[dict]:
    texto = texto.strip()
    if texto.startswith("```"):
        texto = re.sub(r"^```(?:json)?\s*", "", texto, flags=re.IGNORECASE)
        texto = re.sub(r"\s*```$", "", texto)
    try:
        payload = json.loads(texto)
    except json.JSONDecodeError:
        match = re.search(r"\[[\s\S]*\]", texto)
        if match is None:
            raise
        payload = json.loads(match.group(0))
    if not isinstance(payload, list):
        raise ValueError("resposta da IA não é uma lista")
    return [item for item in payload if isinstance(item, dict)]


def _texto_da_resposta(response: Any) -> str:
    partes: list[str] = []
    for bloco in getattr(response, "content", []):
        if getattr(bloco, "type", None) == "text":
            partes.append(getattr(bloco, "text", ""))
    if not partes:
        raise ValueError("resposta da IA sem conteúdo textual")
    return "\n".join(partes)


def enrich_with_anthropic(
    insights: list[dict],
    api_key: str,
    model: str,
    client_factory: Callable[..., Any] | None = None,
) -> list[dict]:
    """Reescreve os textos via Anthropic, preservando cálculos e evidências locais."""
    if not insights:
        return []
    if client_factory is None:
        from anthropic import Anthropic

        client_factory = Anthropic

    payload = [
        {
            "id": item["id"],
            "tipo": item["tipo"],
            "severidade": item["severidade"],
            "titulo_local": item["titulo"],
            "descricao_local": item["descricao"],
            "acao_local": item["acao"],
            "impacto_estimado": item["impacto_estimado"],
            "evidencia": item["evidencia"],
        }
        for item in insights
    ]
    client = client_factory(api_key=api_key)
    response = client.messages.create(
        model=model,
        max_tokens=1_500,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": (
                    "Reescreva os achados abaixo seguindo o contrato definido. "
                    "Não omita nem acrescente itens.\n" + json.dumps(payload, ensure_ascii=False)
                ),
            }
        ],
    )
    revisoes = {item.get("id"): item for item in _extrair_json(_texto_da_resposta(response))}

    resultado = deepcopy(insights)
    for item in resultado:
        revisao = revisoes.get(item["id"])
        if not revisao:
            continue
        campos = ("titulo", "descricao", "acao")
        if not all(isinstance(revisao.get(campo), str) and revisao[campo].strip() for campo in campos):
            continue
        for campo in campos:
            item[campo] = revisao[campo].strip()
        item["fonte"] = "anthropic"
    return resultado


def generate_insights(
    conn: sqlite3.Connection,
    mes: str,
    usar_ia: bool = True,
    client_factory: Callable[..., Any] | None = None,
) -> dict:
    items = build_local_insights(conn, mes)
    model = os.getenv("ANTHROPIC_MODEL", MODELO_PADRAO)
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    meta = {
        "mes": mes,
        "ia_solicitada": usar_ia,
        "ia_usada": False,
        "ia_status": "desativada" if not usar_ia else "sem_chave",
        "modelo": None,
        "aviso": AVISO_FINANCEIRO,
    }

    if not usar_ia or not api_key or not items:
        if usar_ia and api_key and not items:
            meta["ia_status"] = "sem_achados"
        return {"items": items, "meta": meta}

    try:
        items = enrich_with_anthropic(items, api_key, model, client_factory)
        meta.update(
            {
                "ia_usada": any(item["fonte"] == "anthropic" for item in items),
                "ia_status": "sucesso",
                "modelo": model,
            }
        )
    except (ImportError, ModuleNotFoundError):
        meta["ia_status"] = "sdk_indisponivel"
    except Exception:
        # O endpoint nunca quebra por indisponibilidade, timeout ou resposta
        # inválida do provedor. Os conselhos locais permanecem utilizáveis.
        meta["ia_status"] = "fallback_erro"
    return {"items": items, "meta": meta}
