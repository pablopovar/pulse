from __future__ import annotations

import argparse
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from db.sqlite import connect_sqlite

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"
VERSION_RE = re.compile(r"^(?P<version>\d{4})_(?P<name>[A-Za-z0-9_.-]+)\.sql$")


class SchemaCompatibilityError(RuntimeError):
    pass


def migration_files():
    found = []
    for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
        match = VERSION_RE.match(path.name)
        if match:
            found.append((int(match.group("version")), path))
    versions = [version for version, _ in found]
    if len(versions) != len(set(versions)):
        raise RuntimeError("Duplicate migration versions detected.")
    return found


def latest_version():
    migrations = migration_files()
    return migrations[-1][0] if migrations else 0


def ensure_migration_table(con):
    con.execute(
        "CREATE TABLE IF NOT EXISTS schema_migration ("
        "version INTEGER PRIMARY KEY,"
        "name TEXT NOT NULL,"
        "applied_at TEXT NOT NULL)"
    )
    con.commit()


def applied_versions(con):
    ensure_migration_table(con)
    return {
        int(row["version"])
        for row in con.execute("SELECT version FROM schema_migration")
    }


def migrate_up(db_path):
    con = connect_sqlite(db_path)
    try:
        applied = applied_versions(con)
        newly_applied = []

        for version, path in migration_files():
            if version in applied:
                continue

            sql = path.read_text()
            now = datetime.now(timezone.utc).isoformat(timespec="seconds")
            try:
                con.execute("BEGIN IMMEDIATE")
                con.executescript(sql)
                con.execute(
                    "INSERT INTO schema_migration(version,name,applied_at) VALUES (?,?,?)",
                    (version, path.name, now),
                )
                con.commit()
            except Exception:
                con.rollback()
                raise

            newly_applied.append(version)

        return newly_applied
    finally:
        con.close()


def validate_schema_current(db_path):
    path = Path(db_path)
    if not path.exists():
        raise SchemaCompatibilityError(
            f"Pulse database does not exist: {path}. Run migrations before starting the app."
        )

    con = connect_sqlite(path, readonly=True)
    try:
        ledger = con.execute(
            "SELECT 1 FROM sqlite_master "
            "WHERE type='table' AND name='schema_migration'"
        ).fetchone()
        if not ledger:
            raise SchemaCompatibilityError(
                "Pulse database is not migration-managed. "
                "Run: python -m db.migrate up"
            )

        row = con.execute(
            "SELECT MAX(version) AS version FROM schema_migration"
        ).fetchone()
        current = int(row["version"] or 0)
        expected = latest_version()
        if current != expected:
            raise SchemaCompatibilityError(
                f"Pulse schema version {current} is not current; expected {expected}. "
                "Run: python -m db.migrate up"
            )
    finally:
        con.close()


def main():
    parser = argparse.ArgumentParser(description="Pulse database migration runner")
    parser.add_argument("command", choices=["up", "status"], nargs="?", default="up")
    parser.add_argument(
        "--db",
        default=os.environ.get("RESEARCH_DB", "/data/audit/research.db"),
    )
    args = parser.parse_args()

    if args.command == "up":
        applied = migrate_up(args.db)
        if applied:
            print("Applied migrations: " + ", ".join(map(str, applied)))
        else:
            print("Database already current.")
        return 0

    validate_schema_current(args.db)
    print(f"Database schema is current at version {latest_version()}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
