from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from db.sqlite import connect_sqlite
from integrations.opengsc_adapter import OpenGSCAdapter


def _exists(con, name: str) -> bool:
    return bool(con.execute("SELECT 1 FROM sqlite_master WHERE name=? LIMIT 1", (name,)).fetchone())


def _rows(con, sql: str, params=()):
    return [dict(row) for row in con.execute(sql, params).fetchall()]


def _row(con, sql: str, params=()):
    row = con.execute(sql, params).fetchone()
    return dict(row) if row else None


def collect_report_data(domain: str, site_id: str | None, seo_db: Path, research_db: Path):
    data: dict[str, Any] = {
        "domain": domain,
        "site_id": site_id,
        "generated_at": datetime.now(timezone.utc),
        "seo": None,
        "keywords": [],
        "wanted": [],
        "crawl": None,
        "crawl_issues": [],
        "crawl_pages": [],
        "audit": None,
        "audit_summary": None,
        "audit_pages": [],
        "audit_signals": [],
        "domain_score_history": [],
        "page_score_history": [],
    }

    adapter = OpenGSCAdapter(seo_db)
    data.update(adapter.report_core(site_id))

    if research_db.exists():
        with connect_sqlite(research_db) as con:
            if _exists(con, "wanted_keyword"):
                data["wanted"] = _rows(
                    con,
                    """
                    SELECT w.keyword,w.avg_monthly_searches,w.competition,w.source,
                           p.path AS target_path
                    FROM wanted_keyword w
                    LEFT JOIN site_page p ON p.id=w.page_id
                    WHERE w.domain=?
                    ORDER BY w.keyword COLLATE NOCASE
                    """,
                    (domain,),
                )

            if _exists(con, "crawl_run"):
                data["crawl"] = _row(
                    con,
                    "SELECT * FROM crawl_run WHERE domain=? ORDER BY id DESC LIMIT 1",
                    (domain,),
                )
                if data["crawl"]:
                    run_id = data["crawl"]["id"]
                    data["crawl_issues"] = _rows(
                        con,
                        """
                        SELECT severity,title,detail,page_url
                        FROM crawl_issue
                        WHERE crawl_run_id=?
                        ORDER BY CASE severity WHEN 'critical' THEN 1 WHEN 'high' THEN 2
                                               WHEN 'medium' THEN 3 ELSE 4 END,
                                 title,page_url
                        """,
                        (run_id,),
                    )
                    data["crawl_pages"] = _rows(
                        con,
                        """
                        SELECT path,url,status_code,title,description,canonical,
                               word_count,internal_links,external_links,image_count,
                               images_missing_alt,schema_types_json,indexable,response_ms,error
                        FROM crawl_page WHERE crawl_run_id=? ORDER BY path
                        """,
                        (run_id,),
                    )

            if _exists(con, "audit_run"):
                data["audit"] = _row(
                    con,
                    "SELECT * FROM audit_run WHERE domain=? ORDER BY id DESC LIMIT 1",
                    (domain,),
                )
                if data["audit"]:
                    audit_run_id = data["audit"]["id"]
                    if _exists(con, "audit_domain_summary"):
                        data["audit_summary"] = _row(
                            con,
                            "SELECT * FROM audit_domain_summary WHERE audit_run_id=?",
                            (audit_run_id,),
                        )
                        data["domain_score_history"] = _rows(
                            con,
                            """
                            SELECT ar.id AS audit_run_id,ar.completed_at,ar.started_at,
                                   ads.geo_score,ads.aeo_score,ads.combined_score,ads.pages_audited,
                                   ads.fail_count,ads.partial_count,ads.pass_count,ads.unknown_count,ads.manual_count
                            FROM audit_domain_summary ads
                            JOIN audit_run ar ON ar.id=ads.audit_run_id
                            WHERE ads.domain=? ORDER BY ar.id DESC LIMIT 50
                            """,
                            (domain,),
                        )
                    if _exists(con, "audit_page"):
                        data["audit_pages"] = _rows(
                            con,
                            """
                            SELECT ap.*,p.path FROM audit_page ap
                            JOIN site_page p ON p.id=ap.page_id
                            WHERE ap.audit_run_id=? ORDER BY p.path
                            """,
                            (audit_run_id,),
                        )
                        data["page_score_history"] = _rows(
                            con,
                            """
                            SELECT ap.page_id,p.path,ap.audit_run_id,ar.completed_at,ar.started_at,
                                   ap.geo_score,ap.aeo_score,ap.combined_score
                            FROM audit_page ap
                            JOIN audit_run ar ON ar.id=ap.audit_run_id
                            JOIN site_page p ON p.id=ap.page_id
                            WHERE ar.domain=? ORDER BY ap.page_id,ap.audit_run_id DESC
                            """,
                            (domain,),
                        )
                    if _exists(con, "audit_signal"):
                        data["audit_signals"] = _rows(
                            con,
                            """
                            SELECT ap.page_id,ap.url,p.path,s.family,s.signal_key,s.category,s.title,
                                   s.observed_status,s.severity,s.weight,s.evidence,s.recommendation,
                                   s.source_title,s.source_url,
                                   COALESCE(st.workflow_status,'open') workflow_status,
                                   COALESCE(st.priority,'') priority,
                                   COALESCE(st.user_note,'') user_note,
                                   COALESCE(st.override_status,'') override_status
                            FROM audit_signal s
                            JOIN audit_page ap ON ap.id=s.audit_page_id
                            JOIN site_page p ON p.id=ap.page_id
                            LEFT JOIN audit_signal_state st
                              ON st.domain=? AND st.page_id=ap.page_id
                             AND st.family=s.family AND st.signal_key=s.signal_key
                            WHERE ap.audit_run_id=?
                            ORDER BY p.path,s.family,s.category,s.signal_key
                            """,
                            (domain, audit_run_id),
                        )

    return adapter.enrich_report(data, site_id, domain)
