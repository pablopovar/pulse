from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from db.sqlite import connect_sqlite
from integrations.opengsc_adapter import OpenGSCAdapter
from services.sitemap_reconciliation import reconcile_sitemap_urls


def _exists(con, name: str) -> bool:
    return bool(con.execute("SELECT 1 FROM sqlite_master WHERE name=? LIMIT 1", (name,)).fetchone())


def _rows(con, sql: str, params=()):
    return [dict(row) for row in con.execute(sql, params).fetchall()]


def _row(con, sql: str, params=()):
    row = con.execute(sql, params).fetchone()
    return dict(row) if row else None


def collect_report_data(
    domain: str,
    site_id: str | None,
    seo_db: Path,
    research_db: Path,
    *,
    execution_run_id: str,
    audit_run_id: int,
    crawl_run_id: int,
):
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
        "dataforseo_snapshots": [],
        "historical_dataforseo_snapshots": [],
        "llm_sources": [],
        "sitemap_reconciliation": [],
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

            if _exists(con, "dataforseo_snapshot"):
                paid_rows = _rows(
                    con,
                    """SELECT endpoint,created_at,report_run_id
                       FROM dataforseo_snapshot
                       WHERE domain=? COLLATE NOCASE
                       ORDER BY id DESC LIMIT 20""",
                    (domain,),
                )
                data["dataforseo_snapshots"] = [row for row in paid_rows if str(row.get("report_run_id") or "") == execution_run_id]
                data["historical_dataforseo_snapshots"] = [row for row in paid_rows if str(row.get("report_run_id") or "") != execution_run_id]

            data["audit"] = _row(
                con,
                "SELECT * FROM audit_run WHERE id=? AND domain=? COLLATE NOCASE AND execution_run_id=? AND status='completed'",
                (audit_run_id, domain, execution_run_id),
            ) if _exists(con, "audit_run") else None
            data["crawl"] = _row(
                con,
                "SELECT * FROM crawl_run WHERE id=? AND domain=? COLLATE NOCASE AND execution_run_id=? AND status IN ('completed','partial')",
                (crawl_run_id, domain, execution_run_id),
            ) if _exists(con, "crawl_run") else None
            if not data["audit"] or not data["crawl"]:
                raise RuntimeError(
                    f"Report evidence missing or inconsistent for execution {execution_run_id}: "
                    f"audit_run={audit_run_id}, crawl_run={crawl_run_id}"
                )
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
                if _exists(con, "crawl_event"):
                    event = _row(con, "SELECT detail_json FROM crawl_event WHERE crawl_run_id=? AND event_type='agent_readiness_sources' ORDER BY id DESC LIMIT 1", (run_id,))
                    if event:
                        try:
                            data["llm_sources"] = json.loads(event.get("detail_json") or "[]")
                        except (TypeError, ValueError):
                            data["llm_sources"] = []
                data["crawl_pages"] = _rows(
                    con,
                    """
                    SELECT path,url,status_code,title,description,canonical,
                           word_count,internal_links,external_links,image_count,
                           images_missing_alt,schema_types_json,indexable,response_ms,error,
                           content_type,content_bytes,resource_type,response_sha256,audit_status,observed_at,page_type,page_type_confidence
                    FROM crawl_page WHERE crawl_run_id=? ORDER BY path
                    """,
                    (run_id,),
                )
                if _exists(con, "resource_outcome"):
                    data["resource_outcomes"] = _rows(
                        con,
                        """SELECT requested_url,final_url,http_status,content_type,resource_type,response_size,response_sha256,response_headers_json,body_retained,etag,last_modified,redirect_chain_json,discovered_at,observed_at,crawl_state,audit_state,failure_kind,reason,duplicate_or_canonical_target FROM resource_outcome WHERE crawl_run_id=? ORDER BY requested_url""",
                        (run_id,),
                    )
                if _exists(con, "sitemap_source_evidence"):
                    data["sitemap"] = _rows(
                        con,
                        "SELECT requested_url,source_type,discovery_origin,parent_sitemap,http_status,content_type,response_size,response_sha256,observed_at,parse_status,parse_error,child_sitemaps_json FROM sitemap_source_evidence WHERE crawl_run_id=? ORDER BY requested_url",
                        (run_id,),
                    )
                    # data_coverage consumes sitemap_urls for legacy
                    # snapshots.  Feed it the same concrete evidence used
                    # for this crawler-backed observation.
                    data["sitemap_urls"] = list(data["sitemap"])
                if _exists(con, "llm_source_evidence"):
                    data["llm_sources"] = _rows(
                        con,
                        """SELECT source_key AS name,url,availability AS status,http_status,content_type,headers_json AS headers,response_size AS bytes,response_sha256 AS sha256,observed_at,raw_content AS content,body_retained,parse_json,parse_error,reason FROM llm_source_evidence WHERE crawl_run_id=? ORDER BY source_key""",
                        (run_id,),
                    )
                inventory = _rows(con, "SELECT url,source,source_sitemap,eligibility,decision_reason FROM crawl_url_inventory WHERE domain=?", (domain,)) if _exists(con, "crawl_url_inventory") else []
                sitemap_entries = [{"url": row["url"], "source_sitemap": row.get("source_sitemap") or ""} for row in inventory if row.get("source_sitemap")]
                data["sitemap_reconciliation"] = reconcile_sitemap_urls(sitemap_entries, data["crawl_pages"], inventory)

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

            audit = data.get("audit") or {}
            crawl = data.get("crawl") or {}
            linked = bool(audit and crawl and audit.get("execution_run_id") and audit.get("execution_run_id") == crawl.get("execution_run_id"))
            data["observation_provenance"] = {
                "audit_run_id": audit.get("id"),
                "crawl_run_id": crawl.get("id"),
                "execution_run_id": audit.get("execution_run_id") or None,
                "inputs_linked": linked,
                "legacy_unlinked": bool(audit and crawl and not linked),
                "gsc_period_start": (data.get("seo") or {}).get("period_start"),
                "gsc_period_end": (data.get("seo") or {}).get("period_end"),
            }

    if not data["audit"] or not data["crawl"]:
        raise RuntimeError(
            f"Report evidence missing or inconsistent for execution {execution_run_id}: "
            f"audit_run={audit_run_id}, crawl_run={crawl_run_id}"
        )
    return adapter.enrich_report(data, site_id, domain)
