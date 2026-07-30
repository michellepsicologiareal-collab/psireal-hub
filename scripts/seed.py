"""Seed determinístico e idempotente do FinPilot.

Gera ~6 meses de dados realistas em BRL para um perfil de classe média
brasileira. Padrões propositais incluídos:
  - Categoria "Delivery" em tendência clara de alta mês a mês.
  - Orçamento de "Lazer" estourado no mês mais recente.
  - Assinaturas recorrentes de baixo valor "esquecidas" (ex. apps pouco usados).

Idempotente: se já existem categorias/transações geradas pelo seed (marcadas
via metodo_pagamento/notas específicos ou checagem de contagem), o script
limpa os dados de seed anteriores antes de regravar, produzindo sempre o
mesmo resultado determinístico (random.seed fixo).
"""
from __future__ import annotations

import random
import sqlite3
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import get_connection, run_migrations  # noqa: E402
from app.services.dates import somar_meses  # noqa: E402

SEED_MARKER = "seed_script"
RANDOM_SEED = 42
MESES_HISTORICO = 6

CATEGORIAS = [
    {"nome": "Salário", "tipo": "receita", "cor": "#2FD68C", "icone": "wallet", "essencial": 1},
    {"nome": "Freelance", "tipo": "receita", "cor": "#5FD4D0", "icone": "briefcase", "essencial": 0},
    {"nome": "Moradia", "tipo": "despesa", "cor": "#4C8DFF", "icone": "home", "essencial": 1},
    {"nome": "Mercado", "tipo": "despesa", "cor": "#F2B94D", "icone": "shopping-cart", "essencial": 1},
    {"nome": "Transporte", "tipo": "despesa", "cor": "#8BA3C7", "icone": "car", "essencial": 1},
    {"nome": "Energia", "tipo": "despesa", "cor": "#C792EA", "icone": "zap", "essencial": 1},
    {"nome": "Internet", "tipo": "despesa", "cor": "#5FD4D0", "icone": "wifi", "essencial": 1},
    {"nome": "Saúde", "tipo": "despesa", "cor": "#FF5C6C", "icone": "heart", "essencial": 1},
    {"nome": "Streaming", "tipo": "despesa", "cor": "#FF7A45", "icone": "tv", "essencial": 0},
    {"nome": "Delivery", "tipo": "despesa", "cor": "#F2B94D", "icone": "package", "essencial": 0},
    {"nome": "Lazer", "tipo": "despesa", "cor": "#C792EA", "icone": "smile", "essencial": 0},
    {"nome": "Farmácia", "tipo": "despesa", "cor": "#FF5C6C", "icone": "activity", "essencial": 1},
    {"nome": "Imprevistos", "tipo": "despesa", "cor": "#FF7A45", "icone": "alert-triangle", "essencial": 0},
    {"nome": "Assinaturas Diversas", "tipo": "despesa", "cor": "#8BA3C7", "icone": "repeat", "essencial": 0},
]

ORCAMENTOS_PADRAO = {
    "Moradia": 1800.00,
    "Mercado": 900.00,
    "Transporte": 400.00,
    "Energia": 220.00,
    "Internet": 120.00,
    "Saúde": 350.00,
    "Streaming": 80.00,
    "Delivery": 250.00,
    "Lazer": 300.00,
    "Farmácia": 150.00,
    "Assinaturas Diversas": 60.00,
}


def limpar_seed_anterior(conn: sqlite3.Connection) -> None:
    conn.execute("DELETE FROM transactions WHERE metodo_pagamento = ? OR notas = ?", (SEED_MARKER, SEED_MARKER))
    # budgets não tem coluna de marcação; removemos e recriamos todos os orçamentos padrão do seed
    conn.execute(
        "DELETE FROM budgets WHERE category_id IN (SELECT id FROM categories WHERE nome IN ({}))".format(
            ",".join("?" for _ in ORCAMENTOS_PADRAO)
        ),
        list(ORCAMENTOS_PADRAO.keys()),
    )
    conn.commit()


def get_or_create_categories(conn: sqlite3.Connection) -> dict[str, int]:
    ids: dict[str, int] = {}
    for cat in CATEGORIAS:
        row = conn.execute("SELECT id FROM categories WHERE nome = ?", (cat["nome"],)).fetchone()
        if row:
            ids[cat["nome"]] = row["id"]
        else:
            cursor = conn.execute(
                "INSERT INTO categories (nome, tipo, cor, icone, essencial) VALUES (?, ?, ?, ?, ?)",
                (cat["nome"], cat["tipo"], cat["cor"], cat["icone"], cat["essencial"]),
            )
            ids[cat["nome"]] = cursor.lastrowid
    conn.commit()
    return ids


def criar_orcamentos(conn: sqlite3.Connection, cat_ids: dict[str, int]) -> None:
    for nome, limite in ORCAMENTOS_PADRAO.items():
        conn.execute(
            "INSERT INTO budgets (category_id, mes, limite_centavos) VALUES (?, NULL, ?)",
            (cat_ids[nome], round(limite * 100)),
        )
    conn.commit()


def inserir_transacao(
    conn: sqlite3.Connection,
    rng: random.Random,
    data_ref: date,
    descricao: str,
    valor_reais: float,
    tipo: str,
    category_id: int,
    metodo: str,
    recorrente: bool = False,
) -> None:
    conn.execute(
        """
        INSERT INTO transactions (data, descricao, valor_centavos, tipo, category_id, metodo_pagamento, recorrente, notas)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            data_ref.isoformat(),
            descricao,
            round(valor_reais * 100),
            tipo,
            category_id,
            metodo if metodo != SEED_MARKER else SEED_MARKER,
            int(recorrente),
            SEED_MARKER,
        ),
    )


def dia_aleatorio(rng: random.Random, ano: int, mes: int, min_dia: int = 1, max_dia: int = 28) -> date:
    dia = rng.randint(min_dia, max_dia)
    return date(ano, mes, dia)


def gerar_dados(conn: sqlite3.Connection, cat_ids: dict[str, int]) -> None:
    rng = random.Random(RANDOM_SEED)

    hoje = date.today()
    mes_atual_str = f"{hoje.year:04d}-{hoje.month:02d}"
    meses = [somar_meses(mes_atual_str, -i) for i in range(MESES_HISTORICO - 1, -1, -1)]

    for idx, mes_str in enumerate(meses):
        ano, mes = int(mes_str[:4]), int(mes_str[5:7])
        eh_mes_mais_recente = idx == len(meses) - 1

        # --- Receita: salário mensal recorrente ---
        inserir_transacao(
            conn, rng, date(ano, mes, 5), "Salário mensal", 5200.00, "receita", cat_ids["Salário"], SEED_MARKER, recorrente=True
        )

        # Freelance ocasional (nem todo mês)
        if rng.random() < 0.4:
            valor_freela = round(rng.uniform(300, 900), 2)
            inserir_transacao(
                conn, rng, dia_aleatorio(rng, ano, mes), "Projeto freelance", valor_freela, "receita", cat_ids["Freelance"], SEED_MARKER
            )

        # --- Despesas fixas essenciais ---
        inserir_transacao(
            conn, rng, date(ano, mes, 1), "Aluguel apartamento", 1650.00, "despesa", cat_ids["Moradia"], SEED_MARKER, recorrente=True
        )
        inserir_transacao(
            conn, rng, dia_aleatorio(rng, ano, mes, 8, 12), "Conta de energia elétrica",
            round(rng.uniform(160, 240), 2), "despesa", cat_ids["Energia"], SEED_MARKER, recorrente=True
        )
        inserir_transacao(
            conn, rng, date(ano, mes, 10), "Internet fibra 300MB", 99.90, "despesa", cat_ids["Internet"], SEED_MARKER, recorrente=True
        )
        inserir_transacao(
            conn, rng, date(ano, mes, 15), "Plano de saúde", 340.00, "despesa", cat_ids["Saúde"], SEED_MARKER, recorrente=True
        )

        # Mercado: 3-4 compras no mês
        for _ in range(rng.randint(3, 4)):
            valor = round(rng.uniform(120, 320), 2)
            inserir_transacao(
                conn, rng, dia_aleatorio(rng, ano, mes), "Supermercado", valor, "despesa", cat_ids["Mercado"], SEED_MARKER
            )

        # Transporte/combustível: 2-3 abastecimentos + apps de transporte
        for _ in range(rng.randint(2, 3)):
            valor = round(rng.uniform(150, 250), 2)
            inserir_transacao(
                conn, rng, dia_aleatorio(rng, ano, mes), "Combustível posto", valor, "despesa", cat_ids["Transporte"], SEED_MARKER
            )
        for _ in range(rng.randint(2, 5)):
            valor = round(rng.uniform(15, 35), 2)
            inserir_transacao(
                conn, rng, dia_aleatorio(rng, ano, mes), "Corrida de aplicativo", valor, "despesa", cat_ids["Transporte"], SEED_MARKER
            )

        # --- Streaming: assinaturas recorrentes de valor estável ---
        inserir_transacao(conn, rng, date(ano, mes, 3), "Netflix", 39.90, "despesa", cat_ids["Streaming"], SEED_MARKER, recorrente=True)
        inserir_transacao(conn, rng, date(ano, mes, 7), "Spotify Premium", 21.90, "despesa", cat_ids["Streaming"], SEED_MARKER, recorrente=True)

        # --- Assinatura esquecida de baixo valor (padrão proposital) ---
        # Um app de meditação e um de nuvem de fotos, cobrados todo mês, baixo
        # valor, fácil de passar despercebido -- boa dica de "assinatura esquecida".
        inserir_transacao(
            conn, rng, date(ano, mes, 12), "App Meditar+ assinatura", 14.90, "despesa", cat_ids["Assinaturas Diversas"], SEED_MARKER, recorrente=True
        )
        inserir_transacao(
            conn, rng, date(ano, mes, 20), "CloudFotos Backup", 9.90, "despesa", cat_ids["Assinaturas Diversas"], SEED_MARKER, recorrente=True
        )

        # --- Delivery: tendência clara de alta mês a mês (padrão proposital) ---
        # idx vai de 0 (mês mais antigo) a MESES_HISTORICO-1 (mês mais recente).
        num_pedidos = 2 + idx  # cresce a cada mês: 2, 3, 4, 5, 6, 7
        for _ in range(num_pedidos):
            valor = round(rng.uniform(35, 65), 2)
            inserir_transacao(
                conn, rng, dia_aleatorio(rng, ano, mes), "Pedido delivery", valor, "despesa", cat_ids["Delivery"], SEED_MARKER
            )

        # --- Lazer: normal na maioria dos meses, mas estourado no mês mais recente ---
        if eh_mes_mais_recente:
            # Limite do orçamento de Lazer é R$ 300 -- geramos gastos que ultrapassam isso.
            gastos_lazer = [rng.uniform(80, 150) for _ in range(4)]
        else:
            gastos_lazer = [rng.uniform(40, 90) for _ in range(rng.randint(1, 3))]
        for valor in gastos_lazer:
            inserir_transacao(
                conn, rng, dia_aleatorio(rng, ano, mes), "Cinema/lazer", round(valor, 2), "despesa", cat_ids["Lazer"], SEED_MARKER
            )

        # --- Farmácia: ocasional ---
        if rng.random() < 0.7:
            valor = round(rng.uniform(30, 120), 2)
            inserir_transacao(
                conn, rng, dia_aleatorio(rng, ano, mes), "Farmácia", valor, "despesa", cat_ids["Farmácia"], SEED_MARKER
            )

        # --- Imprevistos: raro ---
        if rng.random() < 0.3:
            valor = round(rng.uniform(80, 400), 2)
            inserir_transacao(
                conn, rng, dia_aleatorio(rng, ano, mes), "Despesa imprevista", valor, "despesa", cat_ids["Imprevistos"], SEED_MARKER
            )

    conn.commit()


def main() -> None:
    run_migrations()
    conn = get_connection()
    try:
        limpar_seed_anterior(conn)
        cat_ids = get_or_create_categories(conn)
        criar_orcamentos(conn, cat_ids)
        gerar_dados(conn, cat_ids)

        total = conn.execute(
            "SELECT COUNT(*) AS total FROM transactions WHERE notas = ?", (SEED_MARKER,)
        ).fetchone()["total"]
        print(f"Seed concluído: {total} transações geradas, {len(CATEGORIAS)} categorias, {len(ORCAMENTOS_PADRAO)} orçamentos padrão.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
