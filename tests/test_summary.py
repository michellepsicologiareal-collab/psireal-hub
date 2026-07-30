"""Testes de summary: saldo, receita, despesa, taxa de poupança e variação
percentual mês a mês."""
from __future__ import annotations


def _criar_categoria(client, nome, tipo):
    resp = client.post("/api/categories", json={"nome": nome, "tipo": tipo, "cor": "#4C8DFF"})
    return resp.json()


def _criar_transacao(client, category_id, data, valor, tipo, descricao="Transação"):
    resp = client.post(
        "/api/transactions",
        json={"data": data, "descricao": descricao, "valor": valor, "tipo": tipo, "category_id": category_id},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_summary_calculo_basico(client):
    receita_cat = _criar_categoria(client, "Salário", "receita")
    despesa_cat = _criar_categoria(client, "Mercado", "despesa")

    _criar_transacao(client, receita_cat["id"], "2026-03-05", 5000.0, "receita")
    _criar_transacao(client, despesa_cat["id"], "2026-03-10", 3000.0, "despesa")

    resp = client.get("/api/summary", params={"mes": "2026-03"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_receita"] == 5000.0
    assert data["total_despesa"] == 3000.0
    assert data["saldo"] == 2000.0
    assert data["taxa_poupanca"] == 40.0


def test_summary_variacao_mes_a_mes(client):
    receita_cat = _criar_categoria(client, "Salário", "receita")
    despesa_cat = _criar_categoria(client, "Mercado", "despesa")

    # Mês anterior: receita 4000, despesa 2000, saldo 2000
    _criar_transacao(client, receita_cat["id"], "2026-02-05", 4000.0, "receita")
    _criar_transacao(client, despesa_cat["id"], "2026-02-10", 2000.0, "despesa")

    # Mês atual: receita 5000 (+25%), despesa 3000 (+50%), saldo 2000 (0%)
    _criar_transacao(client, receita_cat["id"], "2026-03-05", 5000.0, "receita")
    _criar_transacao(client, despesa_cat["id"], "2026-03-10", 3000.0, "despesa")

    resp = client.get("/api/summary", params={"mes": "2026-03"})
    data = resp.json()
    assert data["variacao_receita_pct"] == 25.0
    assert data["variacao_despesa_pct"] == 50.0
    assert data["variacao_saldo_pct"] == 0.0


def test_summary_sem_mes_anterior_retorna_variacao_nula(client):
    receita_cat = _criar_categoria(client, "Salário", "receita")
    _criar_transacao(client, receita_cat["id"], "2026-05-05", 1000.0, "receita")

    resp = client.get("/api/summary", params={"mes": "2026-05"})
    data = resp.json()
    assert data["variacao_receita_pct"] is None


def test_spending_by_category_ordenado_e_percentual(client):
    cat_a = _criar_categoria(client, "Categoria A", "despesa")
    cat_b = _criar_categoria(client, "Categoria B", "despesa")

    _criar_transacao(client, cat_a["id"], "2026-04-05", 300.0, "despesa")
    _criar_transacao(client, cat_b["id"], "2026-04-05", 700.0, "despesa")

    resp = client.get("/api/spending-by-category", params={"mes": "2026-04"})
    data = resp.json()
    assert len(data) == 2
    assert data[0]["category_nome"] == "Categoria B"
    assert data[0]["percentual"] == 70.0
    assert data[1]["percentual"] == 30.0


def test_trend_retorna_serie_mensal(client):
    resp = client.get("/api/trend", params={"meses": 3})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 3
    for item in data:
        assert "mes" in item and "receita" in item and "despesa" in item and "saldo" in item
