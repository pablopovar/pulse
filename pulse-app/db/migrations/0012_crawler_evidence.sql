-- Immutable response evidence for new crawler observations.  Existing pages
-- remain untouched; this records the complete URL lifecycle going forward.
CREATE TABLE resource_outcome (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    crawl_run_id INTEGER,
    domain TEXT NOT NULL COLLATE NOCASE,
    requested_url TEXT NOT NULL,
    final_url TEXT NOT NULL DEFAULT '',
    http_status INTEGER,
    content_type TEXT NOT NULL DEFAULT '',
    resource_type TEXT NOT NULL DEFAULT 'unsupported',
    response_size INTEGER NOT NULL DEFAULT 0,
    response_sha256 TEXT NOT NULL DEFAULT '',
    response_headers_json TEXT NOT NULL DEFAULT '{}',
    response_body TEXT NOT NULL DEFAULT '',
    body_retained INTEGER NOT NULL DEFAULT 0 CHECK(body_retained IN (0,1)),
    etag TEXT NOT NULL DEFAULT '',
    last_modified TEXT NOT NULL DEFAULT '',
    redirect_chain_json TEXT NOT NULL DEFAULT '[]',
    discovered_at TEXT NOT NULL DEFAULT '',
    observed_at TEXT NOT NULL DEFAULT '',
    crawl_state TEXT NOT NULL DEFAULT 'discovered',
    audit_state TEXT NOT NULL DEFAULT '',
    failure_kind TEXT NOT NULL DEFAULT '',
    reason TEXT NOT NULL DEFAULT '',
    duplicate_or_canonical_target TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    UNIQUE(crawl_run_id, requested_url)
);
CREATE INDEX idx_resource_outcome_run ON resource_outcome(crawl_run_id, crawl_state);
CREATE INDEX idx_resource_outcome_domain ON resource_outcome(domain, observed_at DESC);

CREATE TABLE sitemap_source_evidence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    crawl_run_id INTEGER,
    domain TEXT NOT NULL COLLATE NOCASE,
    requested_url TEXT NOT NULL,
    source_type TEXT NOT NULL,
    discovery_origin TEXT NOT NULL DEFAULT '',
    parent_sitemap TEXT NOT NULL DEFAULT '',
    http_status INTEGER,
    content_type TEXT NOT NULL DEFAULT '',
    response_size INTEGER NOT NULL DEFAULT 0,
    response_sha256 TEXT NOT NULL DEFAULT '',
    observed_at TEXT NOT NULL,
    parse_status TEXT NOT NULL DEFAULT 'unavailable',
    parse_error TEXT NOT NULL DEFAULT '',
    child_sitemaps_json TEXT NOT NULL DEFAULT '[]',
    UNIQUE(crawl_run_id, requested_url)
);

CREATE TABLE llm_source_evidence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    crawl_run_id INTEGER,
    domain TEXT NOT NULL COLLATE NOCASE,
    source_key TEXT NOT NULL,
    url TEXT NOT NULL,
    availability TEXT NOT NULL,
    http_status INTEGER,
    content_type TEXT NOT NULL DEFAULT '',
    headers_json TEXT NOT NULL DEFAULT '{}',
    response_size INTEGER NOT NULL DEFAULT 0,
    response_sha256 TEXT NOT NULL DEFAULT '',
    observed_at TEXT NOT NULL,
    raw_content TEXT NOT NULL DEFAULT '',
    body_retained INTEGER NOT NULL DEFAULT 0 CHECK(body_retained IN (0,1)),
    parse_json TEXT NOT NULL DEFAULT '{}',
    parse_error TEXT NOT NULL DEFAULT '',
    reason TEXT NOT NULL DEFAULT '',
    UNIQUE(crawl_run_id, source_key)
);

CREATE TABLE durable_job_event (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    detail_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);
CREATE INDEX idx_durable_job_event_job ON durable_job_event(job_id, created_at);
