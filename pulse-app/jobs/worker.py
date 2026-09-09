from __future__ import annotations

import argparse
import os
import socket
import time
import uuid
from pathlib import Path
from typing import Callable

from db.migrate import validate_schema_current
from jobs.handlers import handler_for
from jobs.store import claim_next_job, fail_from_exception, finish_job, recover_abandoned_jobs

DEFAULT_DB = Path(os.environ.get("RESEARCH_DB", "/data/audit/research.db"))


def worker_id() -> str:
    return f"{socket.gethostname()}:{os.getpid()}:{uuid.uuid4().hex[:8]}"


def execute_claimed_job(
    db_path: str | Path,
    job: dict,
    *,
    claimed_by: str,
    resolver: Callable[[str], Callable | None] = handler_for,
) -> None:
    handler = resolver(str(job.get("job_type") or ""))
    if handler is None:
        finish_job(
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
        return

    try:
        import inspect
        if len(inspect.signature(handler).parameters) >= 2:
            outcome = handler(job, worker_id) or {}
        else:
            outcome = handler(job) or {}
        status = str(outcome.get("status") or "completed")
        if status not in {"completed", "partial", "failed"}:
            raise ValueError(f"invalid terminal status returned by handler: {status!r}")
        finish_job(
            db_path,
            job["id"],
            worker_id=claimed_by,
            status=status,
            result_ref=outcome.get("result_ref") or {},
            error=outcome.get("error") or {},
        )
    except BaseException as exc:
        fail_from_exception(
            db_path,
            job["id"],
            worker_id=claimed_by,
            exc=exc,
        )


def run_once(
    db_path: str | Path = DEFAULT_DB,
    *,
    claimed_by: str | None = None,
    lease_seconds: int = 120,
    resolver: Callable[[str], Callable | None] = handler_for,
) -> bool:
    wid = claimed_by or worker_id()
    recover_abandoned_jobs(db_path)
    job = claim_next_job(db_path, worker_id=wid, lease_seconds=lease_seconds)
    if job is None:
        return False
    execute_claimed_job(db_path, job, claimed_by=wid, resolver=resolver)
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
