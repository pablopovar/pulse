from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from werkzeug.security import check_password_hash, generate_password_hash

from db.sqlite import connect_sqlite


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def access_state(db_path: Path, domain: str) -> dict[str, object]:
    with connect_sqlite(db_path, readonly=True) as con:
        row = con.execute(
            "SELECT enabled,password_hash,updated_at FROM domain_public_report_access "
            "WHERE domain=? COLLATE NOCASE", (domain,)
        ).fetchone()
    return {
        "enabled": bool(row and row["enabled"] and row["password_hash"]),
        "configured": bool(row and row["password_hash"]),
        "updated_at": row["updated_at"] if row else "",
    }


def access_state_for_report(db_path: Path, report_id: str) -> dict[str, object] | None:
    """Resolve a report's optional password policy through the DB subsystem.

    Returning ``None`` means the report is not resolvable here. The report
    route remains responsible for its 404 response; this preserves the generic
    security boundary's ability to run in isolated tests.
    """
    try:
        with connect_sqlite(db_path, readonly=True) as con:
            row = con.execute(
                """SELECT r.domain,a.enabled,a.password_hash,a.updated_at
                   FROM report_session r
                   LEFT JOIN domain_public_report_access a
                     ON a.domain=r.domain COLLATE NOCASE
                   WHERE r.id=? LIMIT 1""",
                (report_id,),
            ).fetchone()
    except Exception:
        return None
    if not row:
        return None
    return {
        "domain": str(row["domain"]),
        "enabled": bool(row["enabled"] and row["password_hash"]),
        "configured": bool(row["password_hash"]),
        "updated_at": row["updated_at"] or "",
    }


def set_access_password(db_path: Path, domain: str, password: str, *, enabled: bool = True) -> dict[str, object]:
    if len(password) < 12:
        raise ValueError("Client report password must be at least 12 characters.")
    with connect_sqlite(db_path) as con:
        con.execute(
            """INSERT INTO domain_public_report_access(domain,password_hash,enabled,updated_at)
               VALUES (?,?,?,?)
               ON CONFLICT(domain) DO UPDATE SET password_hash=excluded.password_hash,
                 enabled=excluded.enabled,updated_at=excluded.updated_at""",
            (domain, generate_password_hash(password), int(enabled), _now()),
        )
        con.commit()
    return access_state(db_path, domain)


def disable_access_password(db_path: Path, domain: str) -> dict[str, object]:
    with connect_sqlite(db_path) as con:
        con.execute(
            """INSERT INTO domain_public_report_access(domain,password_hash,enabled,updated_at)
               VALUES (?, '', 0, ?)
               ON CONFLICT(domain) DO UPDATE SET enabled=0,updated_at=excluded.updated_at""",
            (domain, _now()),
        )
        con.commit()
    return access_state(db_path, domain)


def password_valid(db_path: Path, domain: str, password: str) -> bool:
    with connect_sqlite(db_path, readonly=True) as con:
        row = con.execute(
            "SELECT password_hash,enabled FROM domain_public_report_access "
            "WHERE domain=? COLLATE NOCASE", (domain,)
        ).fetchone()
    return bool(row and row["enabled"] and row["password_hash"] and check_password_hash(row["password_hash"], password))
