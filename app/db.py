"""Camada de acesso ao banco de dados do FinPilot.

Em desenvolvimento e nos testes o projeto pode continuar usando SQLite. Na
Vercel, a presença de ``POSTGRES_URL`` (criada pela integração do Supabase)
ativa PostgreSQL automaticamente.

Todo valor monetário é armazenado como inteiro em centavos.
"""
from __future__ import annotations

import os
import re
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterator, Mapping, Sequence
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = os.environ.get("FINPILOT_DB_PATH", str(BASE_DIR / "finpilot.db"))


SQLITE_MIGRATIONS: list[str] = [
    """
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        parent_id INTEGER REFERENCES categories(id) ON DELETE CASCADE,
        nome TEXT NOT NULL,
        tipo TEXT NOT NULL CHECK (tipo IN ('despesa', 'receita')),
        cor TEXT NOT NULL,
        icone TEXT,
        essencial INTEGER NOT NULL DEFAULT 0 CHECK (essencial IN (0, 1)),
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data DATE NOT NULL,
        descricao TEXT NOT NULL,
        valor_centavos INTEGER NOT NULL CHECK (valor_centavos > 0),
        tipo TEXT NOT NULL CHECK (tipo IN ('despesa', 'receita')),
        category_id INTEGER REFERENCES categories(id),
        metodo_pagamento TEXT,
        recorrente INTEGER NOT NULL DEFAULT 0 CHECK (recorrente IN (0, 1)),
        notas TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS budgets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category_id INTEGER NOT NULL REFERENCES categories(id),
        mes TEXT,
        limite_centavos INTEGER NOT NULL CHECK (limite_centavos >= 0)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS goals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        valor_alvo_centavos INTEGER NOT NULL CHECK (valor_alvo_centavos >= 0),
        valor_atual_centavos INTEGER NOT NULL DEFAULT 0 CHECK (valor_atual_centavos >= 0),
        prazo DATE,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS user_settings (
        user_id TEXT NOT NULL DEFAULT 'local-user',
        chave TEXT NOT NULL,
        valor TEXT,
        PRIMARY KEY (user_id, chave)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS pluggy_connections (
        item_id TEXT PRIMARY KEY,
        connector_id TEXT,
        connector_name TEXT,
        status TEXT,
        execution_status TEXT,
        last_sync_at TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS pluggy_accounts (
        account_id TEXT PRIMARY KEY,
        item_id TEXT NOT NULL REFERENCES pluggy_connections(item_id) ON DELETE CASCADE,
        type TEXT,
        subtype TEXT,
        name TEXT NOT NULL,
        number_masked TEXT,
        balance_centavos INTEGER NOT NULL DEFAULT 0,
        currency_code TEXT NOT NULL DEFAULT 'BRL',
        credit_limit_centavos INTEGER,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS pluggy_transaction_links (
        provider_transaction_id TEXT PRIMARY KEY,
        account_id TEXT NOT NULL REFERENCES pluggy_accounts(account_id) ON DELETE CASCADE,
        transaction_id INTEGER UNIQUE REFERENCES transactions(id) ON DELETE SET NULL,
        provider_id TEXT,
        provider_status TEXT,
        raw_category TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS conscious_reflections (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        transaction_id INTEGER NOT NULL UNIQUE
            REFERENCES transactions(id) ON DELETE CASCADE,
        emotion TEXT NOT NULL,
        intensity INTEGER NOT NULL CHECK (intensity BETWEEN 1 AND 5),
        decision_type TEXT NOT NULL,
        context TEXT,
        automatic_thought TEXT,
        chosen_action TEXT,
        trigger_source TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS conscious_weekly_checkins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        week_start DATE NOT NULL UNIQUE,
        financial_stress INTEGER NOT NULL CHECK (financial_stress BETWEEN 1 AND 5),
        confidence INTEGER NOT NULL CHECK (confidence BETWEEN 1 AND 5),
        avoided_finances INTEGER NOT NULL DEFAULT 0 CHECK (avoided_finances IN (0, 1)),
        note TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS reminders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        titulo TEXT NOT NULL,
        data_vencimento DATE NOT NULL,
        valor_centavos INTEGER CHECK (valor_centavos IS NULL OR valor_centavos >= 0),
        recorrente INTEGER NOT NULL DEFAULT 0 CHECK (recorrente IN (0, 1)),
        concluido INTEGER NOT NULL DEFAULT 0 CHECK (concluido IN (0, 1)),
        notas TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS financial_accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        account_type TEXT NOT NULL CHECK (account_type IN ('bank', 'credit_card', 'investment')),
        nome TEXT NOT NULL,
        instituicao TEXT NOT NULL DEFAULT '',
        valor_centavos INTEGER NOT NULL DEFAULT 0 CHECK (valor_centavos >= 0),
        limite_centavos INTEGER CHECK (limite_centavos IS NULL OR limite_centavos >= 0),
        dia_fechamento INTEGER,
        dia_vencimento INTEGER,
        subtipo TEXT NOT NULL DEFAULT '',
        cor TEXT NOT NULL DEFAULT '#7b8f69',
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS purchase_plans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        valor_estimado_centavos INTEGER NOT NULL DEFAULT 0 CHECK (valor_estimado_centavos >= 0),
        prioridade TEXT NOT NULL DEFAULT 'media' CHECK (prioridade IN ('baixa', 'media', 'alta')),
        data_desejada DATE,
        notas TEXT,
        status TEXT NOT NULL DEFAULT 'planejada' CHECK (status IN ('planejada', 'comprada')),
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS scheduled_expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        titulo TEXT NOT NULL,
        valor_centavos INTEGER NOT NULL CHECK (valor_centavos > 0),
        category_id INTEGER REFERENCES categories(id),
        data_vencimento DATE NOT NULL,
        recorrencia TEXT NOT NULL DEFAULT 'mensal' CHECK (recorrencia IN ('unica', 'mensal')),
        notas TEXT,
        ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_transactions_data ON transactions(data)",
    "CREATE INDEX IF NOT EXISTS idx_transactions_category_id ON transactions(category_id)",
    "CREATE INDEX IF NOT EXISTS idx_transactions_tipo ON transactions(tipo)",
    "CREATE INDEX IF NOT EXISTS idx_pluggy_accounts_item_id ON pluggy_accounts(item_id)",
    "CREATE INDEX IF NOT EXISTS idx_pluggy_links_account_id ON pluggy_transaction_links(account_id)",
    "CREATE INDEX IF NOT EXISTS idx_pluggy_links_provider_id ON pluggy_transaction_links(account_id, provider_id)",
    "CREATE INDEX IF NOT EXISTS idx_conscious_reflections_emotion ON conscious_reflections(emotion)",
    "CREATE INDEX IF NOT EXISTS idx_conscious_checkins_week ON conscious_weekly_checkins(week_start)",
    "CREATE INDEX IF NOT EXISTS idx_reminders_due ON reminders(data_vencimento, concluido)",
    "CREATE INDEX IF NOT EXISTS idx_accounts_type ON financial_accounts(account_type)",
    "CREATE INDEX IF NOT EXISTS idx_purchase_plans_status ON purchase_plans(status)",
    "CREATE INDEX IF NOT EXISTS idx_scheduled_expenses_due ON scheduled_expenses(data_vencimento, ativo)",
]


POSTGRES_MIGRATIONS: list[str] = [
    """
    CREATE TABLE IF NOT EXISTS categories (
        id BIGSERIAL PRIMARY KEY,
        parent_id BIGINT REFERENCES categories(id) ON DELETE CASCADE,
        nome TEXT NOT NULL,
        tipo TEXT NOT NULL CHECK (tipo IN ('despesa', 'receita')),
        cor TEXT NOT NULL,
        icone TEXT,
        essencial INTEGER NOT NULL DEFAULT 0 CHECK (essencial IN (0, 1)),
        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS transactions (
        id BIGSERIAL PRIMARY KEY,
        data DATE NOT NULL,
        descricao TEXT NOT NULL,
        valor_centavos BIGINT NOT NULL CHECK (valor_centavos > 0),
        tipo TEXT NOT NULL CHECK (tipo IN ('despesa', 'receita')),
        category_id BIGINT REFERENCES categories(id),
        metodo_pagamento TEXT,
        recorrente INTEGER NOT NULL DEFAULT 0 CHECK (recorrente IN (0, 1)),
        notas TEXT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS budgets (
        id BIGSERIAL PRIMARY KEY,
        category_id BIGINT NOT NULL REFERENCES categories(id),
        mes TEXT,
        limite_centavos BIGINT NOT NULL CHECK (limite_centavos >= 0)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS goals (
        id BIGSERIAL PRIMARY KEY,
        nome TEXT NOT NULL,
        valor_alvo_centavos BIGINT NOT NULL CHECK (valor_alvo_centavos >= 0),
        valor_atual_centavos BIGINT NOT NULL DEFAULT 0 CHECK (valor_atual_centavos >= 0),
        prazo DATE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS user_settings (
        user_id UUID NOT NULL DEFAULT auth.uid(),
        chave TEXT NOT NULL,
        valor TEXT,
        PRIMARY KEY (user_id, chave)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS pluggy_connections (
        item_id TEXT PRIMARY KEY,
        connector_id TEXT,
        connector_name TEXT,
        status TEXT,
        execution_status TEXT,
        last_sync_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS pluggy_accounts (
        account_id TEXT PRIMARY KEY,
        item_id TEXT NOT NULL REFERENCES pluggy_connections(item_id) ON DELETE CASCADE,
        type TEXT,
        subtype TEXT,
        name TEXT NOT NULL,
        number_masked TEXT,
        balance_centavos BIGINT NOT NULL DEFAULT 0,
        currency_code TEXT NOT NULL DEFAULT 'BRL',
        credit_limit_centavos BIGINT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS pluggy_transaction_links (
        provider_transaction_id TEXT PRIMARY KEY,
        account_id TEXT NOT NULL REFERENCES pluggy_accounts(account_id) ON DELETE CASCADE,
        transaction_id BIGINT UNIQUE REFERENCES transactions(id) ON DELETE SET NULL,
        provider_id TEXT,
        provider_status TEXT,
        raw_category TEXT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS conscious_reflections (
        id BIGSERIAL PRIMARY KEY,
        transaction_id BIGINT NOT NULL UNIQUE REFERENCES transactions(id) ON DELETE CASCADE,
        emotion TEXT NOT NULL,
        intensity INTEGER NOT NULL CHECK (intensity BETWEEN 1 AND 5),
        decision_type TEXT NOT NULL,
        context TEXT,
        automatic_thought TEXT,
        chosen_action TEXT,
        trigger_source TEXT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS conscious_weekly_checkins (
        id BIGSERIAL PRIMARY KEY,
        week_start DATE NOT NULL,
        financial_stress INTEGER NOT NULL CHECK (financial_stress BETWEEN 1 AND 5),
        confidence INTEGER NOT NULL CHECK (confidence BETWEEN 1 AND 5),
        avoided_finances INTEGER NOT NULL DEFAULT 0 CHECK (avoided_finances IN (0, 1)),
        note TEXT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS reminders (
        id BIGSERIAL PRIMARY KEY,
        titulo TEXT NOT NULL,
        data_vencimento DATE NOT NULL,
        valor_centavos BIGINT CHECK (valor_centavos IS NULL OR valor_centavos >= 0),
        recorrente INTEGER NOT NULL DEFAULT 0 CHECK (recorrente IN (0, 1)),
        concluido INTEGER NOT NULL DEFAULT 0 CHECK (concluido IN (0, 1)),
        notas TEXT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS financial_accounts (
        id BIGSERIAL PRIMARY KEY,
        account_type TEXT NOT NULL CHECK (account_type IN ('bank', 'credit_card', 'investment')),
        nome TEXT NOT NULL,
        instituicao TEXT NOT NULL DEFAULT '',
        valor_centavos BIGINT NOT NULL DEFAULT 0 CHECK (valor_centavos >= 0),
        limite_centavos BIGINT CHECK (limite_centavos IS NULL OR limite_centavos >= 0),
        dia_fechamento INTEGER,
        dia_vencimento INTEGER,
        subtipo TEXT NOT NULL DEFAULT '',
        cor TEXT NOT NULL DEFAULT '#7b8f69',
        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS purchase_plans (
        id BIGSERIAL PRIMARY KEY,
        nome TEXT NOT NULL,
        valor_estimado_centavos BIGINT NOT NULL DEFAULT 0 CHECK (valor_estimado_centavos >= 0),
        prioridade TEXT NOT NULL DEFAULT 'media' CHECK (prioridade IN ('baixa', 'media', 'alta')),
        data_desejada DATE,
        notas TEXT,
        status TEXT NOT NULL DEFAULT 'planejada' CHECK (status IN ('planejada', 'comprada')),
        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS scheduled_expenses (
        id BIGSERIAL PRIMARY KEY,
        titulo TEXT NOT NULL,
        valor_centavos BIGINT NOT NULL CHECK (valor_centavos > 0),
        category_id BIGINT REFERENCES categories(id),
        data_vencimento DATE NOT NULL,
        recorrencia TEXT NOT NULL DEFAULT 'mensal' CHECK (recorrencia IN ('unica', 'mensal')),
        notas TEXT,
        ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_transactions_data ON transactions(data)",
    "CREATE INDEX IF NOT EXISTS idx_transactions_category_id ON transactions(category_id)",
    "CREATE INDEX IF NOT EXISTS idx_transactions_tipo ON transactions(tipo)",
    "CREATE INDEX IF NOT EXISTS idx_categories_parent ON categories(parent_id)",
    "CREATE INDEX IF NOT EXISTS idx_pluggy_accounts_item_id ON pluggy_accounts(item_id)",
    "CREATE INDEX IF NOT EXISTS idx_pluggy_links_account_id ON pluggy_transaction_links(account_id)",
    "CREATE INDEX IF NOT EXISTS idx_pluggy_links_provider_id ON pluggy_transaction_links(account_id, provider_id)",
    "CREATE INDEX IF NOT EXISTS idx_conscious_reflections_emotion ON conscious_reflections(emotion)",
    "CREATE INDEX IF NOT EXISTS idx_conscious_checkins_week ON conscious_weekly_checkins(week_start)",
    "CREATE INDEX IF NOT EXISTS idx_reminders_due ON reminders(data_vencimento, concluido)",
    "CREATE INDEX IF NOT EXISTS idx_accounts_type ON financial_accounts(account_type)",
    "CREATE INDEX IF NOT EXISTS idx_purchase_plans_status ON purchase_plans(status)",
    "CREATE INDEX IF NOT EXISTS idx_scheduled_expenses_due ON scheduled_expenses(data_vencimento, ativo)",
]

POSTGRES_USER_TABLES: tuple[str, ...] = (
    "categories",
    "transactions",
    "budgets",
    "goals",
    "user_settings",
    "pluggy_connections",
    "pluggy_accounts",
    "pluggy_transaction_links",
    "conscious_reflections",
    "conscious_weekly_checkins",
    "reminders",
    "financial_accounts",
    "purchase_plans",
    "scheduled_expenses",
)

# Acrescenta o dono a tabelas que já possam existir na Supabase e ativa RLS.
# O backend troca para o papel ``authenticated`` em cada requisição, portanto
# nem mesmo uma consulta esquecida sem WHERE consegue atravessar contas.
for _table in POSTGRES_USER_TABLES:
    POSTGRES_MIGRATIONS.extend(
        [
            f"ALTER TABLE {_table} ADD COLUMN IF NOT EXISTS user_id UUID DEFAULT auth.uid()",
            f"ALTER TABLE {_table} ENABLE ROW LEVEL SECURITY",
            f"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE {_table} TO authenticated",
            f"""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1
                    FROM pg_policies
                    WHERE schemaname = 'public'
                      AND tablename = '{_table}'
                      AND policyname = 'finpilot_user_isolation'
                ) THEN
                    CREATE POLICY finpilot_user_isolation ON {_table}
                    FOR ALL TO authenticated
                    USING (user_id = auth.uid())
                    WITH CHECK (user_id = auth.uid());
                END IF;
            EXCEPTION
                WHEN duplicate_object THEN NULL;
            END
            $$
            """,
        ]
    )

POSTGRES_MIGRATIONS.extend(
    [
        """
        ALTER TABLE categories
        ADD COLUMN IF NOT EXISTS parent_id BIGINT REFERENCES categories(id) ON DELETE CASCADE
        """,
        """
        ALTER TABLE conscious_weekly_checkins
        DROP CONSTRAINT IF EXISTS conscious_weekly_checkins_week_start_key
        """,
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_conscious_checkins_user_week
        ON conscious_weekly_checkins(user_id, week_start)
        """,
        "GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO authenticated",
    ]
)

# Compatibilidade com imports antigos e testes que apenas inspecionam a lista.
MIGRATIONS = SQLITE_MIGRATIONS


def _sanitize_postgres_url(value: str) -> str:
    """Remove metadados da integração Vercel que o libpq não reconhece.

    O Marketplace do Supabase pode acrescentar ``supa=...`` à URL apenas para
    identificar a origem da conexão. Esse parâmetro não pertence ao protocolo
    PostgreSQL e faz o psycopg encerrar a aplicação antes de conectar.
    """

    parts = urlsplit(value)
    query = [
        (key, item)
        for key, item in parse_qsl(parts.query, keep_blank_values=True)
        if key.casefold() != "supa"
    ]
    return urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urlencode(query, doseq=True), parts.fragment)
    )


def _postgres_url() -> str | None:
    for name in ("POSTGRES_URL", "DATABASE_URL", "POSTGRES_PRISMA_URL"):
        value = os.getenv(name, "").strip()
        if value:
            return _sanitize_postgres_url(value)
    return None


def _normalize_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    return value


class CompatRow(dict[str, Any]):
    """Linha com acesso por nome e, quando necessário, por posição."""

    def __getitem__(self, key: str | int) -> Any:
        if isinstance(key, int):
            return list(self.values())[key]
        return super().__getitem__(key)


def _normalize_row(row: Mapping[str, Any] | None) -> CompatRow | None:
    if row is None:
        return None
    return CompatRow((key, _normalize_value(value)) for key, value in row.items())


def _translate_postgres_sql(sql: str) -> str:
    translated = sql.replace("?", "%s")
    translated = re.sub(
        r"datetime\s*\(\s*'now'\s*\)",
        "CURRENT_TIMESTAMP",
        translated,
        flags=re.IGNORECASE,
    )
    return translated


class PostgresCursor:
    def __init__(self, cursor: Any):
        self._cursor = cursor
        self.lastrowid: int | None = None

    def fetchone(self) -> CompatRow | None:
        return _normalize_row(self._cursor.fetchone())

    def fetchall(self) -> list[CompatRow]:
        return [_normalize_row(row) for row in self._cursor.fetchall()]  # type: ignore[misc]


class PostgresConnection:
    dialect = "postgres"

    def __init__(self, raw_connection: Any):
        self._connection = raw_connection

    def execute(self, sql: str, params: Sequence[Any] | None = None) -> PostgresCursor:
        from psycopg.rows import dict_row

        cursor = self._connection.cursor(row_factory=dict_row)
        cursor.execute(_translate_postgres_sql(sql), tuple(params or ()))
        return PostgresCursor(cursor)

    def set_user_context(self, user_id: str) -> None:
        """Ativa o papel e o UUID usados pelas políticas RLS do Supabase."""

        from uuid import UUID

        safe_user_id = str(UUID(user_id))
        self.execute("SET LOCAL ROLE authenticated")
        self.execute("SELECT set_config('request.jwt.claim.sub', ?, true)", (safe_user_id,))
        self.execute("SELECT set_config('request.jwt.claim.role', 'authenticated', true)")

    def commit(self) -> None:
        self._connection.commit()

    def rollback(self) -> None:
        self._connection.rollback()

    def close(self) -> None:
        self._connection.close()


def get_connection(db_path: str | None = None) -> sqlite3.Connection | PostgresConnection:
    """Abre SQLite quando um caminho é informado; caso contrário usa Supabase se configurado."""

    postgres_url = None if db_path is not None else _postgres_url()
    if postgres_url:
        import psycopg

        raw = psycopg.connect(
            postgres_url,
            autocommit=False,
            prepare_threshold=None,
            connect_timeout=10,
        )
        return PostgresConnection(raw)

    sqlite_path = db_path or os.environ.get("FINPILOT_DB_PATH", DB_PATH)
    conn = sqlite3.connect(sqlite_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def insert_and_get_id(
    conn: sqlite3.Connection | PostgresConnection,
    sql: str,
    params: Sequence[Any],
) -> int:
    """Executa INSERT e retorna o id gerado nos dois bancos suportados."""

    if getattr(conn, "dialect", "sqlite") == "postgres":
        statement = sql.strip().rstrip(";") + " RETURNING id"
        row = conn.execute(statement, params).fetchone()
        if row is None:
            raise RuntimeError("O banco não retornou o identificador criado.")
        return int(row["id"])
    cursor = conn.execute(sql, params)
    return int(cursor.lastrowid)


def run_migrations(db_path: str | None = None) -> None:
    conn = get_connection(db_path)
    migrations = POSTGRES_MIGRATIONS if getattr(conn, "dialect", "sqlite") == "postgres" else SQLITE_MIGRATIONS
    try:
        for statement in migrations:
            conn.execute(statement)
        if getattr(conn, "dialect", "sqlite") == "sqlite":
            category_columns = {
                row["name"] for row in conn.execute("PRAGMA table_info(categories)").fetchall()
            }
            if "parent_id" not in category_columns:
                conn.execute(
                    "ALTER TABLE categories ADD COLUMN parent_id INTEGER REFERENCES categories(id) ON DELETE CASCADE"
                )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_categories_parent ON categories(parent_id)"
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@contextmanager
def get_db(db_path: str | None = None) -> Iterator[sqlite3.Connection | PostgresConnection]:
    conn = get_connection(db_path)
    try:
        yield conn
    finally:
        conn.close()


def get_db_dependency() -> Iterator[sqlite3.Connection | PostgresConnection]:
    conn = get_connection()
    try:
        if isinstance(conn, PostgresConnection):
            # Import tardio evita ciclo entre a camada de autenticação e banco.
            from app.security import get_current_user_id

            user_id = get_current_user_id()
            if not user_id:
                raise RuntimeError("Acesso ao banco PostgreSQL sem usuário autenticado.")
            conn.set_user_context(user_id)
        yield conn
    finally:
        conn.close()
