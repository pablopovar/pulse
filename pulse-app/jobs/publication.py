from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from db.sqlite import connect_sqlite


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def publish_report_if_owned(
    db_path: str | Path,
    *,
    job_id: str,
    worker_id: str,
    domain: str,
    report_id: str,
) -> bool:
    """Publish one prepared report only while this worker still owns the job.

    The ownership check, current-report pointer update, and publication-state
    transition occur under the same SQLite write transaction. A stale worker
    may leave an immutable report_session artifact, but it cannot advance the
    domain's current Pulse state.
    """
    now = _now()
    with connect_sqlite(db_path) as con:
        con.execute("BEGIN IMMEDIATE")
        owned = con.execute(
            """
            SELECT 1
            FROM durable_job
            WHERE id=?
              AND status='running'
              AND worker_id=?
              AND lease_expires_at IS NOT NULL
              AND lease_expires_at>=?
            """,
            (job_id, worker_id, now),
        ).fetchone()
        if owned is None:
            con.rollback()
            return False

        report = con.execute(
            """
            SELECT id
            FROM report_session
            WHERE id=?
              AND domain=? COLLATE NOCASE
              AND execution_run_id=?
            """,
            (report_id, domain, job_id),
        ).fetchone()
        if report is None:
            con.rollback()
            raise RuntimeError(
                "Cannot publish report: report_session does not belong to the durable job."
            )

        con.execute(
            """
            UPDATE durable_job
            SET stage='publish',publication_status='publishing',updated_at=?
            WHERE id=? AND status='running' AND worker_id=?
            """,
            (now, job_id, worker_id),
        )

        living = con.execute(
            "SELECT baseline_report_id FROM domain_report WHERE domain=? COLLATE NOCASE",
            (domain,),
        ).fetchone()
        if living:
            con.execute(
                """
                UPDATE domain_report
                SET current_report_id=?,updated_at=?
                WHERE domain=? COLLATE NOCASE
                """,
                (report_id, now, domain),
            )
        else:
            con.execute(
                """
                INSERT INTO domain_report(
                    domain,baseline_report_id,current_report_id,created_at,updated_at
                ) VALUES (?,?,?,?,?)
                """,
                (domain, report_id, report_id, now, now),
            )

        changed = con.execute(
            """
            UPDATE durable_job
            SET publication_status='published',updated_at=?
            WHERE id=?
              AND status='running'
              AND worker_id=?
              AND lease_expires_at IS NOT NULL
              AND lease_expires_at>=?
            """,
            (now, job_id, worker_id, now),
        ).rowcount
        if changed != 1:
            con.rollback()
            return False

        con.commit()
        return True
