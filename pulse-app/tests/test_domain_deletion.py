from __future__ import annotations

from db.migrate import migrate_up
from db.sqlite import connect_sqlite
from services.domains import delete_domain_data


def test_domain_deletion_removes_crawl_dependents_and_preserves_other_domains(tmp_path):
    db = tmp_path / "pulse.db"
    migrate_up(db)
    with connect_sqlite(db) as con:
        doomed_run = con.execute(
            """INSERT INTO crawl_run(domain,base_url,status,page_cap,delay_ms,obey_robots,report_scope)
               VALUES ('remove.example','https://remove.example','completed',15,0,1,'report')"""
        ).lastrowid
        kept_run = con.execute(
            """INSERT INTO crawl_run(domain,base_url,status,page_cap,delay_ms,obey_robots,report_scope)
               VALUES ('keep.example','https://keep.example','completed',15,0,1,'report')"""
        ).lastrowid
        doomed_inventory = con.execute(
            """INSERT INTO crawl_url_inventory(domain,url,source,classification,eligibility,decision_reason,
               priority_score,discovered_at,updated_at)
               VALUES ('remove.example','https://remove.example/','sitemap','core_page','eligible','core',1,'now','now')"""
        ).lastrowid
        kept_inventory = con.execute(
            """INSERT INTO crawl_url_inventory(domain,url,source,classification,eligibility,decision_reason,
               priority_score,discovered_at,updated_at)
               VALUES ('keep.example','https://keep.example/','sitemap','core_page','eligible','core',1,'now','now')"""
        ).lastrowid
        for run_id, inventory_id in ((doomed_run, doomed_inventory), (kept_run, kept_inventory)):
            con.execute(
                """INSERT INTO crawl_frontier(crawl_run_id,url_inventory_id,state,reason,priority_score,queued_at,updated_at)
                   VALUES (?,?,'completed','done',1,'now','now')""",
                (run_id, inventory_id),
            )
        con.execute(
            """INSERT INTO durable_job(id,domain,job_type,status,payload_json,result_ref_json,error_json,
                attempts,max_attempts,queued_at,available_at,worker_id,created_at,updated_at,stage,publication_status)
               VALUES ('remove-job','remove.example','report_refresh','completed','{}','{}','{}',0,3,'now','now','','now','now','done','not_applicable')"""
        )
        delete_domain_data(con, "remove.example")
        con.commit()

    with connect_sqlite(db, readonly=True) as con:
        assert con.execute("SELECT COUNT(*) AS n FROM crawl_run WHERE domain='remove.example'").fetchone()["n"] == 0
        assert con.execute("SELECT COUNT(*) AS n FROM crawl_url_inventory WHERE domain='remove.example'").fetchone()["n"] == 0
        assert con.execute("SELECT COUNT(*) AS n FROM durable_job WHERE domain='remove.example'").fetchone()["n"] == 0
        assert con.execute("SELECT COUNT(*) AS n FROM crawl_frontier WHERE crawl_run_id=?", (doomed_run,)).fetchone()["n"] == 0
        assert con.execute("SELECT COUNT(*) AS n FROM crawl_frontier WHERE crawl_run_id=?", (kept_run,)).fetchone()["n"] == 1
        assert con.execute("SELECT COUNT(*) AS n FROM domain_suppression WHERE domain='remove.example'").fetchone()["n"] == 1
