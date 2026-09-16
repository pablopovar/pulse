from __future__ import annotations

import ast
import re
import sqlite3
import threading
from pathlib import Path

import pytest

from db.migrate import (
    SchemaCompatibilityError,
    latest_version,
    migrate_up,
    validate_schema_current,
)
from db.ownership import TABLE_OWNERS
from db.sqlite import DEFAULT_BUSY_TIMEOUT_MS, connect_sqlite

APPDIR = Path(__file__).resolve().parents[1]
DDL_RE = re.compile(
    r"\b(?:CREATE\s+(?:TABLE|INDEX|UNIQUE\s+INDEX|VIEW|TRIGGER)|"
    r"ALTER\s+TABLE|DROP\s+(?:TABLE|INDEX|VIEW|TRIGGER))\b",
    re.I,
)

REQUIRED_TABLES = {
    "research_keyword",
    "wanted_keyword",
    "site_page",
    "audit_run",
    "crawl_run",
    "report_session",
    "manual_ai_source",
    "domain_source",
    "domain_discovery_state",
    "extension_global",
    "ai_question_set",
    "ai_question_definition",
    "ai_visibility_observation",
    "cross_model_provider_response",
    "cross_model_comparison",
    "domain_company_controlled_domain",
}


def _table_names(db: Path) -> set[str]:
    con = connect_sqlite(db, readonly=True)
    try:
        return {
            row["name"]
            for row in con.execute(
                "SELECT name FROM sqlite_master " "WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
        }
    finally:
        con.close()


def test_clean_database_is_created_entirely_by_migrations(tmp_path):
    db = tmp_path / "clean.db"
    applied = migrate_up(db)

    assert applied == list(range(1, latest_version() + 1))
    validate_schema_current(db)
    assert REQUIRED_TABLES <= _table_names(db)


def test_current_pre_migration_schema_is_adopted_and_completed(tmp_path):
    db = tmp_path / "legacy-current.db"
    baseline = (APPDIR / "db" / "migrations" / "0001_baseline.sql").read_text()

    raw = sqlite3.connect(db)
    try:
        raw.executescript(baseline)
        raw.commit()
    finally:
        raw.close()

    assert "schema_migration" not in _table_names(db)
    assert migrate_up(db) == list(range(1, latest_version() + 1))
    validate_schema_current(db)
    assert REQUIRED_TABLES <= _table_names(db)


def test_upgrade_from_version_one_applies_only_pending_migrations(tmp_path):
    db = tmp_path / "v1.db"
    baseline = (APPDIR / "db" / "migrations" / "0001_baseline.sql").read_text()

    raw = sqlite3.connect(db)
    try:
        raw.executescript(baseline)
        raw.execute(
            "CREATE TABLE schema_migration ("
            "version INTEGER PRIMARY KEY,name TEXT NOT NULL,applied_at TEXT NOT NULL)"
        )
        raw.execute(
            "INSERT INTO schema_migration(version,name,applied_at) VALUES (1,?,?)",
            ("0001_baseline.sql", "now"),
        )
        raw.commit()
    finally:
        raw.close()

    assert migrate_up(db) == [2, 3, 4, 5, 6]

    validate_schema_current(db)
    assert "cross_model_comparison" in _table_names(db)
    assert "domain_discovery_state" in _table_names(db)


def test_migrations_are_idempotent(tmp_path):
    db = tmp_path / "idempotent.db"
    migrate_up(db)
    assert migrate_up(db) == []


def test_schema_validation_rejects_unmanaged_database(tmp_path):
    db = tmp_path / "unmanaged.db"
    sqlite3.connect(db).close()
    with pytest.raises(SchemaCompatibilityError):
        validate_schema_current(db)


def test_writable_connections_use_wal_and_busy_timeout(tmp_path):
    db = tmp_path / "configured.db"
    migrate_up(db)

    con = connect_sqlite(db)
    try:
        assert con.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
        assert con.execute("PRAGMA busy_timeout").fetchone()[0] == DEFAULT_BUSY_TIMEOUT_MS
        assert con.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    finally:
        con.close()


def test_readonly_connections_are_query_only(tmp_path):
    db = tmp_path / "readonly.db"
    migrate_up(db)

    con = connect_sqlite(db, readonly=True)
    try:
        assert con.execute("PRAGMA query_only").fetchone()[0] == 1
        assert con.execute("PRAGMA busy_timeout").fetchone()[0] == DEFAULT_BUSY_TIMEOUT_MS
    finally:
        con.close()


def test_writer_contention_waits_for_lock_release(tmp_path):
    db = tmp_path / "contention.db"
    migrate_up(db)

    lock_held = threading.Event()
    release_lock = threading.Event()
    holder_error = []

    def hold_write_lock():
        con = connect_sqlite(db, busy_timeout_ms=1_000)
        try:
            con.execute("BEGIN IMMEDIATE")
            con.execute(
                "INSERT INTO schema_migration(version,name,applied_at) "
                "VALUES (9998,'lock-holder','now')"
            )
            lock_held.set()
            if not release_lock.wait(timeout=2):
                raise RuntimeError("test did not release the writer lock")
            con.rollback()
        except BaseException as exc:
            holder_error.append(exc)
            lock_held.set()
        finally:
            con.close()

    holder = threading.Thread(target=hold_write_lock)
    holder.start()
    assert lock_held.wait(timeout=2)
    assert holder_error == []

    second = connect_sqlite(db, busy_timeout_ms=1_000)
    try:
        assert second.execute("PRAGMA busy_timeout").fetchone()[0] == 1_000
        timer = threading.Timer(0.05, release_lock.set)
        timer.start()
        second.execute("BEGIN IMMEDIATE")
        second.rollback()
        timer.join(timeout=1)
    finally:
        release_lock.set()
        second.close()
        holder.join(timeout=2)

    assert not holder.is_alive()
    assert holder_error == []


def test_every_migration_table_has_exactly_one_owner(tmp_path):
    db = tmp_path / "ownership.db"
    migrate_up(db)
    tables = _table_names(db)

    assert tables - set(TABLE_OWNERS) == set()
    assert all(TABLE_OWNERS.get(table) for table in tables)


def test_no_runtime_schema_mutation_outside_db_subsystem():
    offenders = {}

    for path in APPDIR.rglob("*.py"):
        rel = path.relative_to(APPDIR)
        if rel.parts[0] in {"db", "tests"}:
            continue

        tree = ast.parse(path.read_text())
        hits = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if DDL_RE.search(node.value):
                    hits.append(node.lineno)
        if hits:
            offenders[str(rel)] = sorted(set(hits))

    assert offenders == {}


def test_no_direct_sqlite_connect_outside_db_subsystem():
    offenders = {}

    for path in APPDIR.rglob("*.py"):
        rel = path.relative_to(APPDIR)
        if rel.parts[0] in {"db", "tests"}:
            continue

        tree = ast.parse(path.read_text())
        hits = []
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "connect"
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "sqlite3"
            ):
                hits.append(node.lineno)
        if hits:
            offenders[str(rel)] = hits

    assert offenders == {}
