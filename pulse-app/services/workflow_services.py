from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from audits.geo_aeo.service import run_audit as run_geo_aeo_audit
from db.sqlite import connect_sqlite
from reports.full_pdf import collect_report_data
from reports.manual_ai_analysis import DEFAULT_ANALYSIS_SYSTEM_PROMPT, run_analysis as run_manual_ai_analysis
from reports.web_report import create_report_session

RESEARCH_DB = Path(os.environ.get("RESEARCH_DB", "/data/audit/research.db"))
SEO_DB = Path(os.environ.get("SEO_DB", "/data/opengsc/prod.db"))

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


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def research_db():
    return connect_sqlite(RESEARCH_DB)


def site_id_value(site: dict[str, Any]) -> str | None:
    for key in ("id", "site_id", "gsc_site_id"):
        value = site.get(key)
        if value:
            return str(value)
    return None


def get_site(domain: str) -> dict[str, Any]:
    with connect_sqlite(RESEARCH_DB, readonly=True) as con:
        row = con.execute(
            "SELECT id,domain,base_url,gsc_site_id FROM dashboard_domain WHERE domain=? COLLATE NOCASE",
            (domain,),
        ).fetchone()
    if not row:
        raise LookupError(f"Unknown Pulse domain: {domain}")
    return {
        "id": row["gsc_site_id"] or f"__GSC_MISSING__:{row['domain']}",
        "dashboard_domain_id": row["id"],
        "domain": row["domain"],
        "base_url": row["base_url"],
        "gsc_site_id": row["gsc_site_id"],
        "gsc_missing": not bool(row["gsc_site_id"]),
    }


def _opengsc_source_state(site: dict[str, Any]) -> dict[str, dict[str, Any]]:
    states: dict[str, dict[str, Any]] = {
        "gsc": {
            "connected": not bool(site.get("gsc_missing")),
            "detail": "OpenGSC / GSC property linked" if not site.get("gsc_missing") else "",
        },
        "dataforseo": {
            "connected": bool(os.environ.get("DATAFORSEO_LOGIN") and os.environ.get("DATAFORSEO_PASSWORD")),
            "detail": "Credentials configured" if os.environ.get("DATAFORSEO_LOGIN") and os.environ.get("DATAFORSEO_PASSWORD") else "",
        },
    }
    site_id = site_id_value(site)
    if not site_id or not SEO_DB.exists():
        return states
    try:
        with connect_sqlite(SEO_DB, readonly=True) as con:
            names = {r["name"] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
            if "ClaritySnapshot" in names and con.execute(
                'SELECT 1 FROM "ClaritySnapshot" WHERE siteId=? LIMIT 1', (site_id,)
            ).fetchone():
                states["ga4"] = {"connected": True, "detail": "Analytics/Clarity snapshot available"}
            if "AeoCheck" in names and "TrackedQuestion" in names:
                engines = con.execute(
                    'SELECT DISTINCT c.engine FROM "AeoCheck" c '
                    'JOIN "TrackedQuestion" q ON q.id=c.questionId WHERE q.siteId=?',
                    (site_id,),
                ).fetchall()
                found = {str(r["engine"]).lower() for r in engines if r["engine"]}
                for key in ("chatgpt", "claude", "gemini"):
                    if key in found:
                        states[key] = {"connected": True, "detail": f"Stored {key.title()} observations available"}
    except Exception:
        pass
    return states


def domain_sources_for_site(site: dict[str, Any]) -> list[dict[str, Any]]:
    detected = _opengsc_source_state(site)
    timestamp = now()
    with connect_sqlite(RESEARCH_DB) as con:
        rows = {
            r["source_key"]: dict(r)
            for r in con.execute(
                "SELECT * FROM domain_source WHERE domain=? COLLATE NOCASE",
                (site["domain"],),
            ).fetchall()
        }
        for key, name, _description in SOURCE_CATALOG:
            state = detected.get(key, {})
            if key not in rows and state.get("connected"):
                con.execute(
                    "INSERT OR IGNORE INTO domain_source"
                    "(domain,source_key,source_name,selected,connection_status,detail,updated_at) "
                    "VALUES (?,?,?,?,?,?,?)",
                    (site["domain"], key, name, 1, "connected", state.get("detail", ""), timestamp),
                )
        con.commit()
        rows = {
            r["source_key"]: dict(r)
            for r in con.execute(
                "SELECT * FROM domain_source WHERE domain=? COLLATE NOCASE",
                (site["domain"],),
            ).fetchall()
        }

    out: list[dict[str, Any]] = []
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
    known = {item[0] for item in SOURCE_CATALOG}
    for key, stored in rows.items():
        if key in known:
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


def selected_source_keys(site: dict[str, Any]) -> list[str]:
    return [source["key"] for source in domain_sources_for_site(site) if source["selected"]]


def _load_manual_ai_source(domain: str) -> dict[str, Any]:
    with connect_sqlite(RESEARCH_DB, readonly=True) as con:
        parent = con.execute(
            "SELECT * FROM manual_ai_source WHERE domain=? COLLATE NOCASE", (domain,)
        ).fetchone()
        rows = con.execute(
            "SELECT * FROM manual_ai_state_source WHERE domain=? COLLATE NOCASE ORDER BY phase,state",
            (domain,),
        ).fetchall()
    out = dict(parent) if parent else {
        "domain": domain,
        "question_set_version": 1,
        "analysis_status": "not_run",
        "updated_at": "",
    }
    indexed = {(r["phase"], r["state"]): dict(r) for r in rows}
    for phase in ("phase1", "phase2"):
        for state in ("state1", "state2"):
            row = indexed.get((phase, state), {})
            prefix = f"{phase}_{state}"
            out[f"{prefix}_prompt_text"] = row.get("prompt_text") or ""
            for provider in ("chatgpt", "claude", "gemini"):
                out[f"{prefix}_{provider}_response"] = row.get(f"{provider}_response") or ""
    if not str(out.get("analysis_system_prompt") or "").strip():
        out["analysis_system_prompt"] = DEFAULT_ANALYSIS_SYSTEM_PROMPT
    return out


def _parse_manual_payload(raw: Any) -> dict[str, Any] | None:
    text = str(raw or "").strip()
    if not text:
        return None
    fence = re.match(r"^```(?:json)?\s*([\s\S]*?)\s*```$", text, re.I)
    if fence:
        text = fence.group(1).strip()
    try:
        value = json.loads(text)
        return value if isinstance(value, dict) else None
    except Exception:
        pass
    start = text.find("{")
    if start < 0:
        return None
    try:
        value, _end = json.JSONDecoder().raw_decode(text[start:])
    except Exception:
        return None
    return value if isinstance(value, dict) else None


def manual_ai_source_for_report(domain: str) -> dict[str, Any]:
    source = _load_manual_ai_source(domain)
    phase_rows = []
    total_answers = 0
    parsed_runs = 0
    provider_runs = 0
    for phase in ("phase1", "phase2"):
        prefix = f"{phase}_state2"
        providers = []
        for provider in ("chatgpt", "claude", "gemini"):
            raw = source.get(f"{prefix}_{provider}_response") or ""
            parsed = _parse_manual_payload(raw)
            results = parsed.get("results") if isinstance(parsed, dict) else None
            result_count = len(results) if isinstance(results, list) else 0
            if str(raw).strip():
                provider_runs += 1
            if parsed is not None:
                parsed_runs += 1
                total_answers += result_count
            providers.append({
                "provider": provider,
                "response": raw,
                "parsed": parsed,
                "result_count": result_count,
            })
        phase_rows.append({
            "phase": phase,
            "states": [{
                "state": "retrieval_enabled",
                "providers": providers,
                "provider_count": sum(1 for p in providers if str(p["response"]).strip()),
            }],
        })
    source["available"] = provider_runs > 0
    source["phases"] = phase_rows
    source["provider_runs"] = provider_runs
    source["expected_provider_runs"] = 6
    source["provider_count"] = len({
        p["provider"]
        for phase_row in phase_rows
        for state in phase_row["states"]
        for p in state["providers"]
        if str(p["response"]).strip()
    })
    source["answer_count"] = total_answers
    source["expected_answer_count"] = 24
    source["valid_json_providers"] = parsed_runs
    source["complete"] = provider_runs == 6 and parsed_runs == 6 and total_answers == 24
    return source


def recompute_domain_summary(con, run_id: int, domain: str) -> None:
    pages = con.execute(
        "SELECT geo_score,aeo_score,combined_score FROM audit_page WHERE audit_run_id=?",
        (run_id,),
    ).fetchall()

    def avg(name: str):
        values = [row[name] for row in pages if row[name] is not None]
        return round(sum(values) / len(values)) if values else None

    counts = con.execute(
        """SELECT
        SUM(CASE WHEN s.observed_status='FAIL' THEN 1 ELSE 0 END) fail_count,
        SUM(CASE WHEN s.observed_status='PARTIAL' THEN 1 ELSE 0 END) partial_count,
        SUM(CASE WHEN s.observed_status='PASS' THEN 1 ELSE 0 END) pass_count,
        SUM(CASE WHEN s.observed_status='UNKNOWN' THEN 1 ELSE 0 END) unknown_count,
        SUM(CASE WHEN s.observed_status='MANUAL_REVIEW' THEN 1 ELSE 0 END) manual_count
        FROM audit_signal s JOIN audit_page p ON p.id=s.audit_page_id WHERE p.audit_run_id=?""",
        (run_id,),
    ).fetchone()
    con.execute(
        """INSERT INTO audit_domain_summary(
        audit_run_id,domain,pages_audited,geo_score,aeo_score,combined_score,
        fail_count,partial_count,pass_count,unknown_count,manual_count,created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(audit_run_id) DO UPDATE SET
        pages_audited=excluded.pages_audited,geo_score=excluded.geo_score,aeo_score=excluded.aeo_score,
        combined_score=excluded.combined_score,fail_count=excluded.fail_count,partial_count=excluded.partial_count,
        pass_count=excluded.pass_count,unknown_count=excluded.unknown_count,manual_count=excluded.manual_count""",
        (
            run_id, domain, len(pages), avg("geo_score"), avg("aeo_score"), avg("combined_score"),
            counts["fail_count"] or 0, counts["partial_count"] or 0, counts["pass_count"] or 0,
            counts["unknown_count"] or 0, counts["manual_count"] or 0, now(),
        ),
    )


def store_structured_audit(domain: str, run_id: int, page_id: int, url: str, report: dict[str, Any]) -> None:
    capture = report.get("capture", {})
    geo = report.get("geo", {})
    aeo = report.get("aeo", {})
    combined = report.get("combined", {})
    with connect_sqlite(RESEARCH_DB) as con:
        con.execute(
            """INSERT OR REPLACE INTO audit_page(
            audit_run_id,page_id,url,page_type,geo_score,aeo_score,combined_score,
            geo_json,aeo_json,combined_json,capture_json,created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                run_id, page_id, url, capture.get("page_type"), geo.get("score"), aeo.get("score"),
                combined.get("score"), json.dumps(geo), json.dumps(aeo), json.dumps(combined),
                json.dumps(capture), now(),
            ),
        )
        audit_page_id = con.execute(
            "SELECT id FROM audit_page WHERE audit_run_id=? AND page_id=?", (run_id, page_id)
        ).fetchone()["id"]
        con.execute("DELETE FROM audit_signal WHERE audit_page_id=?", (audit_page_id,))
        for item in report.get("findings", []):
            con.execute(
                """INSERT INTO audit_signal(
                audit_page_id,family,signal_key,category,title,observed_status,severity,
                weight,evidence,recommendation,source_title,source_url)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    audit_page_id, item.get("family", ""), item.get("id", ""), item.get("category", ""),
                    item.get("title", ""), item.get("status", ""), item.get("severity", ""),
                    item.get("weight", 0) or 0, item.get("evidence", ""), item.get("recommendation", ""),
                    item.get("source_title", ""), item.get("source_url", ""),
                ),
            )
        recompute_domain_summary(con, run_id, domain)
        con.commit()


def audit_worker(domain: str, run_id: int, pages: list[dict[str, Any]]) -> None:
    errors: list[str] = []
    for page in pages:
        try:
            store_structured_audit(
                domain, run_id, page["id"], page["url"], run_geo_aeo_audit(page["url"], "auto")
            )
        except Exception as exc:
            errors.append(f'{page["url"]}: {exc}')
    status = "completed" if not errors else ("partial" if len(errors) < len(pages) else "failed")
    with connect_sqlite(RESEARCH_DB) as con:
        con.execute(
            "UPDATE audit_run SET status=?,completed_at=?,error=? WHERE id=?",
            (status, now(), "\n".join(errors), run_id),
        )
        recompute_domain_summary(con, run_id, domain)
        con.commit()


def assemble_report_data(domain: str) -> tuple[dict[str, Any], dict[str, Any]]:
    site = get_site(domain)
    data = collect_report_data(
        domain=domain,
        site_id=site_id_value(site),
        seo_db=SEO_DB,
        research_db=RESEARCH_DB,
    )
    data["selected_sources"] = selected_source_keys(site)
    data["source_inventory"] = domain_sources_for_site(site)
    data["manual_ai_source"] = manual_ai_source_for_report(domain)
    return site, data
