from __future__ import annotations

from datetime import datetime, timedelta, timezone

from db.migrate import migrate_up
from jobs.store import (
    cancel_queued_job,
    claim_next_job,
    enqueue_job,
    finish_job,
    get_job,
    recover_abandoned_jobs,
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
