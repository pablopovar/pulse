from __future__ import annotations

import json
from datetime import datetime, timezone

from db.sqlite import connect_sqlite
from services.page_types import PAGE_TYPES, applicability, classify_page_type


OPTIONAL_CHECKS = {
    "comparison": "Comparison and comparison-table checks",
    "faq": "FAQ and question-led-answer checks",
    "procedural": "How-to and procedural checks",
    "external_evidence": "External-source and claim-attribution checks",
}

CHECK_GROUPS = {
    "comparison": {"comparison intent supported", "comparisons are structured", "tables expose comparable data"},
    "faq": {"faq content is visible", "faq markup matches visible faq", "question-led headings", "multiple relevant question forms", "common follow-up questions addressed"},
    "procedural": {"procedural intent supported"},
    "external_evidence": {"external supporting sources", "quantified claims supported", "references or methodology section", "source attribution language", "claims retain attribution context"},
}

DOMAIN_WIDE_TITLES = {
    "caching policy declared", "hsts on https", "transfer compression observed",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_policy(db_path, domain: str) -> dict:
    with connect_sqlite(db_path, readonly=True) as con:
        row = con.execute("SELECT enabled_checks_json FROM domain_applicability_policy WHERE domain=? COLLATE NOCASE", (domain,)).fetchone()
    try:
        enabled = set(json.loads(row["enabled_checks_json"] or "[]")) if row else set()
    except (TypeError, ValueError):
        enabled = set()
    return {"enabled_checks": sorted(enabled & set(OPTIONAL_CHECKS)), "choices": OPTIONAL_CHECKS}


def save_policy(db_path, domain: str, enabled_checks) -> dict:
    enabled = sorted(set(enabled_checks or []) & set(OPTIONAL_CHECKS))
    with connect_sqlite(db_path) as con:
        con.execute("""INSERT INTO domain_applicability_policy(domain,enabled_checks_json,updated_at) VALUES (?,?,?)
                       ON CONFLICT(domain) DO UPDATE SET enabled_checks_json=excluded.enabled_checks_json,updated_at=excluded.updated_at""", (domain, json.dumps(enabled), _now()))
        con.commit()
    return load_policy(db_path, domain)


def load_page_type_overrides(db_path, domain: str) -> dict[str, str]:
    with connect_sqlite(db_path, readonly=True) as con:
        rows = con.execute("SELECT url,page_type FROM page_type_override WHERE domain=? COLLATE NOCASE", (domain,)).fetchall()
    return {str(row["url"]): str(row["page_type"]) for row in rows}


def save_page_type_override(db_path, domain: str, url: str, page_type: str) -> None:
    if page_type not in PAGE_TYPES:
        raise ValueError("Unknown page type.")
    with connect_sqlite(db_path) as con:
        con.execute("""INSERT INTO page_type_override(domain,url,page_type,updated_at) VALUES (?,?,?,?)
                       ON CONFLICT(domain,url) DO UPDATE SET page_type=excluded.page_type,updated_at=excluded.updated_at""", (domain, url, page_type, _now()))
        con.commit()


def apply_policy(signals: list[dict], *, policy: dict, overrides: dict[str, str]) -> list[dict]:
    enabled = set(policy.get("enabled_checks") or [])
    output = []
    for source in signals:
        signal = dict(source)
        url = str(signal.get("url") or "")
        page_type, confidence = classify_page_type(url)
        page_type = overrides.get(url, page_type)
        title = str(signal.get("title") or "").strip().lower()
        group = next((key for key, titles in CHECK_GROUPS.items() if title in titles), "")
        signal["page_type"] = page_type
        signal["page_type_confidence"] = "operator" if url in overrides else confidence
        signal["applicability"] = applicability(page_type)
        signal["scope"] = "domain" if title in DOMAIN_WIDE_TITLES else "page"
        if group and group not in enabled:
            signal["observed_status"] = "NOT_APPLICABLE"
            signal["applicability_reason"] = f"{OPTIONAL_CHECKS[group]} are disabled for this domain."
        elif page_type in {"privacy_legal", "thank_you", "utility"} and group:
            signal["observed_status"] = "NOT_APPLICABLE"
            signal["applicability_reason"] = f"This check does not apply to a {page_type.replace('_', ' ')} page."
        output.append(signal)
    return output
