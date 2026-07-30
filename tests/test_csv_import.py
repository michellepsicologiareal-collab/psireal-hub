"""Testes do importador de CSV: delimitadores, colunas em pt-BR, valor com
vírgula decimal, de-duplicação e linhas inválidas."""
from __future__ import annotations

import io

from app.services.csv_import import _parse_valor_centavos


def test_parse_valor_usa_arredondamento_decimal_half_up():
    assert _parse_valor_centavos("8,615") == 862
    assert _parse_valor_centavos("1.005") == 101


def test_import_csv_formato_padrao_ponto_virgula(client):
    conteudo = (
        "Data;Descrição;Valor\n"
        "01/03/2026;Supermercado Extra;-150,50\n"
        "05/03/2026;Salário;5000,00\n"
    ).encode("utf-8")

    resp = client.post("/api/import/csv", files={"file": ("extrato.csv", io.BytesIO(conteudo), "text/csv")})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["importadas"] == 2
    assert data["ignoradas_duplicadas"] == 0
    assert data["com_erro"] == 0

    resp = client.get("/api/transactions", params={"mes": "2026-03"})
    itens = resp.json()["items"]
    assert len(itens) == 2
    descricoes = {i["descricao"] for i in itens}
    assert "Supermercado Extra" in descricoes
    valores = {i["valor"] for i in itens}
    assert 150.50 in valores
    assert 5000.00 in valores


def test_import_csv_formato_virgula_delimitador(client):
    conteudo = (
        "data,descricao,valor\n"
        "2026-04-10,Farmacia,-45.00\n"
    ).encode("utf-8")

    resp = client.post("/api/import/csv", files={"file": ("extrato.csv", io.BytesIO(conteudo), "text/csv")})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["importadas"] == 1


def test_import_csv_deduplicacao(client):
    conteudo = (
        "data;descricao;valor\n"
        "01/03/2026;Mercado;-100,00\n"
        "01/03/2026;Mercado;-100,00\n"
    ).encode("utf-8")

    resp = client.post("/api/import/csv", files={"file": ("extrato.csv", io.BytesIO(conteudo), "text/csv")})
    data = resp.json()
    assert data["importadas"] == 1
    assert data["ignoradas_duplicadas"] == 1

    # Importar de novo o mesmo arquivo: agora tudo deve ser duplicado (já no banco)
    resp2 = client.post(
        "/api/import/csv",
        files={"file": ("extrato2.csv", io.BytesIO(conteudo), "text/csv")},
    )
    data2 = resp2.json()
    assert data2["importadas"] == 0
    assert data2["ignoradas_duplicadas"] == 2


def test_import_csv_linhas_invalidas_com_motivo(client):
    conteudo = (
        "data;descricao;valor\n"
        "01/03/2026;Item Válido;-50,00\n"
        "data-invalida;Item Ruim;-30,00\n"
        "02/03/2026;;-20,00\n"
        "03/03/2026;Sem Valor;abc\n"
    ).encode("utf-8")

    resp = client.post("/api/import/csv", files={"file": ("extrato.csv", io.BytesIO(conteudo), "text/csv")})
    data = resp.json()
    assert data["importadas"] == 1
    assert data["com_erro"] == 3
    assert len(data["erros"]) == 3
    for erro in data["erros"]:
        assert erro["linha"] > 0
        assert erro["motivo"]


def test_import_csv_colunas_nao_reconhecidas_retorna_erro(client):
    conteudo = "coluna_x;coluna_y\nabc;def\n".encode("utf-8")
    resp = client.post("/api/import/csv", files={"file": ("extrato.csv", io.BytesIO(conteudo), "text/csv")})
    data = resp.json()
    assert data["importadas"] == 0
    assert data["com_erro"] == 1
    assert "coluna" in data["erros"][0]["motivo"].lower()


def test_import_csv_formato_brasileiro_milhar_e_decimal(client):
    conteudo = (
        "data;descricao;valor\n"
        "01/03/2026;Aluguel;-1.650,00\n"
    ).encode("utf-8")

    resp = client.post("/api/import/csv", files={"file": ("extrato.csv", io.BytesIO(conteudo), "text/csv")})
    data = resp.json()
    assert data["importadas"] == 1

    resp = client.get("/api/transactions", params={"mes": "2026-03"})
    itens = resp.json()["items"]
    assert itens[0]["valor"] == 1650.00
