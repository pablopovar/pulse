-- Pulse research database baseline.
-- Generated from the current pre-migration production/development schema.
-- Schema changes after this point must be new numbered migrations.
PRAGMA foreign_keys=ON;

-- table: audit_domain_summary
CREATE TABLE IF NOT EXISTS audit_domain_summary (
            audit_run_id INTEGER PRIMARY KEY,
            domain TEXT NOT NULL,
            pages_audited INTEGER NOT NULL DEFAULT 0,
            geo_score INTEGER,
            aeo_score INTEGER,
            combined_score INTEGER,
            fail_count INTEGER NOT NULL DEFAULT 0,
            partial_count INTEGER NOT NULL DEFAULT 0,
            pass_count INTEGER NOT NULL DEFAULT 0,
            unknown_count INTEGER NOT NULL DEFAULT 0,
            manual_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        );

-- table: audit_page
CREATE TABLE IF NOT EXISTS audit_page (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            audit_run_id INTEGER NOT NULL,
            page_id INTEGER NOT NULL,
            url TEXT NOT NULL,
            page_type TEXT,
            geo_score INTEGER,
            aeo_score INTEGER,
            combined_score INTEGER,
            geo_json TEXT NOT NULL DEFAULT '{}',
            aeo_json TEXT NOT NULL DEFAULT '{}',
            combined_json TEXT NOT NULL DEFAULT '{}',
            capture_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            UNIQUE(audit_run_id, page_id)
        );

-- table: audit_run
CREATE TABLE IF NOT EXISTS audit_run (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            domain TEXT NOT NULL,
            scope TEXT NOT NULL,
            status TEXT NOT NULL,
            started_at TEXT NOT NULL,
            completed_at TEXT,
            error TEXT
        );

-- table: audit_signal
CREATE TABLE IF NOT EXISTS audit_signal (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            audit_page_id INTEGER NOT NULL,
            family TEXT NOT NULL,
            signal_key TEXT NOT NULL,
            category TEXT NOT NULL,
            title TEXT NOT NULL,
            observed_status TEXT NOT NULL,
            severity TEXT NOT NULL,
            weight REAL NOT NULL DEFAULT 0,
            evidence TEXT NOT NULL,
            recommendation TEXT NOT NULL,
            source_title TEXT,
            source_url TEXT,
            UNIQUE(audit_page_id, family, signal_key)
        );

-- table: audit_signal_state
CREATE TABLE IF NOT EXISTS audit_signal_state (
            domain TEXT NOT NULL,
            page_id INTEGER NOT NULL,
            family TEXT NOT NULL,
            signal_key TEXT NOT NULL,
            workflow_status TEXT NOT NULL DEFAULT 'open',
            priority TEXT NOT NULL DEFAULT '',
            user_note TEXT NOT NULL DEFAULT '',
            override_status TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL,
            PRIMARY KEY(domain, page_id, family, signal_key)
        );

-- table: client_report_config
CREATE TABLE IF NOT EXISTS client_report_config (
            domain TEXT PRIMARY KEY COLLATE NOCASE,
            competitors_json TEXT NOT NULL DEFAULT '[]',
            priority_pages_json TEXT NOT NULL DEFAULT '[]',
            target_topics_json TEXT NOT NULL DEFAULT '[]',
            page_groups_json TEXT NOT NULL DEFAULT '[]',
            integrations_json TEXT NOT NULL DEFAULT '[]',
            monitored_ai_prompts_json TEXT NOT NULL DEFAULT '[]',
            updated_at TEXT NOT NULL DEFAULT ''
        );

-- table: crawl_issue
CREATE TABLE IF NOT EXISTS crawl_issue (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        crawl_run_id INTEGER NOT NULL,
        page_url TEXT,
        issue_key TEXT NOT NULL,
        severity TEXT NOT NULL,
        title TEXT NOT NULL,
        detail TEXT,
        UNIQUE(crawl_run_id, page_url, issue_key, detail)
    );

-- table: crawl_link
CREATE TABLE IF NOT EXISTS crawl_link (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        crawl_run_id INTEGER NOT NULL,
        source_url TEXT NOT NULL,
        target_url TEXT NOT NULL,
        internal INTEGER NOT NULL,
        rel TEXT,
        UNIQUE(crawl_run_id, source_url, target_url, rel)
    );

-- table: crawl_page
CREATE TABLE IF NOT EXISTS crawl_page (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        crawl_run_id INTEGER NOT NULL,
        url TEXT NOT NULL,
        final_url TEXT,
        path TEXT,
        status_code INTEGER,
        content_type TEXT,
        content_bytes INTEGER,
        response_ms INTEGER,
        title TEXT,
        description TEXT,
        canonical TEXT,
        robots_meta TEXT,
        lang TEXT,
        viewport TEXT,
        h1_json TEXT,
        h2_json TEXT,
        word_count INTEGER,
        internal_links INTEGER NOT NULL DEFAULT 0,
        external_links INTEGER NOT NULL DEFAULT 0,
        image_count INTEGER NOT NULL DEFAULT 0,
        images_missing_alt INTEGER NOT NULL DEFAULT 0,
        schema_types_json TEXT,
        hreflang_json TEXT,
        og_title TEXT,
        og_description TEXT,
        og_image TEXT,
        indexable INTEGER,
        robots_allowed INTEGER,
        error TEXT,
        created_at TEXT NOT NULL,
        UNIQUE(crawl_run_id, url)
    );

-- table: crawl_run
CREATE TABLE IF NOT EXISTS crawl_run (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        domain TEXT NOT NULL,
        base_url TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'queued',
        page_cap INTEGER NOT NULL,
        delay_ms INTEGER NOT NULL,
        obey_robots INTEGER NOT NULL DEFAULT 1,
        report_scope TEXT NOT NULL DEFAULT 'full',
        selected_urls_json TEXT,
        started_at TEXT,
        completed_at TEXT,
        pages_discovered INTEGER NOT NULL DEFAULT 0,
        pages_crawled INTEGER NOT NULL DEFAULT 0,
        pages_failed INTEGER NOT NULL DEFAULT 0,
        robots_url TEXT,
        error TEXT
    );

-- table: dashboard_domain
CREATE TABLE IF NOT EXISTS dashboard_domain (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            domain TEXT NOT NULL COLLATE NOCASE UNIQUE,
            base_url TEXT NOT NULL,
            gsc_site_id TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

-- table: dataforseo_snapshot
CREATE TABLE IF NOT EXISTS dataforseo_snapshot(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      domain TEXT NOT NULL COLLATE NOCASE,
      report_run_id INTEGER,
      endpoint TEXT NOT NULL,
      payload_json TEXT NOT NULL,
      created_at TEXT NOT NULL
    );

-- table: domain_company_settings
CREATE TABLE IF NOT EXISTS domain_company_settings (domain TEXT PRIMARY KEY COLLATE NOCASE,company_name TEXT NOT NULL DEFAULT '',updated_at TEXT NOT NULL);

-- table: domain_report
CREATE TABLE IF NOT EXISTS domain_report (
            domain TEXT PRIMARY KEY COLLATE NOCASE,
            baseline_report_id TEXT NOT NULL,
            current_report_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

-- table: domain_source
CREATE TABLE IF NOT EXISTS domain_source (domain TEXT NOT NULL COLLATE NOCASE,source_key TEXT NOT NULL,source_name TEXT NOT NULL,selected INTEGER NOT NULL DEFAULT 0,connection_status TEXT NOT NULL DEFAULT 'not_connected',detail TEXT NOT NULL DEFAULT '',updated_at TEXT NOT NULL,PRIMARY KEY(domain,source_key));

-- table: domain_suppression
CREATE TABLE IF NOT EXISTS domain_suppression (
                domain TEXT PRIMARY KEY COLLATE NOCASE,
                suppressed_at TEXT NOT NULL
            );

-- table: extension_global
CREATE TABLE IF NOT EXISTS extension_global(
      extension_key TEXT PRIMARY KEY,
      kill_switch INTEGER NOT NULL DEFAULT 0,
      updated_at TEXT NOT NULL
    );

-- table: extension_project
CREATE TABLE IF NOT EXISTS extension_project(
      domain TEXT NOT NULL COLLATE NOCASE,
      extension_key TEXT NOT NULL,
      enabled INTEGER NOT NULL DEFAULT 0,
      max_items_per_run INTEGER NOT NULL DEFAULT 10,
      max_calls_per_run INTEGER NOT NULL DEFAULT 2,
      enabled_features_json TEXT NOT NULL DEFAULT '[]',
      updated_at TEXT NOT NULL,
      PRIMARY KEY(domain,extension_key)
    );

-- table: extension_usage
CREATE TABLE IF NOT EXISTS extension_usage(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      domain TEXT NOT NULL COLLATE NOCASE,
      extension_key TEXT NOT NULL,
      run_kind TEXT NOT NULL,
      endpoint TEXT NOT NULL,
      requested_items INTEGER NOT NULL DEFAULT 0,
      returned_items INTEGER NOT NULL DEFAULT 0,
      api_cost REAL,
      status TEXT NOT NULL,
      created_at TEXT NOT NULL
    );

-- table: keyword_note
CREATE TABLE IF NOT EXISTS keyword_note (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            domain TEXT NOT NULL,
            keyword TEXT NOT NULL COLLATE NOCASE,
            content TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL,
            UNIQUE(domain, keyword)
        );

-- table: keyword_tag
CREATE TABLE IF NOT EXISTS keyword_tag (id INTEGER PRIMARY KEY AUTOINCREMENT, domain TEXT NOT NULL, name TEXT NOT NULL COLLATE NOCASE, created_at TEXT NOT NULL, UNIQUE(domain,name));

-- table: keyword_tag_assignment
CREATE TABLE IF NOT EXISTS keyword_tag_assignment (
            domain TEXT NOT NULL,
            keyword TEXT NOT NULL COLLATE NOCASE,
            tag_id INTEGER NOT NULL,
            PRIMARY KEY(domain, keyword, tag_id)
        );

-- table: manual_ai_source
CREATE TABLE IF NOT EXISTS manual_ai_source (domain TEXT PRIMARY KEY COLLATE NOCASE,prompt_text TEXT NOT NULL DEFAULT '',chatgpt_response TEXT NOT NULL DEFAULT '',claude_response TEXT NOT NULL DEFAULT '',gemini_response TEXT NOT NULL DEFAULT '',updated_at TEXT NOT NULL, phase1_prompt_text TEXT NOT NULL DEFAULT '', phase2_prompt_text TEXT NOT NULL DEFAULT '', phase1_chatgpt_response TEXT NOT NULL DEFAULT '', phase1_claude_response TEXT NOT NULL DEFAULT '', phase1_gemini_response TEXT NOT NULL DEFAULT '', phase2_chatgpt_response TEXT NOT NULL DEFAULT '', phase2_claude_response TEXT NOT NULL DEFAULT '', phase2_gemini_response TEXT NOT NULL DEFAULT '', question_set_version INTEGER NOT NULL DEFAULT 1, analysis_model TEXT NOT NULL DEFAULT '', analysis_system_prompt TEXT NOT NULL DEFAULT '', analysis_text TEXT NOT NULL DEFAULT '', analysis_status TEXT NOT NULL DEFAULT 'not_run', analysis_error TEXT NOT NULL DEFAULT '', analysis_updated_at TEXT NOT NULL DEFAULT '', analysis_provider TEXT NOT NULL DEFAULT 'ollama', analysis_reasoning_effort TEXT NOT NULL DEFAULT 'high', analysis_temperature REAL NOT NULL DEFAULT 0.1, analysis_top_p REAL NOT NULL DEFAULT 0.9, analysis_max_output_tokens INTEGER NOT NULL DEFAULT 8000, analysis_system_prompt_version INTEGER NOT NULL DEFAULT 3, analysis_parameters_json TEXT NOT NULL DEFAULT '{}');

-- table: manual_ai_state_source
CREATE TABLE IF NOT EXISTS manual_ai_state_source (domain TEXT NOT NULL COLLATE NOCASE,phase TEXT NOT NULL,state TEXT NOT NULL,prompt_text TEXT NOT NULL DEFAULT '',chatgpt_response TEXT NOT NULL DEFAULT '',claude_response TEXT NOT NULL DEFAULT '',gemini_response TEXT NOT NULL DEFAULT '',updated_at TEXT NOT NULL,PRIMARY KEY(domain,phase,state));

-- table: page_note
CREATE TABLE IF NOT EXISTS page_note (
            page_id INTEGER PRIMARY KEY,
            content TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL,
            FOREIGN KEY(page_id) REFERENCES site_page(id) ON DELETE CASCADE
        );

-- table: page_tag
CREATE TABLE IF NOT EXISTS page_tag (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            domain TEXT NOT NULL,
            name TEXT NOT NULL COLLATE NOCASE,
            created_at TEXT NOT NULL,
            UNIQUE(domain, name)
        );

-- table: recommendation_tracking
CREATE TABLE IF NOT EXISTS recommendation_tracking (
            domain TEXT NOT NULL COLLATE NOCASE,
            finding_key TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'open',
            note TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL,
            PRIMARY KEY(domain,finding_key)
        );

-- table: report_exclusion
CREATE TABLE IF NOT EXISTS report_exclusion (domain TEXT NOT NULL COLLATE NOCASE,scope TEXT NOT NULL,item_key TEXT NOT NULL,page_id INTEGER NOT NULL DEFAULT -1,created_at TEXT NOT NULL,PRIMARY KEY(domain,scope,item_key,page_id));

-- table: report_human_interpretation
CREATE TABLE IF NOT EXISTS report_human_interpretation (domain TEXT NOT NULL COLLATE NOCASE,report_id TEXT NOT NULL,content TEXT NOT NULL DEFAULT '',updated_at TEXT NOT NULL,PRIMARY KEY(domain,report_id));

-- table: report_note
CREATE TABLE IF NOT EXISTS report_note (domain TEXT NOT NULL COLLATE NOCASE,note_key TEXT NOT NULL,content TEXT NOT NULL DEFAULT '',discussion_enabled INTEGER NOT NULL DEFAULT 0,updated_at TEXT NOT NULL,PRIMARY KEY(domain,note_key));

-- table: report_note_reply
CREATE TABLE IF NOT EXISTS report_note_reply (id INTEGER PRIMARY KEY AUTOINCREMENT,domain TEXT NOT NULL COLLATE NOCASE,note_key TEXT NOT NULL,author_role TEXT NOT NULL,content TEXT NOT NULL,created_at TEXT NOT NULL);

-- table: report_session
CREATE TABLE IF NOT EXISTS report_session (
            id TEXT PRIMARY KEY,
            domain TEXT NOT NULL,
            created_at TEXT NOT NULL,
            snapshot_json TEXT NOT NULL
        );

-- table: research_keyword
CREATE TABLE IF NOT EXISTS research_keyword (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            domain TEXT NOT NULL,
            keyword TEXT NOT NULL COLLATE NOCASE,
            avg_monthly_searches INTEGER,
            competition TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(domain, keyword)
        );

-- table: research_keyword_tag
CREATE TABLE IF NOT EXISTS research_keyword_tag (research_keyword_id INTEGER NOT NULL, tag_id INTEGER NOT NULL, PRIMARY KEY(research_keyword_id,tag_id));

-- table: site_page
CREATE TABLE IF NOT EXISTS site_page (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            domain TEXT NOT NULL,
            url TEXT NOT NULL,
            path TEXT NOT NULL,
            source TEXT NOT NULL DEFAULT 'sitemap',
            discovered_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(domain, url)
        );

-- table: site_page_tag
CREATE TABLE IF NOT EXISTS site_page_tag (
            page_id INTEGER NOT NULL,
            tag_id INTEGER NOT NULL,
            PRIMARY KEY(page_id, tag_id)
        );

-- table: wanted_keyword
CREATE TABLE IF NOT EXISTS wanted_keyword (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            domain TEXT NOT NULL,
            keyword TEXT NOT NULL COLLATE NOCASE,
            avg_monthly_searches INTEGER,
            competition TEXT,
            source TEXT NOT NULL DEFAULT 'manual',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL, page_id INTEGER,
            UNIQUE(domain, keyword)
        );

-- table: wanted_keyword_tag
CREATE TABLE IF NOT EXISTS wanted_keyword_tag (wanted_keyword_id INTEGER NOT NULL, tag_id INTEGER NOT NULL, PRIMARY KEY(wanted_keyword_id,tag_id));

-- index: idx_crawl_issue_run
CREATE INDEX IF NOT EXISTS idx_crawl_issue_run
    ON crawl_issue(crawl_run_id, severity);

-- index: idx_crawl_link_target
CREATE INDEX IF NOT EXISTS idx_crawl_link_target
    ON crawl_link(crawl_run_id, target_url);

-- index: idx_crawl_page_run
CREATE INDEX IF NOT EXISTS idx_crawl_page_run
    ON crawl_page(crawl_run_id, status_code);

-- index: idx_crawl_run_domain
CREATE INDEX IF NOT EXISTS idx_crawl_run_domain
    ON crawl_run(domain, id DESC);

-- index: idx_dashboard_domain_gsc
CREATE INDEX IF NOT EXISTS idx_dashboard_domain_gsc
        ON dashboard_domain(gsc_site_id);

-- index: idx_domain_source_domain
CREATE INDEX IF NOT EXISTS idx_domain_source_domain ON domain_source(domain,selected);

-- index: idx_keyword_note_domain_keyword
CREATE INDEX IF NOT EXISTS idx_keyword_note_domain_keyword
        ON keyword_note(domain, keyword);

-- index: idx_keyword_tag_domain_name
CREATE INDEX IF NOT EXISTS idx_keyword_tag_domain_name ON keyword_tag(domain,name);

-- index: idx_manual_ai_state_domain
CREATE INDEX IF NOT EXISTS idx_manual_ai_state_domain ON manual_ai_state_source(domain,phase,state);

-- index: idx_report_exclusion_domain
CREATE INDEX IF NOT EXISTS idx_report_exclusion_domain ON report_exclusion(domain,scope);

-- index: idx_report_note_reply_lookup
CREATE INDEX IF NOT EXISTS idx_report_note_reply_lookup ON report_note_reply(domain,note_key,id);

-- index: idx_report_session_domain_created
CREATE INDEX IF NOT EXISTS idx_report_session_domain_created
        ON report_session(domain, created_at DESC);

-- index: idx_research_keyword_domain_keyword
CREATE INDEX IF NOT EXISTS idx_research_keyword_domain_keyword ON research_keyword(domain, keyword);

-- index: idx_research_keyword_tag_tag
CREATE INDEX IF NOT EXISTS idx_research_keyword_tag_tag ON research_keyword_tag(tag_id,research_keyword_id);

-- index: idx_site_page_domain_path
CREATE INDEX IF NOT EXISTS idx_site_page_domain_path ON site_page(domain, path);

-- index: idx_wanted_keyword_domain_keyword
CREATE INDEX IF NOT EXISTS idx_wanted_keyword_domain_keyword ON wanted_keyword(domain, keyword);

-- index: idx_wanted_keyword_page
CREATE INDEX IF NOT EXISTS idx_wanted_keyword_page ON wanted_keyword(page_id);

-- index: idx_wanted_keyword_tag_tag
CREATE INDEX IF NOT EXISTS idx_wanted_keyword_tag_tag ON wanted_keyword_tag(tag_id,wanted_keyword_id);
