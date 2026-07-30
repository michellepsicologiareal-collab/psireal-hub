from __future__ import annotations

import os
import sqlite3
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import get_connection, run_migrations  # noqa: E402


@pytest.fixture()
def db_path(tmp_path, monkeypatch):
    path = str(tmp_path / "test_finpilot.db")
    monkeypatch.setenv("FINPILOT_DB_PATH", path)
    run_migrations(path)
    yield path


@pytest.fixture()
def conn(db_path):
    connection = get_connection(db_path)
    yield connection
    connection.close()


@pytest.fixture()
def client(db_path, monkeypatch):
    # Garante que app.db use o mesmo DB_PATH do teste (o módulo já lê a env var
    # no import, então atualizamos o atributo diretamente por segurança).
    import app.db as db_module

    monkeypatch.setattr(db_module, "DB_PATH", db_path)

    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client
