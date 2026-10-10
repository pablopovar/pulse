ALTER TABLE crawl_page ADD COLUMN page_type TEXT NOT NULL DEFAULT 'unknown';
ALTER TABLE crawl_page ADD COLUMN page_type_confidence TEXT NOT NULL DEFAULT 'low';
