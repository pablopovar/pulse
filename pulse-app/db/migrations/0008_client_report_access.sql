CREATE TABLE domain_public_report_access (
    domain TEXT PRIMARY KEY COLLATE NOCASE,
    password_hash TEXT NOT NULL DEFAULT '',
    enabled INTEGER NOT NULL DEFAULT 0 CHECK(enabled IN (0,1)),
    updated_at TEXT NOT NULL
);

CREATE INDEX idx_domain_public_report_access_enabled
ON domain_public_report_access(enabled);
