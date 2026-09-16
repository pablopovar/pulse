from __future__ import annotations

import argparse
import inspect
import logging
import os
import socket
import threading
import time
import uuid
from pathlib import Path
from typing import Callable

from db.migrate import validate_schema_current
from jobs.handlers import handler_for
from jobs.store import (
    claim_next_job,
    fail_from_exception,
    finish_job,
    heartbeat_job,
    recover_abandoned_jobs,
)

DEFAULT_DB = Path(os.environ.get("RESEARCH_DB", "/data/audit/research.db"))
LOG = logging.getLogger(__name__)


def worker_id() -> str:
    return f"{socket.gethostname()}:{os.getpid()}:{uuid.uuid4().hex[:8]}"


def _heartbeat_loop(
    db_path: str | Path,
    job_id: str,
    *,
    claimed_by: str,
    lease_seconds: int,
    interval_seconds: float,
    stop_event: threading.Event,
    ownership_lost: threading.Event,
) -> None:
    while not stop_event.wait(interval_seconds):
        try:
            renewed = heartbeat_job(
                db_path,
                job_id,
                worker_id=claimed_by,
                lease_seconds=lease_seconds,
            )
        except BaseException:
            LOG.exception("heartbeat failed for job %s owned by %s", job_id, claimed_by)
            ownership_lost.set()
            return
        if not renewed:
            LOG.error("job ownership lost during heartbeat: job=%s worker=%s", job_id, claimed_by)
            ownership_lost.set()
            return


def execute_claimed_job(
    db_path: str | Path,
    job: dict,
    *,
    claimed_by: str,
    lease_seconds: int = 120,
    heartbeat_interval_seconds: float | None = None,
    resolver: Callable[[str], Callable | None] = handler_for,
) -> None:
    handler = resolver(str(job.get("job_type") or ""))
    if handler is None:
        finished = finish_job(
            db_path,
            job["id"],
            worker_id=claimed_by,
            status="failed",
            error={
                "kind": "unknown_job_type",
                "message": f"No handler registered for {job.get('job_type')!r}.",
                "stage": "dispatch",
            },
        )
        if not finished:
            LOG.error(
                "unable to record unknown job type because ownership was lost: job=%s worker=%s",
                job["id"],
                claimed_by,
            )
        return

    interval = (
        float(heartbeat_interval_seconds)
        if heartbeat_interval_seconds is not None
        else max(0.25, float(lease_seconds) / 3.0)
    )
    stop_event = threading.Event()
    ownership_lost = threading.Event()
    heartbeat = threading.Thread(
        target=_heartbeat_loop,
        args=(db_path, job["id"]),
        kwargs={
            "claimed_by": claimed_by,
            "lease_seconds": lease_seconds,
            "interval_seconds": interval,
            "stop_event": stop_event,
            "ownership_lost": ownership_lost,
        },
        daemon=True,
        name=f"pulse-heartbeat-{job['id']}",
    )
    heartbeat.start()

    outcome: dict = {}
    handler_error: BaseException | None = None
    try:
        if len(inspect.signature(handler).parameters) >= 2:
            outcome = handler(job, claimed_by) or {}
        else:
            outcome = handler(job) or {}
    except BaseException as exc:
        handler_error = exc
    finally:
        stop_event.set()
        heartbeat.join(timeout=max(1.0, interval + 1.0))

    if ownership_lost.is_set():
        LOG.error(
            "discarding terminal result from stale worker: job=%s worker=%s",
            job["id"],
            claimed_by,
        )
        return

    if handler_error is not None:
        failed = fail_from_exception(
            db_path,
            job["id"],
            worker_id=claimed_by,
            exc=handler_error,
        )
        if not failed:
            LOG.error(
                "handler failed after ownership was lost; terminal mutation suppressed: job=%s worker=%s",
                job["id"],
                claimed_by,
            )
        return

    try:
        status = str(outcome.get("status") or "completed")
        if status not in {"completed", "partial", "failed"}:
            raise ValueError(f"invalid terminal status returned by handler: {status!r}")
    except BaseException as exc:
        failed = fail_from_exception(
            db_path,
            job["id"],
            worker_id=claimed_by,
            exc=exc,
        )
        if not failed:
            LOG.error(
                "invalid handler result after ownership was lost; terminal mutation suppressed: job=%s worker=%s",
                job["id"],
                claimed_by,
            )
        return

    finished = finish_job(
        db_path,
        job["id"],
        worker_id=claimed_by,
        status=status,
        result_ref=outcome.get("result_ref") or {},
        error=outcome.get("error") or {},
    )
    if not finished:
        LOG.error(
            "finish_job rejected stale worker ownership: job=%s worker=%s",
            job["id"],
            claimed_by,
        )


def run_once(
    db_path: str | Path = DEFAULT_DB,
    *,
    claimed_by: str | None = None,
    lease_seconds: int = 120,
    heartbeat_interval_seconds: float | None = None,
    resolver: Callable[[str], Callable | None] = handler_for,
) -> bool:
    wid = claimed_by or worker_id()
    recover_abandoned_jobs(db_path)
    job = claim_next_job(db_path, worker_id=wid, lease_seconds=lease_seconds)
    if job is None:
        return False
    execute_claimed_job(
        db_path,
        job,
        claimed_by=wid,
        lease_seconds=lease_seconds,
        heartbeat_interval_seconds=heartbeat_interval_seconds,
        resolver=resolver,
    )
    return True


def run_forever(
    db_path: str | Path = DEFAULT_DB,
    *,
    poll_seconds: float = 1.0,
    lease_seconds: int = 120,
) -> None:
    validate_schema_current(db_path)
    wid = worker_id()
    while True:
        worked = run_once(db_path, claimed_by=wid, lease_seconds=lease_seconds)
        if not worked:
            time.sleep(max(0.1, float(poll_seconds)))


def main() -> int:
    parser = argparse.ArgumentParser(description="Pulse durable job worker")
    parser.add_argument("--db", default=os.environ.get("RESEARCH_DB", "/data/audit/research.db"))
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--poll-seconds", type=float, default=1.0)
    parser.add_argument("--lease-seconds", type=int, default=120)
    args = parser.parse_args()

    validate_schema_current(args.db)
    if args.once:
        run_once(args.db, lease_seconds=args.lease_seconds)
        return 0

    run_forever(args.db, poll_seconds=args.poll_seconds, lease_seconds=args.lease_seconds)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
