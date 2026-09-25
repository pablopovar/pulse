from __future__ import annotations

import json
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from db.sqlite import connect_sqlite

ALL_STATUSES = frozenset({"queued", "running", "paused", "completed", "partial", "failed", "cancelled"})
TERMINAL_STATUSES = frozenset({"completed", "partial", "failed", "cancelled"})


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso(value: datetime | None = None) -> str:
    return (value or utcnow()).isoformat(timespec="seconds")


def _lease_duration(seconds: int) -> int:
    return max(1, int(seconds))


def _json_load_object(raw: str | None) -> dict[str, Any]:
    try:
        value = json.loads(raw or "{}")
    except Exception:
        return {}
    return value if isinstance(value, dict) else {}


def _row_to_job(row) -> dict[str, Any] | None:
    if row is None:
        return None
    out = dict(row)
    out["payload"] = _json_load_object(out.pop("payload_json", "{}"))
    out["result_ref"] = _json_load_object(out.pop("result_ref_json", "{}"))
    out["error"] = _json_load_object(out.pop("error_json", "{}"))
    return out


def enqueue_job(
    db_path: str | Path,
    job_type: str,
    *,
    domain: str = "",
    payload: dict[str, Any] | None = None,
    max_attempts: int = 3,
    job_id: str | None = None,
    available_at: str | None = None,
) -> dict[str, Any]:
    job_type = str(job_type or "").strip()
    if not job_type:
        raise ValueError("job_type is required")
    if int(max_attempts) < 1:
        raise ValueError("max_attempts must be >= 1")

    now = iso()
    job_id = job_id or secrets.token_urlsafe(18)
    with connect_sqlite(db_path) as con:
        con.execute(
            """
            INSERT INTO durable_job(
                id,domain,job_type,status,payload_json,result_ref_json,error_json,
                attempts,max_attempts,queued_at,available_at,created_at,updated_at
            ) VALUES (?,?,?,'queued',?,'{}','{}',0,?,?,?,?,?)
            """,
            (
                job_id,
                str(domain or ""),
                job_type,
                json.dumps(payload or {}, separators=(",", ":")),
                int(max_attempts),
                now,
                available_at or now,
                now,
                now,
            ),
        )
        con.commit()
    job = get_job(db_path, job_id)
    assert job is not None
    return job


def get_job(db_path: str | Path, job_id: str) -> dict[str, Any] | None:
    with connect_sqlite(db_path, readonly=True) as con:
        row = con.execute("SELECT * FROM durable_job WHERE id=?", (job_id,)).fetchone()
    return _row_to_job(row)


def list_jobs(
    db_path: str | Path,
    *,
    domain: str | None = None,
    status: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    limit = max(1, min(int(limit), 250))
    where: list[str] = []
    params: list[Any] = []

    if domain is not None:
        where.append("domain=?")
        params.append(domain)
    if status is not None:
        if status not in ALL_STATUSES:
            raise ValueError(f"invalid job status: {status}")
        where.append("status=?")
        params.append(status)

    sql = "SELECT * FROM durable_job"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    with connect_sqlite(db_path, readonly=True) as con:
        rows = con.execute(sql, params).fetchall()
    return [_row_to_job(row) for row in rows]


def claim_next_job(
    db_path: str | Path,
    *,
    worker_id: str,
    lease_seconds: int = 120,
    at: datetime | None = None,
) -> dict[str, Any] | None:
    current = at or utcnow()
    now = iso(current)
    lease_expires = iso(current + timedelta(seconds=_lease_duration(lease_seconds)))

    with connect_sqlite(db_path) as con:
        con.execute("BEGIN IMMEDIATE")
        row = con.execute(
            """
            SELECT id
            FROM durable_job
            WHERE status='queued' AND (available_at<=? OR available_at=queued_at)
            ORDER BY queued_at ASC, created_at ASC
            LIMIT 1
            """,
            (now,),
        ).fetchone()
        if row is None:
            con.commit()
            return None

        job_id = row["id"]
        changed = con.execute(
            """
            UPDATE durable_job
            SET status='running',
                attempts=attempts+1,
                started_at=?,
                heartbeat_at=?,
                lease_expires_at=?,
                worker_id=?,
                error_json='{}',
                updated_at=?
            WHERE id=? AND status='queued'
            """,
            (now, now, lease_expires, worker_id, now, job_id),
        ).rowcount
        if changed != 1:
            con.rollback()
            return None

        claimed = con.execute("SELECT * FROM durable_job WHERE id=?", (job_id,)).fetchone()
        con.commit()
    return _row_to_job(claimed)


def heartbeat_job(
    db_path: str | Path,
    job_id: str,
    *,
    worker_id: str,
    lease_seconds: int = 120,
) -> bool:
    current = utcnow()
    now = iso(current)
    lease_expires = iso(current + timedelta(seconds=_lease_duration(lease_seconds)))
    with connect_sqlite(db_path) as con:
        changed = con.execute(
            """
            UPDATE durable_job
            SET heartbeat_at=?,lease_expires_at=?,updated_at=?
            WHERE id=?
              AND status='running'
              AND worker_id=?
              AND lease_expires_at IS NOT NULL
              AND lease_expires_at>=?
            """,
            (now, lease_expires, now, job_id, worker_id, now),
        ).rowcount
        con.commit()
    return changed == 1


def worker_owns_job(
    db_path: str | Path,
    job_id: str,
    *,
    worker_id: str,
    at: datetime | None = None,
) -> bool:
    now = iso(at or utcnow())
    with connect_sqlite(db_path, readonly=True) as con:
        row = con.execute(
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
    return row is not None


def finish_job(
    db_path: str | Path,
    job_id: str,
    *,
    worker_id: str,
    status: str,
    result_ref: dict[str, Any] | None = None,
    error: dict[str, Any] | None = None,
) -> bool:
    if status not in {"completed", "partial", "failed"}:
        raise ValueError("status must be completed, partial, or failed")

    now = iso()
    with connect_sqlite(db_path) as con:
        changed = con.execute(
            """
            UPDATE durable_job
            SET status=?,
                result_ref_json=?,
                error_json=?,
                completed_at=?,
                heartbeat_at=NULL,
                lease_expires_at=NULL,
                worker_id='',
                updated_at=?
            WHERE id=?
              AND status='running'
              AND worker_id=?
              AND lease_expires_at IS NOT NULL
              AND lease_expires_at>=?
            """,
            (
                status,
                json.dumps(result_ref or {}, separators=(",", ":")),
                json.dumps(error or {}, separators=(",", ":")),
                now,
                now,
                job_id,
                worker_id,
                now,
            ),
        ).rowcount
        con.commit()
    return changed == 1


def fail_from_exception(
    db_path: str | Path,
    job_id: str,
    *,
    worker_id: str,
    exc: BaseException,
    stage: str = "execute",
) -> bool:
    return finish_job(
        db_path,
        job_id,
        worker_id=worker_id,
        status="failed",
        error={
            "kind": exc.__class__.__name__,
            "message": str(exc),
            "stage": stage,
            "at": iso(),
        },
    )


def cancel_job(db_path: str | Path, job_id: str, *, reason: str = "Cancelled by operator.") -> bool:
    now = iso()
    with connect_sqlite(db_path) as con:
        con.execute("BEGIN IMMEDIATE")
        changed = con.execute(
            """
            UPDATE durable_job
            SET status='cancelled',cancelled_at=?,completed_at=?,heartbeat_at=NULL,
                lease_expires_at=NULL,worker_id='',
                error_json=?,updated_at=?
            WHERE id=? AND status IN ('queued','running','paused')
            """,
            (
                now,
                now,
                json.dumps({"kind": "cancelled", "message": reason, "at": now}, separators=(",", ":")),
                now,
                job_id,
            ),
        ).rowcount
        if changed:
            con.execute(
                """
                UPDATE crawl_run
                SET status='cancelled',cancelled_at=?,completed_at=?,status_reason=?,current_url=''
                WHERE execution_run_id=? AND status IN ('queued','running','paused')
                """,
                (now, now, reason, job_id),
            )
            con.execute(
                """
                UPDATE crawl_frontier SET state='cancelled',reason=?,updated_at=?
                WHERE crawl_run_id IN (SELECT id FROM crawl_run WHERE execution_run_id=?)
                  AND state IN ('queued','fetching')
                """,
                (reason, now, job_id),
            )
        con.commit()
    return changed == 1


def cancel_queued_job(db_path: str | Path, job_id: str) -> bool:
    """Backward-compatible name; cancellation now also supports running jobs."""

    return cancel_job(db_path, job_id)


def pause_job(db_path: str | Path, job_id: str) -> bool:
    now = iso()
    with connect_sqlite(db_path) as con:
        con.execute("BEGIN IMMEDIATE")
        changed = con.execute(
            """
            UPDATE durable_job
            SET status='paused',paused_at=?,heartbeat_at=NULL,lease_expires_at=NULL,
                worker_id='',updated_at=?
            WHERE id=? AND status IN ('queued','running')
            """,
            (now, now, job_id),
        ).rowcount
        if changed:
            con.execute(
                """
                UPDATE crawl_run
                SET status='paused',paused_at=?,status_reason='Paused by operator.',current_url=''
                WHERE execution_run_id=? AND status IN ('queued','running')
                """,
                (now, job_id),
            )
        con.commit()
    return changed == 1


def resume_job(db_path: str | Path, job_id: str) -> bool:
    now = iso()
    with connect_sqlite(db_path) as con:
        con.execute("BEGIN IMMEDIATE")
        changed = con.execute(
            """
            UPDATE durable_job
            SET status='queued',queued_at=?,available_at=?,paused_at=NULL,
                error_json='{}',updated_at=?
            WHERE id=? AND status='paused'
            """,
            (now, now, now, job_id),
        ).rowcount
        if changed:
            con.execute(
                """
                UPDATE crawl_run SET status='queued',paused_at=NULL,status_reason='Resumed by operator.'
                WHERE execution_run_id=? AND status='paused'
                """,
                (job_id,),
            )
        con.commit()
    return changed == 1


def job_control_state(db_path: str | Path, job_id: str) -> str | None:
    with connect_sqlite(db_path, readonly=True) as con:
        row = con.execute("SELECT status FROM durable_job WHERE id=?", (job_id,)).fetchone()
    return str(row["status"]) if row else None


def recover_abandoned_jobs(
    db_path: str | Path,
    *,
    at: datetime | None = None,
) -> dict[str, int]:
    current = at or utcnow()
    now = iso(current)
    requeued = 0
    failed = 0

    with connect_sqlite(db_path) as con:
        con.execute("BEGIN IMMEDIATE")
        rows = con.execute(
            """
            SELECT id,attempts,max_attempts,worker_id,lease_expires_at
            FROM durable_job
            WHERE status='running'
              AND lease_expires_at IS NOT NULL
              AND lease_expires_at < ?
            ORDER BY lease_expires_at ASC
            """,
            (now,),
        ).fetchall()

        for row in rows:
            error = {
                "kind": "abandoned_job",
                "message": "Worker lease expired before terminal completion.",
                "previous_worker_id": row["worker_id"] or "",
                "lease_expires_at": row["lease_expires_at"],
                "recovered_at": now,
            }
            error_json = json.dumps(error, separators=(",", ":"))

            if int(row["attempts"]) < int(row["max_attempts"]):
                con.execute(
                    """
                    UPDATE durable_job
                    SET status='queued',
                        queued_at=?,
                        started_at=NULL,
                        heartbeat_at=NULL,
                        lease_expires_at=NULL,
                        worker_id='',
                        error_json=?,
                        updated_at=?
                    WHERE id=? AND status='running'
                    """,
                    (now, error_json, now, row["id"]),
                )
                requeued += 1
            else:
                con.execute(
                    """
                    UPDATE durable_job
                    SET status='failed',
                        completed_at=?,
                        heartbeat_at=NULL,
                        lease_expires_at=NULL,
                        worker_id='',
                        error_json=?,
                        updated_at=?
                    WHERE id=? AND status='running'
                    """,
                    (now, error_json, now, row["id"]),
                )
                failed += 1
        con.commit()

    return {"requeued": requeued, "failed": failed}


def set_job_stage(db_path, job_id, *, worker_id, stage, publication_status=None):
    now = iso()
    with connect_sqlite(db_path) as con:
        if publication_status is None:
            changed = con.execute(
                """
                UPDATE durable_job
                SET stage=?,updated_at=?
                WHERE id=?
                  AND status='running'
                  AND worker_id=?
                  AND lease_expires_at IS NOT NULL
                  AND lease_expires_at>=?
                """,
                (stage, now, job_id, worker_id, now),
            ).rowcount
        else:
            changed = con.execute(
                """
                UPDATE durable_job
                SET stage=?,publication_status=?,updated_at=?
                WHERE id=?
                  AND status='running'
                  AND worker_id=?
                  AND lease_expires_at IS NOT NULL
                  AND lease_expires_at>=?
                """,
                (stage, publication_status, now, job_id, worker_id, now),
            ).rowcount
        con.commit()
    return changed == 1


def set_job_publication_status(db_path, job_id, *, worker_id, publication_status):
    now = iso()
    with connect_sqlite(db_path) as con:
        changed = con.execute(
            """
            UPDATE durable_job
            SET publication_status=?,updated_at=?
            WHERE id=?
              AND status='running'
              AND worker_id=?
              AND lease_expires_at IS NOT NULL
              AND lease_expires_at>=?
            """,
            (publication_status, now, job_id, worker_id, now),
        ).rowcount
        con.commit()
    return changed == 1
