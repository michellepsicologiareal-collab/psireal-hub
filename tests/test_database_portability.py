from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

from app.db import (
    CompatRow,
    POSTGRES_MIGRATIONS,
    PostgresConnection,
    _normalize_row,
    _sanitize_postgres_url,
    _translate_postgres_sql,
    insert_and_get_id,
)


def test_postgres_sql_translation():
    sql = "UPDATE transactions SET descricao = ?, updated_at = datetime('now') WHERE id = ?"
    translated = _translate_postgres_sql(sql)

    assert translated.count("%s") == 2
    assert "CURRENT_TIMESTAMP" in translated
    assert "datetime('now')" not in translated


def test_supabase_vercel_metadata_is_removed_from_postgres_url():
    raw = (
        "postgresql://user:secret@db.example.com:5432/postgres"
        "?sslmode=require&supa=base-pooler.x&application_name=finpilot"
    )

    cleaned = _sanitize_postgres_url(raw)

    assert "supa=" not in cleaned
    assert "sslmode=require" in cleaned
    assert "application_name=finpilot" in cleaned
    assert cleaned.startswith("postgresql://user:secret@db.example.com:5432/postgres?")


def test_postgres_migrations_do_not_use_sqlite_only_syntax():
    schema = "\n".join(POSTGRES_MIGRATIONS)

    assert "AUTOINCREMENT" not in schema
    assert "datetime('now')" not in schema
    assert "BIGSERIAL PRIMARY KEY" in schema
    assert "ENABLE ROW LEVEL SECURITY" in schema
    assert "user_id UUID DEFAULT auth.uid()" in schema
    assert "CREATE POLICY finpilot_user_isolation" in schema
    assert "USING (user_id = auth.uid())" in schema
    assert "idx_conscious_checkins_user_week" in schema


def test_postgres_rows_keep_sqlite_style_access():
    row = _normalize_row(
        {
            "id": Decimal("7"),
            "data": date(2026, 7, 29),
            "created_at": datetime(2026, 7, 29, 12, tzinfo=timezone.utc),
        }
    )

    assert isinstance(row, CompatRow)
    assert row["id"] == 7
    assert row[0] == 7
    assert row["data"] == "2026-07-29"
    assert row["created_at"].startswith("2026-07-29T12:00:00")


def test_insert_and_get_id_uses_returning_on_postgres():
    class FakeCursor:
        def __init__(self):
            self.sql = ""
            self.params = ()

        def execute(self, sql, params):
            self.sql = sql
            self.params = params

        def fetchone(self):
            return {"id": 42}

    class FakeRawConnection:
        def __init__(self):
            self.cursor_instance = FakeCursor()

        def cursor(self, **_kwargs):
            return self.cursor_instance

    raw = FakeRawConnection()
    conn = PostgresConnection(raw)

    created_id = insert_and_get_id(
        conn,
        "INSERT INTO categories (nome, tipo, cor) VALUES (?, ?, ?)",
        ("Mercado", "despesa", "#123456"),
    )

    assert created_id == 42
    assert raw.cursor_instance.sql.endswith("RETURNING id")
    assert raw.cursor_instance.sql.count("%s") == 3


def test_postgres_connection_sets_authenticated_user_context():
    class FakeCursor:
        def __init__(self, calls):
            self.calls = calls

        def execute(self, sql, params):
            self.calls.append((sql, params))

    class FakeRawConnection:
        def __init__(self):
            self.calls = []

        def cursor(self, **_kwargs):
            return FakeCursor(self.calls)

    raw = FakeRawConnection()
    conn = PostgresConnection(raw)
    user_id = "67e55044-10b1-426f-9247-bb680e5fe0c8"

    conn.set_user_context(user_id)

    assert raw.calls[0][0] == "SET LOCAL ROLE authenticated"
    assert "request.jwt.claim.sub" in raw.calls[1][0]
    assert raw.calls[1][1] == (user_id,)
    assert "request.jwt.claim.role" in raw.calls[2][0]
