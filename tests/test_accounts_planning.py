from __future__ import annotations

from datetime import date


def test_account_crud(client):
    created = client.post(
        "/api/accounts",
        json={
            "account_type": "bank",
            "nome": "Conta principal",
            "instituicao": "Banco Teste",
            "valor": 1250.75,
            "subtipo": "Conta corrente",
            "cor": "#7046d9",
        },
    )
    assert created.status_code == 201
    account = created.json()
    assert account["valor"] == 1250.75

    updated = client.patch(f"/api/accounts/{account['id']}", json={"valor": 1400})
    assert updated.status_code == 200
    assert updated.json()["valor"] == 1400

    listed = client.get("/api/accounts")
    assert listed.status_code == 200
    assert len(listed.json()) == 1


def test_categories_accept_subcategories(client):
    parent = client.post(
        "/api/categories",
        json={
            "nome": "Casa",
            "tipo": "despesa",
            "cor": "#7046d9",
            "icone": "🏠",
            "essencial": True,
        },
    ).json()
    child = client.post(
        "/api/categories",
        json={
            "nome": "Móveis",
            "tipo": "despesa",
            "cor": "#7046d9",
            "icone": "🛋️",
            "essencial": False,
            "parent_id": parent["id"],
        },
    )
    assert child.status_code == 201
    assert child.json()["parent_id"] == parent["id"]


def test_scheduled_expense_can_be_paid_into_diary(client):
    category = client.post(
        "/api/categories",
        json={
            "nome": "Moradia",
            "tipo": "despesa",
            "cor": "#7868d8",
            "icone": "🏠",
            "essencial": True,
        },
    ).json()
    due = date.today().replace(day=1).isoformat()
    created = client.post(
        "/api/scheduled-expenses",
        json={
            "titulo": "Aluguel",
            "valor": 1600,
            "category_id": category["id"],
            "data_vencimento": due,
            "recorrencia": "mensal",
        },
    )
    assert created.status_code == 201
    expense = created.json()

    paid = client.post(
        f"/api/scheduled-expenses/{expense['id']}/pay",
        json={"data_pagamento": date.today().isoformat(), "metodo_pagamento": "Pix"},
    )
    assert paid.status_code == 200
    assert paid.json()["data_vencimento"] > date.today().isoformat()

    transactions = client.get(f"/api/transactions?mes={date.today():%Y-%m}&limit=20").json()["items"]
    assert len(transactions) == 1
    assert transactions[0]["descricao"] == "Aluguel"
    assert transactions[0]["valor"] == 1600


def test_purchase_plan_status(client):
    created = client.post(
        "/api/purchase-plans",
        json={
            "nome": "Notebook",
            "valor_estimado": 4500,
            "prioridade": "alta",
        },
    )
    assert created.status_code == 201
    plan = created.json()
    assert plan["status"] == "planejada"

    bought = client.patch(f"/api/purchase-plans/{plan['id']}", json={"status": "comprada"})
    assert bought.status_code == 200
    assert bought.json()["status"] == "comprada"
