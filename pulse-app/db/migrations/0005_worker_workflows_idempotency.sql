ALTER TABLE durable_job ADD COLUMN stage TEXT NOT NULL DEFAULT 'queued';
ALTER TABLE durable_job ADD COLUMN publication_status TEXT NOT NULL DEFAULT 'not_applicable';

ALTER TABLE crawl_run ADD COLUMN execution_run_id TEXT;
CREATE UNIQUE INDEX idx_crawl_run_execution_run_id ON crawl_run(execution_run_id) WHERE execution_run_id IS NOT NULL;

ALTER TABLE audit_run ADD COLUMN execution_run_id TEXT;
CREATE UNIQUE INDEX idx_audit_run_execution_run_id ON audit_run(execution_run_id) WHERE execution_run_id IS NOT NULL;

ALTER TABLE report_session ADD COLUMN execution_run_id TEXT;
CREATE UNIQUE INDEX idx_report_session_execution_run_id ON report_session(execution_run_id) WHERE execution_run_id IS NOT NULL;

CREATE TABLE manual_ai_analysis_run (
  run_id TEXT PRIMARY KEY,
  domain TEXT NOT NULL COLLATE NOCASE,
  status TEXT NOT NULL CHECK(status IN ('queued','running','completed','partial','failed','cancelled')),
  provider TEXT NOT NULL DEFAULT '',
  model TEXT NOT NULL DEFAULT '',
  parameters_json TEXT NOT NULL DEFAULT '{}',
  source_snapshot_json TEXT NOT NULL DEFAULT '{}',
  analysis_text TEXT NOT NULL DEFAULT '',
  error_json TEXT NOT NULL DEFAULT '{}',
  started_at TEXT,
  completed_at TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX idx_manual_ai_analysis_run_domain ON manual_ai_analysis_run(domain,created_at DESC);
