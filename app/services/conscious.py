"""Modo Consciente: reflexão financeira e padrões comportamentais.

O módulo não realiza diagnóstico, psicoterapia ou avaliação psicológica.
Perguntas e ações são geradas por regras locais e não julgadoras. Quando a IA
é habilitada, ela recebe apenas padrões agregados, nunca os textos livres do
usuário.
"""
from __future__ import annotations

import json
import os
import sqlite3
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import date, timedelta
from typing import Any, Callable

from app.models import ConsciousReflectionCreate, ConsciousWeeklyCheckinCreate
from app.services.budgets import compute_budget_status
from app.services.dates import mes_bounds

NOTICE = (
    "O Modo Consciente oferece educação e reflexão sobre hábitos financeiros. "
    "Não realiza diagnóstico e não substitui psicólogo ou orientação financeira profissional."
)

EMOTIONS = {
    "tranquilo": "Tranquilo",
    "feliz": "Feliz",
    "ansioso": "Ansioso",
    "estressado": "Estressado",
    "triste": "Triste",
    "entediado": "Entediado",
    "cansado": "Cansado",
    "pressionado": "Pressionado",
    "outro": "Outro",
    "prefiro_nao_informar": "Prefiro não informar",
}

DECISION_TYPES = {
    "planejada": "Compra planejada",
    "necessaria": "Necessidade do momento",
    "impulso": "Decisão por impulso",
    "compensacao": "Busca de conforto ou recompensa",
    "influencia_social": "Influência social",
    "outro": "Outro motivo",
}

ACTIONS = {
    "pausa_30_min": {
        "titulo": "Pausa de 30 minutos",
        "descricao": "Antes de uma compra parecida, espere 30 minutos e confira se ela continua fazendo sentido.",
    },
    "esperar_24h": {
        "titulo": "Lista de 24 horas",
        "descricao": "Coloque o item em uma lista e espere um dia antes de decidir.",
    },
    "definir_teto": {
        "titulo": "Teto para a categoria",
        "descricao": "Defina um valor máximo realista para essa categoria até o fim da semana.",
    },
    "alternativa_baixo_custo": {
        "titulo": "Alternativa de baixo custo",
        "descricao": "Anote uma forma mais barata de atender à mesma necessidade.",
    },
    "conversar_com_alguem": {
        "titulo": "Decisão compartilhada",
        "descricao": "Converse com alguém de confiança antes de assumir uma despesa importante.",
    },
    "nenhuma": {
        "titulo": "Somente observar",
        "descricao": "Registrar o padrão já é um passo. Nenhuma ação adicional é obrigatória.",
    },
}

AI_SYSTEM_PROMPT = """Você é o redator do Modo Consciente do FinPilot.
Receberá somente padrões financeiros agregados, sem relatos privados.
Reescreva pergunta e ação em português do Brasil, com curiosidade, respeito e
linguagem breve.

Regras:
- responda somente com um array JSON válido;
- preserve exatamente o id de cada item;
- retorne apenas id, pergunta e acao;
- não faça diagnóstico psicológico;
- não use os termos terapia, tratamento, transtorno ou crença disfuncional;
- não atribua causalidade entre emoção e gasto;
- não dê aconselhamento médico ou de investimento;
- nunca use culpa, vergonha ou tom alarmista.
"""


def options() -> dict[str, Any]:
    return {
        "emotions": [{"value": key, "label": value} for key, value in EMOTIONS.items()],
        "decision_types": [{"value": key, "label": value} for key, value in DECISION_TYPES.items()],
        "actions": [{"value": key, **value} for key, value in ACTIONS.items()],
        "intensity": {
            "min": 1,
            "max": 5,
            "labels": {"1": "Leve", "3": "Moderada", "5": "Muito intensa"},
        },
        "privacy": (
            "Responder é opcional. Seus textos ficam no banco do FinPilot e não são enviados à IA. "
            "Somente contagens agregadas podem ser usadas quando você ativa a IA."
        ),
        "notice": NOTICE,
    }


def _reflection_to_out(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "transaction_id": row["transaction_id"],
        "emotion": row["emotion"],
        "intensity": row["intensity"],
        "decision_type": row["decision_type"],
        "context": row["context"],
        "automatic_thought": row["automatic_thought"],
        "chosen_action": row["chosen_action"],
        "trigger_source": row["trigger_source"],
        "transaction_date": row["transaction_date"],
        "transaction_description": row["transaction_description"],
        "transaction_value": round(row["transaction_value_centavos"] / 100, 2),
        "category_name": row["category_name"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


REFLECTION_SELECT = """
    SELECT r.*, t.data AS transaction_date,
           t.descricao AS transaction_description,
           t.valor_centavos AS transaction_value_centavos,
           c.nome AS category_name
    FROM conscious_reflections r
    JOIN transactions t ON t.id = r.transaction_id
    LEFT JOIN categories c ON c.id = t.category_id
"""


def save_reflection(
    conn: sqlite3.Connection,
    payload: ConsciousReflectionCreate,
) -> dict[str, Any]:
    transaction = conn.execute(
        "SELECT id, tipo FROM transactions WHERE id = ?",
        (payload.transaction_id,),
    ).fetchone()
    if transaction is None:
        raise LookupError("Lançamento não encontrado.")
    if transaction["tipo"] != "despesa":
        raise ValueError("O Modo Consciente registra reflexões somente para despesas.")

    values = payload.model_dump()
    conn.execute(
        """
        INSERT INTO conscious_reflections
            (transaction_id, emotion, intensity, decision_type, context,
             automatic_thought, chosen_action, trigger_source, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
        ON CONFLICT(transaction_id) DO UPDATE SET
            emotion = excluded.emotion,
            intensity = excluded.intensity,
            decision_type = excluded.decision_type,
            context = excluded.context,
            automatic_thought = excluded.automatic_thought,
            chosen_action = excluded.chosen_action,
            trigger_source = excluded.trigger_source,
            updated_at = datetime('now')
        """,
        (
            values["transaction_id"],
            values["emotion"],
            values["intensity"],
            values["decision_type"],
            values["context"],
            values["automatic_thought"],
            values["chosen_action"],
            values["trigger_source"],
        ),
    )
    conn.commit()
    row = conn.execute(
        REFLECTION_SELECT + " WHERE r.transaction_id = ?",
        (payload.transaction_id,),
    ).fetchone()
    return _reflection_to_out(row)


def list_reflections(
    conn: sqlite3.Connection,
    *,
    mes: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    where = ""
    params: list[Any] = []
    if mes:
        inicio, fim = mes_bounds(mes)
        where = " WHERE t.data BETWEEN ? AND ?"
        params.extend([inicio, fim])
    total = conn.execute(
        """
        SELECT COUNT(*) AS total
        FROM conscious_reflections r
        JOIN transactions t ON t.id = r.transaction_id
        """ + where,
        params,
    ).fetchone()["total"]
    rows = conn.execute(
        REFLECTION_SELECT
        + where
        + " ORDER BY t.data DESC, r.id DESC LIMIT ? OFFSET ?",
        [*params, limit, offset],
    ).fetchall()
    return {
        "items": [_reflection_to_out(row) for row in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
        "notice": NOTICE,
    }


def _prompt_for(
    row: sqlite3.Row,
    trigger: str,
    *,
    explanation: str,
    action_code: str,
) -> dict[str, Any]:
    questions = {
        "fora_do_padrao": [
            "Essa compra já estava nos seus planos?",
            "O que estava acontecendo no momento da decisão?",
            "Que necessidade você esperava atender com essa compra?",
        ],
        "alto_valor": [
            "Essa despesa foi planejada ou surgiu no momento?",
            "Existe alguma parte dessa decisão que você gostaria de rever com calma?",
        ],
        "orcamento_em_risco": [
            "Houve alguma situação diferente nesta categoria durante o mês?",
            "Qual pequeno ajuste seria possível sem abrir mão do que é importante?",
        ],
        "padrao_de_dia": [
            "O que costuma acontecer nesse dia da semana?",
            "Esse padrão combina com suas prioridades atuais?",
        ],
    }[trigger]
    return {
        "id": f"{trigger}-{row['id']}",
        "trigger": trigger,
        "explanation": explanation,
        "transaction": {
            "id": row["id"],
            "date": row["data"],
            "description": row["descricao"],
            "value": round(row["valor_centavos"] / 100, 2),
            "category_id": row["category_id"],
            "category_name": row["category_name"],
        },
        "questions": questions,
        "suggested_action": {"code": action_code, **ACTIONS[action_code]},
        "notice": NOTICE,
    }


def build_prompts(conn: sqlite3.Connection, mes: str) -> list[dict[str, Any]]:
    inicio, fim = mes_bounds(mes)
    rows = conn.execute(
        """
        SELECT t.id, t.data, t.descricao, t.valor_centavos, t.category_id,
               c.nome AS category_name, COALESCE(c.essencial, 0) AS essential
        FROM transactions t
        LEFT JOIN categories c ON c.id = t.category_id
        LEFT JOIN conscious_reflections r ON r.transaction_id = t.id
        WHERE t.tipo = 'despesa' AND t.data BETWEEN ? AND ? AND r.id IS NULL
        ORDER BY t.valor_centavos DESC, t.data DESC
        """,
        (inicio, fim),
    ).fetchall()
    prompts_by_transaction: dict[int, dict[str, Any]] = {}

    for row in rows:
        if row["category_id"] is not None:
            transaction_day = date.fromisoformat(str(row["data"])[:10])
            history_start = transaction_day - timedelta(days=90)
            history = conn.execute(
                """
                SELECT COUNT(*) AS quantity, AVG(valor_centavos) AS average_value
                FROM transactions
                WHERE tipo = 'despesa' AND category_id = ?
                  AND data < ? AND data >= ?
                """,
                (
                    row["category_id"],
                    transaction_day.isoformat(),
                    history_start.isoformat(),
                ),
            ).fetchone()
        else:
            history = {"quantity": 0, "average_value": None}

        quantity = int(history["quantity"] or 0)
        average = int(history["average_value"] or 0)
        if quantity >= 3 and average > 0 and row["valor_centavos"] >= average * 1.75 and row["valor_centavos"] - average >= 5_000:
            explanation = (
                f"Esse valor ficou {round(row['valor_centavos'] / average, 1)}× acima "
                f"da média recente de {row['category_name'] or 'despesas semelhantes'}."
            )
            prompts_by_transaction[row["id"]] = _prompt_for(
                row,
                "fora_do_padrao",
                explanation=explanation,
                action_code="pausa_30_min",
            )
        elif not row["essential"] and row["valor_centavos"] >= 30_000:
            prompts_by_transaction[row["id"]] = _prompt_for(
                row,
                "alto_valor",
                explanation="É uma despesa não essencial de valor relevante para uma revisão consciente.",
                action_code="esperar_24h",
            )

    budget_by_category = {
        item["category_id"]: item
        for item in compute_budget_status(conn, mes)
        if item["estado"] in ("atencao", "estourado")
    }
    for row in rows:
        if row["id"] in prompts_by_transaction or row["category_id"] not in budget_by_category:
            continue
        status = budget_by_category[row["category_id"]]
        prompts_by_transaction[row["id"]] = _prompt_for(
            row,
            "orcamento_em_risco",
            explanation=(
                f"{row['category_name']} já utilizou {status['percentual']:.0f}% "
                "do limite definido para o mês."
            ),
            action_code="definir_teto",
        )

    weekday_groups: dict[tuple[int | None, str], list[sqlite3.Row]] = defaultdict(list)
    for row in rows:
        weekday = str(date.fromisoformat(str(row["data"])[:10]).weekday())
        weekday_groups[(row["category_id"], weekday)].append(row)
    for group in weekday_groups.values():
        if len(group) < 3:
            continue
        row = max(group, key=lambda item: (item["data"], item["id"]))
        if row["id"] not in prompts_by_transaction:
            prompts_by_transaction[row["id"]] = _prompt_for(
                row,
                "padrao_de_dia",
                explanation=(
                    f"Foram registradas {len(group)} despesas de "
                    f"{row['category_name'] or 'uma mesma categoria'} no mesmo dia da semana."
                ),
                action_code="alternativa_baixo_custo",
            )

    return list(prompts_by_transaction.values())[:6]


def _monday(value: date) -> date:
    return value - timedelta(days=value.weekday())


def save_weekly_checkin(
    conn: sqlite3.Connection,
    payload: ConsciousWeeklyCheckinCreate,
) -> dict[str, Any]:
    week_start = _monday(payload.week_start)
    existing = conn.execute(
        "SELECT id FROM conscious_weekly_checkins WHERE week_start = ?",
        (week_start.isoformat(),),
    ).fetchone()
    values = (
        payload.financial_stress,
        payload.confidence,
        int(payload.avoided_finances),
        payload.note,
    )
    if existing:
        conn.execute(
            """
            UPDATE conscious_weekly_checkins
            SET financial_stress = ?, confidence = ?, avoided_finances = ?,
                note = ?, updated_at = datetime('now')
            WHERE id = ?
            """,
            (*values, existing["id"]),
        )
    else:
        conn.execute(
            """
            INSERT INTO conscious_weekly_checkins
                (week_start, financial_stress, confidence, avoided_finances, note, updated_at)
            VALUES (?, ?, ?, ?, ?, datetime('now'))
            """,
            (week_start.isoformat(), *values),
        )
    conn.commit()
    row = conn.execute(
        "SELECT * FROM conscious_weekly_checkins WHERE week_start = ?",
        (week_start.isoformat(),),
    ).fetchone()
    return {
        "id": row["id"],
        "week_start": row["week_start"],
        "financial_stress": row["financial_stress"],
        "confidence": row["confidence"],
        "avoided_finances": bool(row["avoided_finances"]),
        "note": row["note"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _local_patterns(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[sqlite3.Row]] = defaultdict(list)
    for row in rows:
        grouped[(row["emotion"], row["category_name"] or "Sem categoria")].append(row)

    patterns: list[dict[str, Any]] = []
    for (emotion, category), group in grouped.items():
        if len(group) < 2 or emotion == "prefiro_nao_informar":
            continue
        total = round(sum(item["valor_centavos"] for item in group) / 100, 2)
        action_code = "pausa_30_min"
        if emotion in ("estressado", "ansioso", "triste", "cansado", "entediado"):
            action_code = "alternativa_baixo_custo"
        pattern_id = f"{emotion}-{category.casefold().replace(' ', '-')}"
        patterns.append(
            {
                "id": pattern_id,
                "emotion": emotion,
                "emotion_label": EMOTIONS[emotion],
                "category": category,
                "occurrences": len(group),
                "total": total,
                "question": (
                    f"Você percebe alguma relação entre momentos em que se sentiu "
                    f"{EMOTIONS[emotion].casefold()} e gastos com {category}?"
                ),
                "action": ACTIONS[action_code]["descricao"],
                "action_code": action_code,
                "source": "local",
            }
        )
    patterns.sort(key=lambda item: (-item["occurrences"], -item["total"], item["id"]))
    return patterns[:5]


def _enrich_patterns(
    patterns: list[dict[str, Any]],
    *,
    api_key: str,
    model: str,
    client_factory: Callable[..., Any] | None = None,
) -> list[dict[str, Any]]:
    if not patterns:
        return patterns
    if client_factory is None:
        from anthropic import Anthropic

        client_factory = Anthropic
    safe_payload = [
        {
            "id": item["id"],
            "emotion": item["emotion_label"],
            "category": item["category"],
            "occurrences": item["occurrences"],
            "total": item["total"],
            "pergunta_local": item["question"],
            "acao_local": item["action"],
        }
        for item in patterns
    ]
    client = client_factory(api_key=api_key)
    response = client.messages.create(
        model=model,
        max_tokens=900,
        system=AI_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": json.dumps(safe_payload, ensure_ascii=False)}],
    )
    text = "\n".join(
        getattr(block, "text", "")
        for block in getattr(response, "content", [])
        if getattr(block, "type", None) == "text"
    ).strip()
    if text.startswith("```"):
        text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    revisions = json.loads(text)
    if not isinstance(revisions, list):
        raise ValueError("Resposta da IA inválida.")
    by_id = {item.get("id"): item for item in revisions if isinstance(item, dict)}

    output = deepcopy(patterns)
    for item in output:
        revision = by_id.get(item["id"])
        if not revision:
            continue
        question = revision.get("pergunta")
        action = revision.get("acao")
        if not isinstance(question, str) or not question.strip():
            continue
        if not isinstance(action, str) or not action.strip():
            continue
        item["question"] = question.strip()[:400]
        item["action"] = action.strip()[:400]
        item["source"] = "anthropic"
    return output


def build_weekly_summary(
    conn: sqlite3.Connection,
    week: date,
    *,
    use_ai: bool = False,
    client_factory: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    week_start = _monday(week)
    week_end = week_start + timedelta(days=6)
    rows = conn.execute(
        """
        SELECT r.*, t.data, t.valor_centavos, t.descricao,
               c.nome AS category_name
        FROM conscious_reflections r
        JOIN transactions t ON t.id = r.transaction_id
        LEFT JOIN categories c ON c.id = t.category_id
        WHERE t.data BETWEEN ? AND ?
        ORDER BY t.data, r.id
        """,
        (week_start.isoformat(), week_end.isoformat()),
    ).fetchall()
    expense_count = conn.execute(
        """
        SELECT COUNT(*) AS quantity
        FROM transactions
        WHERE tipo = 'despesa' AND data BETWEEN ? AND ?
        """,
        (week_start.isoformat(), week_end.isoformat()),
    ).fetchone()["quantity"]
    checkin_row = conn.execute(
        "SELECT * FROM conscious_weekly_checkins WHERE week_start = ?",
        (week_start.isoformat(),),
    ).fetchone()

    emotion_counts = Counter(row["emotion"] for row in rows)
    decision_counts = Counter(row["decision_type"] for row in rows)
    patterns = _local_patterns(rows)
    ai_meta = {
        "requested": use_ai,
        "used": False,
        "status": "disabled" if not use_ai else "missing_key",
        "privacy": "Textos livres não são enviados à IA; somente contagens agregadas.",
    }
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if use_ai and api_key and patterns:
        try:
            patterns = _enrich_patterns(
                patterns,
                api_key=api_key,
                model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5"),
                client_factory=client_factory,
            )
            ai_meta.update(
                {
                    "used": any(item["source"] == "anthropic" for item in patterns),
                    "status": "success",
                }
            )
        except (ImportError, ModuleNotFoundError):
            ai_meta["status"] = "sdk_unavailable"
        except Exception:
            ai_meta["status"] = "local_fallback"
    elif use_ai and api_key and not patterns:
        ai_meta["status"] = "no_patterns"

    dominant_emotion = emotion_counts.most_common(1)[0][0] if emotion_counts else None
    next_step: dict[str, str]
    if decision_counts.get("impulso", 0) >= 2:
        next_step = {"code": "pausa_30_min", **ACTIONS["pausa_30_min"]}
    elif sum(emotion_counts.get(value, 0) for value in ("ansioso", "estressado", "triste", "cansado")) >= 2:
        next_step = {"code": "alternativa_baixo_custo", **ACTIONS["alternativa_baixo_custo"]}
    elif rows:
        next_step = {
            "code": "continuar_observando",
            "titulo": "Continue observando",
            "descricao": "Faça mais uma reflexão na próxima compra que chamar sua atenção.",
        }
    else:
        next_step = {
            "code": "primeira_reflexao",
            "titulo": "Comece com uma pergunta",
            "descricao": "Escolha uma despesa da semana e registre como você estava no momento.",
        }

    return {
        "week_start": week_start.isoformat(),
        "week_end": week_end.isoformat(),
        "reflections": len(rows),
        "expenses": expense_count,
        "coverage_percentage": round((len(rows) / expense_count) * 100, 1) if expense_count else 0.0,
        "reflected_total": round(sum(row["valor_centavos"] for row in rows) / 100, 2),
        "dominant_emotion": (
            {"value": dominant_emotion, "label": EMOTIONS[dominant_emotion]}
            if dominant_emotion
            else None
        ),
        "emotion_counts": [
            {"value": key, "label": EMOTIONS[key], "count": count}
            for key, count in emotion_counts.most_common()
        ],
        "decision_counts": [
            {"value": key, "label": DECISION_TYPES[key], "count": count}
            for key, count in decision_counts.most_common()
        ],
        "patterns": patterns,
        "next_step": next_step,
        "checkin": (
            {
                "id": checkin_row["id"],
                "financial_stress": checkin_row["financial_stress"],
                "confidence": checkin_row["confidence"],
                "avoided_finances": bool(checkin_row["avoided_finances"]),
                "note": checkin_row["note"],
            }
            if checkin_row
            else None
        ),
        "ai": ai_meta,
        "notice": NOTICE,
    }
