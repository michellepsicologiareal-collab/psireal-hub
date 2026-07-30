"""Importador tolerante de extrato CSV.

Detecta delimitador e colunas (data/descrição/valor) com variações comuns
de nome em pt-BR, aceita valor com vírgula decimal/formato brasileiro,
faz de-duplicação (mesma data+descricao+valor) e retorna resumo detalhado.
"""
from __future__ import annotations

import csv
import io
import re
import sqlite3
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

# Nomes de coluna aceitos (normalizados: minúsculo, sem acento) por campo lógico.
COLUNAS_DATA = {"data", "dt", "date", "data lancamento", "data_lancamento", "dt lancamento", "data mov", "data movimento"}
COLUNAS_DESCRICAO = {
    "descricao", "descrição", "desc", "historico", "histórico", "historico lancamento",
    "lancamento", "lançamento", "detalhes", "descricao lancamento", "title", "memo",
}
COLUNAS_VALOR = {
    "valor", "valor (r$)", "valor r$", "montante", "quantia", "amount", "vl",
    "valor lancamento", "valor transacao", "valor transação",
}

FORMATOS_DATA = [
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%d/%m/%y",
    "%m/%d/%Y",
]


def _normalizar_cabecalho(nome: str) -> str:
    nome = nome.strip().lower()
    nome = (
        nome.replace("á", "a").replace("ã", "a").replace("â", "a")
        .replace("é", "e").replace("ê", "e")
        .replace("í", "i")
        .replace("ó", "o").replace("õ", "o").replace("ô", "o")
        .replace("ú", "u")
        .replace("ç", "c")
    )
    return nome


def _detectar_delimitador(amostra: str) -> str:
    try:
        dialect = csv.Sniffer().sniff(amostra, delimiters=[",", ";", "\t", "|"])
        return dialect.delimiter
    except csv.Error:
        # fallback: conta ocorrências dos delimitadores mais comuns na primeira linha
        primeira_linha = amostra.splitlines()[0] if amostra.splitlines() else ""
        contagens = {d: primeira_linha.count(d) for d in [",", ";", "\t", "|"]}
        return max(contagens, key=contagens.get) if any(contagens.values()) else ","


def _mapear_colunas(cabecalho: list[str]) -> dict[str, int]:
    mapa: dict[str, int] = {}
    for idx, nome_original in enumerate(cabecalho):
        nome_norm = _normalizar_cabecalho(nome_original)
        if nome_norm in COLUNAS_DATA and "data" not in mapa:
            mapa["data"] = idx
        elif nome_norm in COLUNAS_DESCRICAO and "descricao" not in mapa:
            mapa["descricao"] = idx
        elif nome_norm in COLUNAS_VALOR and "valor" not in mapa:
            mapa["valor"] = idx
    return mapa


def _parse_data(valor: str) -> str:
    valor = valor.strip()
    for fmt in FORMATOS_DATA:
        try:
            dt = datetime.strptime(valor, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    raise ValueError(f"data inválida: '{valor}'")


def _parse_valor_centavos(valor: str) -> int:
    """Aceita formatos: '1234.56', '1234,56', '1.234,56', 'R$ 1.234,56', '-45,00'."""
    original = valor
    valor = valor.strip().replace("R$", "").replace("r$", "").strip()
    if not valor:
        raise ValueError(f"valor vazio: '{original}'")

    negativo = valor.startswith("-")
    valor = valor.lstrip("-").strip()

    # Formato brasileiro: milhar com '.', decimal com ','
    if "," in valor:
        valor = valor.replace(".", "").replace(",", ".")
    # Se não tem vírgula mas tem múltiplos pontos, assume pontos de milhar (raro, mas tolerante)
    elif valor.count(".") > 1:
        partes = valor.split(".")
        valor = "".join(partes[:-1]) + "." + partes[-1]

    if not re.match(r"^\d+(\.\d+)?$", valor):
        raise ValueError(f"valor não numérico: '{original}'")

    try:
        decimal = Decimal(valor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except InvalidOperation as exc:
        raise ValueError(f"valor não numérico: '{original}'") from exc
    centavos = int(decimal * 100)
    return -centavos if negativo else centavos


def import_csv(conn: sqlite3.Connection, conteudo_bytes: bytes) -> dict:
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            texto = conteudo_bytes.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        texto = conteudo_bytes.decode("utf-8", errors="replace")

    linhas_nao_vazias = [l for l in texto.splitlines() if l.strip()]
    if not linhas_nao_vazias:
        return {"importadas": 0, "ignoradas_duplicadas": 0, "com_erro": 0, "erros": []}

    amostra = "\n".join(linhas_nao_vazias[:5])
    delimitador = _detectar_delimitador(amostra)

    reader = csv.reader(io.StringIO(texto), delimiter=delimitador)
    linhas = [linha for linha in reader if any(campo.strip() for campo in linha)]

    if not linhas:
        return {"importadas": 0, "ignoradas_duplicadas": 0, "com_erro": 0, "erros": []}

    cabecalho = linhas[0]
    mapa_colunas = _mapear_colunas(cabecalho)

    linhas_dados = linhas[1:]
    inicio_numero_linha = 2  # linha 1 é o cabeçalho

    faltando = {"data", "descricao", "valor"} - mapa_colunas.keys()
    if faltando:
        erro_msg = f"colunas obrigatórias não encontradas no cabeçalho: {', '.join(sorted(faltando))}"
        return {
            "importadas": 0,
            "ignoradas_duplicadas": 0,
            "com_erro": len(linhas_dados),
            "erros": [
                {"linha": inicio_numero_linha + i, "motivo": erro_msg, "conteudo": ";".join(linha)}
                for i, linha in enumerate(linhas_dados)
            ],
        }

    existentes = set(
        (r["data"], r["descricao"].strip().lower(), r["valor_centavos"])
        for r in conn.execute("SELECT data, descricao, valor_centavos FROM transactions").fetchall()
    )

    importadas = 0
    ignoradas_duplicadas = 0
    erros: list[dict] = []
    vistos_no_arquivo: set[tuple[str, str, int]] = set()

    idx_data = mapa_colunas["data"]
    idx_desc = mapa_colunas["descricao"]
    idx_valor = mapa_colunas["valor"]

    # Se nenhum valor do arquivo tem sinal negativo, é provável que se trate de
    # um extrato só de despesas (ex. fatura de cartão de crédito) -- nesse caso
    # tratamos todos os valores como despesa em vez de receita.
    algum_negativo = False
    for linha in linhas_dados:
        if len(linha) > idx_valor:
            bruto = linha[idx_valor].strip()
            if bruto.startswith("-"):
                algum_negativo = True
                break
    somente_despesas = not algum_negativo

    for i, linha in enumerate(linhas_dados):
        numero_linha = inicio_numero_linha + i
        conteudo_linha = delimitador.join(linha)

        try:
            if len(linha) <= max(idx_data, idx_desc, idx_valor):
                raise ValueError("número de colunas insuficiente")

            data_str = _parse_data(linha[idx_data])
            descricao = linha[idx_desc].strip()
            if not descricao:
                raise ValueError("descrição vazia")

            valor_centavos = _parse_valor_centavos(linha[idx_valor])
            if valor_centavos == 0:
                raise ValueError("valor igual a zero")

            # Convenção de extrato bancário: valor negativo = saída (despesa),
            # valor positivo = entrada (receita). Exceção: se o arquivo inteiro
            # não tem nenhum valor negativo, tratamos como extrato só de
            # despesas (ex. fatura de cartão de crédito).
            if somente_despesas:
                tipo = "despesa"
            else:
                tipo = "receita" if valor_centavos > 0 else "despesa"
            valor_centavos_abs = abs(valor_centavos)

            chave_dedupe = (data_str, descricao.strip().lower(), valor_centavos_abs)
            if chave_dedupe in existentes or chave_dedupe in vistos_no_arquivo:
                ignoradas_duplicadas += 1
                continue

            conn.execute(
                """
                INSERT INTO transactions (data, descricao, valor_centavos, tipo, category_id, metodo_pagamento, recorrente, notas)
                VALUES (?, ?, ?, ?, NULL, ?, 0, NULL)
                """,
                (data_str, descricao, valor_centavos_abs, tipo, "importado_csv"),
            )
            vistos_no_arquivo.add(chave_dedupe)
            importadas += 1
        except ValueError as e:
            erros.append({"linha": numero_linha, "motivo": str(e), "conteudo": conteudo_linha})
        except Exception as e:  # noqa: BLE001 - queremos capturar qualquer erro de linha e continuar
            erros.append({"linha": numero_linha, "motivo": f"erro inesperado: {e}", "conteudo": conteudo_linha})

    conn.commit()

    return {
        "importadas": importadas,
        "ignoradas_duplicadas": ignoradas_duplicadas,
        "com_erro": len(erros),
        "erros": erros,
    }
