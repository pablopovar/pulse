CREATE TABLE IF NOT EXISTS ai_question_set (
    domain TEXT NOT NULL COLLATE NOCASE,
    version INTEGER NOT NULL,
    label TEXT NOT NULL DEFAULT '',
    approved INTEGER NOT NULL DEFAULT 0,
    comparison_set_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    approved_at TEXT,
    PRIMARY KEY(domain,version)
);

CREATE TABLE IF NOT EXISTS ai_question_definition (
    domain TEXT NOT NULL COLLATE NOCASE,
    question_set_version INTEGER NOT NULL,
    question_id TEXT NOT NULL,
    phase TEXT NOT NULL,
    position INTEGER NOT NULL,
    question_text TEXT NOT NULL,
    category_tag TEXT NOT NULL DEFAULT '',
    PRIMARY KEY(domain,question_set_version,question_id)
);

CREATE TABLE IF NOT EXISTS ai_visibility_observation (
    domain TEXT NOT NULL COLLATE NOCASE,
    report_id TEXT NOT NULL,
    question_set_version INTEGER NOT NULL,
    question_id TEXT NOT NULL,
    phase TEXT NOT NULL,
    provider TEXT NOT NULL,
    model TEXT NOT NULL DEFAULT '',
    search_mode TEXT NOT NULL,
    repeat_index INTEGER NOT NULL,
    provider_status TEXT NOT NULL,
    raw_answer TEXT NOT NULL DEFAULT '',
    citations_json TEXT NOT NULL DEFAULT '[]',
    atomic_claims_json TEXT NOT NULL DEFAULT '[]',
    observed_at TEXT NOT NULL,
    PRIMARY KEY(
        domain,report_id,question_set_version,question_id,
        provider,search_mode,repeat_index
    )
);

CREATE INDEX IF NOT EXISTS idx_aiobs_report
ON ai_visibility_observation(domain,report_id,question_set_version,question_id);

CREATE TABLE IF NOT EXISTS cross_model_provider_response (
    domain TEXT NOT NULL COLLATE NOCASE,
    report_id TEXT NOT NULL,
    question_id TEXT NOT NULL,
    family_id TEXT NOT NULL,
    template_question TEXT NOT NULL,
    rendered_question TEXT NOT NULL,
    provider TEXT NOT NULL,
    model TEXT NOT NULL DEFAULT '',
    raw_answer TEXT NOT NULL DEFAULT '',
    citations_json TEXT NOT NULL DEFAULT '[]',
    observed_at TEXT NOT NULL,
    country TEXT NOT NULL DEFAULT '',
    city TEXT NOT NULL DEFAULT '',
    answer_language TEXT NOT NULL DEFAULT '',
    live_search_status TEXT NOT NULL DEFAULT '',
    provider_status TEXT NOT NULL DEFAULT 'success',
    PRIMARY KEY(domain,report_id,question_id,provider)
);

CREATE TABLE IF NOT EXISTS cross_model_comparison (
    domain TEXT NOT NULL COLLATE NOCASE,
    report_id TEXT NOT NULL,
    question_id TEXT NOT NULL,
    family_id TEXT NOT NULL,
    rendered_question TEXT NOT NULL,
    valid_provider_count INTEGER NOT NULL DEFAULT 0,
    concept_consistency REAL,
    concept_consistency_pct REAL,
    company_source_numerator INTEGER NOT NULL DEFAULT 0,
    company_source_denominator INTEGER NOT NULL DEFAULT 0,
    company_source_pct REAL,
    direct_contradiction INTEGER NOT NULL DEFAULT 0,
    direct_contradiction_count INTEGER NOT NULL DEFAULT 0,
    judge_provider TEXT NOT NULL DEFAULT '',
    judge_model TEXT NOT NULL DEFAULT '',
    judge_prompt_version TEXT NOT NULL DEFAULT '',
    judged_at TEXT,
    raw_judge_json TEXT NOT NULL DEFAULT '',
    derived_json TEXT NOT NULL DEFAULT '{}',
    judge_status TEXT NOT NULL DEFAULT 'not_run',
    judge_error TEXT NOT NULL DEFAULT '',
    PRIMARY KEY(domain,report_id,question_id)
);

CREATE TABLE IF NOT EXISTS domain_company_controlled_domain (
    domain TEXT NOT NULL COLLATE NOCASE,
    controlled_domain TEXT NOT NULL COLLATE NOCASE,
    created_at TEXT NOT NULL,
    PRIMARY KEY(domain,controlled_domain)
);

CREATE INDEX IF NOT EXISTS idx_xm_response_report
ON cross_model_provider_response(domain,report_id,question_id);

CREATE INDEX IF NOT EXISTS idx_xm_comparison_report
ON cross_model_comparison(domain,report_id,question_id);
