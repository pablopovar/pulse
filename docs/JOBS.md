# Durable jobs

Pulse uses the Pulse-owned SQLite `RESEARCH_DB` as its durable job queue. Redis
is not required for the current workload.

## States

A job is always in one of:

- `queued`
- `running`
- `completed`
- `partial`
- `failed`
- `cancelled`

Each job stores its type, domain, JSON payload, result references, structured
error information, attempt count, maximum attempts, worker identity, queue/start/
heartbeat/lease/completion/cancellation timestamps, and created/updated times.

## Claiming and recovery

Workers claim jobs with a short `BEGIN IMMEDIATE` transaction. External work is
never executed while the SQLite write transaction is held.

A running job has a lease. Before claiming new work, the worker recovers expired
leases:

- if attempts remain, the job is safely returned to `queued`;
- if attempts are exhausted, it becomes `failed` with an `abandoned_job` error.

This means a Flask restart or worker crash does not erase queued/running state.

## Worker process

`docker-compose.yml` defines `audit-worker`, which runs:

```text
python -m jobs.worker
```

The worker has no HTTP port. It shares the Pulse database volume with
`audit-app` and reads OpenGSC storage read-only.

## Query surface

The authenticated management API exposes:

- `GET /api/jobs`
- `GET /api/jobs/<job_id>`
- `POST /api/jobs/<job_id>/cancel` for queued jobs

Running-job cancellation is intentionally deferred until workflow migration can
make cancellation cooperative. Marking an actively executing job cancelled
without stopping the underlying work would be unsafe.

## Scope boundary

This item creates the durable queue, claiming, recovery, status/query surface,
and separate worker process. Existing crawl/audit/manual-AI thread dispatch is
migrated to this queue in the next worker-migration/idempotency item.
