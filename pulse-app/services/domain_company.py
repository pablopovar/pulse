from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from db.sqlite import connect_sqlite


def _company_name_from_title(title) -> str:
    if not title:
        return ""
    candidate = str(title).strip()
    for separator in (" | ", " · ", " — ", " - ", ": "):
        if separator in candidate:
            candidate = candidate.split(separator, 1)[0].strip()
            break
    return candidate


def infer_company_name(db_path: str | Path, domain: str) -> str:
    with connect_sqlite(db_path, readonly=True) as con:
        row = con.execute(
            "SELECT company_name FROM domain_company_settings "
            "WHERE domain=? COLLATE NOCASE",
            (domain,),
        ).fetchone()
        if row and str(row["company_name"] or "").strip():
            return str(row["company_name"]).strip()

        row = con.execute(
            "SELECT cp.title FROM crawl_page cp "
            "JOIN crawl_run cr ON cr.id=cp.crawl_run_id "
            "WHERE cr.domain=? COLLATE NOCASE AND cp.path='/' "
            "AND TRIM(COALESCE(cp.title,''))<>'' "
            "ORDER BY cr.id DESC LIMIT 1",
            (domain,),
        ).fetchone()
        if row:
            candidate = _company_name_from_title(row["title"])
            if candidate:
                return candidate

    label = domain.lower().split(":")[0].strip().strip("/")
    if label.startswith("www."):
        label = label[4:]
    label = label.split(".")[0]
    words = [word for word in re.split(r"[-_]+", label) if word]
    return " ".join(word.capitalize() for word in words) if words else domain


def save_company_name(db_path: str | Path, domain: str, company_name: str) -> str:
    value = str(company_name or "").strip() or domain
    updated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with connect_sqlite(db_path) as con:
        con.execute(
            "INSERT INTO domain_company_settings(domain,company_name,updated_at) "
            "VALUES (?,?,?) "
            "ON CONFLICT(domain) DO UPDATE SET "
            "company_name=excluded.company_name,updated_at=excluded.updated_at",
            (domain, value, updated_at),
        )
        con.commit()
    return value
