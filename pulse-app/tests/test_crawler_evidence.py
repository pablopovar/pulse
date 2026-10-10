from datetime import timedelta

from db.migrate import migrate_up
from db.sqlite import connect_sqlite
from jobs.store import claim_next_job, enqueue_job, recover_abandoned_jobs, utcnow
from services.resource_outcome import MAX_RETAINED_BODY_BYTES, persist_resource_outcome, response_evidence


def test_resource_outcome_retains_bounded_text_and_keeps_binary_metadata(tmp_path):
    db = tmp_path / "research.db"
    migrate_up(db)
    with connect_sqlite(db) as con:
        text = response_evidence(
            requested_url="https://example.com/a.json", status=200,
            headers={"content-type": "application/json", "etag": "abc"}, body=b'{"ok":true}',
        )
        binary = response_evidence(
            requested_url="https://example.com/a.pdf", status=200,
            headers={"content-type": "application/pdf"}, body=b"%PDF",
        )
        oversized = response_evidence(
            requested_url="https://example.com/large.txt", status=200,
            headers={"content-type": "text/plain"}, body=b"x" * (MAX_RETAINED_BODY_BYTES + 1),
        )
        persist_resource_outcome(con, crawl_run_id=None, domain="example.com", outcome=text)
        persist_resource_outcome(con, crawl_run_id=None, domain="example.com", outcome=binary)
        persist_resource_outcome(con, crawl_run_id=None, domain="example.com", outcome=oversized)
        rows = con.execute("SELECT requested_url,resource_type,body_retained,response_body,reason FROM resource_outcome ORDER BY requested_url").fetchall()
    assert rows[0]["resource_type"] == "json" and rows[0]["body_retained"] == 1
    assert rows[1]["resource_type"] == "pdf" and rows[1]["body_retained"] == 0
    assert rows[2]["body_retained"] == 0 and rows[2]["reason"] == "body_over_size_limit"


def test_expired_lease_is_requeued_with_event_and_frontier_recovery(tmp_path):
    db = tmp_path / "research.db"
    migrate_up(db)
    job = enqueue_job(db, "crawl", domain="example.com", max_attempts=2)
    claimed = claim_next_job(db, worker_id="old-worker", lease_seconds=1)
    assert claimed and claimed["id"] == job["id"]
    with connect_sqlite(db) as con:
        run_id = con.execute("INSERT INTO crawl_run(domain,base_url,status,page_cap,delay_ms,obey_robots,execution_run_id) VALUES ('example.com','https://example.com','running',1,0,1,?)", (job["id"],)).lastrowid
        inventory_id = con.execute("INSERT INTO crawl_url_inventory(domain,url,discovered_at,updated_at) VALUES ('example.com','https://example.com/', 'now','now')").lastrowid
        con.execute("INSERT INTO crawl_frontier(crawl_run_id,url_inventory_id,state,queued_at,updated_at) VALUES (?,?, 'fetching','now','now')", (run_id, inventory_id))
        con.execute("UPDATE durable_job SET lease_expires_at=? WHERE id=?", ((utcnow() - timedelta(minutes=1)).isoformat(timespec="seconds"), job["id"]))
        con.commit()
    result = recover_abandoned_jobs(db)
    assert result == {"requeued": 1, "failed": 0}
    with connect_sqlite(db, readonly=True) as con:
        assert con.execute("SELECT status FROM durable_job WHERE id=?", (job["id"],)).fetchone()["status"] == "queued"
        assert con.execute("SELECT state FROM crawl_frontier WHERE crawl_run_id=?", (run_id,)).fetchone()["state"] == "queued"
        assert con.execute("SELECT event_type FROM durable_job_event WHERE job_id=? ORDER BY id DESC", (job["id"],)).fetchone()["event_type"] == "ownership_lost_requeued"
