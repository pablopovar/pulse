from datetime import datetime, timezone
import json
from flask import redirect, render_template, request, url_for

def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def _tables(con):
    return {
        r["name"] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
    }

def _cols(con, table):
    return {r["name"] for r in con.execute(f'PRAGMA table_info("{table}")').fetchall()}

def _ids(con, table, domain):
    if table not in _tables(con):
        return []
    cols = _cols(con, table)
    if "id" not in cols or "domain" not in cols:
        return []
    return [r["id"] for r in con.execute(f'SELECT id FROM "{table}" WHERE domain=?', (domain,)).fetchall()]

def _delete_ids(con, table, col, ids):
    if not ids or table not in _tables(con):
        return
    marks = ",".join("?" for _ in ids)
    con.execute(f'DELETE FROM "{table}" WHERE "{col}" IN ({marks})', ids)

def delete_domain_data(con, domain):
    tables = _tables(con)

    page_ids = _ids(con, "site_page", domain)
    audit_run_ids = _ids(con, "audit_run", domain)
    crawl_run_ids = _ids(con, "crawl_run", domain)

    audit_page_ids = []
    if "audit_page" in tables and audit_run_ids:
        marks = ",".join("?" for _ in audit_run_ids)
        audit_page_ids = [r["id"] for r in con.execute(
            f"SELECT id FROM audit_page WHERE audit_run_id IN ({marks})", audit_run_ids
        ).fetchall()]

    _delete_ids(con, "audit_signal", "audit_page_id", audit_page_ids)
    _delete_ids(con, "audit_page", "audit_run_id", audit_run_ids)
    _delete_ids(con, "audit_domain_summary", "audit_run_id", audit_run_ids)

    for t in ("crawl_link", "crawl_issue", "crawl_page"):
        _delete_ids(con, t, "crawl_run_id", crawl_run_ids)

    for t in ("site_page_tag", "page_note"):
        _delete_ids(con, t, "page_id", page_ids)

    preserve = {"keyword_tag", "page_tag", "domain_suppression", "operational_audit"}
    for table in sorted(tables):
        if table in preserve:
            continue
        cols = _cols(con, table)
        if "domain" in cols:
            con.execute(f'DELETE FROM "{table}" WHERE domain=?', (domain,))

    for table in sorted(tables):
        if table in preserve:
            continue
        cols = _cols(con, table)
        if "page_id" in cols:
            _delete_ids(con, table, "page_id", page_ids)

    if "site_page" in tables:
        con.execute("DELETE FROM site_page WHERE domain=?", (domain,))
    if "dashboard_domain" in tables:
        con.execute("DELETE FROM dashboard_domain WHERE domain=? COLLATE NOCASE", (domain,))

    con.execute(
        """INSERT INTO domain_suppression(domain,suppressed_at)
           VALUES (?,?)
           ON CONFLICT(domain) DO UPDATE SET suppressed_at=excluded.suppressed_at""",
        (domain, _now())
    )


def active_domain_jobs(con, domain):
    if "durable_job" not in _tables(con):
        return []
    return con.execute(
        """
        SELECT id,job_type,status,stage,created_at FROM durable_job
        WHERE domain=? COLLATE NOCASE AND status IN ('queued','running','paused')
        ORDER BY created_at
        """,
        (domain,),
    ).fetchall()

def register_delete_domain(app, research_db, get_site, get_sites):
    @app.get("/d/<domain>/delete")
    def domain_delete_confirm(domain):
        site = get_site(domain)
        with research_db() as con:
            active_jobs = active_domain_jobs(con, site["domain"])
        return render_template(
            "domain_delete.html", sites=get_sites(), site=site,
            active_jobs=active_jobs, error="",
        )

    @app.post("/d/<domain>/delete")
    def domain_delete(domain):
        site = get_site(domain)
        deleted = site["domain"]
        confirmation = request.form.get("confirmation", "").strip()
        if confirmation != deleted:
            with research_db() as con:
                active_jobs = active_domain_jobs(con, deleted)
            return render_template(
                "domain_delete.html", sites=get_sites(), site=site,
                active_jobs=active_jobs,
                error="Confirmation did not exactly match the domain.",
            ), 400
        with research_db() as con:
            con.execute("BEGIN IMMEDIATE")
            active_jobs = active_domain_jobs(con, deleted)
            if active_jobs:
                con.rollback()
                return render_template(
                    "domain_delete.html", sites=get_sites(), site=site,
                    active_jobs=active_jobs,
                    error="Cancel active and paused jobs before permanently deleting this domain.",
                ), 409
            delete_domain_data(con, deleted)
            con.execute(
                "INSERT INTO operational_audit(domain,action,detail_json,created_at) VALUES (?,?,?,?)",
                (
                    deleted, "domain_deleted",
                    json.dumps({"recovery": "not_available", "confirmation": "exact_domain"}),
                    _now(),
                ),
            )
            con.commit()

        sites = get_sites()
        if sites:
            return redirect(url_for("overview", domain=sites[0]["domain"]))
        return redirect("/")
