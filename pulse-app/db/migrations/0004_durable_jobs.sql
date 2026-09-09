CREATE TABLE durable_job (
    id TEXT PRIMARY KEY,
    domain TEXT NOT NULL DEFAULT '',
    job_type TEXT NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN ('queued','running','completed','partial','failed','cancelled')
    ),
    payload_json TEXT NOT NULL DEFAULT '{}',
    result_ref_json TEXT NOT NULL DEFAULT '{}',
    error_json TEXT NOT NULL DEFAULT '{}',
    attempts INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 3 CHECK (max_attempts >= 1),
    queued_at TEXT NOT NULL,
    started_at TEXT,
    heartbeat_at TEXT,
    lease_expires_at TEXT,
    completed_at TEXT,
    cancelled_at TEXT,
    worker_id TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX idx_durable_job_claim
ON durable_job(status, queued_at, created_at);

CREATE INDEX idx_durable_job_domain
ON durable_job(domain, created_at DESC);

CREATE INDEX idx_durable_job_lease
ON durable_job(status, lease_expires_at);
