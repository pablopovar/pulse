from __future__ import annotations

import threading
import time
from datetime import datetime, timedelta, timezone

from db.migrate import migrate_up
from jobs.store import (
    cancel_job,
    cancel_queued_job,
    claim_next_job,
    enqueue_job,
    finish_job,
    get_job,
    heartbeat_job,
    pause_job,
    recover_abandoned_jobs,
    resume_job,
    worker_owns_job,
)
from jobs.worker import run_once


def migrated_db(tmp_path):
    db = tmp_path / "jobs.db"
    migrate_up(db)
    return db


def test_job_survives_reopen(tmp_path):
    db = migrated_db(tmp_path)
    created = enqueue_job(db, "worker.healthcheck", domain="example.com", payload={"x": 1})
    reopened = get_job(db, created["id"])
    assert reopened["status"] == "queued"
    assert reopened["payload"] == {"x": 1}
    assert reopened["domain"] == "example.com"


def test_claim_is_persistent_and_exclusive(tmp_path):
    db = migrated_db(tmp_path)
    created = enqueue_job(db, "worker.healthcheck")
    claimed = claim_next_job(db, worker_id="worker-a", lease_seconds=60)
    assert claimed["id"] == created["id"]
    assert claimed["status"] == "running"
    assert claimed["attempts"] == 1
    assert claimed["worker_id"] == "worker-a"
    assert claim_next_job(db, worker_id="worker-b", lease_seconds=60) is None


def test_separate_worker_executes_queued_job(tmp_path):
    db = migrated_db(tmp_path)
    created = enqueue_job(db, "worker.healthcheck", payload={"hello": "world"})
    assert run_once(db, claimed_by="worker-a") is True
    job = get_job(db, created["id"])
    assert job["status"] == "completed"
    assert job["result_ref"] == {"kind": "worker_healthcheck", "echo": {"hello": "world"}}


def test_failed_job_retains_structured_error(tmp_path):
    db = migrated_db(tmp_path)
    created = enqueue_job(db, "test.explode")

    def explode(_job):
        raise RuntimeError("deliberate failure")

    def resolver(job_type):
        return explode if job_type == "test.explode" else None

    assert run_once(db, claimed_by="worker-a", resolver=resolver) is True
    job = get_job(db, created["id"])
    assert job["status"] == "failed"
    assert job["error"]["kind"] == "RuntimeError"
    assert job["error"]["message"] == "deliberate failure"
    assert job["error"]["stage"] == "execute"
    assert job["completed_at"]


def test_unknown_job_type_fails_with_dispatch_error(tmp_path):
    db = migrated_db(tmp_path)
    created = enqueue_job(db, "unknown.type")
    assert run_once(db, claimed_by="worker-a") is True
    job = get_job(db, created["id"])
    assert job["status"] == "failed"
    assert job["error"]["kind"] == "unknown_job_type"
    assert job["error"]["stage"] == "dispatch"


def test_abandoned_running_job_requeues_when_attempts_remain(tmp_path):
    db = migrated_db(tmp_path)
    created = enqueue_job(db, "worker.healthcheck", max_attempts=3)
    past = datetime.now(timezone.utc) - timedelta(minutes=10)
    claim_next_job(db, worker_id="dead-worker", lease_seconds=10, at=past)
    assert recover_abandoned_jobs(db) == {"requeued": 1, "failed": 0}
    job = get_job(db, created["id"])
    assert job["status"] == "queued"
    assert job["attempts"] == 1
    assert job["error"]["kind"] == "abandoned_job"


def test_abandoned_running_job_fails_when_attempts_exhausted(tmp_path):
    db = migrated_db(tmp_path)
    created = enqueue_job(db, "worker.healthcheck", max_attempts=1)
    past = datetime.now(timezone.utc) - timedelta(minutes=10)
    claim_next_job(db, worker_id="dead-worker", lease_seconds=10, at=past)
    assert recover_abandoned_jobs(db) == {"requeued": 0, "failed": 1}
    job = get_job(db, created["id"])
    assert job["status"] == "failed"
    assert job["error"]["kind"] == "abandoned_job"
    assert job["completed_at"]


def test_partial_terminal_state_is_supported(tmp_path):
    db = migrated_db(tmp_path)
    created = enqueue_job(db, "test.partial")
    claim_next_job(db, worker_id="worker-a")
    assert finish_job(
        db,
        created["id"],
        worker_id="worker-a",
        status="partial",
        result_ref={"completed_items": 4, "failed_items": 1},
        error={"kind": "partial_completion", "message": "One item failed."},
    )
    job = get_job(db, created["id"])
    assert job["status"] == "partial"
    assert job["result_ref"]["completed_items"] == 4
    assert job["error"]["kind"] == "partial_completion"


def test_queued_job_can_be_cancelled(tmp_path):
    db = migrated_db(tmp_path)
    created = enqueue_job(db, "worker.healthcheck")
    assert cancel_queued_job(db, created["id"])
    job = get_job(db, created["id"])
    assert job["status"] == "cancelled"
    assert job["cancelled_at"]


def test_running_job_cancellation_is_persistent_and_not_reclaimed(tmp_path):
    db = migrated_db(tmp_path)
    created = enqueue_job(db, "worker.healthcheck")
    claimed = claim_next_job(db, worker_id="worker-a", lease_seconds=60)
    assert claimed and claimed["id"] == created["id"]
    assert cancel_job(db, created["id"])
    cancelled = get_job(db, created["id"])
    assert cancelled["status"] == "cancelled"
    assert cancelled["worker_id"] == ""
    assert cancelled["lease_expires_at"] is None
    assert recover_abandoned_jobs(db) == {"requeued": 0, "failed": 0}
    assert claim_next_job(db, worker_id="worker-b") is None


def test_pause_and_resume_survive_job_reopen(tmp_path):
    db = migrated_db(tmp_path)
    created = enqueue_job(db, "worker.healthcheck")
    claim_next_job(db, worker_id="worker-a")
    assert pause_job(db, created["id"])
    assert get_job(db, created["id"])["status"] == "paused"
    assert claim_next_job(db, worker_id="worker-b") is None
    assert resume_job(db, created["id"])
    replacement = claim_next_job(db, worker_id="worker-b")
    assert replacement and replacement["id"] == created["id"]


def test_delayed_background_job_is_not_claimed_early(tmp_path):
    db = migrated_db(tmp_path)
    future = datetime.now(timezone.utc) + timedelta(hours=1)
    created = enqueue_job(
        db,
        "background_crawl",
        domain="example.com",
        available_at=future.isoformat(timespec="seconds"),
    )
    assert claim_next_job(db, worker_id="worker-a") is None
    claimed = claim_next_job(db, worker_id="worker-a", at=future + timedelta(seconds=1))
    assert claimed and claimed["id"] == created["id"]


def test_heartbeat_renews_current_worker_lease(tmp_path):
    db = migrated_db(tmp_path)
    created = enqueue_job(db, "worker.healthcheck")
    claimed = claim_next_job(db, worker_id="worker-a", lease_seconds=2)
    first_expiry = claimed["lease_expires_at"]
    time.sleep(1.05)
    assert heartbeat_job(db, created["id"], worker_id="worker-a", lease_seconds=2)
    renewed = get_job(db, created["id"])
    assert renewed["lease_expires_at"] > first_expiry
    assert worker_owns_job(db, created["id"], worker_id="worker-a")


def test_long_running_job_is_not_reclaimed_while_heartbeating(tmp_path):
    db = migrated_db(tmp_path)
    created = enqueue_job(db, "test.slow")

    def slow(_job):
        time.sleep(1.5)
        return {"status": "completed", "result_ref": {"ok": True}}

    def resolver(job_type):
        return slow if job_type == "test.slow" else None

    runner = threading.Thread(
        target=run_once,
        kwargs={
            "db_path": db,
            "claimed_by": "worker-a",
            "lease_seconds": 1,
            "heartbeat_interval_seconds": 0.2,
            "resolver": resolver,
        },
    )
    runner.start()
    time.sleep(1.15)
    assert recover_abandoned_jobs(db) == {"requeued": 0, "failed": 0}
    assert claim_next_job(db, worker_id="worker-b", lease_seconds=1) is None
    runner.join(timeout=3)
    assert not runner.is_alive()
    job = get_job(db, created["id"])
    assert job["status"] == "completed"
    assert job["result_ref"] == {"ok": True}


def test_crashed_worker_job_is_recoverable_after_lease_expiry(tmp_path):
    db = migrated_db(tmp_path)
    created = enqueue_job(db, "worker.healthcheck", max_attempts=3)
    past = datetime.now(timezone.utc) - timedelta(seconds=5)
    claim_next_job(db, worker_id="crashed-worker", lease_seconds=1, at=past)
    assert recover_abandoned_jobs(db) == {"requeued": 1, "failed": 0}
    recovered = claim_next_job(db, worker_id="worker-b", lease_seconds=30)
    assert recovered["id"] == created["id"]
    assert recovered["worker_id"] == "worker-b"


def test_stale_worker_cannot_heartbeat_or_finish_after_recovery(tmp_path):
    db = migrated_db(tmp_path)
    created = enqueue_job(db, "worker.healthcheck", max_attempts=3)
    past = datetime.now(timezone.utc) - timedelta(seconds=5)
    claim_next_job(db, worker_id="worker-a", lease_seconds=1, at=past)
    assert recover_abandoned_jobs(db) == {"requeued": 1, "failed": 0}
    replacement = claim_next_job(db, worker_id="worker-b", lease_seconds=30)
    assert replacement["id"] == created["id"]

    assert not heartbeat_job(db, created["id"], worker_id="worker-a", lease_seconds=30)
    assert not finish_job(db, created["id"], worker_id="worker-a", status="completed")
    current = get_job(db, created["id"])
    assert current["status"] == "running"
    assert current["worker_id"] == "worker-b"
