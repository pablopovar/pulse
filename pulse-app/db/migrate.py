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


def migration_files() -> list[tuple[int, Path]]:
    migrations: list[tuple[int, Path]] = []
    for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
        match = VERSION_RE.match(path.name)
        if match:
            migrations.append((int(match.group("version")), path))

    versions = [version for version, _ in migrations]
    if len(versions) != len(set(versions)):
        raise RuntimeError("Duplicate migration versions detected.")
    return migrations


def latest_version() -> int:
    files = migration_files()
    return files[-1][0] if files else 0


def _ensure_ledger(con) -> None:
    # The migration subsystem exclusively owns its own ledger table.
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migration (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at TEXT NOT NULL
        )
        """
    )
    con.commit()


def applied_versions(con) -> set[int]:
    _ensure_ledger(con)
    return {
        int(row["version"])
        for row in con.execute("SELECT version FROM schema_migration ORDER BY version")
    }


def _sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def migrate_up(db_path: str | Path) -> list[int]:
    """Apply each pending SQL migration atomically with its ledger row."""
    con = connect_sqlite(db_path)
    try:
        applied = applied_versions(con)
        newly_applied: list[int] = []

        for version, path in migration_files():
            if version in applied:
                continue

            applied_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
            body = path.read_text().strip()

            # sqlite3.executescript() commits pending transactions before it runs,
            # so BEGIN/COMMIT must be inside the script itself. This keeps the
            # migration body and ledger insertion atomic.
            script = (
                "BEGIN IMMEDIATE;\n"
                + body
                + "\nINSERT INTO schema_migration(version,name,applied_at) VALUES ("
                + str(version)
                + ","
                + _sql_literal(path.name)
                + ","
                + _sql_literal(applied_at)
                + ");\nCOMMIT;\n"
            )

            try:
                con.executescript(script)
            except Exception:
                try:
                    con.execute("ROLLBACK")
                except Exception:
                    pass
                raise

            newly_applied.append(version)
            applied.add(version)

        return newly_applied
    finally:
        con.close()


def validate_schema_current(db_path: str | Path) -> None:
    path = Path(db_path)
    if not path.exists():
        raise SchemaCompatibilityError(
            f"Pulse database does not exist: {path}. Run migrations before starting Pulse."
        )

    con = connect_sqlite(path, readonly=True)
    try:
        ledger = con.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='schema_migration'"
        ).fetchone()
        if not ledger:
            raise SchemaCompatibilityError(
                "Pulse database is not migration-managed. Run: python -m db.migrate up"
            )

        applied = {
            int(row["version"])
            for row in con.execute("SELECT version FROM schema_migration")
        }
        expected = {version for version, _ in migration_files()}
        missing = sorted(expected - applied)
        unknown = sorted(applied - expected)

        if missing or unknown:
            details = []
            if missing:
                details.append(f"missing migrations {missing}")
            if unknown:
                details.append(f"unknown migrations {unknown}")
            raise SchemaCompatibilityError(
                "Pulse schema is incompatible: " + "; ".join(details)
            )
    finally:
        con.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Pulse database migrations")
    parser.add_argument("command", choices=["up", "status"], nargs="?", default="up")
    parser.add_argument(
        "--db",
        default=os.environ.get("RESEARCH_DB", "/data/audit/research.db"),
    )
    args = parser.parse_args()

    if args.command == "up":
        applied = migrate_up(args.db)
        if applied:
            print("Applied migrations: " + ", ".join(str(v) for v in applied))
        else:
            print("Database already current.")
        return 0

    validate_schema_current(args.db)
    print(f"Database schema is current at version {latest_version()}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
