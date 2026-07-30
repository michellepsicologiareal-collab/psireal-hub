"""Testes de budgets/status: percentual, estado (normal/atencao/estourado) e
ritmo diário projetado."""
from __future__ import annotations

from datetime import date

from app.services.dates import mes_atual


def _criar_categoria(client, nome="Lazer", tipo="despesa"):
    resp = client.post("/api/categories", json={"nome": nome, "tipo": tipo, "cor": "#C792EA"})
    return resp.json()


def _criar_transacao(client, category_id, data, valor, tipo="despesa"):
    resp = client.post(
        "/api/transactions",
        json={"data": data, "descricao": "Gasto", "valor": valor, "tipo": tipo, "category_id": category_id},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _criar_orcamento(client, category_id, limite, mes=None):
    resp = client.post("/api/budgets", json={"category_id": category_id, "mes": mes, "limite": limite})
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_budget_estado_normal(client):
    cat = _criar_categoria(client)
    _criar_orcamento(client, cat["id"], limite=1000.0)

    mes = mes_atual()
    _criar_transacao(client, cat["id"], f"{mes}-01", 200.0)

    resp = client.get("/api/budgets/status", params={"mes": mes})
    data = resp.json()
    item = next(i for i in data if i["category_id"] == cat["id"])
    assert item["estado"] == "normal"
    assert item["percentual"] == 20.0


def test_budget_estado_atencao_acima_de_80_pct(client):
    cat = _criar_categoria(client)
    _criar_orcamento(client, cat["id"], limite=1000.0)

    mes = mes_atual()
    _criar_transacao(client, cat["id"], f"{mes}-01", 850.0)

    resp = client.get("/api/budgets/status", params={"mes": mes})
    data = resp.json()
    item = next(i for i in data if i["category_id"] == cat["id"])
    assert item["estado"] == "atencao"
    assert item["percentual"] == 85.0


def test_budget_estado_estourado(client):
    cat = _criar_categoria(client)
    _criar_orcamento(client, cat["id"], limite=500.0)

    mes = mes_atual()
    _criar_transacao(client, cat["id"], f"{mes}-01", 600.0)

    resp = client.get("/api/budgets/status", params={"mes": mes})
    data = resp.json()
    item = next(i for i in data if i["category_id"] == cat["id"])
    assert item["estado"] == "estourado"
    assert item["percentual"] == 120.0


def test_budget_dias_restantes_e_ritmo(client):
    cat = _criar_categoria(client)
    _criar_orcamento(client, cat["id"], limite=1000.0)

    mes = mes_atual()
    _criar_transacao(client, cat["id"], f"{mes}-01", 300.0)

    resp = client.get("/api/budgets/status", params={"mes": mes})
    data = resp.json()
    item = next(i for i in data if i["category_id"] == cat["id"])
    assert item["dias_restantes"] >= 0
    assert item["ritmo_diario_projetado"] >= 0


def test_budget_especifico_do_mes_sobrepoe_recorrente(client):
    cat = _criar_categoria(client)
    _criar_orcamento(client, cat["id"], limite=1000.0)  # recorrente (mes=None)

    mes = mes_atual()
    _criar_orcamento(client, cat["id"], limite=200.0, mes=mes)  # específico do mês

    _criar_transacao(client, cat["id"], f"{mes}-01", 150.0)

    resp = client.get("/api/budgets/status", params={"mes": mes})
    data = resp.json()
    item = next(i for i in data if i["category_id"] == cat["id"])
    assert item["limite"] == 200.0  # usou o específico, não o recorrente de 1000


def test_categoria_sem_orcamento_nao_aparece_no_status(client):
    cat = _criar_categoria(client, nome="Sem Orçamento")
    mes = mes_atual()
    _criar_transacao(client, cat["id"], f"{mes}-01", 100.0)

    resp = client.get("/api/budgets/status", params={"mes": mes})
    data = resp.json()
    assert all(i["category_id"] != cat["id"] for i in data)
