CREATE TABLE domain_discovery_state (
    domain TEXT PRIMARY KEY COLLATE NOCASE,
    status TEXT NOT NULL DEFAULT 'not_started' CHECK(status IN ('not_started','queued','running','ready','failed')),
    job_id TEXT NOT NULL DEFAULT '',
    sitemap_source TEXT NOT NULL DEFAULT '',
    sitemap_count INTEGER NOT NULL DEFAULT 0,
    ranking_count INTEGER NOT NULL DEFAULT 0,
    last_successful_at TEXT,
    error TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX idx_domain_discovery_status
ON domain_discovery_state(status, updated_at);
