from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from db.sqlite import connect_sqlite
from integrations.opengsc_adapter import OpenGSCAdapter

SOURCE_CATALOG = [
    ("gsc", "Google Search Console", "Observed Google search queries, landing pages, impressions, clicks, CTR and positions."),
    ("ga4", "Google Analytics 4", "Audience, session, engagement, event, conversion and revenue context."),
    ("clarity", "Microsoft Clarity", "Behavioral evidence such as sessions, recordings and interaction summaries."),
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
    gsc_site_id = site_id_value(site)
    opengsc = OpenGSCAdapter(opengsc_db)
    try:
        gsc_connected = bool(
            gsc_site_id
            and str(gsc_site_id) in {str(row.get("id") or "") for row in opengsc.list_sites()}
        )
    except Exception:
        gsc_connected = False
    states = {
        "gsc": {
            "connected": gsc_connected,
            "detail": "OpenGSC property linked; Pulse reads it" if gsc_connected else "",
        },
    }
    try:
        states.update(opengsc.detected_source_state(gsc_site_id))
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
    dataforseo_setup = "Not configured"
    dataforseo_enabled = False
    try:
        with connect_sqlite(research_db) as con:
            project = con.execute(
                "SELECT enabled FROM extension_project WHERE domain=? AND extension_key='dataforseo'",
                (domain,),
            ).fetchone()
            global_settings = con.execute(
                "SELECT kill_switch FROM extension_global WHERE extension_key='dataforseo'"
            ).fetchone()
        if str(os.environ.get("DATAFORSEO_KILL_SWITCH", "")).strip().lower() in {"1", "true", "yes", "on", "enabled"}:
            dataforseo_setup = "Blocked by environment kill switch"
        elif global_settings and global_settings["kill_switch"]:
            dataforseo_setup = "Blocked by kill switch"
        elif not (os.environ.get("DATAFORSEO_LOGIN") and os.environ.get("DATAFORSEO_PASSWORD")):
            dataforseo_setup = "API credentials not configured"
        elif not (project and project["enabled"]):
            dataforseo_setup = "Credentials configured; enable for this domain in DataForSEO settings"
        else:
            dataforseo_setup = "Enabled for this domain; the first provider request will verify credentials"
            dataforseo_enabled = True
    except Exception:
        dataforseo_setup = "DataForSEO settings could not be read"
    detected["dataforseo"] = {"connected": dataforseo_enabled, "detail": dataforseo_setup}
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
        selected = bool(stored.get("selected"))
        if key == "gsc":
            connector_status = "OpenGSC property linked" if connected else "Not connected in OpenGSC"
            connection_kind = "external_read_only"
        elif key == "dataforseo":
            connector_status = dataforseo_setup
            connection_kind = "api_connector"
        elif key == "manual_ai":
            connector_status = "Manual provider responses supported"
            connection_kind = "manual"
        elif key == "clarity":
            connector_status = "Stored Clarity observations available" if connected else "No Clarity observations available"
            connection_kind = "stored_observations"
        elif key in {"chatgpt", "claude", "gemini"}:
            connector_status = "Stored observations available" if connected else "No live API connector; use Manual AI Responses"
            connection_kind = "stored_observations"
        elif key in {"ga4", "semrush", "google_apis"}:
            connector_status = "Connector not implemented in Pulse"
            connection_kind = "unavailable"
        else:
            connector_status = "No connector configured"
            connection_kind = "unavailable"
        out.append({
            "key": key,
            "name": name,
            "description": description,
            "selected": selected,
            "status": "Selected for reports" if selected else "Not selected for reports",
            "status_class": "selected" if selected else "off",
            "detail": state.get("detail") or stored.get("detail") or "",
            "connector_status": connector_status,
            "connection_kind": connection_kind,
            "updated_at": stored.get("updated_at") or "",
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
            "status": "Selected for reports" if stored["selected"] else "Not selected for reports",
            "status_class": "selected" if stored["selected"] else "off",
            "detail": stored["detail"] or "",
            "connector_status": "Custom source; no Pulse connector configured",
            "connection_kind": "unavailable",
            "updated_at": stored.get("updated_at") or "",
        })
    return out


def selected_source_keys(site: dict, *, research_db: str | Path, opengsc_db: str | Path) -> list[str]:
    return [
        row["key"]
        for row in domain_sources_for_site(site, research_db=research_db, opengsc_db=opengsc_db)
        if row["selected"]
    ]


def save_domain_sources(
    site: dict,
    *,
    research_db: str | Path,
    opengsc_db: str | Path,
    selected: set[str],
    custom_name: str = "",
    custom_detail: str = "",
) -> None:
    detected = detected_source_state(site, opengsc_db)
    updated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    domain = site["domain"]
    with connect_sqlite(research_db) as con:
        for key, name, _description in SOURCE_CATALOG:
            state = detected.get(key, {})
            connected = bool(state.get("connected"))
            con.execute(
                """
                INSERT INTO domain_source(
                    domain,source_key,source_name,selected,connection_status,detail,updated_at
                ) VALUES (?,?,?,?,?,?,?)
                ON CONFLICT(domain,source_key) DO UPDATE SET
                    source_name=excluded.source_name,
                    selected=excluded.selected,
                    connection_status=excluded.connection_status,
                    detail=CASE
                        WHEN excluded.detail<>'' THEN excluded.detail
                        ELSE domain_source.detail
                    END,
                    updated_at=excluded.updated_at
                """,
                (
                    domain,
                    key,
                    name,
                    int(key in selected),
                    "connected" if connected else "not_connected",
                    state.get("detail", ""),
                    updated_at,
                ),
            )

        clean_name = str(custom_name or "").strip()
        if clean_name:
            custom_key = "custom_" + re.sub(
                r"[^a-z0-9]+", "_", clean_name.lower()
            ).strip("_")
            if custom_key == "custom_":
                custom_key = "custom_source"
            con.execute(
                """
                INSERT INTO domain_source(
                    domain,source_key,source_name,selected,connection_status,detail,updated_at
                ) VALUES (?,?,?,1,'not_connected',?,?)
                ON CONFLICT(domain,source_key) DO UPDATE SET
                    source_name=excluded.source_name,
                    selected=1,
                    detail=excluded.detail,
                    updated_at=excluded.updated_at
                """,
                (domain, custom_key, clean_name, custom_detail, updated_at),
            )
        con.commit()
