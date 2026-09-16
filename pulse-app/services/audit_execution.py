from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from audits.geo_aeo.service import run_audit as run_geo_aeo_audit
from db.sqlite import connect_sqlite


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def recompute_domain_summary(con, run_id: int, domain: str) -> None:
    pages = con.execute(
        "SELECT geo_score,aeo_score,combined_score FROM audit_page WHERE audit_run_id=?",
        (run_id,),
    ).fetchall()

    def avg(name: str):
        values = [row[name] for row in pages if row[name] is not None]
        return round(sum(values) / len(values)) if values else None

    counts = con.execute(
        """
        SELECT
          SUM(CASE WHEN s.observed_status='FAIL' THEN 1 ELSE 0 END) fail_count,
          SUM(CASE WHEN s.observed_status='PARTIAL' THEN 1 ELSE 0 END) partial_count,
          SUM(CASE WHEN s.observed_status='PASS' THEN 1 ELSE 0 END) pass_count,
          SUM(CASE WHEN s.observed_status='UNKNOWN' THEN 1 ELSE 0 END) unknown_count,
          SUM(CASE WHEN s.observed_status='MANUAL_REVIEW' THEN 1 ELSE 0 END) manual_count
        FROM audit_signal s
        JOIN audit_page p ON p.id=s.audit_page_id
        WHERE p.audit_run_id=?
        """,
        (run_id,),
    ).fetchone()
    con.execute(
        """
        INSERT INTO audit_domain_summary(
            audit_run_id,domain,pages_audited,geo_score,aeo_score,combined_score,
            fail_count,partial_count,pass_count,unknown_count,manual_count,created_at
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(audit_run_id) DO UPDATE SET
            pages_audited=excluded.pages_audited,
            geo_score=excluded.geo_score,
            aeo_score=excluded.aeo_score,
            combined_score=excluded.combined_score,
            fail_count=excluded.fail_count,
            partial_count=excluded.partial_count,
            pass_count=excluded.pass_count,
            unknown_count=excluded.unknown_count,
            manual_count=excluded.manual_count
        """,
        (
            run_id, domain, len(pages), avg("geo_score"), avg("aeo_score"), avg("combined_score"),
            counts["fail_count"] or 0, counts["partial_count"] or 0,
            counts["pass_count"] or 0, counts["unknown_count"] or 0,
            counts["manual_count"] or 0, _now(),
        ),
    )


def store_structured_audit(
    db_path: str | Path,
    domain: str,
    run_id: int,
    page_id: int,
    url: str,
    report: dict,
) -> None:
    capture = report.get("capture", {})
    geo = report.get("geo", {})
    aeo = report.get("aeo", {})
    combined = report.get("combined", {})
    with connect_sqlite(db_path) as con:
        con.execute(
            """
            INSERT OR REPLACE INTO audit_page(
                audit_run_id,page_id,url,page_type,geo_score,aeo_score,combined_score,
                geo_json,aeo_json,combined_json,capture_json,created_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                run_id, page_id, url, capture.get("page_type"), geo.get("score"),
                aeo.get("score"), combined.get("score"), json.dumps(geo), json.dumps(aeo),
                json.dumps(combined), json.dumps(capture), _now(),
            ),
        )
        row = con.execute(
            "SELECT id FROM audit_page WHERE audit_run_id=? AND page_id=?",
            (run_id, page_id),
        ).fetchone()
        audit_page_id = row["id"]
        con.execute("DELETE FROM audit_signal WHERE audit_page_id=?", (audit_page_id,))
        for item in report.get("findings", []):
            con.execute(
                """
                INSERT INTO audit_signal(
                    audit_page_id,family,signal_key,category,title,observed_status,severity,
                    weight,evidence,recommendation,source_title,source_url
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    audit_page_id, item.get("family", ""), item.get("id", ""),
                    item.get("category", ""), item.get("title", ""), item.get("status", ""),
                    item.get("severity", ""), item.get("weight", 0) or 0,
                    item.get("evidence", ""), item.get("recommendation", ""),
                    item.get("source_title", ""), item.get("source_url", ""),
                ),
            )
        recompute_domain_summary(con, run_id, domain)
        con.commit()


def run_audit_pages(
    db_path: str | Path,
    domain: str,
    run_id: int,
    pages: list[dict],
) -> str:
    errors: list[str] = []
    for page in pages:
        try:
            report = run_geo_aeo_audit(page["url"])
            store_structured_audit(db_path, domain, run_id, page["id"], page["url"], report)
        except Exception as exc:
            errors.append(f'{page["url"]}: {exc}')
    status = "completed" if not errors else ("partial" if len(errors) < len(pages) else "failed")
    with connect_sqlite(db_path) as con:
        con.execute(
            "UPDATE audit_run SET status=?,completed_at=?,error=? WHERE id=?",
            (status, _now(), "\n".join(errors), run_id),
        )
        recompute_domain_summary(con, run_id, domain)
        con.commit()
    return status
