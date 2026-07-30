"""Testes de aritmética em centavos: garante que não há erro de arredondamento
ao converter reais <-> centavos e ao agregar valores monetários."""
from __future__ import annotations

from app.models import centavos_to_reais, reais_to_centavos


def test_reais_to_centavos_basico():
    assert reais_to_centavos(10.00) == 1000
    assert reais_to_centavos(0.01) == 1
    assert reais_to_centavos(123.45) == 12345


def test_reais_to_centavos_evita_erro_float():
    # 0.1 + 0.2 = 0.30000000000000004 em float puro -- garantimos que o
    # arredondamento correto (round) evita esse tipo de erro na conversão.
    assert reais_to_centavos(19.99) == 1999
    assert reais_to_centavos(2.90) == 290
    assert reais_to_centavos(0.29) == 29
    assert reais_to_centavos(1.005) == 101
    assert reais_to_centavos(8.615) == 862


def test_centavos_to_reais_basico():
    assert centavos_to_reais(1000) == 10.00
    assert centavos_to_reais(12345) == 123.45
    assert centavos_to_reais(1) == 0.01


def test_soma_de_centavos_nao_acumula_erro():
    valores_reais = [19.90, 9.90, 39.90, 0.10, 100.01]
    centavos = [reais_to_centavos(v) for v in valores_reais]
    total_centavos = sum(centavos)
    # Soma exata esperada: 1990+990+3990+10+10001 = 16981 centavos = 169.81
    assert total_centavos == 16981
    assert centavos_to_reais(total_centavos) == 169.81


def test_multiplas_conversoes_permanecem_inteiras():
    for i in range(1, 100000):
        valor_centavos_original = i
        valor_reais = centavos_to_reais(valor_centavos_original)
        valor_centavos_convertido = reais_to_centavos(valor_reais)
        assert valor_centavos_convertido == valor_centavos_original
