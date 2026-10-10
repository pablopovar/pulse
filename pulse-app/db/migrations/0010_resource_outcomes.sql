ALTER TABLE crawl_page ADD COLUMN resource_type TEXT NOT NULL DEFAULT 'html';
ALTER TABLE crawl_page ADD COLUMN response_sha256 TEXT NOT NULL DEFAULT '';
ALTER TABLE crawl_page ADD COLUMN audit_status TEXT NOT NULL DEFAULT 'audited';
ALTER TABLE crawl_page ADD COLUMN observed_at TEXT;
