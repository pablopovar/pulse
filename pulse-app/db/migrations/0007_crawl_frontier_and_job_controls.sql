-- Durable jobs need explicit pause/cancel states and delayed availability for
-- polite background crawl batches. SQLite cannot alter a CHECK constraint, so
-- rebuild the table while preserving every existing row.
CREATE TABLE durable_job_v2 (
    id TEXT PRIMARY KEY,
    domain TEXT NOT NULL DEFAULT '',
    job_type TEXT NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN ('queued','running','paused','completed','partial','failed','cancelled')
    ),
    payload_json TEXT NOT NULL DEFAULT '{}',
    result_ref_json TEXT NOT NULL DEFAULT '{}',
    error_json TEXT NOT NULL DEFAULT '{}',
    attempts INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 3 CHECK (max_attempts >= 1),
    queued_at TEXT NOT NULL,
    available_at TEXT NOT NULL,
    started_at TEXT,
    heartbeat_at TEXT,
    lease_expires_at TEXT,
    completed_at TEXT,
    cancelled_at TEXT,
    paused_at TEXT,
    worker_id TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    stage TEXT NOT NULL DEFAULT 'queued',
    publication_status TEXT NOT NULL DEFAULT 'not_applicable'
);

INSERT INTO durable_job_v2(
    id,domain,job_type,status,payload_json,result_ref_json,error_json,
    attempts,max_attempts,queued_at,available_at,started_at,heartbeat_at,
    lease_expires_at,completed_at,cancelled_at,paused_at,worker_id,
    created_at,updated_at,stage,publication_status
)
SELECT
    id,domain,job_type,status,payload_json,result_ref_json,error_json,
    attempts,max_attempts,queued_at,queued_at,started_at,heartbeat_at,
    lease_expires_at,completed_at,cancelled_at,NULL,worker_id,
    created_at,updated_at,stage,publication_status
FROM durable_job;

DROP TABLE durable_job;
ALTER TABLE durable_job_v2 RENAME TO durable_job;

CREATE INDEX idx_durable_job_claim
ON durable_job(status, available_at, queued_at, created_at);
CREATE INDEX idx_durable_job_domain
ON durable_job(domain, created_at DESC);
CREATE INDEX idx_durable_job_lease
ON durable_job(status, lease_expires_at);

ALTER TABLE crawl_run ADD COLUMN crawl_mode TEXT NOT NULL DEFAULT 'initial';
ALTER TABLE crawl_run ADD COLUMN batch_number INTEGER NOT NULL DEFAULT 1;
ALTER TABLE crawl_run ADD COLUMN pages_eligible INTEGER NOT NULL DEFAULT 0;
ALTER TABLE crawl_run ADD COLUMN pages_skipped INTEGER NOT NULL DEFAULT 0;
ALTER TABLE crawl_run ADD COLUMN pages_unchanged INTEGER NOT NULL DEFAULT 0;
ALTER TABLE crawl_run ADD COLUMN pages_remaining INTEGER NOT NULL DEFAULT 0;
ALTER TABLE crawl_run ADD COLUMN current_url TEXT NOT NULL DEFAULT '';
ALTER TABLE crawl_run ADD COLUMN configuration_json TEXT NOT NULL DEFAULT '{}';
ALTER TABLE crawl_run ADD COLUMN status_reason TEXT NOT NULL DEFAULT '';
ALTER TABLE crawl_run ADD COLUMN cooldown_until TEXT;
ALTER TABLE crawl_run ADD COLUMN paused_at TEXT;
ALTER TABLE crawl_run ADD COLUMN cancelled_at TEXT;

ALTER TABLE crawl_page ADD COLUMN response_etag TEXT NOT NULL DEFAULT '';
ALTER TABLE crawl_page ADD COLUMN response_last_modified TEXT NOT NULL DEFAULT '';
ALTER TABLE crawl_page ADD COLUMN content_fingerprint TEXT NOT NULL DEFAULT '';
ALTER TABLE crawl_page ADD COLUMN content_simhash TEXT NOT NULL DEFAULT '';
ALTER TABLE crawl_page ADD COLUMN unchanged INTEGER NOT NULL DEFAULT 0;
ALTER TABLE crawl_page ADD COLUMN duplicate_of_url TEXT NOT NULL DEFAULT '';
ALTER TABLE crawl_page ADD COLUMN failure_kind TEXT NOT NULL DEFAULT '';
ALTER TABLE crawl_page ADD COLUMN redirect_chain_json TEXT NOT NULL DEFAULT '[]';

CREATE TABLE domain_crawl_policy (
    domain TEXT PRIMARY KEY COLLATE NOCASE,
    initial_target INTEGER NOT NULL DEFAULT 15 CHECK(initial_target BETWEEN 1 AND 100),
    max_urls_per_batch INTEGER NOT NULL DEFAULT 10 CHECK(max_urls_per_batch BETWEEN 1 AND 500),
    delay_ms INTEGER NOT NULL DEFAULT 2000 CHECK(delay_ms BETWEEN 0 AND 60000),
    batch_cooldown_seconds INTEGER NOT NULL DEFAULT 21600 CHECK(batch_cooldown_seconds >= 0),
    daily_page_budget INTEGER NOT NULL DEFAULT 40 CHECK(daily_page_budget >= 0),
    weekly_page_budget INTEGER NOT NULL DEFAULT 200 CHECK(weekly_page_budget >= 0),
    max_consecutive_failures INTEGER NOT NULL DEFAULT 3 CHECK(max_consecutive_failures >= 1),
    max_retry_count INTEGER NOT NULL DEFAULT 3 CHECK(max_retry_count >= 0),
    max_crawl_depth INTEGER NOT NULL DEFAULT 5 CHECK(max_crawl_depth >= 0),
    allowed_patterns_json TEXT NOT NULL DEFAULT '[]',
    excluded_patterns_json TEXT NOT NULL DEFAULT '[]',
    included_sitemaps_json TEXT NOT NULL DEFAULT '[]',
    background_enabled INTEGER NOT NULL DEFAULT 1 CHECK(background_enabled IN (0,1)),
    updated_at TEXT NOT NULL
);

CREATE TABLE crawl_url_inventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    domain TEXT NOT NULL COLLATE NOCASE,
    url TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'unknown',
    source_sitemap TEXT NOT NULL DEFAULT '',
    classification TEXT NOT NULL DEFAULT 'unknown',
    eligibility TEXT NOT NULL DEFAULT 'deferred' CHECK(
        eligibility IN ('eligible','deferred','excluded','duplicate')
    ),
    decision_reason TEXT NOT NULL DEFAULT '',
    priority_score INTEGER NOT NULL DEFAULT 0,
    sitemap_lastmod TEXT NOT NULL DEFAULT '',
    sitemap_priority REAL,
    crawl_depth INTEGER NOT NULL DEFAULT 0,
    operator_selected INTEGER NOT NULL DEFAULT 0 CHECK(operator_selected IN (0,1)),
    final_url TEXT NOT NULL DEFAULT '',
    canonical_url TEXT NOT NULL DEFAULT '',
    duplicate_of_url TEXT NOT NULL DEFAULT '',
    http_status INTEGER,
    noindex INTEGER NOT NULL DEFAULT 0 CHECK(noindex IN (0,1)),
    etag TEXT NOT NULL DEFAULT '',
    last_modified TEXT NOT NULL DEFAULT '',
    content_fingerprint TEXT NOT NULL DEFAULT '',
    content_simhash TEXT NOT NULL DEFAULT '',
    last_crawled_at TEXT,
    next_crawl_at TEXT,
    retry_count INTEGER NOT NULL DEFAULT 0,
    consecutive_failures INTEGER NOT NULL DEFAULT 0,
    last_error TEXT NOT NULL DEFAULT '',
    discovered_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(domain,url)
);

CREATE INDEX idx_crawl_inventory_domain_decision
ON crawl_url_inventory(domain,eligibility,classification,priority_score DESC);
CREATE INDEX idx_crawl_inventory_due
ON crawl_url_inventory(domain,next_crawl_at,last_crawled_at);
CREATE INDEX idx_crawl_inventory_fingerprint
ON crawl_url_inventory(domain,content_fingerprint);

CREATE TABLE crawl_frontier (
    crawl_run_id INTEGER NOT NULL,
    url_inventory_id INTEGER NOT NULL,
    state TEXT NOT NULL DEFAULT 'queued' CHECK(
        state IN ('queued','fetching','completed','unchanged','failed','skipped','cancelled')
    ),
    reason TEXT NOT NULL DEFAULT '',
    priority_score INTEGER NOT NULL DEFAULT 0,
    attempts INTEGER NOT NULL DEFAULT 0,
    queued_at TEXT NOT NULL,
    started_at TEXT,
    completed_at TEXT,
    updated_at TEXT NOT NULL,
    PRIMARY KEY(crawl_run_id,url_inventory_id),
    FOREIGN KEY(crawl_run_id) REFERENCES crawl_run(id) ON DELETE CASCADE,
    FOREIGN KEY(url_inventory_id) REFERENCES crawl_url_inventory(id) ON DELETE CASCADE
);

CREATE INDEX idx_crawl_frontier_next
ON crawl_frontier(crawl_run_id,state,priority_score DESC,queued_at);

CREATE TABLE crawl_event (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    crawl_run_id INTEGER,
    domain TEXT NOT NULL COLLATE NOCASE,
    event_type TEXT NOT NULL,
    detail_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    FOREIGN KEY(crawl_run_id) REFERENCES crawl_run(id) ON DELETE CASCADE
);

CREATE INDEX idx_crawl_event_run
ON crawl_event(crawl_run_id,created_at);

CREATE TABLE operational_audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    domain TEXT NOT NULL COLLATE NOCASE,
    action TEXT NOT NULL,
    detail_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);
