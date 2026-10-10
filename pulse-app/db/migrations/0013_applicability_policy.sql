CREATE TABLE domain_applicability_policy (
    domain TEXT PRIMARY KEY COLLATE NOCASE,
    enabled_checks_json TEXT NOT NULL DEFAULT '[]',
    updated_at TEXT NOT NULL
);

CREATE TABLE page_type_override (
    domain TEXT NOT NULL COLLATE NOCASE,
    url TEXT NOT NULL,
    page_type TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY(domain, url)
);
