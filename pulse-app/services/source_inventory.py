from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from db.sqlite import connect_sqlite
from integrations.opengsc_adapter import OpenGSCAdapter

SOURCE_CATALOG = [
    ("gsc", "Google Search Console", "Observed Google search queries, landing pages, impressions, clicks, CTR and positions."),
    ("ga4", "Google Analytics 4", "Audience, session, engagement, event, conversion and revenue context."),
    ("dataforseo", "DataForSEO", "Keyword demand, SERP, competitive and supplemental search visibility data."),
    ("chatgpt", "ChatGPT API", "AI answer, mention and citation observations from configured OpenAI models."),
    ("claude", "Claude API", "AI answer, mention and citation observations from configured Anthropic models."),
    ("gemini", "Gemini API", "AI answer, mention and citation observations from configured Gemini models."),
    ("semrush", "Semrush", "Search demand, competitor, backlink and authority datasets."),
    ("google_apis", "Google APIs", "Additional Google services and evidence sources used by report checks."),
    ("manual_ai", "Manual AI Responses", "Copy one editable provider-agnostic prompt, then paste or upload the raw ChatGPT, Claude and Gemini responses."),
]


def site_id_value(site: Any):
    for key in ("id", "site_id", "gsc_site_id"):
        try:
            value = site[key]
            if value and not str(value).startswith("__GSC_MISSING__:"):
                return value
        except Exception:
            pass
        try:
            value = getattr(site, key)
            if value and not str(value).startswith("__GSC_MISSING__:"):
                return value
        except Exception:
            pass
    return None


def detected_source_state(site: dict, opengsc_db: str | Path) -> dict[str, dict]:
    states = {
        "gsc": {
            "connected": not bool(site.get("gsc_missing")),
            "detail": "OpenGSC / GSC property linked" if not site.get("gsc_missing") else "",
        },
        "dataforseo": {
            "connected": bool(os.environ.get("DATAFORSEO_LOGIN") and os.environ.get("DATAFORSEO_PASSWORD")),
            "detail": "Credentials configured" if os.environ.get("DATAFORSEO_LOGIN") and os.environ.get("DATAFORSEO_PASSWORD") else "",
        },
    }
    try:
        states.update(OpenGSCAdapter(opengsc_db).detected_source_state(site_id_value(site)))
    except Exception:
        pass
    return states


def domain_sources_for_site(
    site: dict,
    *,
    research_db: str | Path,
    opengsc_db: str | Path,
) -> list[dict]:
    detected = detected_source_state(site, opengsc_db)
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    domain = site["domain"]
    with connect_sqlite(research_db) as con:
        rows = {
            row["source_key"]: dict(row)
            for row in con.execute(
                "SELECT * FROM domain_source WHERE domain=? COLLATE NOCASE", (domain,)
            ).fetchall()
        }
        for key, name, _description in SOURCE_CATALOG:
            state = detected.get(key, {})
            if key not in rows and state.get("connected"):
                con.execute(
                    """
                    INSERT OR IGNORE INTO domain_source(
                        domain,source_key,source_name,selected,connection_status,detail,updated_at
                    ) VALUES (?,?,?,?,?,?,?)
                    """,
                    (domain, key, name, 1, "connected", state.get("detail", ""), ts),
                )
        con.commit()
        rows = {
            row["source_key"]: dict(row)
            for row in con.execute(
                "SELECT * FROM domain_source WHERE domain=? COLLATE NOCASE", (domain,)
            ).fetchall()
        }

    out: list[dict] = []
    for key, name, description in SOURCE_CATALOG:
        stored = rows.get(key, {})
        state = detected.get(key, {})
        connected = bool(state.get("connected"))
        selected = bool(stored.get("selected")) or connected
        out.append({
            "key": key,
            "name": name,
            "description": description,
            "selected": selected,
            "status": "Connected" if connected else ("Selected" if selected else "Not selected"),
            "status_class": "connected" if connected else ("selected" if selected else "off"),
            "detail": state.get("detail") or stored.get("detail") or "",
        })
    catalog = {row[0] for row in SOURCE_CATALOG}
    for key, stored in rows.items():
        if key in catalog:
            continue
        out.append({
            "key": key,
            "name": stored["source_name"],
            "description": "Custom or future evidence source.",
            "selected": bool(stored["selected"]),
            "status": "Selected" if stored["selected"] else "Not selected",
            "status_class": "selected" if stored["selected"] else "off",
            "detail": stored["detail"] or "",
        })
    return out


def selected_source_keys(site: dict, *, research_db: str | Path, opengsc_db: str | Path) -> list[str]:
    return [
        row["key"]
        for row in domain_sources_for_site(site, research_db=research_db, opengsc_db=opengsc_db)
        if row["selected"]
    ]
