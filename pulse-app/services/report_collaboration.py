from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from db.sqlite import connect_sqlite


class ReportCollaborationError(RuntimeError):
    pass


class ReportNotFound(ReportCollaborationError):
    pass


class DiscussionDisabled(ReportCollaborationError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def report_domain(db_path: str | Path, report_id: str) -> str | None:
    with connect_sqlite(db_path, readonly=True) as con:
        row = con.execute(
            "SELECT domain FROM report_session WHERE id=? LIMIT 1", (report_id,)
        ).fetchone()
    return str(row["domain"]) if row else None


def set_exclusions(
    db_path: str | Path,
    domain: str,
    *,
    action: str,
    targets: list[tuple[str, str, int]],
) -> int:
    now = _now()
    with connect_sqlite(db_path) as con:
        for scope, key, page_id in targets:
            if action == "include":
                con.execute(
                    "DELETE FROM report_exclusion "
                    "WHERE domain=? COLLATE NOCASE AND scope=? AND item_key=? AND page_id=?",
                    (domain, scope, key, page_id),
                )
            else:
                con.execute(
                    "INSERT OR IGNORE INTO report_exclusion"
                    "(domain,scope,item_key,page_id,created_at) VALUES (?,?,?,?,?)",
                    (domain, scope, key, page_id, now),
                )
        con.commit()
    return len(targets)


def load_human_interpretation(
    db_path: str | Path, domain: str, report_id: str
) -> dict:
    with connect_sqlite(db_path, readonly=True) as con:
        row = con.execute(
            "SELECT content,updated_at FROM report_human_interpretation "
            "WHERE domain=? COLLATE NOCASE AND report_id=?",
            (domain, report_id),
        ).fetchone()
    return dict(row) if row else {"content": "", "updated_at": None}


def save_human_interpretation(
    db_path: str | Path, domain: str, report_id: str, content: str
) -> str:
    updated_at = _now()
    with connect_sqlite(db_path) as con:
        con.execute(
            "INSERT INTO report_human_interpretation(domain,report_id,content,updated_at) "
            "VALUES (?,?,?,?) "
            "ON CONFLICT(domain,report_id) DO UPDATE SET "
            "content=excluded.content,updated_at=excluded.updated_at",
            (domain, report_id, content, updated_at),
        )
        con.commit()
    return updated_at


def load_report_notes(db_path: str | Path, domain: str) -> dict:
    with connect_sqlite(db_path, readonly=True) as con:
        rows = con.execute(
            "SELECT note_key,content,discussion_enabled,updated_at "
            "FROM report_note WHERE domain=? COLLATE NOCASE",
            (domain,),
        ).fetchall()
        replies = con.execute(
            "SELECT id,note_key,author_role,content,created_at "
            "FROM report_note_reply WHERE domain=? COLLATE NOCASE ORDER BY id",
            (domain,),
        ).fetchall()

    notes = {
        row["note_key"]: {
            "content": row["content"],
            "discussion_enabled": bool(row["discussion_enabled"]),
            "updated_at": row["updated_at"],
            "replies": [],
        }
        for row in rows
    }
    for row in replies:
        notes.setdefault(
            row["note_key"],
            {
                "content": "",
                "discussion_enabled": False,
                "updated_at": None,
                "replies": [],
            },
        )["replies"].append(dict(row))
    return notes


def save_report_note(
    db_path: str | Path,
    domain: str,
    key: str,
    content: str,
    discussion_enabled: bool,
) -> dict:
    updated_at = _now()
    with connect_sqlite(db_path) as con:
        con.execute(
            "INSERT INTO report_note(domain,note_key,content,discussion_enabled,updated_at) "
            "VALUES (?,?,?,?,?) "
            "ON CONFLICT(domain,note_key) DO UPDATE SET "
            "content=excluded.content,"
            "discussion_enabled=excluded.discussion_enabled,"
            "updated_at=excluded.updated_at",
            (domain, key, content, int(discussion_enabled), updated_at),
        )
        con.commit()
    return {
        "updated_at": updated_at,
        "has_note": bool(content.strip()),
        "discussion_enabled": bool(discussion_enabled),
    }


def add_reply(
    db_path: str | Path,
    domain: str,
    key: str,
    content: str,
    *,
    author_role: str,
) -> dict:
    role = author_role if author_role in {"owner", "client"} else "client"
    with connect_sqlite(db_path) as con:
        note = con.execute(
            "SELECT discussion_enabled FROM report_note "
            "WHERE domain=? COLLATE NOCASE AND note_key=?",
            (domain, key),
        ).fetchone()
        if not note or not bool(note["discussion_enabled"]):
            raise DiscussionDisabled("discussion is not enabled for this note")

        created_at = _now()
        cur = con.execute(
            "INSERT INTO report_note_reply(domain,note_key,author_role,content,created_at) "
            "VALUES (?,?,?,?,?)",
            (domain, key, role, content, created_at),
        )
        con.commit()
    return {
        "id": cur.lastrowid,
        "created_at": created_at,
        "author_role": role,
    }


def add_public_reply(
    db_path: str | Path,
    report_id: str,
    key: str,
    content: str,
) -> dict:
    domain = report_domain(db_path, report_id)
    if not domain:
        raise ReportNotFound("report not found")
    return add_reply(db_path, domain, key, content, author_role="client")
