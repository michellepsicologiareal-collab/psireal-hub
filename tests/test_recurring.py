"""Testes de detecção determinística de recorrentes/assinaturas."""
from __future__ import annotations

from app.services.recurring import detect_recurring, normalizar_descricao


def _criar_categoria(client, nome="Streaming"):
    resp = client.post("/api/categories", json={"nome": nome, "tipo": "despesa", "cor": "#FF7A45"})
    return resp.json()


def _criar_transacao(client, category_id, data, valor, descricao):
    resp = client.post(
        "/api/transactions",
        json={"data": data, "descricao": descricao, "valor": valor, "tipo": "despesa", "category_id": category_id},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_normalizar_descricao():
    assert normalizar_descricao("Netflix.com") == "netflix com"
    assert normalizar_descricao("NETFLIX  ") == "netflix"
    assert normalizar_descricao("Café Grão Especial") == "cafe grao especial"


def test_detecta_recorrente_3_meses_consecutivos(client):
    cat = _criar_categoria(client)
    _criar_transacao(client, cat["id"], "2026-01-05", 39.90, "Netflix")
    _criar_transacao(client, cat["id"], "2026-02-05", 39.90, "Netflix")
    _criar_transacao(client, cat["id"], "2026-03-05", 39.90, "Netflix")

    resp = client.get("/api/recurring")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["descricao_normalizada"] == "netflix"
    assert data[0]["ocorrencias"] == 3
    assert data[0]["valor_medio"] == 39.90


def test_nao_detecta_com_apenas_2_meses(client):
    cat = _criar_categoria(client)
    _criar_transacao(client, cat["id"], "2026-01-05", 39.90, "Netflix")
    _criar_transacao(client, cat["id"], "2026-02-05", 39.90, "Netflix")

    resp = client.get("/api/recurring")
    data = resp.json()
    assert len(data) == 0


def test_nao_detecta_meses_nao_consecutivos(client):
    cat = _criar_categoria(client)
    _criar_transacao(client, cat["id"], "2026-01-05", 39.90, "Netflix")
    _criar_transacao(client, cat["id"], "2026-03-05", 39.90, "Netflix")
    _criar_transacao(client, cat["id"], "2026-05-05", 39.90, "Netflix")

    resp = client.get("/api/recurring")
    data = resp.json()
    assert len(data) == 0


def test_detecta_recorrente_com_valor_proximo_nao_identico(client):
    cat = _criar_categoria(client)
    _criar_transacao(client, cat["id"], "2026-01-08", 89.90, "Conta de Energia")
    _criar_transacao(client, cat["id"], "2026-02-08", 92.30, "Conta de Energia")
    _criar_transacao(client, cat["id"], "2026-03-08", 88.50, "Conta de Energia")

    resp = client.get("/api/recurring")
    data = resp.json()
    assert len(data) == 1
    assert data[0]["ocorrencias"] == 3


def test_valores_muito_diferentes_nao_sao_agrupados(client):
    cat = _criar_categoria(client)
    _criar_transacao(client, cat["id"], "2026-01-08", 20.00, "Assinatura X")
    _criar_transacao(client, cat["id"], "2026-02-08", 20.00, "Assinatura X")
    _criar_transacao(client, cat["id"], "2026-03-08", 20.00, "Assinatura X")
    # valor bem diferente (upgrade de plano, > 5% de tolerância), mesma descrição,
    # não deve se juntar ao grupo de recorrência de R$20 já detectado
    _criar_transacao(client, cat["id"], "2026-04-08", 200.00, "Assinatura X")

    resp = client.get("/api/recurring")
    data = resp.json()
    grupo_20 = next(i for i in data if abs(i["valor_medio"] - 20.00) < 0.01)
    assert grupo_20["ocorrencias"] == 3
