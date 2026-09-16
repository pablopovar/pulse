from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from db.sqlite import connect_sqlite
from jobs.publication import publish_report_if_owned
from jobs.store import set_job_stage, set_job_publication_status
from reports.full_pdf import collect_report_data
from reports.manual_ai_analysis import run_analysis as run_manual_ai_analysis
from reports.web_report import create_report_session
from services.audit_execution import run_audit_pages
from services.domain_registry import get_site
from services.manual_ai_report import manual_ai_source_for_report
from services.page_discovery import set_discovery_state, sync_site_pages
from services.source_inventory import domain_sources_for_site, selected_source_keys, site_id_value

RESEARCH_DB = Path(os.environ.get("RESEARCH_DB", "/data/audit/research.db"))
SEO_DB = Path(os.environ.get("SEO_DB", "/data/opengsc/prod.db"))


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def result(status, **refs):
    return {"status": status, "result_ref": refs}


def _require_owned(ok: bool, *, stage: str):
    if not ok:
        raise RuntimeError(f"Durable job ownership lost during {stage}.")


def _research_db():
    return connect_sqlite(RESEARCH_DB)


def ensure_crawl(job):
    p = job["payload"]
    rid = job["id"]
    with connect_sqlite(RESEARCH_DB) as con:
        row = con.execute(
            "SELECT id,status FROM crawl_run WHERE execution_run_id=?", (rid,)
        ).fetchone()
        if row:
            return int(row["id"]), str(row["status"])
        urls = p.get("selected_urls") or []
        cur = con.execute(
            """
            INSERT INTO crawl_run(
                domain,base_url,status,page_cap,delay_ms,obey_robots,
                report_scope,selected_urls_json,execution_run_id
            ) VALUES (?,?,?,?,?,?,?,?,?)
            """,
            (
                p["domain"], p.get("base_url") or "https://" + p["domain"], "queued",
                int(p.get("page_cap") or len(urls) or 100), int(p.get("delay_ms") or 0),
                int(bool(p.get("obey_robots", True))), p.get("report_scope") or "",
                json.dumps(urls), rid,
            ),
        )
        con.commit()
        return int(cur.lastrowid), "queued"


def reset_crawl(run_id):
    with connect_sqlite(RESEARCH_DB) as con:
        con.execute("DELETE FROM crawl_issue WHERE crawl_run_id=?", (run_id,))
        con.execute("DELETE FROM crawl_link WHERE crawl_run_id=?", (run_id,))
        con.execute("DELETE FROM crawl_page WHERE crawl_run_id=?", (run_id,))
        con.execute(
            """
            UPDATE crawl_run
            SET status='queued',started_at=NULL,completed_at=NULL,error=NULL,
                pages_discovered=0,pages_crawled=0,pages_failed=0
            WHERE id=?
            """,
            (run_id,),
        )
        con.commit()


def run_crawl(job, worker_id):
    from crawlers.seo import crawl_worker

    p = job["payload"]
    run_id, status = ensure_crawl(job)
    if status in {"completed", "partial"}:
        return result(status, crawl_run_id=run_id)
    reset_crawl(run_id)
    _require_owned(
        set_job_stage(RESEARCH_DB, job["id"], worker_id=worker_id, stage="crawl"),
        stage="crawl",
    )
    urls = p.get("selected_urls") or None
    crawl_worker(
        run_id,
        p["domain"],
        p.get("base_url") or "https://" + p["domain"],
        int(p.get("page_cap") or len(urls or []) or 100),
        int(p.get("delay_ms") or 0),
        bool(p.get("obey_robots", True)),
        _research_db,
        urls,
        bool(p.get("follow_links", not bool(urls))),
    )
    with connect_sqlite(RESEARCH_DB, readonly=True) as con:
        row = con.execute("SELECT status,error FROM crawl_run WHERE id=?", (run_id,)).fetchone()
    status = str(row["status"] or "failed")
    if status == "failed":
        raise RuntimeError(row["error"] or "crawl failed")
    return result(status, crawl_run_id=run_id)


def ensure_audit(job, scope):
    with connect_sqlite(RESEARCH_DB) as con:
        row = con.execute(
            "SELECT id,status FROM audit_run WHERE execution_run_id=?", (job["id"],)
        ).fetchone()
        if row:
            return int(row["id"]), str(row["status"])
        cur = con.execute(
            "INSERT INTO audit_run(domain,scope,status,started_at,execution_run_id) VALUES (?,?, 'running', ?, ?)",
            (job["payload"]["domain"], scope, now(), job["id"]),
        )
        con.commit()
        return int(cur.lastrowid), "running"


def reset_audit(run_id):
    with connect_sqlite(RESEARCH_DB) as con:
        ids = [
            int(row["id"])
            for row in con.execute("SELECT id FROM audit_page WHERE audit_run_id=?", (run_id,))
        ]
        for audit_page_id in ids:
            con.execute("DELETE FROM audit_signal WHERE audit_page_id=?", (audit_page_id,))
        con.execute("DELETE FROM audit_page WHERE audit_run_id=?", (run_id,))
        con.execute("DELETE FROM audit_domain_summary WHERE audit_run_id=?", (run_id,))
        con.execute(
            "UPDATE audit_run SET status='running',completed_at=NULL,error='' WHERE id=?", (run_id,)
        )
        con.commit()


def audit_pages(domain, page_ids):
    with connect_sqlite(RESEARCH_DB, readonly=True) as con:
        if page_ids:
            placeholders = ",".join("?" for _ in page_ids)
            rows = con.execute(
                f"SELECT id,url,path FROM site_page WHERE domain=? AND id IN ({placeholders}) ORDER BY path COLLATE NOCASE",
                [domain, *page_ids],
            ).fetchall()
        else:
            rows = con.execute(
                "SELECT id,url,path FROM site_page WHERE domain=? ORDER BY path COLLATE NOCASE",
                (domain,),
            ).fetchall()
    return [dict(row) for row in rows]


def run_audit(job, worker_id):
    p = job["payload"]
    run_id, status = ensure_audit(job, p.get("scope") or "whole_site")
    if status in {"completed", "partial"}:
        return result(status, audit_run_id=run_id)
    reset_audit(run_id)
    _require_owned(
        set_job_stage(RESEARCH_DB, job["id"], worker_id=worker_id, stage="audit"),
        stage="audit",
    )
    pages = audit_pages(p["domain"], p.get("page_ids") or [])
    if not pages:
        raise RuntimeError(
            "No site pages are available to audit. Run page discovery before the audit."
        )
    status = run_audit_pages(RESEARCH_DB, p["domain"], run_id, pages)
    if status == "failed":
        with connect_sqlite(RESEARCH_DB, readonly=True) as con:
            row = con.execute("SELECT error FROM audit_run WHERE id=?", (run_id,)).fetchone()
        raise RuntimeError((row["error"] if row else "") or "audit failed")
    return result(status, audit_run_id=run_id)


def run_page_discovery(job, worker_id):
    p = job["payload"]
    domain = p["domain"]
    rid = job["id"]
    _require_owned(
        set_job_stage(RESEARCH_DB, rid, worker_id=worker_id, stage="page_discovery"),
        stage="page_discovery",
    )
    set_discovery_state(RESEARCH_DB, domain, "running", job_id=rid, error="")
    site = get_site(RESEARCH_DB, domain)
    if not site:
        set_discovery_state(RESEARCH_DB, domain, "failed", job_id=rid, error="Domain not found.")
        raise RuntimeError(f"Domain not found: {domain}")
    try:
        outcome = sync_site_pages(
            domain,
            research_db=RESEARCH_DB,
            opengsc_db=SEO_DB,
            site_id=site_id_value(site),
            max_depth=int(p.get("max_depth") or 5),
            max_urls=int(p.get("max_urls") or 20_000),
        )
    except Exception as exc:
        set_discovery_state(RESEARCH_DB, domain, "failed", job_id=rid, error=str(exc))
        raise
    set_discovery_state(
        RESEARCH_DB,
        domain,
        "ready",
        job_id=rid,
        sitemap_source=outcome["sitemap_source"],
        sitemap_count=outcome["sitemap_count"],
        ranking_count=outcome["ranking_count"],
        error="\n".join(outcome.get("warnings") or []),
        successful=True,
    )
    return result(
        "completed",
        sitemap_count=outcome["sitemap_count"],
        ranking_count=outcome["ranking_count"],
        sitemap_source=outcome["sitemap_source"],
    )


def run_ai(job, worker_id):
    p = job["payload"]
    rid = job["id"]
    src = p["source_snapshot"]
    prm = p["parameters"]
    ts = now()
    with connect_sqlite(RESEARCH_DB) as con:
        row = con.execute(
            "SELECT status FROM manual_ai_analysis_run WHERE run_id=?", (rid,)
        ).fetchone()
        if row and row["status"] == "completed":
            return result("completed", manual_ai_analysis_run_id=rid)
        con.execute(
            """
            INSERT INTO manual_ai_analysis_run(
                run_id,domain,status,provider,model,parameters_json,source_snapshot_json,
                started_at,created_at,updated_at
            ) VALUES (?,?, 'running', ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                status='running',error_json='{}',started_at=excluded.started_at,
                completed_at=NULL,updated_at=excluded.updated_at
            """,
            (
                rid, p["domain"], prm.get("provider") or "", prm.get("model") or "",
                json.dumps(prm), json.dumps(src), ts, ts, ts,
            ),
        )
        con.commit()
    _require_owned(
        set_job_stage(RESEARCH_DB, rid, worker_id=worker_id, stage="ai_analysis"),
        stage="ai_analysis",
    )
    try:
        analysis = run_manual_ai_analysis(
            src,
            prm.get("model") or "",
            prm.get("system_prompt") or "",
            provider=prm.get("provider") or "ollama",
            reasoning_effort=prm.get("reasoning_effort") or "high",
            temperature=float(prm.get("temperature", .1)),
            top_p=float(prm.get("top_p", .9)),
            max_output_tokens=int(prm.get("max_output_tokens", 8000)),
        )
    except Exception as exc:
        err = {"kind": exc.__class__.__name__, "message": str(exc), "stage": "provider_execution", "at": now()}
        with connect_sqlite(RESEARCH_DB) as con:
            con.execute(
                "UPDATE manual_ai_analysis_run SET status='failed',error_json=?,completed_at=?,updated_at=? WHERE run_id=?",
                (json.dumps(err), now(), now(), rid),
            )
            con.commit()
        raise

    ts = now()
    with connect_sqlite(RESEARCH_DB) as con:
        con.execute("BEGIN IMMEDIATE")
        owned = con.execute(
            """
            SELECT 1 FROM durable_job
            WHERE id=? AND status='running' AND worker_id=?
              AND lease_expires_at IS NOT NULL AND lease_expires_at>=?
            """,
            (rid, worker_id, ts),
        ).fetchone()
        if owned is None:
            con.rollback()
            raise RuntimeError("Durable job ownership lost before AI current-state publication.")
        con.execute(
            "UPDATE manual_ai_analysis_run SET status='completed',analysis_text=?,error_json='{}',completed_at=?,updated_at=? WHERE run_id=?",
            (analysis, ts, ts, rid),
        )
        con.execute(
            """
            UPDATE manual_ai_source
            SET analysis_provider=?,analysis_model=?,analysis_reasoning_effort=?,
                analysis_temperature=?,analysis_top_p=?,analysis_max_output_tokens=?,
                analysis_system_prompt_version=?,analysis_parameters_json=?,analysis_system_prompt=?,
                analysis_text=?,analysis_status='success',analysis_error='',analysis_updated_at=?,updated_at=?
            WHERE domain=? COLLATE NOCASE
            """,
            (
                prm.get("provider") or "ollama", prm.get("model") or "",
                prm.get("reasoning_effort") or "high", float(prm.get("temperature", .1)),
                float(prm.get("top_p", .9)), int(prm.get("max_output_tokens", 8000)),
                int(prm.get("system_prompt_version", 1)), json.dumps(prm),
                prm.get("system_prompt") or "", analysis, ts, ts, p["domain"],
            ),
        )
        con.commit()
    return result("completed", manual_ai_analysis_run_id=rid)


def run_report_refresh(job, worker_id):
    p = job["payload"]
    domain = p["domain"]
    rid = job["id"]
    _require_owned(
        set_job_publication_status(
            RESEARCH_DB, rid, worker_id=worker_id, publication_status="not_started"
        ),
        stage="report_refresh",
    )

    crawl = run_crawl(
        {
            **job,
            "payload": {
                "domain": domain,
                "base_url": "https://" + domain,
                "page_cap": int(p.get("page_cap") or 5000),
                "delay_ms": int(p.get("delay_ms") or 0),
                "obey_robots": True,
                "report_scope": "report",
                "selected_urls": [],
                "follow_links": True,
            },
        },
        worker_id,
    )
    if crawl["status"] != "completed":
        _require_owned(
            set_job_publication_status(
                RESEARCH_DB, rid, worker_id=worker_id, publication_status="withheld"
            ),
            stage="withhold_report",
        )
        return {
            "status": "partial",
            "result_ref": {**crawl["result_ref"], "publication": "withheld"},
            "error": {"kind": "prerequisite_partial", "message": "crawl incomplete"},
        }

    # The crawl is allowed to discover links, but the audit consumes the durable
    # site_page inventory. If this is a new domain, run the canonical discovery
    # service explicitly rather than hiding network work inside audit_pages().
    if not audit_pages(domain, []):
        discovery = run_page_discovery(
            {**job, "payload": {"domain": domain, "max_urls": int(p.get("page_cap") or 5000)}},
            worker_id,
        )
        if discovery["status"] != "completed":
            _require_owned(
                set_job_publication_status(
                    RESEARCH_DB, rid, worker_id=worker_id, publication_status="withheld"
                ),
                stage="withhold_report",
            )
            return {
                "status": "partial",
                "result_ref": {**crawl["result_ref"], **discovery["result_ref"], "publication": "withheld"},
                "error": {"kind": "prerequisite_partial", "message": "page discovery incomplete"},
            }

    audit = run_audit({**job, "payload": {"domain": domain, "scope": "report", "page_ids": []}}, worker_id)
    if audit["status"] != "completed":
        _require_owned(
            set_job_publication_status(
                RESEARCH_DB, rid, worker_id=worker_id, publication_status="withheld"
            ),
            stage="withhold_report",
        )
        return {
            "status": "partial",
            "result_ref": {**crawl["result_ref"], **audit["result_ref"], "publication": "withheld"},
            "error": {"kind": "prerequisite_partial", "message": "audit incomplete"},
        }

    _require_owned(
        set_job_stage(RESEARCH_DB, rid, worker_id=worker_id, stage="assemble_report"),
        stage="assemble_report",
    )
    site = get_site(RESEARCH_DB, domain)
    if not site:
        raise RuntimeError(f"Domain not found: {domain}")
    data = collect_report_data(
        domain=domain,
        site_id=site_id_value(site),
        seo_db=SEO_DB,
        research_db=RESEARCH_DB,
    )
    data["selected_sources"] = selected_source_keys(
        site, research_db=RESEARCH_DB, opengsc_db=SEO_DB
    )
    data["source_inventory"] = domain_sources_for_site(
        site, research_db=RESEARCH_DB, opengsc_db=SEO_DB
    )
    data["manual_ai_source"] = manual_ai_source_for_report(RESEARCH_DB, domain)

    report_id = create_report_session(
        RESEARCH_DB, domain, data, execution_run_id=rid, publish=False
    )
    try:
        published = publish_report_if_owned(
            RESEARCH_DB,
            job_id=rid,
            worker_id=worker_id,
            domain=domain,
            report_id=report_id,
        )
    except Exception:
        set_job_publication_status(
            RESEARCH_DB, rid, worker_id=worker_id, publication_status="failed"
        )
        raise
    if not published:
        raise RuntimeError("Durable job ownership lost immediately before report publication.")

    return result(
        "completed",
        crawl_run_id=crawl["result_ref"]["crawl_run_id"],
        audit_run_id=audit["result_ref"]["audit_run_id"],
        report_id=report_id,
        publication="published",
    )
