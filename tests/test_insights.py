"""Testes do motor determinístico e do fallback da integração Anthropic."""
from __future__ import annotations

from types import SimpleNamespace

from app.services.insights import enrich_with_anthropic, generate_insights


def _categoria(client, nome="Mercado", essencial=False):
    response = client.post(
        "/api/categories",
        json={
            "nome": nome,
            "tipo": "despesa",
            "cor": "#4C8DFF",
            "essencial": essencial,
        },
    )
    assert response.status_code == 201
    return response.json()


def _transacao(client, category_id, data, valor, descricao="Compra"):
    response = client.post(
        "/api/transactions",
        json={
            "data": data,
            "descricao": descricao,
            "valor": valor,
            "tipo": "despesa",
            "category_id": category_id,
        },
    )
    assert response.status_code == 201


def test_endpoint_retorna_alerta_de_orcamento_sem_chave(client, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    categoria = _categoria(client)
    response = client.post(
        "/api/budgets",
        json={"category_id": categoria["id"], "mes": "2026-03", "limite": 1_000},
    )
    assert response.status_code == 201
    _transacao(client, categoria["id"], "2026-03-10", 1_200)

    response = client.get("/api/insights", params={"mes": "2026-03"})

    assert response.status_code == 200
    payload = response.json()
    alerta = next(item for item in payload["items"] if item["tipo"] == "orcamento_estourado")
    assert alerta["impacto_estimado"] == 200
    assert alerta["fonte"] == "local"
    assert payload["meta"]["ia_status"] == "sem_chave"
    assert payload["meta"]["ia_usada"] is False


def test_detecta_aumento_relevante_sem_duplicar_alerta_de_orcamento(client):
    categoria = _categoria(client, "Restaurantes")
    _transacao(client, categoria["id"], "2026-02-10", 100)
    _transacao(client, categoria["id"], "2026-03-10", 180)

    payload = client.get(
        "/api/insights",
        params={"mes": "2026-03", "usar_ia": "false"},
    ).json()

    alerta = next(item for item in payload["items"] if item["tipo"] == "aumento_gastos")
    assert alerta["impacto_estimado"] == 80
    assert alerta["evidencia"]["variacao_percentual"] == 80
    assert payload["meta"]["ia_status"] == "desativada"


def test_anthropic_so_pode_reescrever_textos_e_preserva_numeros():
    insights = [
        {
            "id": "alerta-1",
            "tipo": "aumento_gastos",
            "severidade": "atencao",
            "titulo": "Título local",
            "descricao": "Descrição local",
            "acao": "Ação local",
            "impacto_estimado": 123.45,
            "evidencia": {"diferenca": 123.45},
            "fonte": "local",
        }
    ]

    class FakeMessages:
        def create(self, **kwargs):
            return SimpleNamespace(
                content=[
                    SimpleNamespace(
                        type="text",
                        text=(
                            '[{"id":"alerta-1","titulo":"Novo título",'
                            '"descricao":"Nova descrição","acao":"Nova ação",'
                            '"impacto_estimado":999999}]'
                        ),
                    )
                ]
            )

    class FakeClient:
        def __init__(self, **kwargs):
            self.messages = FakeMessages()

    resultado = enrich_with_anthropic(
        insights,
        api_key="chave-teste",
        model="claude-teste",
        client_factory=FakeClient,
    )

    assert resultado[0]["titulo"] == "Novo título"
    assert resultado[0]["impacto_estimado"] == 123.45
    assert resultado[0]["evidencia"] == {"diferenca": 123.45}
    assert resultado[0]["fonte"] == "anthropic"


def test_falha_da_ia_mantem_fallback_local(conn, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "chave-teste")
    category_id = conn.execute(
        """
        INSERT INTO categories (nome, tipo, cor, essencial)
        VALUES ('Lazer', 'despesa', '#4C8DFF', 0)
        """
    ).lastrowid
    conn.execute(
        "INSERT INTO budgets (category_id, mes, limite_centavos) VALUES (?, '2026-03', 10000)",
        (category_id,),
    )
    conn.execute(
        """
        INSERT INTO transactions (data, descricao, valor_centavos, tipo, category_id)
        VALUES ('2026-03-10', 'Cinema', 15000, 'despesa', ?)
        """,
        (category_id,),
    )
    conn.commit()

    class BrokenClient:
        def __init__(self, **kwargs):
            raise TimeoutError

    resultado = generate_insights(conn, "2026-03", client_factory=BrokenClient)

    assert resultado["meta"]["ia_status"] == "fallback_erro"
    assert resultado["meta"]["ia_usada"] is False
    assert resultado["items"][0]["fonte"] == "local"
    assert resultado["items"][0]["impacto_estimado"] == 50
