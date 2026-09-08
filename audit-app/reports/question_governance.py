from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any

PHASES = {"blind", "named"}
SEARCH_MODES = {"off", "on"}
SOURCE_TYPES = {"third_party", "first_party", "model_prior", "unknown"}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def ensure_schema(con: sqlite3.Connection) -> None:
        pass
        pass
        pass
        pass
    con.commit()


def create_question_set(con: sqlite3.Connection, domain: str, version: int, questions: list[dict[str, Any]], comparison_set: list[str], label: str = "") -> None:
    ensure_schema(con)
    if not comparison_set:
        raise ValueError("comparison_set is a required human decision")
    con.execute("INSERT INTO ai_question_set(domain,version,label,approved,comparison_set_json,created_at) VALUES (?,?,?,0,?,?)", (domain, version, label, json.dumps(comparison_set), now_iso()))
    for pos, q in enumerate(questions, start=1):
        phase = str(q.get("phase") or "")
        if phase not in PHASES:
            raise ValueError(f"invalid phase: {phase}")
        con.execute("INSERT INTO ai_question_definition(domain,question_set_version,question_id,phase,position,question_text,category_tag) VALUES (?,?,?,?,?,?,?)", (domain, version, q["question_id"], phase, pos, q["question_text"], q.get("category_tag") or ""))
    con.commit()


def approve_question_set(con: sqlite3.Connection, domain: str, version: int) -> None:
    ensure_schema(con)
    row = con.execute("SELECT 1 FROM ai_question_definition WHERE domain=? COLLATE NOCASE AND question_set_version=? LIMIT 1", (domain, version)).fetchone()
    if not row:
        raise ValueError("question set has no questions")
    con.execute("UPDATE ai_question_set SET approved=1,approved_at=? WHERE domain=? COLLATE NOCASE AND version=?", (now_iso(), domain, version))
    con.commit()


def execution_matrix(con: sqlite3.Connection, domain: str, version: int, providers: list[str], repeats: int = 3) -> list[dict[str, Any]]:
    ensure_schema(con)
    qset = con.execute("SELECT approved FROM ai_question_set WHERE domain=? COLLATE NOCASE AND version=?", (domain, version)).fetchone()
    if not qset or not qset["approved"]:
        raise ValueError("question set must be human-approved before execution")
    questions = con.execute("SELECT question_id,phase,position,question_text,category_tag FROM ai_question_definition WHERE domain=? COLLATE NOCASE AND question_set_version=? ORDER BY CASE phase WHEN 'blind' THEN 1 ELSE 2 END,position", (domain, version)).fetchall()
    attempts = []
    for q in questions:
        for provider in providers:
            for search_mode in ("off", "on"):
                for repeat_index in range(1, max(1, repeats) + 1):
                    attempts.append({**dict(q), "question_set_version": version, "provider": provider, "search_mode": search_mode, "repeat_index": repeat_index})
    return attempts


def validate_atomic_claims(claims: Any) -> list[dict[str, Any]]:
    if not isinstance(claims, list):
        raise ValueError("atomic claims must be a list")
    out = []
    for item in claims:
        if not isinstance(item, dict) or not str(item.get("claim") or "").strip():
            raise ValueError("each atomic claim requires claim text")
        source_type = str(item.get("source_type") or "unknown")
        if source_type not in SOURCE_TYPES:
            raise ValueError(f"invalid source_type: {source_type}")
        confidence = item.get("confidence")
        if confidence is not None:
            confidence = float(confidence)
            if confidence < 0 or confidence > 1:
                raise ValueError("confidence must be between 0 and 1")
        out.append({"claim": str(item["claim"]).strip(), "source_type": source_type, "confidence": confidence, "source_url": item.get("source_url")})
    return out
