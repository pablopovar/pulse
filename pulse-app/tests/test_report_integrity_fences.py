import json
import threading

import pytest

from db.migrate import migrate_up
from db.sqlite import connect_sqlite
from jobs.publication import publish_report_if_owned
from jobs.store import cancel_job, claim_next_job, enqueue_job
from reports import web_report
from services import audit_execution


DOMAIN = "example.com"


def _owned_job(db, job_type, job_id):
    enqueue_job(db, job_type, domain=DOMAIN, job_id=job_id)
    claimed = claim_next_job(db, worker_id="worker-a", lease_seconds=60)
    assert claimed and claimed["id"] == job_id


def test_cancel_during_audit_capture_cannot_write_page_or_complete_run(tmp_path, monkeypatch):
    db = tmp_path / "pulse.db"
    migrate_up(db)
    _owned_job(db, "audit", "audit-job")
    with connect_sqlite(db) as con:
        run_id = con.execute(
            "INSERT INTO audit_run(domain,scope,status,started_at,execution_run_id) "
            "VALUES (?, 'whole_site', 'running', 'now', ?)",
            (DOMAIN, "audit-job"),
        ).lastrowid
        con.commit()

    def capture(_url):
        assert cancel_job(db, "audit-job")
        return {"findings": []}

    monkeypatch.setattr(audit_execution, "run_geo_aeo_audit", capture)
    with pytest.raises(audit_execution.AuditOwnershipLost):
        audit_execution.run_audit_pages(
            db, DOMAIN, run_id, [{"id": 1, "url": "https://example.com/"}],
            job_id="audit-job", worker_id="worker-a",
        )
    with connect_sqlite(db, readonly=True) as con:
        assert con.execute("SELECT COUNT(*) FROM audit_page WHERE audit_run_id=?", (run_id,)).fetchone()[0] == 0
        assert con.execute("SELECT status FROM audit_run WHERE id=?", (run_id,)).fetchone()[0] == "running"


def test_cancel_during_crawl_fetch_cannot_write_page_or_complete_run(tmp_path, monkeypatch):
    from crawlers import seo

    db = tmp_path / "pulse.db"
    migrate_up(db)
    _owned_job(db, "crawl", "crawl-job")
    with connect_sqlite(db) as con:
        run_id = con.execute(
            "INSERT INTO crawl_run(domain,base_url,status,page_cap,delay_ms,obey_robots,crawl_mode,execution_run_id) "
            "VALUES (?, ?, 'queued', 1, 0, 1, 'initial', ?)",
            (DOMAIN, "https://example.com", "crawl-job"),
        ).lastrowid
        con.commit()
    monkeypatch.setattr(seo, "build_robot_parser", lambda _url: (None, "", None))
    monkeypatch.setattr(seo, "discover_domain_sitemap_inventory", lambda *a, **kw: ([], "", []))
    monkeypatch.setattr(seo, "RESEARCH_DB_PATH", db)

    def fetch(url, **_kwargs):
        assert cancel_job(db, "crawl-job")
        return {
            "ok": True, "status": 200, "final_url": url, "content_type": "text/html",
            "content_length": 20, "elapsed_ms": 1, "headers": {},
            "body": b"<html><h1>Evidence</h1></html>", "error": None,
        }

    monkeypatch.setattr(seo, "fetch", fetch)
    with pytest.raises(seo.CrawlOwnershipLost):
        seo.crawl_worker(
            run_id, DOMAIN, "https://example.com", 1, 0, True,
            lambda: connect_sqlite(db), crawl_mode="initial",
            execution_run_id="crawl-job", worker_id="worker-a",
        )
    with connect_sqlite(db, readonly=True) as con:
        assert con.execute("SELECT COUNT(*) FROM crawl_page WHERE crawl_run_id=?", (run_id,)).fetchone()[0] == 0
        assert con.execute("SELECT status FROM crawl_run WHERE id=?", (run_id,)).fetchone()[0] == "cancelled"


def test_staged_report_does_not_change_live_tracking_or_current_listing(tmp_path, monkeypatch):
    db = tmp_path / "pulse.db"
    migrate_up(db)
    baseline = web_report.create_report_session(db, DOMAIN, {"domain": DOMAIN}, publish=True)
    with connect_sqlite(db) as con:
        con.execute(
            "INSERT INTO recommendation_tracking(domain,finding_key,status,updated_at) "
            "VALUES (?, 'finding', 'implemented', 'now')", (DOMAIN,),
        )
        con.commit()
    _owned_job(db, "report_refresh", "refresh-job")
    monkeypatch.setattr(web_report, "_recommendation_updates", lambda *a: {"finding": "verified"})
    # publication imports the same function; patch both call sites.
    from jobs import publication
    monkeypatch.setattr(publication, "_recommendation_updates", lambda *a: {"finding": "verified"})
    staged = web_report.create_report_session(
        db, DOMAIN, {"domain": DOMAIN}, execution_run_id="refresh-job", publish=False,
    )
    with connect_sqlite(db, readonly=True) as con:
        assert con.execute("SELECT status FROM recommendation_tracking WHERE finding_key='finding'").fetchone()[0] == "implemented"
        assert con.execute("SELECT current_report_id FROM domain_report WHERE domain=?", (DOMAIN,)).fetchone()[0] == baseline
    assert [row["id"] for row in web_report.list_report_sessions(db, DOMAIN)] == [baseline]

    assert publish_report_if_owned(
        db, job_id="refresh-job", worker_id="worker-a", domain=DOMAIN, report_id=staged,
    )
    with connect_sqlite(db, readonly=True) as con:
        assert con.execute("SELECT status FROM recommendation_tracking WHERE finding_key='finding'").fetchone()[0] == "verified"
        snapshot = json.loads(con.execute("SELECT snapshot_json FROM report_session WHERE id=?", (staged,)).fetchone()[0])
        assert snapshot["recommendation_tracking"]["finding"]["status"] == "verified"
        assert con.execute("SELECT current_report_id FROM domain_report WHERE domain=?", (DOMAIN,)).fetchone()[0] == staged
    assert web_report.list_report_sessions(db, DOMAIN)[0]["id"] == staged


def test_two_refresh_workflows_keep_their_own_evidence(tmp_path, monkeypatch):
    """B's newer audit must not be captured in A's report assembly."""
    from jobs import workflows
    from services import report_data

    db = tmp_path / "pulse.db"
    migrate_up(db)
    with connect_sqlite(db) as con:
        con.execute(
            "INSERT INTO dashboard_domain(domain,base_url,created_at,updated_at) "
            "VALUES (?, ?, 'now', 'now')", (DOMAIN, "https://example.com"),
        )
        page_id = con.execute(
            "INSERT INTO site_page(domain,url,path,source,discovered_at,updated_at) "
            "VALUES (?, ?, '/', 'sitemap', 'now', 'now')",
            (DOMAIN, "https://example.com/"),
        ).lastrowid
        con.commit()
    enqueue_job(db, "report_refresh", domain=DOMAIN, payload={"domain": DOMAIN}, job_id="A")
    enqueue_job(db, "report_refresh", domain=DOMAIN, payload={"domain": DOMAIN}, job_id="B")
    first = claim_next_job(db, worker_id="worker-A", lease_seconds=60)
    second = claim_next_job(db, worker_id="worker-B", lease_seconds=60)
    assert {first["id"], second["id"]} == {"A", "B"}
    monkeypatch.setattr(workflows, "RESEARCH_DB", db)
    monkeypatch.setattr(workflows, "SEO_DB", tmp_path / "seo.db")
    monkeypatch.setattr(workflows, "schedule_background_crawl", lambda *a, **kw: None)
    monkeypatch.setattr(workflows, "selected_source_keys", lambda *a, **kw: [])
    monkeypatch.setattr(workflows, "domain_sources_for_site", lambda *a, **kw: [])
    monkeypatch.setattr(workflows, "manual_ai_source_for_report", lambda *a, **kw: {})
    monkeypatch.setattr(workflows, "load_client_report_config", lambda *a, **kw: {})

    class EmptyAdapter:
        def __init__(self, _path):
            pass

        def report_core(self, _site_id):
            return {}

        def enrich_report(self, data, _site_id, _domain):
            return data

    monkeypatch.setattr(report_data, "OpenGSCAdapter", EmptyAdapter)

    def crawl(job, _worker_id):
        with connect_sqlite(db) as con:
            run_id = con.execute(
                "INSERT INTO crawl_run(domain,base_url,status,page_cap,delay_ms,obey_robots,execution_run_id) "
                "VALUES (?, ?, 'completed', 1, 0, 1, ?)",
                (DOMAIN, "https://example.com", job["id"]),
            ).lastrowid
            con.execute(
                "INSERT INTO crawl_page(crawl_run_id,url,final_url,path,status_code,created_at) "
                "VALUES (?, ?, ?, '/', 200, 'now')",
                (run_id, "https://example.com/", "https://example.com/"),
            )
            con.commit()
        return {"status": "completed", "result_ref": {"crawl_run_id": run_id}}

    b_audit_ready = threading.Event()

    def audit(job, _worker_id):
        with connect_sqlite(db) as con:
            run_id = con.execute(
                "INSERT INTO audit_run(domain,scope,status,started_at,execution_run_id) "
                "VALUES (?, 'report', 'completed', 'now', ?)",
                (DOMAIN, job["id"]),
            ).lastrowid
            con.commit()
        if job["id"] == "A":
            assert b_audit_ready.wait(10), "B did not complete its newer audit"
        else:
            b_audit_ready.set()
        return {"status": "completed", "result_ref": {"audit_run_id": run_id}}

    monkeypatch.setattr(workflows, "run_crawl", crawl)
    monkeypatch.setattr(workflows, "run_audit", audit)
    results = {}
    errors = []

    def run(job, owner):
        try:
            results[job["id"]] = workflows.run_report_refresh(job, owner)
        except BaseException as exc:
            errors.append(exc)

    ta = threading.Thread(target=run, args=(first, "worker-A"))
    tb = threading.Thread(target=run, args=(second, "worker-B"))
    ta.start()
    tb.start()
    ta.join(15)
    tb.join(15)
    assert not ta.is_alive() and not tb.is_alive()
    assert not errors, errors
    with connect_sqlite(db, readonly=True) as con:
        for job_id in ("A", "B"):
            ref = results[job_id]["result_ref"]
            row = con.execute(
                "SELECT snapshot_json,execution_run_id FROM report_session WHERE id=?",
                (ref["report_id"],),
            ).fetchone()
            snapshot = json.loads(row["snapshot_json"])
            assert row["execution_run_id"] == job_id
            assert snapshot["audit"]["id"] == ref["audit_run_id"]
            assert snapshot["crawl"]["id"] == ref["crawl_run_id"]
            assert snapshot["audit"]["execution_run_id"] == job_id
            assert snapshot["crawl"]["execution_run_id"] == job_id
