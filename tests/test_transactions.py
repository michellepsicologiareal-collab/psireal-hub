"""Testes dos endpoints de categories e transactions, incluindo filtros,
paginação e bloqueio de exclusão de categoria com transações vinculadas."""
from __future__ import annotations


def _criar_categoria(client, nome="Mercado", tipo="despesa", cor="#F2B94D"):
    resp = client.post("/api/categories", json={"nome": nome, "tipo": tipo, "cor": cor, "essencial": True})
    assert resp.status_code == 201, resp.text
    return resp.json()


def _criar_transacao(client, category_id, data="2026-01-10", descricao="Compra", valor=100.0, tipo="despesa"):
    resp = client.post(
        "/api/transactions",
        json={
            "data": data,
            "descricao": descricao,
            "valor": valor,
            "tipo": tipo,
            "category_id": category_id,
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_criar_categoria(client):
    cat = _criar_categoria(client)
    assert cat["nome"] == "Mercado"
    assert cat["essencial"] is True
    assert isinstance(cat["id"], int)


def test_criar_transacao_valor_em_centavos_no_banco(client, conn):
    cat = _criar_categoria(client)
    tx = _criar_transacao(client, cat["id"], valor=123.45)
    assert tx["valor"] == 123.45

    row = conn.execute("SELECT valor_centavos FROM transactions WHERE id = ?", (tx["id"],)).fetchone()
    assert row["valor_centavos"] == 12345
    assert isinstance(row["valor_centavos"], int)


def test_bloquear_exclusao_categoria_com_transacoes(client):
    cat = _criar_categoria(client)
    _criar_transacao(client, cat["id"])

    resp = client.delete(f"/api/categories/{cat['id']}")
    assert resp.status_code == 409
    assert "transa" in resp.json()["detail"].lower()


def test_excluir_categoria_sem_transacoes_funciona(client):
    cat = _criar_categoria(client, nome="Categoria Vazia")
    resp = client.delete(f"/api/categories/{cat['id']}")
    assert resp.status_code == 204


def test_filtro_transactions_por_mes(client):
    cat = _criar_categoria(client)
    _criar_transacao(client, cat["id"], data="2026-01-05")
    _criar_transacao(client, cat["id"], data="2026-02-05")

    resp = client.get("/api/transactions", params={"mes": "2026-01"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["data"] == "2026-01-05"


def test_filtro_transactions_por_categoria_e_tipo(client):
    cat_despesa = _criar_categoria(client, nome="Despesa X", tipo="despesa")
    cat_receita = _criar_categoria(client, nome="Receita X", tipo="receita")
    _criar_transacao(client, cat_despesa["id"], tipo="despesa")
    _criar_transacao(client, cat_receita["id"], tipo="receita", valor=500.0)

    resp = client.get("/api/transactions", params={"tipo": "receita"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["tipo"] == "receita"

    resp = client.get("/api/transactions", params={"category_id": cat_despesa["id"]})
    assert resp.json()["total"] == 1


def test_filtro_transactions_por_busca(client):
    cat = _criar_categoria(client)
    _criar_transacao(client, cat["id"], descricao="Supermercado Extra")
    _criar_transacao(client, cat["id"], descricao="Farmácia São João")

    resp = client.get("/api/transactions", params={"busca": "Extra"})
    data = resp.json()
    assert data["total"] == 1
    assert "Extra" in data["items"][0]["descricao"]


def test_paginacao_transactions(client):
    cat = _criar_categoria(client)
    for i in range(5):
        _criar_transacao(client, cat["id"], data=f"2026-01-{10+i:02d}", descricao=f"Item {i}")

    resp = client.get("/api/transactions", params={"limit": 2, "offset": 0})
    data = resp.json()
    assert data["total"] == 5
    assert len(data["items"]) == 2
    assert data["limit"] == 2
    assert data["offset"] == 0


def test_ciclo_post_patch_delete_transacao(client):
    cat = _criar_categoria(client)
    tx = _criar_transacao(client, cat["id"], valor=50.0, descricao="Original")
    assert tx["valor"] == 50.0

    resp = client.patch(f"/api/transactions/{tx['id']}", json={"valor": 75.5, "descricao": "Atualizada"})
    assert resp.status_code == 200
    atualizada = resp.json()
    assert atualizada["valor"] == 75.5
    assert atualizada["descricao"] == "Atualizada"

    resp = client.delete(f"/api/transactions/{tx['id']}")
    assert resp.status_code == 204

    resp = client.get("/api/transactions", params={"category_id": cat["id"]})
    assert resp.json()["total"] == 0


def test_transacao_com_categoria_inexistente_falha(client):
    resp = client.post(
        "/api/transactions",
        json={"data": "2026-01-01", "descricao": "X", "valor": 10.0, "tipo": "despesa", "category_id": 9999},
    )
    assert resp.status_code == 422
