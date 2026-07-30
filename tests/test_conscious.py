from __future__ import annotations

import json
from datetime import date
from types import SimpleNamespace

from app.services.conscious import build_weekly_summary


def _category(client, name="Lazer", essential=False):
    response = client.post(
        "/api/categories",
        json={
            "nome": name,
            "tipo": "despesa",
            "cor": "#7C5CF6",
            "icone": "gamepad-2",
            "essencial": essential,
        },
    )
    assert response.status_code == 201
    return response.json()


def _transaction(client, category_id, day, value, description="Compra"):
    response = client.post(
        "/api/transactions",
        json={
            "data": day,
            "descricao": description,
            "valor": value,
            "tipo": "despesa",
            "category_id": category_id,
        },
    )
    assert response.status_code == 201
    return response.json()


def _reflection(client, transaction_id, *, emotion="estressado", decision="impulso", context=None):
    response = client.post(
        "/api/conscious/reflections",
        json={
            "transaction_id": transaction_id,
            "emotion": emotion,
            "intensity": 4,
            "decision_type": decision,
            "context": context,
            "automatic_thought": "Eu mereço comprar isso agora",
            "chosen_action": "pausa_30_min",
            "trigger_source": "fora_do_padrao",
        },
    )
    assert response.status_code == 200
    return response.json()


def test_conscious_migrations(conn):
    names = {
        row["name"]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name LIKE 'conscious_%'"
        ).fetchall()
    }
    assert names == {"conscious_reflections", "conscious_weekly_checkins"}


def test_options_are_optional_and_non_clinical(client):
    response = client.get("/api/conscious/options")
    assert response.status_code == 200
    body = response.json()
    assert any(item["value"] == "prefiro_nao_informar" for item in body["emotions"])
    assert "opcional" in body["privacy"].lower()
    assert "não realiza diagnóstico" in body["notice"].lower()


def test_reflection_is_upserted_without_duplication(client):
    category = _category(client)
    transaction = _transaction(client, category["id"], "2026-07-27", 95.56)

    first = _reflection(client, transaction["id"])
    second_response = client.post(
        "/api/conscious/reflections",
        json={
            "transaction_id": transaction["id"],
            "emotion": "tranquilo",
            "intensity": 2,
            "decision_type": "planejada",
            "chosen_action": "nenhuma",
        },
    )
    assert second_response.status_code == 200
    second = second_response.json()
    assert second["id"] == first["id"]
    assert second["emotion"] == "tranquilo"

    listed = client.get("/api/conscious/reflections", params={"mes": "2026-07"}).json()
    assert listed["total"] == 1
    assert listed["items"][0]["transaction_value"] == 95.56


def test_reflection_rejects_income(client):
    response = client.post(
        "/api/categories",
        json={"nome": "Salário", "tipo": "receita", "cor": "#19A974"},
    )
    category = response.json()
    transaction = client.post(
        "/api/transactions",
        json={
            "data": "2026-07-27",
            "descricao": "Salário",
            "valor": 5000,
            "tipo": "receita",
            "category_id": category["id"],
        },
    ).json()
    response = client.post(
        "/api/conscious/reflections",
        json={
            "transaction_id": transaction["id"],
            "emotion": "feliz",
            "intensity": 3,
            "decision_type": "planejada",
        },
    )
    assert response.status_code == 422


def test_prompt_detects_outlier_and_disappears_after_reflection(client):
    category = _category(client, "Restaurantes")
    for index, value in enumerate((40, 45, 50), start=1):
        _transaction(client, category["id"], f"2026-06-{index + 10:02d}", value)
    outlier = _transaction(client, category["id"], "2026-07-28", 180, "Jantar especial")

    response = client.get("/api/conscious/prompts", params={"mes": "2026-07"})
    assert response.status_code == 200
    prompt = response.json()["items"][0]
    assert prompt["trigger"] == "fora_do_padrao"
    assert prompt["transaction"]["id"] == outlier["id"]
    assert "sentindo" not in prompt["explanation"].lower()

    _reflection(client, outlier["id"])
    assert client.get("/api/conscious/prompts", params={"mes": "2026-07"}).json()["total"] == 0


def test_weekly_summary_finds_pattern_and_normalizes_monday(client):
    category = _category(client)
    first = _transaction(client, category["id"], "2026-07-27", 80, "Cinema")
    second = _transaction(client, category["id"], "2026-07-29", 120, "Passeio")
    _reflection(client, first["id"], context="Semana exigente")
    _reflection(client, second["id"], context="Queria descansar")

    checkin = client.post(
        "/api/conscious/weekly-checkins",
        json={
            "week_start": "2026-07-29",
            "financial_stress": 4,
            "confidence": 2,
            "avoided_finances": True,
            "note": "Preferi não abrir o extrato",
        },
    )
    assert checkin.status_code == 200
    assert checkin.json()["week_start"] == "2026-07-27"

    summary = client.get(
        "/api/conscious/weekly",
        params={"semana": "2026-07-30"},
    ).json()
    assert summary["week_start"] == "2026-07-27"
    assert summary["reflections"] == 2
    assert summary["patterns"][0]["emotion"] == "estressado"
    assert summary["patterns"][0]["occurrences"] == 2
    assert summary["next_step"]["code"] == "pausa_30_min"
    assert summary["checkin"]["avoided_finances"] is True


def test_ai_receives_only_aggregated_patterns(conn, monkeypatch):
    category_id = conn.execute(
        "INSERT INTO categories (nome, tipo, cor) VALUES ('Compras', 'despesa', '#7C5CF6')"
    ).lastrowid
    captured: dict = {}
    for index, description in enumerate(("Tênis", "Roupa"), start=1):
        transaction_id = conn.execute(
            """
            INSERT INTO transactions
                (data, descricao, valor_centavos, tipo, category_id)
            VALUES (?, ?, 10000, 'despesa', ?)
            """,
            (f"2026-07-{26 + index}", description, category_id),
        ).lastrowid
        conn.execute(
            """
            INSERT INTO conscious_reflections
                (transaction_id, emotion, intensity, decision_type,
                 context, automatic_thought, chosen_action)
            VALUES (?, 'ansioso', 4, 'impulso', ?, ?, 'pausa_30_min')
            """,
            (
                transaction_id,
                "SEGREDO: discussão particular",
                "SEGREDO: pensamento particular",
            ),
        )
    conn.commit()

    class FakeMessages:
        def create(self, **kwargs):
            captured.update(kwargs)
            safe_input = json.loads(kwargs["messages"][0]["content"])
            pattern_id = safe_input[0]["id"]
            return SimpleNamespace(
                content=[
                    SimpleNamespace(
                        type="text",
                        text=json.dumps(
                            [
                                {
                                    "id": pattern_id,
                                    "pergunta": "Que situação costuma aparecer antes dessas compras?",
                                    "acao": "Experimente uma pausa curta antes da próxima decisão.",
                                }
                            ],
                            ensure_ascii=False,
                        ),
                    )
                ]
            )

    class FakeClient:
        def __init__(self, **kwargs):
            self.messages = FakeMessages()

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    result = build_weekly_summary(
        conn,
        date(2026, 7, 29),
        use_ai=True,
        client_factory=FakeClient,
    )
    sent = captured["messages"][0]["content"]
    assert "SEGREDO" not in sent
    assert "automatic_thought" not in sent
    assert result["ai"]["used"] is True
    assert result["patterns"][0]["source"] == "anthropic"

