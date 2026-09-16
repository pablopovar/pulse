from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from db.sqlite import connect_sqlite
from integrations.opengsc_adapter import OpenGSCAdapter


def normalize_dashboard_domain(value: str | None):
    value = (value or "").strip()
    if not value:
        return None, None
    if value.lower().startswith("sc-domain:"):
        value = value.split(":", 1)[1].strip()
    if "://" not in value:
        value = "https://" + value
    try:
        parsed = urlsplit(value)
    except Exception:
        return None, None
    host = (parsed.hostname or "").strip().lower()
    if not host or "." not in host:
        return None, None
    return host, "https://" + host


def _opengsc_site_domain(site: dict):
    for key in ("domain", "url", "siteId", "site_url", "property"):
        value = site.get(key)
        if not value:
            continue
        domain, _ = normalize_dashboard_domain(str(value))
        if domain:
            return domain
    return None


def sync_dashboard_domains_from_opengsc(
    research_db: str | Path,
    opengsc_db: str | Path,
) -> None:
    with connect_sqlite(research_db, readonly=True) as con:
        suppressed = {
            row["domain"].lower()
            for row in con.execute("SELECT domain FROM domain_suppression").fetchall()
        }
    try:
        sites = OpenGSCAdapter(opengsc_db).list_sites()
    except Exception:
        sites = []
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with connect_sqlite(research_db) as con:
        for site in sites:
            domain = _opengsc_site_domain(site)
            gsc_id = site.get("id")
            if not domain or not gsc_id or domain.lower() in suppressed:
                continue
            con.execute(
                """
                INSERT INTO dashboard_domain(domain,base_url,gsc_site_id,created_at,updated_at)
                VALUES (?,?,?,?,?)
                ON CONFLICT(domain) DO UPDATE SET
                    gsc_site_id=excluded.gsc_site_id,
                    base_url=excluded.base_url,
                    updated_at=excluded.updated_at
                """,
                (domain, "https://" + domain, str(gsc_id), ts, ts),
            )
        con.commit()


def get_site(
    research_db: str | Path,
    domain: str,
    *,
    opengsc_db: str | Path | None = None,
    sync_opengsc: bool = False,
) -> dict | None:
    wanted, _ = normalize_dashboard_domain(domain)
    if not wanted:
        return None
    if sync_opengsc and opengsc_db is not None:
        sync_dashboard_domains_from_opengsc(research_db, opengsc_db)
    with connect_sqlite(research_db, readonly=True) as con:
        row = con.execute(
            "SELECT id,domain,base_url,gsc_site_id FROM dashboard_domain WHERE domain=? COLLATE NOCASE",
            (wanted,),
        ).fetchone()
    if not row:
        return None
    return {
        "id": row["gsc_site_id"] or f"__GSC_MISSING__:{row['domain']}",
        "dashboard_domain_id": row["id"],
        "domain": row["domain"],
        "base_url": row["base_url"],
        "gsc_site_id": row["gsc_site_id"],
        "gsc_missing": not bool(row["gsc_site_id"]),
    }


def list_sites(
    research_db: str | Path,
    *,
    opengsc_db: str | Path | None = None,
    sync_opengsc: bool = False,
) -> list[dict]:
    if sync_opengsc and opengsc_db is not None:
        sync_dashboard_domains_from_opengsc(research_db, opengsc_db)
    with connect_sqlite(research_db, readonly=True) as con:
        rows = con.execute(
            "SELECT id,domain,base_url,gsc_site_id FROM dashboard_domain ORDER BY domain COLLATE NOCASE"
        ).fetchall()
    return [{
        "id": row["gsc_site_id"] or f"__GSC_MISSING__:{row['domain']}",
        "dashboard_domain_id": row["id"],
        "domain": row["domain"],
        "base_url": row["base_url"],
        "gsc_site_id": row["gsc_site_id"],
        "gsc_missing": not bool(row["gsc_site_id"]),
    } for row in rows]
