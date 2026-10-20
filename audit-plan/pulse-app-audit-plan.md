# Pulse App — audit handoff and execution plan

Repository: `pablopovar/pulse`  
Pinned commit: `5b4148c0e24030494fca8609e0180ab3a4b0fc9d`  
Revision: 20 October 2026. Status: audit executing; see the execution ledger at the end for observed coverage and findings.

## Objective and scope

Assess current Pulse App behavior for defects, omissions, inconsistent contracts, overlapping implementations, security boundaries, evidence integrity and report accuracy. Deliver findings without implementing fixes.

Review only `pulse-app/`. Exclude `pulse-app/tests/` entirely, including fixtures; `pulse-app/db/migrations/`; the migration runner `pulse-app/db/migrate.py`; and test configuration `pulse-app/pytest.ini`. All repository paths outside `pulse-app/`, including OpenGSC internals and root deployment files, remain excluded. Empty package initializers remain omitted. README and report-contract documents are context.

Current database access, schema assumptions, table ownership, constraints and indexes remain in scope through runtime code and, if available, a read-only schema inspection of the existing database. Do not infer actual database state from source alone. No historical migration review, migration execution, fresh-install certification, upgrade-safety assessment or test-suite audit is included. Inspect startup invocation and failure propagation at its call site without tracing excluded migration internals. Existing tests may optionally be run as supporting evidence, but their source is not an audit target and they are not a completion requirement. Do not follow excluded files without an explicit scope amendment.

Inventory: **88 primary audit files; 56 primary runs; eight comparison runs; eight integration/reconciliation runs**. Original B IDs are preserved. Excluded-only former runs: B004, B005, B006, B014, B017, B020, B022, B025, B027, B037, B049. They require no work and do not count as unfinished runs. This document contains the complete task list; no companion file is required.

## Execution rules and outputs

1. Confirm the pinned commit before each run; record source drift separately. Work against isolated copies of existing-state data and synthetic inputs; do not run migrations or mutate production data.
2. Read every listed file/window. Include enclosing definitions and relevant in-scope callers as context. At the last window of a split file, reconcile the whole file. Compare interfaces even when their implementation is assigned to a later run.
3. Trace input → authentication and validation → service → database/external/filesystem effects → response or presentation. Record domain boundaries, failures, time, provenance and ownership.
4. For each run record status (planned/in progress/blocked/complete), commit, exact coverage, caller links, checks and results, findings, limitations and outstanding questions. Static reading is not a runtime pass.
5. Findings require severity, confidence, file and line, trigger, affected behavior, evidence and reproduction where feasible. Separate confirmed defects, suspected defects, intentional differences and unreachable-code candidates. Consolidate duplicate findings.
6. Use small isolated runtime probes where useful; record commands and actual outcomes. Mock external contracts locally without relying on excluded test fixtures. Avoid live provider charges and external writes.
7. Use the execution schedule below. Integration checks follow the relevant flow; I08 is the final gate. Record prerequisite gaps during preliminary checks and reconcile them when primary coverage is complete. All runs below start as **planned**.

Every primary run must produce an evidence-backed review note and ledger entry. A blocked check must remain explicitly qualified. The final output is a consolidated findings report, completed coverage record, remaining uncertainties and corrected architecture description.

## Instructions to the receiving auditor

Execute this independent audit; do not implement fixes. This handoff supersedes earlier ZIP plans and run ordering. Begin by confirming the pinned source and reading the in-scope README and REPORT_CONTRACT.md. Respect repository instructions that apply, without silently expanding exclusions. No defect-audit run has been completed by preparing this handoff. Architectural concerns below are investigation seeds, not certified defects.

The application’s defining risk is a plausible but incorrect report. Prioritize security, cross-domain data integrity, execution provenance and evidence meaning. Read all scoped files even if the initial risk pass finds nothing. Stop only for a material missing prerequisite; continue independent static work and record blocked runtime checks. Do not equate optional existing test success with proof.

## Audit invariants

- **Domain isolation:** requests, jobs, evidence, reports, notes, skins and exports remain bound to the intended domain and permitted actor.
- **Publication ownership:** lease loss, cancellation or stale worker identity prevents publication and other ownership-protected writes.
- **Execution identity:** a report uses the intended observation/run, not merely any internally coherent latest audit/crawl pair.
- **Honest coverage:** missing, failed, unavailable and nonapplicable evidence cannot silently become a pass, complete coverage or resolved finding.
- **Historical meaning:** current inputs, new interpretations and presentation changes cannot silently substitute historical evidence or its meaning; mutable overlays are identifiable.
- **Safe input boundaries:** crawled/pasted/provider content and URLs cannot gain authority over access, network targets, filesystem paths or rendered executable content.
- **Operator control:** initiation, progress, partial success, failure, retry and cancellation communicate the actual state; the operator can identify the affected run and recover without guessing.
- **Evidence consistency:** displayed findings, counts, dates, confidence and exports have traceable support and consistent semantics.

## Execution schedule

Run order is governed by this schedule, not numeric IDs. Existing IDs are retained solely for traceability. Record one primary coverage entry per file/window; later revisits add evidence without double-counting coverage.

| Stage | Work in order | Gate/output |
| --- | --- | --- |
| 0. Orient | Confirm commit, instructions, README/report contract and available runtime/database evidence. Inventory route/job registration from production code. | Scope and environment record; no migration execution. |
| 1. Early risk pass | Focused reads of B015, B023, B019, B021, B046 and relevant web_report/app callers; preliminary C04 and I01/I02/I04 probes. | Assess unauthorized access, unsafe fetching, stale publication and misleading report identity first. These focused reads do not close whole-file batches unless fully reviewed. |
| 2. Runtime foundation and access | B001, B002, B003, B007, B008–B013, B015, B016, B018; C01; initial C07/C08; I01 boundary checks, I06 adapter checks and I07 configuration/filesystem checks. | Configuration, domain identity and access map; carry UI-specific route checks forward. |
| 3. Jobs and capture | B019, B021, B023, B024, B026, B028–B036; C02, C05; I02/I03. | Ownership/recovery and two-capture evidence results. Reconcile publication portion after report assembly review. |
| 4. Manual and external evidence | B038–B042; C03; I05 and remaining I06. | Completeness, raw retention, stale analysis, provider settings and bounded-cost behavior. |
| 5. Reports and historical meaning | B043–B048, B050–B061; finish C04; I04 and publication portion of I02. | Snapshot/history/export/localization parity and evidence-backed finding semantics. |
| 6. Operator workflows | B062–B067; finish C06/C07/C08; reconcile I01/I07 and affected I04 checks against all UI routes. | Research/keyword/taxonomy actions, recovery feedback, files and complete route dispositions. |
| 7. Close | I08 after all 56 retained B runs, C01–C08 and I01–I07 have outcomes. | Consolidated findings, coverage and limitations; corrected architecture. |

Integration work can begin before every related batch is finished. It closes only after relevant callers, UI and comparison dependencies are reconciled. Revisit a passing probe only when new code evidence, changes or unresolved contradictions justify it.

## Finding and run record

For every run retain: ID, pinned commit, status, files/windows actually read, consulted in-scope context, caller/storage/output links, invariant checked, expected behavior, evidence or probe command/result, findings, unresolved edges and next action. Carry this record in the final audit report or session handoff; this plan is the single input document.

A finding records: ID; severity (critical/high/medium/low, with impact rationale); confidence; confirmed or suspected; file/line and symbol; trigger; expected versus actual behavior; user/data consequence; supporting evidence; affected flows; and verification limits. Recommendations describe the required correction without implementing it. Informational observations and intentional differences are separate from defects.

## Architecture and critical provenance

Flask routes enforce management/client access and serve domain, research, source and report workspaces. Routes enqueue durable SQLite jobs; a lease-owning worker performs discovery, crawling, GEO/AEO scoring, optional AI analysis and report publication. Pulse's OpenGSC adapter reads an external database; DataForSEO and AI clients call external providers. These external implementations are outside scope.

The crawler and GEO/AEO engine independently fetch pages. Report collection chooses the latest eligible domain audit and its matching crawl; refresh does not supply expected run IDs to collection. Comparison C04 must establish whether concurrent refreshes can mix current-job identity. Reports are first staged, then published with ownership checks. Historical evidence snapshots coexist with separately loaded notes, interpretation, navigation and presentation logic; their immutability must be checked separately.

Manual AI answers are collected outside Pulse, pasted and parsed, projected into reports and optionally interpreted by a background analysis job. Verify actual phase/state/provider/question denominators and reachability of alternate governance code. Domain creation, sync/deletion, research/taxonomy, provider settings, discussion and filesystem skins are separate flows that also require review.

## Primary file-review runs
### B001 — 01. Deployment and dependencies

Files/windows:

- `pulse-app/.env.example`

**Establish:** Which settings are required and which silently fall back?

Tasks:

- Compare documented database, provider and security variables with runtime consumers; flag examples that encourage insecure deployment or expose secrets.
- Trace one ordinary case and one relevant counterexample through the listed code; record expected versus actual behavior. Use an isolated probe when executable; otherwise record the static evidence and verification limit.
- Record findings, caller links and exact coverage. Resolve enclosing definitions and carry unresolved cross-file questions to the assigned comparison/integration run.

**Completion evidence:** file/line references, input/condition, observed or inferred result, applicable invariant, and explicit status. At the last window of any split file, reconcile the whole file.

### B002 — 01. Deployment and dependencies

Files/windows:

- `pulse-app/Dockerfile`
- `pulse-app/entrypoint.sh`
- `pulse-app/requirements.txt`

**Establish:** Does the supported container start the intended application with predictable configuration?

Tasks:

- Trace entrypoint commands, environment propagation, user/permissions, mounts and dependency versions. Inspect only the migration invocation/failure handling, not migration implementation or upgrade behavior.
- Trace one ordinary case and one relevant counterexample through the listed code; record expected versus actual behavior. Use an isolated probe when executable; otherwise record the static evidence and verification limit.
- Record findings, caller links and exact coverage. Resolve enclosing definitions and carry unresolved cross-file questions to the assigned comparison/integration run.

**Completion evidence:** file/line references, input/condition, observed or inferred result, applicable invariant, and explicit status. At the last window of any split file, reconcile the whole file.

### B003 — 02. Pulse schema and storage

Files/windows:

- `pulse-app/db/__init__.py`

**Establish:** Does runtime database initialization use the intended database and transaction boundary?

Tasks:

- Trace exports, connection selection and runtime initialization in db/__init__.py; identify hidden writes and failure handling without following excluded migration code.
- Trace one ordinary case and one relevant counterexample through the listed code; record expected versus actual behavior. Use an isolated probe when executable; otherwise record the static evidence and verification limit.
- Record findings, caller links and exact coverage. Resolve enclosing definitions and carry unresolved cross-file questions to the assigned comparison/integration run.

**Completion evidence:** file/line references, input/condition, observed or inferred result, applicable invariant, and explicit status. At the last window of any split file, reconcile the whole file.

### B007 — 02. Pulse schema and storage

Files/windows:

- `pulse-app/db/ownership.py`
- `pulse-app/db/sqlite.py`

**Establish:** Are connection behavior and table ownership consistent with actual writers?

Tasks:

- Check foreign-key enablement, busy timeouts, WAL/read-only handling, transaction cleanup and ownership registration. Distinguish declared constraints from confirmed current schema.
- Trace one ordinary case and one relevant counterexample through the listed code; record expected versus actual behavior. Use an isolated probe when executable; otherwise record the static evidence and verification limit.
- Record findings, caller links and exact coverage. Resolve enclosing definitions and carry unresolved cross-file questions to the assigned comparison/integration run.

**Completion evidence:** file/line references, input/condition, observed or inferred result, applicable invariant, and explicit status. At the last window of any split file, reconcile the whole file.

### B008 — 03. Pulse HTTP shell and route contracts

Files/windows:

- `pulse-app/app.py` — lines 1–400

Navigation anchors: db (78–81), sqlite_regexp (86–92), research_db (95–98), detected_source_state (102–103), domain_sources_for_site (106–111), manual_ai_default_prompt (113–133), load_manual_ai_source (136–142), _manual_ai_upload_text (145–150), infer_company_name (171–172), research_state_from_request (175–176), research_redirect (178–179), normalize_tag_name (181–182), move_research_keyword_to_wanted (184–194), _fetch_sitemap_urls (198–204), sitemap_pages (207–209), _site_id_value (212–213), gsc_rows_for_domain (216–220), sync_site_pages (223–231), canonical_keyword_tags (233–241), ensure_keyword_tag (244–250), ensure_page_tag (253–259), parse_keyword_csv_enriched (261–304), parse_keyword_csv (306–325), host_from_site (327–336), _opengsc_get_sites (339–345), _opengsc_get_site (347–351), domain_seo (354–355), page_rows (358–359), page_detail (362–363), keyword_rows (366–367), build_domain_export (370–391), geo_engine_audit (393–394), latest_audit_page (397–403), find (274–278), csv_bytes (376–383).

**Establish:** Do the routes and helpers in this window preserve authorization, domain identity and service contracts?

Tasks:

- For each named route/helper, map accepted methods/inputs, boundary checks, invoked services, SQL/filesystem/network effects and rendered response. Inspect wrappers versus inline implementations and record links for C01/C02/C06/C08. Reconcile corresponding route-checklist rows.
- Trace one ordinary case and one relevant counterexample through the listed code; record expected versus actual behavior. Use an isolated probe when executable; otherwise record the static evidence and verification limit.
- Record findings, caller links and exact coverage. Resolve enclosing definitions and carry unresolved cross-file questions to the assigned comparison/integration run.

**Completion evidence:** file/line references, input/condition, observed or inferred result, applicable invariant, and explicit status. At the last window of any split file, reconcile the whole file.

### B009 — 03. Pulse HTTP shell and route contracts

Files/windows:

- `pulse-app/app.py` — lines 401–800

Navigation anchors: latest_audit_page (397–403), recompute_domain_summary (406–432), store_structured_audit (435–461), audit_worker (464–476), start_audit_run (479–481), report_files (484–500), normalize_dashboard_domain (504–519), _site_value (522–530), _opengsc_site_domain (533–541), sync_dashboard_domains_from_opengsc (544–577), get_sites (581–594), get_site (597–616), create_dashboard_domain (619–637), index (641–645), domain_new (650–675), domain_sources (678–711), save_source_company_name (716–719), save_domain_skin (723–737), save_report_scope (741–762), save_domain_applicability (766–772), save_domain_page_type (776–786), save_report_quick_links (789–801), avg (408–410), lines (743–744).

**Establish:** Do the routes and helpers in this window preserve authorization, domain identity and service contracts?

Tasks:

- For each named route/helper, map accepted methods/inputs, boundary checks, invoked services, SQL/filesystem/network effects and rendered response. Inspect wrappers versus inline implementations and record links for C01/C02/C06/C08. Reconcile corresponding route-checklist rows.
- Trace one ordinary case and one relevant counterexample through the listed code; record expected versus actual behavior. Use an isolated probe when executable; otherwise record the static evidence and verification limit.
- Record findings, caller links and exact coverage. Resolve enclosing definitions and carry unresolved cross-file questions to the assigned comparison/integration run.

**Completion evidence:** file/line references, input/condition, observed or inferred result, applicable invariant, and explicit status. At the last window of any split file, reconcile the whole file.

### B010 — 03. Pulse HTTP shell and route contracts

Files/windows:

- `pulse-app/app.py` — lines 801–1200

Navigation anchors: save_report_quick_links (789–801), save_client_report_access (805–821), domain_settings (825–827), manual_ai_source (830–867), manual_ai_analysis_models (871–877), manual_ai_source_analyze (881–901), tools (906–908), overview (915–918), pages (922–957), page (962–975), keywords_dashboard (980–982), keywords (987–994), export_domain (998–1011), wanted (1017–1141), wanted_add (1146–1154), wanted_delete (1157–1161), research_save (1164–1170), research (1174–1204), f (887–890).

**Establish:** Do the routes and helpers in this window preserve authorization, domain identity and service contracts?

Tasks:

- For each named route/helper, map accepted methods/inputs, boundary checks, invoked services, SQL/filesystem/network effects and rendered response. Inspect wrappers versus inline implementations and record links for C01/C02/C06/C08. Reconcile corresponding route-checklist rows.
- Trace one ordinary case and one relevant counterexample through the listed code; record expected versus actual behavior. Use an isolated probe when executable; otherwise record the static evidence and verification limit.
- Record findings, caller links and exact coverage. Resolve enclosing definitions and carry unresolved cross-file questions to the assigned comparison/integration run.

**Completion evidence:** file/line references, input/condition, observed or inferred result, applicable invariant, and explicit status. At the last window of any split file, reconcile the whole file.

### B011 — 03. Pulse HTTP shell and route contracts

Files/windows:

- `pulse-app/app.py` — lines 1201–1600

Navigation anchors: research (1174–1204), research_bulk_save (1208–1222), research_bulk_tag (1226–1245), research_bulk_delete (1248–1259), research_upload (1263–1301), research_edit (1305–1313), research_delete (1316–1320), pages_sync (1324–1334), page_workspace (1337–1366), page_wanted_add (1370–1418), page_note_save (1422–1434), wanted_assign_page (1438–1447), keyword_note_get (1451–1463), keyword_note_save (1467–1489), taxonomy_lookup (1494–1510), taxonomy_apply (1514–1546), keyword_workspace (1550–1568), keyword_wanted_set (1572–1586), keyword_tag_change (1590–1608).

**Establish:** Do the routes and helpers in this window preserve authorization, domain identity and service contracts?

Tasks:

- For each named route/helper, map accepted methods/inputs, boundary checks, invoked services, SQL/filesystem/network effects and rendered response. Inspect wrappers versus inline implementations and record links for C01/C02/C06/C08. Reconcile corresponding route-checklist rows.
- Trace one ordinary case and one relevant counterexample through the listed code; record expected versus actual behavior. Use an isolated probe when executable; otherwise record the static evidence and verification limit.
- Record findings, caller links and exact coverage. Resolve enclosing definitions and carry unresolved cross-file questions to the assigned comparison/integration run.

**Completion evidence:** file/line references, input/condition, observed or inferred result, applicable invariant, and explicit status. At the last window of any split file, reconcile the whole file.

### B012 — 03. Pulse HTTP shell and route contracts

Files/windows:

- `pulse-app/app.py` — lines 1601–2000

Navigation anchors: keyword_tag_change (1590–1608), keyword_note_page_save (1612–1620), geo_aeo_integrated (1623–1649), geo_aeo_run_domain (1653–1660), geo_aeo_run_page (1664–1669), geo_aeo_page_json (1673–1688), geo_aeo_signal_state (1692–1709), geo_aeo_report (1713–1729), reports (1732–1743), generate_full_web_report (1747–1750), public_report_static (1755–1756), domain_skin (1760–1771), public_report_access (1775–1794), public_report_note_reply (1799–1811), public_report (1815–1819), public_report_export (1823–1832), public_report_pdf (1836–1840), report_workflow_exclusion (1844–1866), save_report_human_interpretation (1870–1878), save_report_note (1882–1895), save_report_note_reply (1899–1916), report_notes_json (1920–1922), report_session_view (1926–1959), report_session_export (1963–1965), _send_observation_export (1968–1984), report_session_pdf (1989–1991), run_audit (1995–1996).

**Establish:** Do the routes and helpers in this window preserve authorization, domain identity and service contracts?

Tasks:

- For each named route/helper, map accepted methods/inputs, boundary checks, invoked services, SQL/filesystem/network effects and rendered response. Inspect wrappers versus inline implementations and record links for C01/C02/C06/C08. Reconcile corresponding route-checklist rows.
- Trace one ordinary case and one relevant counterexample through the listed code; record expected versus actual behavior. Use an isolated probe when executable; otherwise record the static evidence and verification limit.
- Record findings, caller links and exact coverage. Resolve enclosing definitions and carry unresolved cross-file questions to the assigned comparison/integration run.

**Completion evidence:** file/line references, input/condition, observed or inferred result, applicable invariant, and explicit status. At the last window of any split file, reconcile the whole file.

### B013 — 03. Pulse HTTP shell and route contracts

Files/windows:

- `pulse-app/app.py` — lines 2001–2118

Navigation anchors: download_report (2001–2004), helpers (2008–2014), durable_job_status (2035–2039), durable_jobs_index (2043–2051), durable_job_cancel (2055–2065), durable_job_pause (2069–2075), durable_job_resume (2079–2085), _domain_job_or_404 (2088–2093), domain_job_cancel (2097–2100), domain_job_pause (2104–2107), domain_job_resume (2111–2114), pct (2009–2013).

**Establish:** Do the routes and helpers in this window preserve authorization, domain identity and service contracts?

Tasks:

- For each named route/helper, map accepted methods/inputs, boundary checks, invoked services, SQL/filesystem/network effects and rendered response. Inspect wrappers versus inline implementations and record links for C01/C02/C06/C08. Reconcile corresponding route-checklist rows.
- Trace one ordinary case and one relevant counterexample through the listed code; record expected versus actual behavior. Use an isolated probe when executable; otherwise record the static evidence and verification limit.
- Record findings, caller links and exact coverage. Resolve enclosing definitions and carry unresolved cross-file questions to the assigned comparison/integration run.

**Completion evidence:** file/line references, input/condition, observed or inferred result, applicable invariant, and explicit status. At the last window of any split file, reconcile the whole file.

### B015 — 04. Pulse security and client access

Files/windows:

- `pulse-app/services/public_report_access.py`
- `pulse-app/services/security_boundary.py`

**Establish:** Can an unauthorized actor reach management or another domain’s client report?

Tasks:

- Trace proxy trust, management authentication, CSRF, tokens, password checks, expiry/revocation and exempt paths. Probe denied and permitted requests through the actual boundary.
- Trace one ordinary case and one relevant counterexample through the listed code; record expected versus actual behavior. Use an isolated probe when executable; otherwise record the static evidence and verification limit.
- Record findings, caller links and exact coverage. Resolve enclosing definitions and carry unresolved cross-file questions to the assigned comparison/integration run.

**Completion evidence:** file/line references, input/condition, observed or inferred result, applicable invariant, and explicit status. At the last window of any split file, reconcile the whole file.

### B016 — 05. Pulse domain lifecycle and presentation settings

Files/windows:

- `pulse-app/services/domain_company.py`
- `pulse-app/services/domain_registry.py`
- `pulse-app/services/domain_skin.py`
- `pulse-app/services/domains.py`

**Establish:** Do web/worker domain identity, deletion and presentation settings agree?

Tasks:

- Compare normalization and imported fields; trace suppression and deletion dependencies. Check company metadata isolation, custom CSS paths, traversal, atomic writes and cleanup.
- Trace one ordinary case and one relevant counterexample through the listed code; record expected versus actual behavior. Use an isolated probe when executable; otherwise record the static evidence and verification limit.
- Record findings, caller links and exact coverage. Resolve enclosing definitions and carry unresolved cross-file questions to the assigned comparison/integration run.

**Completion evidence:** file/line references, input/condition, observed or inferred result, applicable invariant, and explicit status. At the last window of any split file, reconcile the whole file.

### B018 — 06. Pulse OpenGSC adapter

Files/windows:

- `pulse-app/integrations/opengsc_adapter.py`

**Establish:** Do external database reads produce correctly scoped and qualified evidence?

Tasks:

- Check read-only enforcement, schema/NULL handling, site matching, timezone/date windows, missing versus zero and bounded metrics; use isolated contract data.
- Trace one ordinary case and one relevant counterexample through the listed code; record expected versus actual behavior. Use an isolated probe when executable; otherwise record the static evidence and verification limit.
- Record findings, caller links and exact coverage. Resolve enclosing definitions and carry unresolved cross-file questions to the assigned comparison/integration run.

**Completion evidence:** file/line references, input/condition, observed or inferred result, applicable invariant, and explicit status. At the last window of any split file, reconcile the whole file.

### B019 — 07. Pulse durable job lifecycle

Files/windows:

- `pulse-app/jobs/__init__.py`
- `pulse-app/jobs/handlers.py`
- `pulse-app/jobs/store.py`
- `pulse-app/jobs/worker.py`

**Establish:** Can two workers claim or complete the same work incorrectly?

Tasks:

- Inspect claim transactions, leases, heartbeats, retries, worker identity, handler dispatch and pause/cancel transitions. Map every HANDLERS entry to payload and result contracts.
- Trace one ordinary case and one relevant counterexample through the listed code; record expected versus actual behavior. Use an isolated probe when executable; otherwise record the static evidence and verification limit.
- Record findings, caller links and exact coverage. Resolve enclosing definitions and carry unresolved cross-file questions to the assigned comparison/integration run.

**Completion evidence:** file/line references, input/condition, observed or inferred result, applicable invariant, and explicit status. At the last window of any split file, reconcile the whole file.

### B021 — 08. Pulse workflow and publication

Files/windows:

- `pulse-app/jobs/publication.py`
- `pulse-app/jobs/workflows.py`

**Establish:** Can a refresh publish incomplete, stale or foreign-execution evidence?

Tasks:

- Trace stage transitions, prerequisites, idempotency, lost ownership, publication withholding, current/baseline pointers and background scheduling. Enumerate all direct and fenced publication callers.
- Trace one ordinary case and one relevant counterexample through the listed code; record expected versus actual behavior. Use an isolated probe when executable; otherwise record the static evidence and verification limit.
- Record findings, caller links and exact coverage. Resolve enclosing definitions and carry unresolved cross-file questions to the assigned comparison/integration run.

**Completion evidence:** file/line references, input/condition, observed or inferred result, applicable invariant, and explicit status. At the last window of any split file, reconcile the whole file.

### B023 — 09. Pulse URL and outbound HTTP boundary

Files/windows:

- `pulse-app/services/safe_fetcher.py`
- `pulse-app/services/url_policy.py`

**Establish:** Can attacker-controlled URLs escape the allowed fetch boundary?

Tasks:

- Probe schemes, ports, credentials, IDNA, IP literals, DNS answers, redirects, private/link-local addresses, timeouts and response limits. Check the validated address is the address actually contacted.
- Trace one ordinary case and one relevant counterexample through the listed code; record expected versus actual behavior. Use an isolated probe when executable; otherwise record the static evidence and verification limit.
- Record findings, caller links and exact coverage. Resolve enclosing definitions and carry unresolved cross-file questions to the assigned comparison/integration run.

**Completion evidence:** file/line references, input/condition, observed or inferred result, applicable invariant, and explicit status. At the last window of any split file, reconcile the whole file.

### B024 — 10. Pulse page discovery and reconciliation

Files/windows:

- `pulse-app/services/page_discovery.py`
- `pulse-app/services/sitemap_reconciliation.py`

**Establish:** Does discovery preserve eligibility and source provenance under malformed inputs?

Tasks:

- Check nested/text/gzip sitemap handling, depth/size/cycle limits, deduplication, unavailable sources and reconciliation. Identify request-time network I/O and use of SafeFetcher.
- Trace one ordinary case and one relevant counterexample through the listed code; record expected versus actual behavior. Use an isolated probe when executable; otherwise record the static evidence and verification limit.
- Record findings, caller links and exact coverage. Resolve enclosing definitions and carry unresolved cross-file questions to the assigned comparison/integration run.

**Completion evidence:** file/line references, input/condition, observed or inferred result, applicable invariant, and explicit status. At the last window of any split file, reconcile the whole file.

### B026 — 11. Pulse crawl selection and frontier

Files/windows:

- `pulse-app/services/crawl_frontier.py`

**Establish:** Does the frontier spend crawl budgets on the intended eligible pages?

Tasks:

- Trace ranking, page classes, deduplication, delayed/retried work and persisted decisions. Check starvation, budget boundaries and restart behavior.
- Trace one ordinary case and one relevant counterexample through the listed code; record expected versus actual behavior. Use an isolated probe when executable; otherwise record the static evidence and verification limit.
- Record findings, caller links and exact coverage. Resolve enclosing definitions and carry unresolved cross-file questions to the assigned comparison/integration run.

**Completion evidence:** file/line references, input/condition, observed or inferred result, applicable invariant, and explicit status. At the last window of any split file, reconcile the whole file.

### B028 — 12. Pulse crawler and evidence

Files/windows:

- `pulse-app/crawlers/seo.py` — lines 1–400

Navigation anchors: utcnow (54–55), same_site (58–59), PageParser (62–210), fetch (213–259), decode_body (262–270), parse_sitemap (273–280), _candidate_reason (288–299), _candidate_score (301–326), ten_page_candidates (328–370), discover_seed_urls (372–384), build_robot_parser (386–412), __init__ (63–84), handle_starttag (86–133), handle_endtag (135–156), handle_data (158–166), _extract_schema (168–187), result (189–210), walk (174–185).

**Establish:** Does this crawler segment preserve policy, execution ownership and captured evidence?

Tasks:

- Trace the listed symbols through fetch/parse/store/control stages. Check robots and redirect handling, response limits, conditional requests, evidence hashes/timestamps, partial failures and lease/cancel checks where present. Carry cross-window dependencies to the final crawler window.
- Trace one ordinary case and one relevant counterexample through the listed code; record expected versus actual behavior. Use an isolated probe when executable; otherwise record the static evidence and verification limit.
- Record findings, caller links and exact coverage. Resolve enclosing definitions and carry unresolved cross-file questions to the assigned comparison/integration run.

**Completion evidence:** file/line references, input/condition, observed or inferred result, applicable invariant, and explicit status. At the last window of any split file, reconcile the whole file.

### B029 — 12. Pulse crawler and evidence

Files/windows:

- `pulse-app/crawlers/seo.py` — lines 401–800

Navigation anchors: build_robot_parser (386–412), _content_fingerprints (415–427), _content_is_substantial (430–441), _hamming (444–448), _failure_kind (451–466), _revalidate_legacy_duplicates (469–499), _reclassify_redirect_aliases (502–570), _sync_url_inventory (573–635), add_issue (639–645), best_effort_site_page (648–667), persist_page (670–925).

**Establish:** Does this crawler segment preserve policy, execution ownership and captured evidence?

Tasks:

- Trace the listed symbols through fetch/parse/store/control stages. Check robots and redirect handling, response limits, conditional requests, evidence hashes/timestamps, partial failures and lease/cancel checks where present. Carry cross-window dependencies to the final crawler window.
- Trace one ordinary case and one relevant counterexample through the listed code; record expected versus actual behavior. Use an isolated probe when executable; otherwise record the static evidence and verification limit.
- Record findings, caller links and exact coverage. Resolve enclosing definitions and carry unresolved cross-file questions to the assigned comparison/integration run.

**Completion evidence:** file/line references, input/condition, observed or inferred result, applicable invariant, and explicit status. At the last window of any split file, reconcile the whole file.

### B030 — 12. Pulse crawler and evidence

Files/windows:

- `pulse-app/crawlers/seo.py` — lines 801–1200

Navigation anchors: persist_page (670–925), crawl_worker (928–1261).

**Establish:** Does this crawler segment preserve policy, execution ownership and captured evidence?

Tasks:

- Trace the listed symbols through fetch/parse/store/control stages. Check robots and redirect handling, response limits, conditional requests, evidence hashes/timestamps, partial failures and lease/cancel checks where present. Carry cross-window dependencies to the final crawler window.
- Trace one ordinary case and one relevant counterexample through the listed code; record expected versus actual behavior. Use an isolated probe when executable; otherwise record the static evidence and verification limit.
- Record findings, caller links and exact coverage. Resolve enclosing definitions and carry unresolved cross-file questions to the assigned comparison/integration run.

**Completion evidence:** file/line references, input/condition, observed or inferred result, applicable invariant, and explicit status. At the last window of any split file, reconcile the whole file.

### B031 — 12. Pulse crawler and evidence

Files/windows:

- `pulse-app/crawlers/seo.py` — lines 1201–1519

Navigation anchors: crawl_worker (928–1261), register_crawler (1264–1519), seo_crawl (1268–1344), get_sites_for_template (1348–1354), ten_page_select (1358–1367), ten_page_run (1370–1412), seo_crawl_run (1415–1450), seo_crawl_policy (1453–1474), _domain_job (1476–1481), seo_crawl_pause (1484–1487), seo_crawl_resume (1490–1493), seo_crawl_cancel (1496–1499), seo_crawl_status (1502–1519).

**Establish:** Does this crawler segment preserve policy, execution ownership and captured evidence?

Tasks:

- Trace the listed symbols through fetch/parse/store/control stages. Check robots and redirect handling, response limits, conditional requests, evidence hashes/timestamps, partial failures and lease/cancel checks where present. Carry cross-window dependencies to the final crawler window.
- Trace one ordinary case and one relevant counterexample through the listed code; record expected versus actual behavior. Use an isolated probe when executable; otherwise record the static evidence and verification limit.
- Record findings, caller links and exact coverage. Resolve enclosing definitions and carry unresolved cross-file questions to the assigned comparison/integration run.

**Completion evidence:** file/line references, input/condition, observed or inferred result, applicable invariant, and explicit status. At the last window of any split file, reconcile the whole file.

### B032 — 12. Pulse crawler and evidence

Files/windows:

- `pulse-app/services/resource_outcome.py`
- `pulse-app/templates/crawl.html`
- `pulse-app/templates/ten_page_select.html`

**Establish:** Do resource outcomes and crawl UI accurately describe the evidence obtained?

Tasks:

- Trace unavailable/failed/partial outcomes into counts and labels. Check selection submission, page/domain identifiers, escaping and actionable crawl status.
- Trace one ordinary case and one relevant counterexample through the listed code; record expected versus actual behavior. Use an isolated probe when executable; otherwise record the static evidence and verification limit.
- Record findings, caller links and exact coverage. Resolve enclosing definitions and carry unresolved cross-file questions to the assigned comparison/integration run.

**Completion evidence:** file/line references, input/condition, observed or inferred result, applicable invariant, and explicit status. At the last window of any split file, reconcile the whole file.

### B033 — 13. Pulse GEO/AEO audit and scoring

Files/windows:

- `pulse-app/audits/geo_aeo/engine.py` — lines 1–400

Navigation anchors: normalize_url (33–37), _text (40–41), _meta (44–46), _property (49–51), _decode_response (54–55), _schema_objects (58–78), _schema_types (81–89), _page_type (92–108), _supporting_file (111–121), _robots_blocks (124–135), capture_page (138–297), _status (300–301), evaluate (304–522), collect (62–70), add (307–316).

**Establish:** Are the assessments produced here supported by the engine’s own capture?

Tasks:

- Trace the listed detectors and capture helpers, supporting-resource requests, parsing assumptions and evidence references. Check unknown versus fail, applicability, score denominators and error behavior. Compare second-capture timing with crawler evidence in C05.
- Trace one ordinary case and one relevant counterexample through the listed code; record expected versus actual behavior. Use an isolated probe when executable; otherwise record the static evidence and verification limit.
- Record findings, caller links and exact coverage. Resolve enclosing definitions and carry unresolved cross-file questions to the assigned comparison/integration run.

**Completion evidence:** file/line references, input/condition, observed or inferred result, applicable invariant, and explicit status. At the last window of any split file, reconcile the whole file.

### B034 — 13. Pulse GEO/AEO audit and scoring

Files/windows:

- `pulse-app/audits/geo_aeo/engine.py` — lines 401–571

Navigation anchors: evaluate (304–522), summarize (525–538), build_report (541–571).

**Establish:** Are the assessments produced here supported by the engine’s own capture?

Tasks:

- Trace the listed detectors and capture helpers, supporting-resource requests, parsing assumptions and evidence references. Check unknown versus fail, applicability, score denominators and error behavior. Compare second-capture timing with crawler evidence in C05.
- Trace one ordinary case and one relevant counterexample through the listed code; record expected versus actual behavior. Use an isolated probe when executable; otherwise record the static evidence and verification limit.
- Record findings, caller links and exact coverage. Resolve enclosing definitions and carry unresolved cross-file questions to the assigned comparison/integration run.

**Completion evidence:** file/line references, input/condition, observed or inferred result, applicable invariant, and explicit status. At the last window of any split file, reconcile the whole file.

### B035 — 13. Pulse GEO/AEO audit and scoring

Files/windows:

- `pulse-app/audits/geo_aeo/service.py`
- `pulse-app/services/applicability_policy.py`
- `pulse-app/services/audit_execution.py`
- `pulse-app/services/page_types.py`

**Establish:** Do classification, applicability and persistence yield defensible aggregate scores?

Tasks:

- Trace page-type assignment, unknown/nonapplicable handling, weights, denominators and summary writes. Compare service storage with app.py persistence in C02.
- Trace one ordinary case and one relevant counterexample through the listed code; record expected versus actual behavior. Use an isolated probe when executable; otherwise record the static evidence and verification limit.
- Record findings, caller links and exact coverage. Resolve enclosing definitions and carry unresolved cross-file questions to the assigned comparison/integration run.

**Completion evidence:** file/line references, input/condition, observed or inferred result, applicable invariant, and explicit status. At the last window of any split file, reconcile the whole file.

### B036 — 13. Pulse GEO/AEO audit and scoring

Files/windows:

- `pulse-app/static/page-geo-aeo.js`
- `pulse-app/templates/geo_aeo.html`
- `pulse-app/templates/geo_aeo_integrated.html`
- `pulse-app/templates/geo_aeo_report.html`

**Establish:** Does the GEO/AEO UI faithfully display the assessment and its limits?

Tasks:

- Trace API fields into all three views and page JS; check escaping, missing-data states, status labels, denominators and cross-domain links.
- Trace one ordinary case and one relevant counterexample through the listed code; record expected versus actual behavior. Use an isolated probe when executable; otherwise record the static evidence and verification limit.
- Record findings, caller links and exact coverage. Resolve enclosing definitions and carry unresolved cross-file questions to the assigned comparison/integration run.

**Completion evidence:** file/line references, input/condition, observed or inferred result, applicable invariant, and explicit status. At the last window of any split file, reconcile the whole file.

### B038 — 14. Pulse manual AI evidence and analysis

Files/windows:

- `pulse-app/reports/cross_model.py`

**Establish:** Is cross-model comparison active, and what can its evidence actually establish?

Tasks:

- Find callers and validate model/source comparability, absent responses, citations and conclusions. Record unreachable candidates with reachability limits.
- Trace one ordinary case and one relevant counterexample through the listed code; record expected versus actual behavior. Use an isolated probe when executable; otherwise record the static evidence and verification limit.
- Record findings, caller links and exact coverage. Resolve enclosing definitions and carry unresolved cross-file questions to the assigned comparison/integration run.

**Completion evidence:** file/line references, input/condition, observed or inferred result, applicable invariant, and explicit status. At the last window of any split file, reconcile the whole file.

### B039 — 14. Pulse manual AI evidence and analysis

Files/windows:

- `pulse-app/reports/manual_ai_analysis.py`
- `pulse-app/reports/question_governance.py`
- `pulse-app/services/manual_ai_payload.py`
- `pulse-app/services/manual_ai_report.py`

**Establish:** Can parsing, governance or optional analysis misstate manual evidence?

Tasks:

- Trace phase/state/question/provider identities, malformed payloads, citation grounding, analysis parameters, source snapshots and stale-result fencing.
- Trace one ordinary case and one relevant counterexample through the listed code; record expected versus actual behavior. Use an isolated probe when executable; otherwise record the static evidence and verification limit.
- Record findings, caller links and exact coverage. Resolve enclosing definitions and carry unresolved cross-file questions to the assigned comparison/integration run.

**Completion evidence:** file/line references, input/condition, observed or inferred result, applicable invariant, and explicit status. At the last window of any split file, reconcile the whole file.

### B040 — 14. Pulse manual AI evidence and analysis

Files/windows:

- `pulse-app/services/manual_ai_sources.py`
- `pulse-app/templates/manual_ai_responses.html`

**Establish:** Does pasted evidence survive storage and UI rendering with correct identity?

Tasks:

- Check raw retention, provider/state completeness, save validation, parsing errors and escaped display; reconcile the storage loader with report projection in C03.
- Trace one ordinary case and one relevant counterexample through the listed code; record expected versus actual behavior. Use an isolated probe when executable; otherwise record the static evidence and verification limit.
- Record findings, caller links and exact coverage. Resolve enclosing definitions and carry unresolved cross-file questions to the assigned comparison/integration run.

**Completion evidence:** file/line references, input/condition, observed or inferred result, applicable invariant, and explicit status. At the last window of any split file, reconcile the whole file.

### B041 — 15. Pulse source selection and paid integration

Files/windows:

- `pulse-app/integrations/dataforseo/connector.py`
- `pulse-app/integrations/dataforseo/extension.py`
- `pulse-app/reports/extended_sources.py`
- `pulse-app/services/source_inventory.py`

**Establish:** Do source selection and paid-provider calls respect operator intent?

Tasks:

- Trace available versus selected sources, settings scope, credentials, kill switches, usage/cost accounting, failures and captured dates. Check alternate enrichment reachability.
- Trace one ordinary case and one relevant counterexample through the listed code; record expected versus actual behavior. Use an isolated probe when executable; otherwise record the static evidence and verification limit.
- Record findings, caller links and exact coverage. Resolve enclosing definitions and carry unresolved cross-file questions to the assigned comparison/integration run.

**Completion evidence:** file/line references, input/condition, observed or inferred result, applicable invariant, and explicit status. At the last window of any split file, reconcile the whole file.

### B042 — 15. Pulse source selection and paid integration

Files/windows:

- `pulse-app/templates/dataforseo.html`
- `pulse-app/templates/sources.html`

**Establish:** Can operators understand and control source/provider state?

Tasks:

- Check settings forms, selected-source persistence, disabled/error states, secret exposure, CSRF and messaging about provider calls or unavailable data.
- Trace one ordinary case and one relevant counterexample through the listed code; record expected versus actual behavior. Use an isolated probe when executable; otherwise record the static evidence and verification limit.
- Record findings, caller links and exact coverage. Resolve enclosing definitions and carry unresolved cross-file questions to the assigned comparison/integration run.

**Completion evidence:** file/line references, input/condition, observed or inferred result, applicable invariant, and explicit status. At the last window of any split file, reconcile the whole file.

### B043 — 16. Pulse report collection and immutable sessions

Files/windows:

- `pulse-app/reports/web_report.py` — lines 1–400

Navigation anchors: _connect (82–83), _json_default (88–92), _load_client_config (103–123), load_client_report_config (126–133), _table_exists (136–139), _json_list (142–147), _build_monitoring_inventory_snapshot (150–261), _monitoring_change (264–276), _attach_monitoring_history (279–295), save_client_report_config (298–308), _load_recommendation_tracking (311–313), set_recommendation_tracking (316–326), _auto_update_recommendations (329–349), create_report_session (352–417), parsed (107–112).

**Establish:** Does this report segment preserve observation identity and avoid unsupported completeness?

Tasks:

- Trace source selection, domain/run IDs, dates, snapshot fields, missing-data handling and publication/read paths in the listed symbols. Check serialization, legacy fallbacks and mutable overlays. Record expected-execution questions for C04 and parity checks for I04.
- Trace one ordinary case and one relevant counterexample through the listed code; record expected versus actual behavior. Use an isolated probe when executable; otherwise record the static evidence and verification limit.
- Record findings, caller links and exact coverage. Resolve enclosing definitions and carry unresolved cross-file questions to the assigned comparison/integration run.

**Completion evidence:** file/line references, input/condition, observed or inferred result, applicable invariant, and explicit status. At the last window of any split file, reconcile the whole file.

### B044 — 16. Pulse report collection and immutable sessions

Files/windows:

- `pulse-app/reports/web_report.py` — lines 401–800

Navigation anchors: create_report_session (352–417), _session_with_history (420–466), load_report_session (469–472), load_current_report_session (475–482), list_report_sessions (485–488), _impact (491–498), _rollup_status (501–502), _rollup_severity (505–507), _audit_family (510–588), _ai_family (591–610), _seo_family (613–628), _onsite_family (631–636), _merge_answer_readiness_executive_findings (639–664), _dedupe_executive_root_causes (667–695), _apply_recommendation_tracking (698–707), _normalize_manual_ai_snapshot (710–820), _active_manual_ai_json (758–768).

**Establish:** Does this report segment preserve observation identity and avoid unsupported completeness?

Tasks:

- Trace source selection, domain/run IDs, dates, snapshot fields, missing-data handling and publication/read paths in the listed symbols. Check serialization, legacy fallbacks and mutable overlays. Record expected-execution questions for C04 and parity checks for I04.
- Trace one ordinary case and one relevant counterexample through the listed code; record expected versus actual behavior. Use an isolated probe when executable; otherwise record the static evidence and verification limit.
- Record findings, caller links and exact coverage. Resolve enclosing definitions and carry unresolved cross-file questions to the assigned comparison/integration run.

**Completion evidence:** file/line references, input/condition, observed or inferred result, applicable invariant, and explicit status. At the last window of any split file, reconcile the whole file.

### B045 — 16. Pulse report collection and immutable sessions

Files/windows:

- `pulse-app/reports/web_report.py` — lines 801–961

Navigation anchors: _normalize_manual_ai_snapshot (710–820), prepare_report_view (823–961).

**Establish:** Does this report segment preserve observation identity and avoid unsupported completeness?

Tasks:

- Trace source selection, domain/run IDs, dates, snapshot fields, missing-data handling and publication/read paths in the listed symbols. Check serialization, legacy fallbacks and mutable overlays. Record expected-execution questions for C04 and parity checks for I04.
- Trace one ordinary case and one relevant counterexample through the listed code; record expected versus actual behavior. Use an isolated probe when executable; otherwise record the static evidence and verification limit.
- Record findings, caller links and exact coverage. Resolve enclosing definitions and carry unresolved cross-file questions to the assigned comparison/integration run.

**Completion evidence:** file/line references, input/condition, observed or inferred result, applicable invariant, and explicit status. At the last window of any split file, reconcile the whole file.

### B046 — 16. Pulse report collection and immutable sessions

Files/windows:

- `pulse-app/services/report_data.py`

**Establish:** Does report-data collection preserve the intended run and domain identity?

Tasks:

- Trace execution selection, joins and missing/legacy linkage through report_data; compare requested refresh identity with selected latest audit and matching crawl.
- Trace one ordinary case and one relevant counterexample through the listed code; record expected versus actual behavior. Use an isolated probe when executable; otherwise record the static evidence and verification limit.
- Record findings, caller links and exact coverage. Resolve enclosing definitions and carry unresolved cross-file questions to the assigned comparison/integration run.

**Completion evidence:** file/line references, input/condition, observed or inferred result, applicable invariant, and explicit status. At the last window of any split file, reconcile the whole file.

### B047 — 17. Pulse findings, history and prioritization

Files/windows:

- `pulse-app/reports/prioritization.py`
- `pulse-app/reports/pulse_history.py`

**Establish:** Can history or prioritization turn missing evidence into improvement?

Tasks:

- Check finding keys, missing-versus-resolved rules, baseline/current comparisons, deduplication, exposure factors, zero nonissue scores and material-event counts.
- Trace one ordinary case and one relevant counterexample through the listed code; record expected versus actual behavior. Use an isolated probe when executable; otherwise record the static evidence and verification limit.
- Record findings, caller links and exact coverage. Resolve enclosing definitions and carry unresolved cross-file questions to the assigned comparison/integration run.

**Completion evidence:** file/line references, input/condition, observed or inferred result, applicable invariant, and explicit status. At the last window of any split file, reconcile the whole file.

### B048 — 17. Pulse findings, history and prioritization

Files/windows:

- `pulse-app/reports/report_intelligence.py`

**Establish:** Are conclusions, confidence and recommended work supported by evidence?

Tasks:

- Trace report-intelligence inputs, root-cause grouping, priority claims and required finding fields. Distinguish implemented recommendations from verified outcomes.
- Trace one ordinary case and one relevant counterexample through the listed code; record expected versus actual behavior. Use an isolated probe when executable; otherwise record the static evidence and verification limit.
- Record findings, caller links and exact coverage. Resolve enclosing definitions and carry unresolved cross-file questions to the assigned comparison/integration run.

**Completion evidence:** file/line references, input/condition, observed or inferred result, applicable invariant, and explicit status. At the last window of any split file, reconcile the whole file.

### B050 — 18. Pulse report presentation and export

Files/windows:

- `pulse-app/reports/__init__.py`
- `pulse-app/reports/full_pdf.py`

**Establish:** Does PDF generation reproduce the saved observation safely?

Tasks:

- Trace report/session selection, conversion options, local/network resource access, temporary files, subprocess failures and output parity; inspect report package exports.
- Trace one ordinary case and one relevant counterexample through the listed code; record expected versus actual behavior. Use an isolated probe when executable; otherwise record the static evidence and verification limit.
- Record findings, caller links and exact coverage. Resolve enclosing definitions and carry unresolved cross-file questions to the assigned comparison/integration run.

**Completion evidence:** file/line references, input/condition, observed or inferred result, applicable invariant, and explicit status. At the last window of any split file, reconcile the whole file.

### B051 — 18. Pulse report presentation and export

Files/windows:

- `pulse-app/reports/localization.py`

**Establish:** Does localization preserve observation meaning and identity?

Tasks:

- Check locale selection, fallback, status/number/date formatting and whether translation changes evidence, IDs, links or confidence.
- Trace one ordinary case and one relevant counterexample through the listed code; record expected versus actual behavior. Use an isolated probe when executable; otherwise record the static evidence and verification limit.
- Record findings, caller links and exact coverage. Resolve enclosing definitions and carry unresolved cross-file questions to the assigned comparison/integration run.

**Completion evidence:** file/line references, input/condition, observed or inferred result, applicable invariant, and explicit status. At the last window of any split file, reconcile the whole file.

### B052 — 18. Pulse report presentation and export

Files/windows:

- `pulse-app/reports/localization_es_detectors.py`

**Establish:** Can Spanish detector translations change the technical conclusion?

Tasks:

- Compare detector keys and status-sensitive phrases against their source meanings; check missing translations, interpolation and unsupported stronger claims.
- Trace one ordinary case and one relevant counterexample through the listed code; record expected versus actual behavior. Use an isolated probe when executable; otherwise record the static evidence and verification limit.
- Record findings, caller links and exact coverage. Resolve enclosing definitions and carry unresolved cross-file questions to the assigned comparison/integration run.

**Completion evidence:** file/line references, input/condition, observed or inferred result, applicable invariant, and explicit status. At the last window of any split file, reconcile the whole file.

### B053 — 18. Pulse report presentation and export

Files/windows:

- `pulse-app/reports/observation_export.py`
- `pulse-app/services/report_collaboration.py`
- `pulse-app/static/analysis-markdown.js`
- `pulse-app/static/collapsible-notes.js`

**Establish:** Are exports and collaboration safely separated from immutable evidence?

Tasks:

- Trace export quality gates and field parity; verify note/reply/interpretation permissions and domain/report binding. Inspect Markdown escaping and browser interaction state.
- Trace one ordinary case and one relevant counterexample through the listed code; record expected versus actual behavior. Use an isolated probe when executable; otherwise record the static evidence and verification limit.
- Record findings, caller links and exact coverage. Resolve enclosing definitions and carry unresolved cross-file questions to the assigned comparison/integration run.

**Completion evidence:** file/line references, input/condition, observed or inferred result, applicable invariant, and explicit status. At the last window of any split file, reconcile the whole file.

### B054 — 18. Pulse report presentation and export

Files/windows:

- `pulse-app/static/skins/default.css`

**Establish:** Can skin styling obscure or misrepresent evidence?

Tasks:

- Check readable status distinctions, long content, print behavior and CSS assumptions; ensure skin errors do not hide essential report content or controls.
- Trace one ordinary case and one relevant counterexample through the listed code; record expected versus actual behavior. Use an isolated probe when executable; otherwise record the static evidence and verification limit.
- Record findings, caller links and exact coverage. Resolve enclosing definitions and carry unresolved cross-file questions to the assigned comparison/integration run.

**Completion evidence:** file/line references, input/condition, observed or inferred result, applicable invariant, and explicit status. At the last window of any split file, reconcile the whole file.

### B055 — 18. Pulse report presentation and export

Files/windows:

- `pulse-app/templates/full_report.html` — lines 1–400

Navigation anchors: line 2: {% block title %}{{ site.domain }} · Living Domain Pulse{% endblock %}; line 3: {% block content %}; line 5: {% macro note_marker(note_key) -%}; line 12: {% macro note_panel(note_key, label="Pablo's note", compact=True) -%}; line 51: {% macro llm_guidance_evidence(llm_sources) -%}; line 54: llms.txt evidence.

**Establish:** Does this report-template segment present saved evidence faithfully and safely?

Tasks:

- Inventory each visible section and bind its displayed claim, status, count, date, link and action to its input field and source. Check escaping, absent/partial states, history/current context and locale/export differences; identify whether data comes from the snapshot or a mutable overlay.
- Trace one ordinary case and one relevant counterexample through the listed code; record expected versus actual behavior. Use an isolated probe when executable; otherwise record the static evidence and verification limit.
- Record findings, caller links and exact coverage. Resolve enclosing definitions and carry unresolved cross-file questions to the assigned comparison/integration run.

**Completion evidence:** file/line references, input/condition, observed or inferred result, applicable invariant, and explicit status. At the last window of any split file, reconcile the whole file.

### B056 — 18. Pulse report presentation and export

Files/windows:

- `pulse-app/templates/full_report.html` — lines 401–800

Navigation anchors: template data bindings, conditions and controls in the listed window.

**Establish:** Does this report-template segment present saved evidence faithfully and safely?

Tasks:

- Inventory each visible section and bind its displayed claim, status, count, date, link and action to its input field and source. Check escaping, absent/partial states, history/current context and locale/export differences; identify whether data comes from the snapshot or a mutable overlay.
- Trace one ordinary case and one relevant counterexample through the listed code; record expected versus actual behavior. Use an isolated probe when executable; otherwise record the static evidence and verification limit.
- Record findings, caller links and exact coverage. Resolve enclosing definitions and carry unresolved cross-file questions to the assigned comparison/integration run.

**Completion evidence:** file/line references, input/condition, observed or inferred result, applicable invariant, and explicit status. At the last window of any split file, reconcile the whole file.

### B057 — 18. Pulse report presentation and export

Files/windows:

- `pulse-app/templates/full_report.html` — lines 801–1200

Navigation anchors: line 890: Your visibility and website report; line 925: {{ opening_note.get('content') or executive_finding.get('title') or 'Current observations are availa; line 937: High-signal findings; line 956: Highest-value actions; line 991: What does Benefit-to-fix mean? A qualitative explanation of the likely practical value of resolving ; line 1030: {{ report.check_history_index|tojson }}; line 1039: {{ family.name }} {{ note_marker(family_note_key) }}; line 1057: SITEMAP RECONCILIATION Sitemap URL evidence; line 1069: AI RESPONSE SOURCE Manual AI response evidence; line 1082: AI RESPONSE ANALYSIS Model interpretation; line 1090: Human interpretation; line 1113: Confirmed findings.

**Establish:** Does this report-template segment present saved evidence faithfully and safely?

Tasks:

- Inventory each visible section and bind its displayed claim, status, count, date, link and action to its input field and source. Check escaping, absent/partial states, history/current context and locale/export differences; identify whether data comes from the snapshot or a mutable overlay.
- Trace one ordinary case and one relevant counterexample through the listed code; record expected versus actual behavior. Use an isolated probe when executable; otherwise record the static evidence and verification limit.
- Record findings, caller links and exact coverage. Resolve enclosing definitions and carry unresolved cross-file questions to the assigned comparison/integration run.

**Completion evidence:** file/line references, input/condition, observed or inferred result, applicable invariant, and explicit status. At the last window of any split file, reconcile the whole file.

### B058 — 18. Pulse report presentation and export

Files/windows:

- `pulse-app/templates/full_report.html` — lines 1201–1600

Navigation anchors: line 1201: {% if family.dataforseo_snapshots %} DataForSEO evidence captured This report includes {{ family.dat; line 1202: 6.1 Organic Search Performance; line 1207: 6.2 Search Opportunities Striking Distance Keywords {% if family.striking_distance %} Query Page Lat; line 1208: 6.3 Cannibalization Exact-query cannibalization {% if family.exact_cannibalization %} Query Ranking ; line 1209: 6.4 Content Decay DATA_UNAVAILABLE Content Decay is not persisted in the current observation.; line 1210: 6.5 Rank Tracking {% if family.rank_tracking %} Keyword Last position Previous Best URL Last checked; line 1211: 6.6 Keyword Demand {% if family.wanted %} Wanted keyword Target page Monthly searches Competition So; line 1212: 6.7 Competitive Search Gaps {% if family.competitor_keywords %} Competitor Keyword Position Volume D; line 1213: 6.8 Backlinks & Search Authority {% if family.domain_metrics %} DR {{ family.domain_metrics.dr or '—; line 1214: 6.9 Audience / Search Performance Context {% if family.clarity %} {{ family.clarity.data }} {% else ; line 1225: About this report; line 1325: .

**Establish:** Does this report-template segment present saved evidence faithfully and safely?

Tasks:

- Inventory each visible section and bind its displayed claim, status, count, date, link and action to its input field and source. Check escaping, absent/partial states, history/current context and locale/export differences; identify whether data comes from the snapshot or a mutable overlay.
- Trace one ordinary case and one relevant counterexample through the listed code; record expected versus actual behavior. Use an isolated probe when executable; otherwise record the static evidence and verification limit.
- Record findings, caller links and exact coverage. Resolve enclosing definitions and carry unresolved cross-file questions to the assigned comparison/integration run.

**Completion evidence:** file/line references, input/condition, observed or inferred result, applicable invariant, and explicit status. At the last window of any split file, reconcile the whole file.

### B059 — 18. Pulse report presentation and export

Files/windows:

- `pulse-app/templates/full_report.html` — lines 1601–2000

Navigation anchors: template data bindings, conditions and controls in the listed window.

**Establish:** Does this report-template segment present saved evidence faithfully and safely?

Tasks:

- Inventory each visible section and bind its displayed claim, status, count, date, link and action to its input field and source. Check escaping, absent/partial states, history/current context and locale/export differences; identify whether data comes from the snapshot or a mutable overlay.
- Trace one ordinary case and one relevant counterexample through the listed code; record expected versus actual behavior. Use an isolated probe when executable; otherwise record the static evidence and verification limit.
- Record findings, caller links and exact coverage. Resolve enclosing definitions and carry unresolved cross-file questions to the assigned comparison/integration run.

**Completion evidence:** file/line references, input/condition, observed or inferred result, applicable invariant, and explicit status. At the last window of any split file, reconcile the whole file.

### B060 — 18. Pulse report presentation and export

Files/windows:

- `pulse-app/templates/full_report.html` — lines 2001–2044

Navigation anchors: template data bindings, conditions and controls in the listed window.

**Establish:** Does this report-template segment present saved evidence faithfully and safely?

Tasks:

- Inventory each visible section and bind its displayed claim, status, count, date, link and action to its input field and source. Check escaping, absent/partial states, history/current context and locale/export differences; identify whether data comes from the snapshot or a mutable overlay. Finish with a whole-template synthesis of section conditions, scripts, links and export controls.
- Trace one ordinary case and one relevant counterexample through the listed code; record expected versus actual behavior. Use an isolated probe when executable; otherwise record the static evidence and verification limit.
- Record findings, caller links and exact coverage. Resolve enclosing definitions and carry unresolved cross-file questions to the assigned comparison/integration run.

**Completion evidence:** file/line references, input/condition, observed or inferred result, applicable invariant, and explicit status. At the last window of any split file, reconcile the whole file.

### B061 — 18. Pulse report presentation and export

Files/windows:

- `pulse-app/templates/public_report_access.html`
- `pulse-app/templates/reports.html`

**Establish:** Do report navigation and public access expose only intended observations?

Tasks:

- Trace report/session/domain identifiers, token/password flow, expired/revoked access, historical links and empty/error states.
- Trace one ordinary case and one relevant counterexample through the listed code; record expected versus actual behavior. Use an isolated probe when executable; otherwise record the static evidence and verification limit.
- Record findings, caller links and exact coverage. Resolve enclosing definitions and carry unresolved cross-file questions to the assigned comparison/integration run.

**Completion evidence:** file/line references, input/condition, observed or inferred result, applicable invariant, and explicit status. At the last window of any split file, reconcile the whole file.

### B062 — 19. Pulse research and operator UI

Files/windows:

- `pulse-app/static/app.css`

**Establish:** Does operator styling keep state and controls understandable?

Tasks:

- Check overflow, hidden content, focus/disabled states, contrast of error/coverage labels and desktop/mobile readability of dense evidence.
- Trace one ordinary case and one relevant counterexample through the listed code; record expected versus actual behavior. Use an isolated probe when executable; otherwise record the static evidence and verification limit.
- Record findings, caller links and exact coverage. Resolve enclosing definitions and carry unresolved cross-file questions to the assigned comparison/integration run.

**Completion evidence:** file/line references, input/condition, observed or inferred result, applicable invariant, and explicit status. At the last window of any split file, reconcile the whole file.

### B063 — 19. Pulse research and operator UI

Files/windows:

- `pulse-app/static/nav-keyword-links.js`
- `pulse-app/static/sortable.js`
- `pulse-app/static/taxonomy.js`
- `pulse-app/templates/base.html`

**Establish:** Do shared navigation and browser helpers preserve route and data identity?

Tasks:

- Trace template URL construction, keyword links, sorting, taxonomy edits, JS initialization and escaping; confirm mutations surface failures and apply to the intended domain.
- Trace one ordinary case and one relevant counterexample through the listed code; record expected versus actual behavior. Use an isolated probe when executable; otherwise record the static evidence and verification limit.
- Record findings, caller links and exact coverage. Resolve enclosing definitions and carry unresolved cross-file questions to the assigned comparison/integration run.

**Completion evidence:** file/line references, input/condition, observed or inferred result, applicable invariant, and explicit status. At the last window of any split file, reconcile the whole file.

### B064 — 19. Pulse research and operator UI

Files/windows:

- `pulse-app/templates/domain_delete.html`
- `pulse-app/templates/domain_new.html`
- `pulse-app/templates/domain_settings.html`
- `pulse-app/templates/empty.html`

**Establish:** Are domain creation, settings and deletion safe and intelligible?

Tasks:

- Check form fields against handlers, CSRF, normalization errors, secret handling, destructive confirmation and stale domain identifiers.
- Trace one ordinary case and one relevant counterexample through the listed code; record expected versus actual behavior. Use an isolated probe when executable; otherwise record the static evidence and verification limit.
- Record findings, caller links and exact coverage. Resolve enclosing definitions and carry unresolved cross-file questions to the assigned comparison/integration run.

**Completion evidence:** file/line references, input/condition, observed or inferred result, applicable invariant, and explicit status. At the last window of any split file, reconcile the whole file.

### B065 — 19. Pulse research and operator UI

Files/windows:

- `pulse-app/templates/keyword_workspace.html`
- `pulse-app/templates/keywords.html`
- `pulse-app/templates/keywords_dashboard.html`
- `pulse-app/templates/overview.html`

**Establish:** Do keyword workspaces report the same entities and metrics as their handlers?

Tasks:

- Trace filters, assignment/taxonomy controls, sorting, dates, missing-data labels, empty states and mutations across the four views.
- Trace one ordinary case and one relevant counterexample through the listed code; record expected versus actual behavior. Use an isolated probe when executable; otherwise record the static evidence and verification limit.
- Record findings, caller links and exact coverage. Resolve enclosing definitions and carry unresolved cross-file questions to the assigned comparison/integration run.

**Completion evidence:** file/line references, input/condition, observed or inferred result, applicable invariant, and explicit status. At the last window of any split file, reconcile the whole file.

### B066 — 19. Pulse research and operator UI

Files/windows:

- `pulse-app/templates/page.html`
- `pulse-app/templates/page_workspace.html`
- `pulse-app/templates/pages.html`
- `pulse-app/templates/research.html`

**Establish:** Can page and research workflows silently lose or misassign work?

Tasks:

- Trace page/domain/keyword identities, imports/exports, pagination, assignment/note actions and error recovery across page and research views.
- Trace one ordinary case and one relevant counterexample through the listed code; record expected versus actual behavior. Use an isolated probe when executable; otherwise record the static evidence and verification limit.
- Record findings, caller links and exact coverage. Resolve enclosing definitions and carry unresolved cross-file questions to the assigned comparison/integration run.

**Completion evidence:** file/line references, input/condition, observed or inferred result, applicable invariant, and explicit status. At the last window of any split file, reconcile the whole file.

### B067 — 19. Pulse research and operator UI

Files/windows:

- `pulse-app/templates/tools.html`
- `pulse-app/templates/wanted.html`

**Establish:** Do tools and wanted-keyword actions perform the work their UI promises?

Tasks:

- Compare forms and links with route contracts, validation, mutation permissions, empty/error states and request-time side effects.
- Trace one ordinary case and one relevant counterexample through the listed code; record expected versus actual behavior. Use an isolated probe when executable; otherwise record the static evidence and verification limit.
- Record findings, caller links and exact coverage. Resolve enclosing definitions and carry unresolved cross-file questions to the assigned comparison/integration run.

**Completion evidence:** file/line references, input/condition, observed or inferred result, applicable invariant, and explicit status. At the last window of any split file, reconcile the whole file.

## Comparison runs

These deliberately revisit implementations. Use their listed prerequisites and compare related files in small subpasses. Start alongside the flow schedule and close after all prerequisites are reviewed.

## C01. Web/worker domain parity

Compare normalization, imported site fields, case/IDNA/ports, suppression and sync side effects. Exercise the same domain fixtures through both paths. Record intended differences; do not assume matching names imply identical contracts.

Prerequisite primary coverage: B008, B009, B010, B011, B012, B013, B016, B021, B023.

Files:
- `pulse-app/app.py`
- `pulse-app/services/domain_registry.py`
- `pulse-app/services/url_policy.py`
- `pulse-app/jobs/workflows.py`

Required counterexample/check: Submit uppercase/IDNA/port variants through both web and worker paths; compare canonical identity and synced fields.

Completion: document actual callers, contract differences, check results and uncertainty. Status: planned.

## C02. Audit persistence duplication and reachability

Trace audit_worker and both persistence/aggregation implementations. Establish callers across all scoped source, decorators and callbacks before calling a chain dead. Compare SQL, transactions, errors and summary denominators.

Prerequisite primary coverage: B008, B009, B010, B011, B012, B013, B019, B021, B035.

Files:
- `pulse-app/app.py`
- `pulse-app/services/audit_execution.py`
- `pulse-app/jobs/handlers.py`
- `pulse-app/jobs/workflows.py`

Required counterexample/check: Feed the same isolated audit result into each reachable persistence path; compare stored signals, aggregate denominators and transaction failure behavior.

Completion: document actual callers, contract differences, check results and uncertainty. Status: planned.

## C03. Manual AI storage, projection and governance

Compare four stored phase/state combinations with the two active report states; validate provider/question denominators and stale analysis. Establish actual callers for cross_model/question_governance; distinguish dormant schema/API from active product behavior.

Prerequisite primary coverage: B008, B009, B010, B011, B012, B013, B038, B039, B040, B043, B044, B045.

Files:
- `pulse-app/services/manual_ai_sources.py`
- `pulse-app/services/manual_ai_report.py`
- `pulse-app/services/manual_ai_payload.py`
- `pulse-app/reports/question_governance.py`
- `pulse-app/reports/cross_model.py`
- `pulse-app/reports/web_report.py`
- `pulse-app/app.py`

Required counterexample/check: Omit one provider answer and change retrieval state; compare raw storage, completeness indicators and the report projection without counting unavailable answers as agreement.

Completion: document actual callers, contract differences, check results and uncertainty. Status: planned.

## C04. Publication mechanisms and execution identity

Enumerate every caller of create_report_session and publish_report_if_owned, across in-scope production code. Test publish=True versus staged publication. Interleave two domain refreshes and prove collection uses the intended execution, not merely a coherent latest audit/crawl pair.

Prerequisite primary coverage: B021, B043, B044, B045, B046.

Files:
- `pulse-app/reports/web_report.py`
- `pulse-app/jobs/publication.py`
- `pulse-app/jobs/workflows.py`
- `pulse-app/services/report_data.py`

Required counterexample/check: Pause refresh A after capture, complete refresh B, resume A; trace each report component to expected execution and verify lease loss prevents A from publishing.

Completion: document actual callers, contract differences, check results and uncertainty. Status: planned.

## C05. Parallel HTTP capture and parsing

Compare crawler and audit requests, robots behavior, supporting files, MIME/redirect limits, timestamps, hashing and parsing. Test a page changing between captures; identify which evidence supports each claim. Separate configured provider HTTP clients from arbitrary-URL fetching.

Prerequisite primary coverage: B023, B024, B028, B029, B030, B031, B032, B033, B034, B035.

Files:
- `pulse-app/crawlers/seo.py`
- `pulse-app/audits/geo_aeo/engine.py`
- `pulse-app/audits/geo_aeo/service.py`
- `pulse-app/services/page_discovery.py`
- `pulse-app/services/safe_fetcher.py`
- `pulse-app/services/resource_outcome.py`

Required counterexample/check: Serve different page bodies on crawl and audit requests and record timestamps/hashes; verify which capture each reported claim actually references.

Completion: document actual callers, contract differences, check results and uncertainty. Status: planned.

## C06. Wrappers, aliases and alternate entry paths

Classify delegates versus substantive duplicates. Trace sitemap compatibility helpers, extended_sources enrichment, source detection and aliases. Search all scoped templates/JS plus imports and callbacks; unresolved dynamic references remain uncertain.

Prerequisite primary coverage: B008, B009, B010, B011, B012, B013, B016, B018, B024, B041.

Files:
- `pulse-app/app.py`
- `pulse-app/services/source_inventory.py`
- `pulse-app/services/domain_company.py`
- `pulse-app/services/page_discovery.py`
- `pulse-app/reports/extended_sources.py`
- `pulse-app/integrations/opengsc_adapter.py`

Required counterexample/check: Trace an apparent duplicate by imports, registrations, templates, callbacks and jobs; distinguish a delegate from independent behavior before making a duplication/dead-code claim.

Completion: document actual callers, contract differences, check results and uncertainty. Status: planned.

## C07. Configuration, startup and filesystem parity

Create configuration table for RESEARCH_DB/SEO_DB/REPORTS_DIR/skin/provider/security settings across entry points. Check env unset/set/malformed and concurrent startup without executing migrations. Verify skin/temp/export paths, domain deletion, traversal, atomic writes and cleanup. app.py and workflows currently have different fallback RESEARCH_DB paths; assess launch-dependent impact.

Prerequisite primary coverage: B002, B003, B008, B009, B010, B011, B012, B013, B016, B019, B021, B053.

Files:
- `pulse-app/app.py`
- `pulse-app/Dockerfile`
- `pulse-app/entrypoint.sh`
- `pulse-app/jobs/worker.py`
- `pulse-app/jobs/workflows.py`
- `pulse-app/services/domain_skin.py`
- `pulse-app/reports/observation_export.py`

Required counterexample/check: Unset RESEARCH_DB in isolated web/worker configuration resolution, then set it explicitly; compare resolved paths and report the launch conditions under which they diverge.

Completion: document actual callers, contract differences, check results and uncertainty. Status: planned.

## C08. Ownership, contracts and route completeness

Reconcile registered table owners with actual scoped modules/writers. Enumerate nested registered routes as well as top-level app routes. Check indirect GET network work, route-method conflicts and contract assertions; validate coverage from production registrations directly.

Prerequisite primary coverage: B007, B008, B009, B010, B011, B012, B013, B016, B028, B029, B030, B031, B041.

Files:
- `pulse-app/db/ownership.py`
- `pulse-app/reports/REPORT_CONTRACT.md`
- `pulse-app/app.py`
- `pulse-app/crawlers/seo.py`
- `pulse-app/integrations/dataforseo/extension.py`
- `pulse-app/services/domains.py`

Required counterexample/check: Compare recursive static route declarations with runtime URL-map output; nested crawler/DataForSEO registrations must remain visible even without architectural tests.

Completion: document actual callers, contract differences, check results and uncertainty. Status: planned.

## Integration and final reconciliation runs

### I01 — Authorization across all routes

Prerequisites: B008–B013, B015, C08.

Tasks: Reconcile the 93 declared registrations below with runtime URL-map output when available; include nested registrations, implicit HEAD/OPTIONS and static routes. For every method check management/client/anonymous behavior, CSRF, domain isolation, public tokens/passwords, revocation and export permissions. Record each row as checked, inapplicable with reason, or blocked.

Output: evidence, actual probe results, affected route/job rows, findings and unverified cases. Status: planned.

### I02 — Worker lifecycle and concurrency

Prerequisites: B019, B021, C02, C04.

Tasks: Exercise all seven handler types below. Check atomic claims, lease expiry/loss, heartbeat, retries, idempotency, pause/cancel/resume and process death. Interleave refreshes and confirm stale workers cannot write or publish. Trace direct subworkflow calls and scheduled follow-up jobs.

Output: evidence, actual probe results, affected route/job rows, findings and unverified cases. Status: planned.

### I03 — Capture and evidence consistency

Prerequisites: B023–B035, C05.

Tasks: Trace discovery → frontier → crawl → separate audit capture → persisted evidence. Probe redirects, robots denial/unavailability, failed fetches, changing content, unavailable evidence and page eligibility. Verify execution IDs, timestamps and coverage denominators, including publication withholding.

Output: evidence, actual probe results, affected route/job rows, findings and unverified cases. Status: planned.

### I04 — Report snapshots, history and delivery

Prerequisites: B043–B061, C04.

Tasks: Compare the same observation across HTML, JSON, CSV and PDF and supported locales. Change current source data and add notes/interpretation; confirm historical evidence and baseline/current semantics. Check finding identity, missing versus resolved, deduplication, priorities and report-quality export blocking.

Output: evidence, actual probe results, affected route/job rows, findings and unverified cases. Status: planned.

### I05 — Manual AI lifecycle

Prerequisites: B038–B040, C03.

Tasks: Ingest valid/malformed/partial answers and citations; check phase/state/provider/question completeness. Run isolated analysis with a stub provider, change its source while analysis is pending, and verify stale-result protection. Confirm report snapshot behavior and distinguish model-prior from retrieval evidence.

Output: evidence, actual probe results, affected route/job rows, findings and unverified cases. Status: planned.

### I06 — External adapter contracts

Prerequisites: B018, B041–B042, C06.

Tasks: Use newly constructed local contract data for OpenGSC and stubbed DataForSEO/analysis responses. Check read-only database access, absent/incompatible tables, site isolation, date windows, missing versus zero, provider errors, credentials, kill switches and request/cost controls. Do not audit provider internals or claim live correctness.

Output: evidence, actual probe results, affected route/job rows, findings and unverified cases. Status: planned.

### I07 — Current configuration and filesystem

Prerequisites: B001, B002, B003, B007, B016, C07.

Tasks: Inspect actual configuration resolution in web and worker paths, especially RESEARCH_DB defaults. Compare current schema assumptions with a read-only schema dump if supplied; otherwise qualify database-state uncertainty. Probe skin/export paths, traversal, permissions, atomic writes, concurrent access and cleanup/deletion using temporary directories. Do not run or review migration implementations.

Output: evidence, actual probe results, affected route/job rows, findings and unverified cases. Status: planned.

### I08 — Final reconciliation

Prerequisites: All retained B runs, C01–C08, I01–I07.

Tasks: Confirm every retained file/window has an outcome, all route rows and seven handlers have dispositions, and every contract check below has evidence or a recorded gap. Reconcile duplication and reachability claims, remove duplicate findings and update architecture based on verified behavior. State runtime/database access limits. Do not claim test-suite quality, upgrade safety, fresh-install reliability or certification of outside components.

Output: evidence, actual probe results, affected route/job rows, findings and unverified cases. Status: planned.

## Required report-contract checks

Read `pulse-app/reports/REPORT_CONTRACT.md` as required context. Ranges below refer only to retained runs; excluded runs never add work.

| Requirement | Owning review |
| --- | --- |
| FAIL/PARTIAL versus MANUAL_REVIEW/NOT_APPLICABLE/DATA_UNAVAILABLE; legacy UNKNOWN normalization | B033–B036, B043–B048, I04 |
| Exact page/check identity; missing assessment is not resolution; material-event history and unique-page movements | B047–B048, I04 |
| Implemented versus verified recommendations, root-cause evidence retention and required finding fields | B043–B048, I04 |
| Current/baseline pointer versus immutable observations; completed unchanged monitoring runs | B021, B043–B046, C04, I02, I04 |
| Coverage states and timestamps; GA4 versus Clarity; bounded GSC dates/click labels | B018, B041–B049, I06 |
| Same-execution provenance and limits for legacy data; expected current execution under concurrency | B021, B043–B046, C04, I02–I03 |
| Value-to-fix-v2 factors, missing exposure and zero nonissue scores | B047–B048, I04 |
| Provider/state/question denominators; model-prior versus retrieval; unsupported causal/truth claims | B038–B040, C03, I05 |
| Report-quality errors block relevant exports; HTML/PDF/CSV/JSON agree | B043–B061, I04 |

## Complete route-registration checklist

Static inventory from the pinned source; candidate relationships require confirmation. Each row is an I01 task and belongs to the listed primary run. Empty metadata does not prove no side effects.

| Route | Methods | Endpoint | Source | Run |
| --- | --- | --- | --- | --- |
| / | GET | index | pulse-app/app.py:641 | B009 |
| /domains/new | GET; POST | domain_new | pulse-app/app.py:650 | B009 |
| /d/<domain>/sources | GET; POST | domain_sources | pulse-app/app.py:678 | B009 |
| /d/<domain>/sources/company-name | POST | save_source_company_name | pulse-app/app.py:716 | B009 |
| /d/<domain>/sources/skin | POST | save_domain_skin | pulse-app/app.py:723 | B009 |
| /d/<domain>/sources/report-scope | POST | save_report_scope | pulse-app/app.py:741 | B009 |
| /d/<domain>/sources/applicability | POST | save_domain_applicability | pulse-app/app.py:766 | B009 |
| /d/<domain>/sources/page-type | POST | save_domain_page_type | pulse-app/app.py:776 | B009 |
| /d/<domain>/report-quick-links | POST | save_report_quick_links | pulse-app/app.py:789 | B009 |
| /d/<domain>/sources/client-report-access | POST | save_client_report_access | pulse-app/app.py:805 | B010 |
| /d/<domain>/settings | GET | domain_settings | pulse-app/app.py:825 | B010 |
| /d/<domain>/sources/manual-ai | GET; POST | manual_ai_source | pulse-app/app.py:830 | B010 |
| /d/<domain>/sources/manual-ai/models | GET | manual_ai_analysis_models | pulse-app/app.py:871 | B010 |
| /d/<domain>/sources/manual-ai/analyze | POST | manual_ai_source_analyze | pulse-app/app.py:881 | B010 |
| /d/<domain>/tools | GET | tools | pulse-app/app.py:906 | B010 |
| /d/<domain>/ | GET | overview | pulse-app/app.py:915 | B010 |
| /d/<domain>/pages | GET | pages | pulse-app/app.py:922 | B010 |
| /d/<domain>/page | GET | page | pulse-app/app.py:962 | B010 |
| /d/<domain>/keywords-dashboard | GET | keywords_dashboard | pulse-app/app.py:980 | B010 |
| /d/<domain>/keywords | GET | keywords | pulse-app/app.py:987 | B010 |
| /d/<domain>/export | GET | export_domain | pulse-app/app.py:998 | B010 |
| /d/<domain>/wanted | GET | wanted | pulse-app/app.py:1017 | B010 |
| /d/<domain>/wanted/add | POST | wanted_add | pulse-app/app.py:1146 | B010 |
| /d/<domain>/wanted/<int:keyword_id>/delete | POST | wanted_delete | pulse-app/app.py:1157 | B010 |
| /d/<domain>/research/<int:keyword_id>/save | POST | research_save | pulse-app/app.py:1164 | B010 |
| /d/<domain>/research | GET | research | pulse-app/app.py:1174 | B010 |
| /d/<domain>/research/bulk-save | POST | research_bulk_save | pulse-app/app.py:1208 | B011 |
| /d/<domain>/research/bulk-tag | POST | research_bulk_tag | pulse-app/app.py:1226 | B011 |
| /d/<domain>/research/bulk-delete | POST | research_bulk_delete | pulse-app/app.py:1248 | B011 |
| /d/<domain>/research/upload | POST | research_upload | pulse-app/app.py:1263 | B011 |
| /d/<domain>/research/<int:keyword_id>/edit | POST | research_edit | pulse-app/app.py:1305 | B011 |
| /d/<domain>/research/<int:keyword_id>/delete | POST | research_delete | pulse-app/app.py:1316 | B011 |
| /d/<domain>/pages/sync | POST | pages_sync | pulse-app/app.py:1324 | B011 |
| /d/<domain>/pages/<int:page_id> | GET | page_workspace | pulse-app/app.py:1337 | B011 |
| /d/<domain>/pages/<int:page_id>/wanted/add | POST | page_wanted_add | pulse-app/app.py:1370 | B011 |
| /d/<domain>/pages/<int:page_id>/note | POST | page_note_save | pulse-app/app.py:1422 | B011 |
| /d/<domain>/wanted/<int:keyword_id>/page | POST | wanted_assign_page | pulse-app/app.py:1438 | B011 |
| /d/<domain>/keyword-note | GET | keyword_note_get | pulse-app/app.py:1451 | B011 |
| /d/<domain>/keyword-note | POST | keyword_note_save | pulse-app/app.py:1467 | B011 |
| /d/<domain>/taxonomy/lookup | POST | taxonomy_lookup | pulse-app/app.py:1494 | B011 |
| /d/<domain>/taxonomy/apply | POST | taxonomy_apply | pulse-app/app.py:1514 | B011 |
| /d/<domain>/keyword | GET | keyword_workspace | pulse-app/app.py:1550 | B011 |
| /d/<domain>/keyword/wanted | POST | keyword_wanted_set | pulse-app/app.py:1572 | B011 |
| /d/<domain>/keyword/tag | POST | keyword_tag_change | pulse-app/app.py:1590 | B011 |
| /d/<domain>/keyword/note | POST | keyword_note_page_save | pulse-app/app.py:1612 | B012 |
| /d/<domain>/geo-aeo | GET | geo_aeo_integrated | pulse-app/app.py:1623 | B012 |
| /d/<domain>/geo-aeo/run | POST | geo_aeo_run_domain | pulse-app/app.py:1653 | B012 |
| /d/<domain>/pages/<int:page_id>/geo-aeo/run | POST | geo_aeo_run_page | pulse-app/app.py:1664 | B012 |
| /d/<domain>/pages/<int:page_id>/geo-aeo.json | GET | geo_aeo_page_json | pulse-app/app.py:1673 | B012 |
| /d/<domain>/pages/<int:page_id>/geo-aeo/state | POST | geo_aeo_signal_state | pulse-app/app.py:1692 | B012 |
| /d/<domain>/geo-aeo/report/<int:run_id> | GET | geo_aeo_report | pulse-app/app.py:1713 | B012 |
| /d/<domain>/reports | GET | reports | pulse-app/app.py:1732 | B012 |
| /d/<domain>/reports/full | POST | generate_full_web_report | pulse-app/app.py:1747 | B012 |
| /reports/_static/<path:filename> | GET | public_report_static | pulse-app/app.py:1755 | B012 |
| /d/<domain>/skin.css | GET | domain_skin | pulse-app/app.py:1760 | B012 |
| /reports/<report_id>/access | GET; POST | public_report_access | pulse-app/app.py:1775 | B012 |
| /reports/<report_id>/reply | POST | public_report_note_reply | pulse-app/app.py:1799 | B012 |
| /reports/<report_id> | GET | public_report | pulse-app/app.py:1815 | B012 |
| /reports/<report_id>/export.<fmt> | GET | public_report_export | pulse-app/app.py:1823 | B012 |
| /reports/<report_id>/pdf | GET | public_report_pdf | pulse-app/app.py:1836 | B012 |
| /d/<domain>/report-workflow/exclusion | POST | report_workflow_exclusion | pulse-app/app.py:1844 | B012 |
| /d/<domain>/reports/<report_id>/human-interpretation | POST | save_report_human_interpretation | pulse-app/app.py:1870 | B012 |
| /d/<domain>/report-notes | POST | save_report_note | pulse-app/app.py:1882 | B012 |
| /d/<domain>/report-notes/reply | POST | save_report_note_reply | pulse-app/app.py:1899 | B012 |
| /d/<domain>/report-notes.json | GET | report_notes_json | pulse-app/app.py:1920 | B012 |
| /d/<domain>/reports/<report_id> | GET | report_session_view | pulse-app/app.py:1926 | B012 |
| /d/<domain>/reports/<report_id>/export.<fmt> | GET | report_session_export | pulse-app/app.py:1963 | B012 |
| /d/<domain>/reports/<report_id>/pdf | GET | report_session_pdf | pulse-app/app.py:1989 | B012 |
| /d/<domain>/audit | POST | run_audit | pulse-app/app.py:1995 | B012 |
| /reports/<path:filename> | GET | download_report | pulse-app/app.py:2001 | B013 |
| /api/jobs/<job_id> | GET | durable_job_status | pulse-app/app.py:2035 | B013 |
| /api/jobs | GET | durable_jobs_index | pulse-app/app.py:2043 | B013 |
| /api/jobs/<job_id>/cancel | POST | durable_job_cancel | pulse-app/app.py:2055 | B013 |
| /api/jobs/<job_id>/pause | POST | durable_job_pause | pulse-app/app.py:2069 | B013 |
| /api/jobs/<job_id>/resume | POST | durable_job_resume | pulse-app/app.py:2079 | B013 |
| /d/<domain>/jobs/<job_id>/cancel | POST | domain_job_cancel | pulse-app/app.py:2097 | B013 |
| /d/<domain>/jobs/<job_id>/pause | POST | domain_job_pause | pulse-app/app.py:2104 | B013 |
| /d/<domain>/jobs/<job_id>/resume | POST | domain_job_resume | pulse-app/app.py:2111 | B013 |
| /d/<domain>/crawl | GET | seo_crawl | pulse-app/crawlers/seo.py:1268 | B031 |
| /d/<domain>/crawl/ten-page | GET | ten_page_select | pulse-app/crawlers/seo.py:1358 | B031 |
| /d/<domain>/crawl/ten-page/run | POST | ten_page_run | pulse-app/crawlers/seo.py:1370 | B031 |
| /d/<domain>/crawl/run | POST | seo_crawl_run | pulse-app/crawlers/seo.py:1415 | B031 |
| /d/<domain>/crawl/policy | POST | seo_crawl_policy | pulse-app/crawlers/seo.py:1453 | B031 |
| /d/<domain>/crawl/jobs/<job_id>/pause | POST | seo_crawl_pause | pulse-app/crawlers/seo.py:1484 | B031 |
| /d/<domain>/crawl/jobs/<job_id>/resume | POST | seo_crawl_resume | pulse-app/crawlers/seo.py:1490 | B031 |
| /d/<domain>/crawl/jobs/<job_id>/cancel | POST | seo_crawl_cancel | pulse-app/crawlers/seo.py:1496 | B031 |
| /d/<domain>/crawl/<int:run_id>.json | GET | seo_crawl_status | pulse-app/crawlers/seo.py:1502 | B031 |
| /d/<domain>/extensions/dataforseo | GET | dataforseo_extension | pulse-app/integrations/dataforseo/extension.py:7 | B041 |
| /d/<domain>/extensions/dataforseo/settings | POST | dataforseo_settings | pulse-app/integrations/dataforseo/extension.py:16 | B041 |
| /d/<domain>/extensions/dataforseo/kill-switch | POST | dataforseo_kill_switch | pulse-app/integrations/dataforseo/extension.py:37 | B041 |
| /d/<domain>/extensions/dataforseo/pull-minimal | POST | dataforseo_pull_minimal | pulse-app/integrations/dataforseo/extension.py:46 | B041 |
| /d/<domain>/delete | GET | domain_delete_confirm | pulse-app/services/domains.py:99 | B016 |
| /d/<domain>/delete | POST | domain_delete | pulse-app/services/domains.py:109 | B016 |

## Complete job-handler checklist

Each row is an I02 task. Check payload/domain validation, ownership, replay, cancellation, error/retry and publication for every applicable handler.

| Job type | Handler | Location | Primary runs |
| --- | --- | --- | --- |
| worker.healthcheck | jobs.handlers._healthcheck | pulse-app/jobs/handlers.py:11 | B019 |
| crawl | jobs.workflows.run_crawl | pulse-app/jobs/workflows.py:140 | B021 |
| background_crawl | jobs.workflows.run_background_crawl | pulse-app/jobs/workflows.py:176 | B021 |
| page_discovery | jobs.workflows.run_page_discovery | pulse-app/jobs/workflows.py:289 | B021 |
| geo_aeo_audit | jobs.workflows.run_audit | pulse-app/jobs/workflows.py:266 | B021 |
| manual_ai_analysis | jobs.workflows.run_ai | pulse-app/jobs/workflows.py:350 | B021 |
| report_refresh | jobs.workflows.run_report_refresh | pulse-app/jobs/workflows.py:442 | B021 |

## Inventory and closing criteria

The following list is the authoritative primary scope. Every file is assigned above, including all split-file windows. Context documents are not counted as primary targets.

- `pulse-app/.env.example` — B001
- `pulse-app/Dockerfile` — B002
- `pulse-app/app.py` — B008, B009, B010, B011, B012, B013
- `pulse-app/audits/geo_aeo/engine.py` — B033, B034
- `pulse-app/audits/geo_aeo/service.py` — B035
- `pulse-app/crawlers/seo.py` — B028, B029, B030, B031
- `pulse-app/db/__init__.py` — B003
- `pulse-app/db/ownership.py` — B007
- `pulse-app/db/sqlite.py` — B007
- `pulse-app/entrypoint.sh` — B002
- `pulse-app/integrations/dataforseo/connector.py` — B041
- `pulse-app/integrations/dataforseo/extension.py` — B041
- `pulse-app/integrations/opengsc_adapter.py` — B018
- `pulse-app/jobs/__init__.py` — B019
- `pulse-app/jobs/handlers.py` — B019
- `pulse-app/jobs/publication.py` — B021
- `pulse-app/jobs/store.py` — B019
- `pulse-app/jobs/worker.py` — B019
- `pulse-app/jobs/workflows.py` — B021
- `pulse-app/reports/__init__.py` — B050
- `pulse-app/reports/cross_model.py` — B038
- `pulse-app/reports/extended_sources.py` — B041
- `pulse-app/reports/full_pdf.py` — B050
- `pulse-app/reports/localization.py` — B051
- `pulse-app/reports/localization_es_detectors.py` — B052
- `pulse-app/reports/manual_ai_analysis.py` — B039
- `pulse-app/reports/observation_export.py` — B053
- `pulse-app/reports/prioritization.py` — B047
- `pulse-app/reports/pulse_history.py` — B047
- `pulse-app/reports/question_governance.py` — B039
- `pulse-app/reports/report_intelligence.py` — B048
- `pulse-app/reports/web_report.py` — B043, B044, B045
- `pulse-app/requirements.txt` — B002
- `pulse-app/services/applicability_policy.py` — B035
- `pulse-app/services/audit_execution.py` — B035
- `pulse-app/services/crawl_frontier.py` — B026
- `pulse-app/services/domain_company.py` — B016
- `pulse-app/services/domain_registry.py` — B016
- `pulse-app/services/domain_skin.py` — B016
- `pulse-app/services/domains.py` — B016
- `pulse-app/services/manual_ai_payload.py` — B039
- `pulse-app/services/manual_ai_report.py` — B039
- `pulse-app/services/manual_ai_sources.py` — B040
- `pulse-app/services/page_discovery.py` — B024
- `pulse-app/services/page_types.py` — B035
- `pulse-app/services/public_report_access.py` — B015
- `pulse-app/services/report_collaboration.py` — B053
- `pulse-app/services/report_data.py` — B046
- `pulse-app/services/resource_outcome.py` — B032
- `pulse-app/services/safe_fetcher.py` — B023
- `pulse-app/services/security_boundary.py` — B015
- `pulse-app/services/sitemap_reconciliation.py` — B024
- `pulse-app/services/source_inventory.py` — B041
- `pulse-app/services/url_policy.py` — B023
- `pulse-app/static/analysis-markdown.js` — B053
- `pulse-app/static/app.css` — B062
- `pulse-app/static/collapsible-notes.js` — B053
- `pulse-app/static/nav-keyword-links.js` — B063
- `pulse-app/static/page-geo-aeo.js` — B036
- `pulse-app/static/skins/default.css` — B054
- `pulse-app/static/sortable.js` — B063
- `pulse-app/static/taxonomy.js` — B063
- `pulse-app/templates/base.html` — B063
- `pulse-app/templates/crawl.html` — B032
- `pulse-app/templates/dataforseo.html` — B042
- `pulse-app/templates/domain_delete.html` — B064
- `pulse-app/templates/domain_new.html` — B064
- `pulse-app/templates/domain_settings.html` — B064
- `pulse-app/templates/empty.html` — B064
- `pulse-app/templates/full_report.html` — B055, B056, B057, B058, B059, B060
- `pulse-app/templates/geo_aeo.html` — B036
- `pulse-app/templates/geo_aeo_integrated.html` — B036
- `pulse-app/templates/geo_aeo_report.html` — B036
- `pulse-app/templates/keyword_workspace.html` — B065
- `pulse-app/templates/keywords.html` — B065
- `pulse-app/templates/keywords_dashboard.html` — B065
- `pulse-app/templates/manual_ai_responses.html` — B040
- `pulse-app/templates/overview.html` — B065
- `pulse-app/templates/page.html` — B066
- `pulse-app/templates/page_workspace.html` — B066
- `pulse-app/templates/pages.html` — B066
- `pulse-app/templates/public_report_access.html` — B061
- `pulse-app/templates/reports.html` — B061
- `pulse-app/templates/research.html` — B066
- `pulse-app/templates/sources.html` — B042
- `pulse-app/templates/ten_page_select.html` — B032
- `pulse-app/templates/tools.html` — B067
- `pulse-app/templates/wanted.html` — B067

Close only when all 56 primary runs, eight comparisons and eight integration/reconciliation runs have recorded outcomes. A blocked runtime check is a limitation, never an assumed pass. The final opinion must distinguish reviewed source, observed runtime behavior and unverified current database state.

## Execution ledger — started 18 October 2026

This section records progress against the schedule above. Earlier plan sections describe intended work; this section is observed audit work. No application source was modified.

### Stage 0 — orientation: complete for available source, runtime evidence pending

- The linked handoff on `audit-plan` was fetched and checked against this document. Source is pinned to `5b4148c0e24030494fca8609e0180ab3a4b0fc9d`.
- All 88 in-scope source files have been checked against their Git blob hashes. The two CSS files absent from the initial local snapshot were fetched from that commit and verified; the source set is now complete.
- Read `pulse-app/README.md` and `pulse-app/reports/REPORT_CONTRACT.md`. Inventoried declared Flask routes, including the nested registration sites, and the seven `HANDLERS` entries. Full route-method behavior remains I01 work.
- No production runtime or current database was supplied. No migrations were run. Isolated runtime probes are pending; this environment lacks Flask, so current observations below are source-backed, not behavioral reproductions.

### Stage 1 — early risk pass: in progress

| ID | Status | Source evidence | Next check |
| --- | --- | --- | --- |
| R1 — refresh execution provenance | Suspected high-impact defect, source-backed | `jobs/workflows.py:559–574` calls `collect_report_data(domain, site_id, seo_db, research_db)` without the current job's audit or crawl ID, then labels the new session with `execution_run_id=rid`. `services/report_data.py:80–98` selects the latest completed/partial audit for the domain and its corresponding crawl. An overlapping audit can be selected between refresh A's audit and its collection. `jobs/publication.py` checks that the staged report belongs to A's job but not that its embedded evidence does. | Isolated interleaved two-refresh probe for C04/I02. Verify actual database uniqueness/locking and report-quality gates before confirming impact. |
| R2 — password rotation and session authorization | Suspected medium-impact access defect, source-backed | `app.py:1774–1794` stores authorized report IDs in the signed session after successful password entry. `services/security_boundary.py:168–184` accepts any session containing the report ID while password protection is enabled. `services/public_report_access.py:57–67` changes password hash and `updated_at`, but the boundary does not compare `updated_at` or another authorization generation. An already authorized browser appears to remain authorized after rotation. | Isolated Flask session probe for B015/I01; establish intended password-rotation semantics and test disable/re-enable. Environment currently lacks Flask. |
| R3 — URL fetch boundary | Preliminary positive observation, not a completed audit | `services/safe_fetcher.py` resolves and validates addresses, connects production requests to a selected validated IP, and revalidates each redirect; response sizes and content types are bounded. | Complete B023 with edge cases and isolated transport probes, including malformed ports/hostnames and redirects. |
| R4 — publication lease fence | Preliminary positive observation, not a completed audit | `jobs/publication.py` uses `BEGIN IMMEDIATE`, checks running job/worker/lease and the report's domain/execution ID, then updates the living pointer and publication state in one transaction. | Complete B019/B021/C04/I02; check concurrent acquisition, lease timing and alternate publication callers. |

No B, C or I run is marked complete by these focused reads. Continue Stage 1, then execute Stages 2–7 in the schedule. Findings R1/R2 remain hypotheses until the specified checks or equivalent evidence resolve them.

### Stage 1 probe checkpoint — 20 October 2026

The earlier R1/R2 labels remain for continuity; these probes verify the named function behavior, not the entire Flask/worker flow. The isolated probe script is ephemeral and outside the audit deliverable. It extracts the production function bodies without modifying application code or reading excluded tests/migrations.

- **R1, confirmed selection behavior; end-to-end impact still to establish.** In a temporary SQLite database containing completed audit/crawl pairs for `job-A` and `job-B` under the same domain, executing the actual `collect_report_data` function returned `audit_run_id=2`, `crawl_run_id=2`, `execution_run_id=job-B`, `inputs_linked=True`. The function accepts no expected execution ID. A refresh for A can therefore receive B's evidence if B becomes the latest eligible audit before A collects. The worker call and later staged session code support this path, but an interleaved full workflow and any quality gate remain to be checked before assigning final severity.
- **R2, confirmed middleware behavior; product semantics still to establish.** Executing the actual `_require_public_report_password` function with an enabled password policy whose `updated_at` had changed and a session containing `report-1` returned `None`, permitting the request. The middleware does not compare the session grant with the policy version. This demonstrates that password rotation alone does not invalidate an authorized session at this boundary; full Flask route behavior and intended rotation semantics remain I01 work.
- **Probe limits.** The function bodies ran with narrow stubs for external dependencies, a temporary database with only needed tables, and a simulated Flask request/session. They did not exercise actual HTTP requests, the production database, a live worker, or a full report. No tests or migrations were audited or executed.

B015, B019, B021, B023, B046, C04, I01, I02 and I04 remain open. Next: complete the URL and ownership boundaries, then proceed through the scheduled flow batches.

### Stage 1 boundary checkpoint — 20 October 2026

- **R3, fetch safeguards observed in an isolated probe.** Executing the production `SafeFetcher` class with stubbed DNS and HTTP transport accepted a public destination, rejected a redirect to `127.0.0.1` before making a second request, and rejected a response exceeding the configured byte cap. Source inspection shows that production transport connects to the validated IP with the original hostname used for Host, TLS SNI and certificate verification. An initial URL with port `99999` raises a raw `ValueError` from `parsed.port` instead of `SafeFetchError`. Several callers construct URLs from the domain or catch all exceptions; the reachability and user impact of this edge are unresolved. The probe did not send network requests or prove all URL cases. B023 remains open.
- **R4, publication fence observed in an isolated SQLite probe.** Executing the production `publish_report_if_owned` function rejected a wrong worker and an expired lease, rejected a report from a different execution, left the living report pointer unchanged on those failures, and published a report with a valid owner/lease. The probe used the minimal tables required by this function. Concurrent workers, timing at the lease boundary, other publication paths, and complete workflow behavior remain to be checked in B019/B021/C04/I02.
- These are focused behavioral observations, not completed batch reviews. No app source was changed and no excluded tests or migrations were inspected.

### Stage 1 findings and limits — 20 October 2026

The following are audit findings, not application changes. Severity is provisional until the relevant integration runs close.

| ID | Status / severity / confidence | Trigger and consequence | Evidence and remaining limit |
| --- | --- | --- | --- |
| F01 — wrong execution evidence in refresh report | Confirmed code path; high; high confidence | Two refreshes of one domain overlap. A completes its capture; B completes a newer audit before A assembles. A selects B's audit and crawl, creates a session labelled with A's job ID, and the publication fence can publish it as A's report. This misstates provenance and may make the published report describe the wrong observation. | `jobs/workflows.py:552–583`; `services/report_data.py:80–101`; `reports/web_report.py:352–400`; `jobs/publication.py:39–62`. Isolated SQLite selection returned B's audit/crawl for A's intended assembly; publication probe confirms the fence checks session execution ID, not snapshot audit ID. Full interleaved worker execution and current schema uniqueness remain I02/C04 work. Expected: assembly selects or verifies A's audit/crawl IDs and refuses inconsistent evidence. |
| F02 — password rotation leaves prior browser grant active | Confirmed boundary behavior; medium; high confidence; product intent to confirm | A client authenticates, then the domain password changes. The signed session still contains the report ID and bypasses the new password policy. | `app.py:1774–1794`; `services/security_boundary.py:168–184`; `services/public_report_access.py:57–67`. Isolated execution of the actual boundary function allowed an old grant after policy `updated_at` changed. Full Flask session and revocation expectation remain I01 work. Expected if rotation revokes access: bind grants to policy version. |
| F03 — password check fails open on policy lookup error | Confirmed function behavior; medium conditional; high confidence for the error path | A report row is resolvable but its policy join raises (for example a missing policy table). `access_state_for_report` returns `None`; the security boundary interprets `None` as permission to proceed, and the report route's separate lookup can still resolve the report. | `services/public_report_access.py:31–50`; `services/security_boundary.py:168–178`; `services/report_collaboration.py:25–31`; `app.py:1815–1819`. An isolated SQLite probe with `report_session` present and the policy table absent returned `None` while the report row remained resolvable. Standard container entrypoint runs schema setup before serving (`entrypoint.sh:4`), so reachability in a healthy deployment and actual database state are unverified. Expected: a lookup error should not grant access to a potentially protected report. |
| F04 — compressed inventory expansion is unbounded | Confirmed code path; medium; high confidence | A remote `.gz` sitemap within the five MiB transport cap can expand far beyond it in memory, followed by XML/JSON parsing. A 9,751-byte gzip payload expanded to ten MiB in an isolated standard-library check; this is illustrative, not a measured service failure. | `services/page_discovery.py:34–37,185–193`; `services/safe_fetcher.py:198–215`. No decoded-size cap is applied. Crawler also calls `gzip.decompress` at `crawlers/seo.py:230–236`; inspect transport decompression semantics in B028/C05 before treating that second path as independently reachable. Expected: cap decoded bytes before parsing. |
| F05 — malformed initial port escapes fetch error contract | Confirmed function behavior; low; high confidence; caller impact unverified | `SafeFetcher.resolve_and_validate('https://example.com:99999/')` raises raw `ValueError` from `parsed.port` rather than `SafeFetchError`; callers that only catch the latter do not receive their normal failed-fetch result. | `services/safe_fetcher.py:165–170,308–317`; `crawlers/seo.py:215–255`; `audits/geo_aeo/engine.py:142–151`. An isolated boundary matrix rejected non-HTTP schemes, credentials, localhost, loopback, metadata address and invalid hostname; only this error type differed. Main crawl/audit inputs generally pass `crawl_url_identity`/`audit_target_url` first, so public reachability is not established. |

The R3 public-address, redirect and body-cap checks, and R4 publication ownership checks are positive observations for their tested cases. They do not resolve all B023/B019/B021 cases. No excluded tests or migration implementation were read or executed.

### Stage 2 — runtime foundation, first primary runs

| Run | Status / pinned commit | Actual coverage and trace | Result and limit |
| --- | --- | --- | --- |
| B001 | Complete, static; `5b4148c0e24030494fca8609e0180ab3a4b0fc9d` | Entire six-line `.env.example`; compared with `app.py:35–38`, `jobs/workflows.py:21–22`, `jobs/worker.py:24`, `services/security_boundary.py:42–69`, `Dockerfile:12–18`. Ordinary case: Docker environment sets the research DB and port. Counterexample: direct app invocation without `RESEARCH_DB`. | Example only names `DASHBOARD_PORT`, while the app uses `PORT` (direct launch) and the Docker Gunicorn bind is literal 4018; no database/security variables are documented there. App fallback `/data/dashboard/research.db` differs from worker/Docker `/data/audit/research.db`; direct unconfigured web/worker launches can address different databases. Deployment-specific impact requires C07/I07; no live environment supplied. |
| B002 | Complete, static; same commit | Entire `Dockerfile`, `entrypoint.sh`, `requirements.txt`; startup call sites in `app.py:2116–2118`, `jobs/worker.py:220,236`; no migration internals inspected. Ordinary case: entrypoint's `set -eu` stops on a failed `python -m db.migrate up`, then execs Gunicorn. Counterexample: invoking Gunicorn directly imports `app:app` and skips `__main__` schema validation. | Docker startup defaults align app/worker DB when both use provided environment; Gunicorn bind ignores changed `PORT`. Direct Gunicorn launch lacks an app import-time schema gate. Requirements pin Flask/pytest but range-limit others; reproducibility is not exact. Container startup and filesystem permissions unverified because no supported runtime/mount configuration was supplied; revisit C07/I07. |
| B003 | Complete, static; same commit | Entire `db/__init__.py` (one docstring), plus connection caller context in `db/sqlite.py` and `app.py`. Ordinary and counterexample: importing `db` performs no initialization or writes; real connection and transaction behavior live in `connect_sqlite`. | No defect in this package initializer. Runtime database state unverified; B007/I07 own connection and schema evidence. |
| B007 | Complete for source and isolated connection behavior; same commit | Entire `db/ownership.py` and `db/sqlite.py`; compared actual writers in `services/public_report_access.py`, `services/report_collaboration.py`, `services/domain_company.py` and `reports/web_report.py`. A temporary SQLite probe observed WAL, 30-second busy timeout, foreign keys enabled, rejected a foreign-key violation, and rejected a write on a read-only/query-only connection. | Connection defaults held in the probe. `TABLE_OWNERS` is a declaration with no in-scope runtime consumer; entries such as `domain_company_settings: app.sources` and `report_note: reports.web_report` do not name the current service writers. Treat as stale architecture documentation, not an enforced access-control flaw; reconcile C08. Actual deployed schema, indexes, mount permissions and transaction contention remain I07 limitations. |

### Stage 1 ownership follow-through and completed primary source reviews

| Run | Status / pinned commit | Coverage, ordinary case and counterexample | Result and remaining integration work |
| --- | --- | --- | --- |
| B015 | Complete for assigned source; `5b4148c0e24030494fca8609e0180ab3a4b0fc9d` | Entire `services/security_boundary.py` and `services/public_report_access.py`; management and public report callers in `app.py:1754–1840`, report identity in `services/report_collaboration.py:25–31`. Normal mode rejects absent Basic credentials; reverse-proxy mode requires configured header; public report routes check revocation, optional password and CSRF for writes. Counterexamples F02 rotation and F03 policy lookup error were probed. | F02/F03. `internal` mode intentionally has no app auth; proxy header trust depends on network configuration. Signed session uses a random per-process secret when `PULSE_SECRET_KEY` is absent, making grants unstable across workers/restarts, but no unauthorized grant was shown. Flask request-path and every route disposition remain I01; no Flask runtime in this isolated environment. |
| B019 | Complete for assigned source and focused ownership probe; same commit | Entire `jobs/__init__.py`, `jobs/handlers.py`, `jobs/store.py`, `jobs/worker.py`. Seven handlers mapped: worker healthcheck, crawl, background crawl, page discovery, GEO/AEO audit, manual AI analysis, report refresh. Normal claim uses `BEGIN IMMEDIATE`; heartbeat, stage, terminal writes and recovery test worker/status/lease. Counterexample: expired/wrong owner cannot publish in the isolated publication probe. | The terminal fence holds, but some handlers and audit persistence write results outside it (F06 below). Pausing/cancelling a running job clears its worker/lease; old handler execution is not interrupted. Concurrent claim/recovery, all handler payloads and retry side effects remain I02/C02 work. |
| B021 | Complete for assigned source; same commit | Entire `jobs/publication.py` and `jobs/workflows.py`, with `services/report_data.py`, `reports/web_report.py`, `services/audit_execution.py` caller context. Ordinary refresh with qualifying crawl/audit stages a report and publishes it while lease-owned. Counterexample A/B overlap selects B's evidence for A (F01). Publication probe rejected wrong owner/foreign session. | F01 and F06. `run_audit` calls `reset_audit` before its owner check; `run_audit_pages` persists and finalizes without an owner parameter. `run_ai` error recording also lacks an ownership check and needs I05 assessment. Background scheduling follows publication; alternate direct publishers remain C04. Full workflow concurrency remains I02. |
| B023 | Complete for assigned source and isolated fetch checks; same commit | Entire `services/safe_fetcher.py` and `services/url_policy.py`; crawlers and GEO/AEO caller entry points. Probe accepted a stubbed public DNS answer; rejected file scheme, credentials, localhost, loopback/metadata IP, invalid hostname, private redirect before a second transport call and an oversized body. Counterexample malformed port yielded `ValueError` (F05). | Validated IP is used as the production pool host while original host supplies TLS SNI/cert check and Host header. Source indicates each redirect is revalidated. Actual urllib3 transport, IDNA edge behavior and compressed downstream parsing need I03/C05; the probe substituted DNS/transport and made no network request. |

| Finding | Status / severity / confidence | Reproduction and impact | Correction target / limits |
| --- | --- | --- | --- |
| F06 — audit writes after job ownership loss | Confirmed code path; high; high confidence | `jobs/workflows.py:266–282` resets a run before its owner check. `services/audit_execution.py:117–139` captures each page, writes audit evidence, and marks the audit completed without checking durable job state or worker ID. An isolated execution of the actual `run_audit_pages` body cancelled its job during a simulated page capture; it then inserted page evidence and returned/recorded `completed` while the job stayed `cancelled`. A separate isolated `reset_audit` probe deleted an audit signal while the durable job row was owned by another worker. | Fence reset, per-page writes and final audit status by active owner, including pause/cancel/recovery. The probes used minimal temporary SQLite tables and stubbed the external capture; no live worker concurrency or deployed database was exercised. The final `finish_job` fence prevents stale terminal job status but does not prevent these audit writes. Reconcile retry and report implications in I02/C02. |

### Stage 2 — domain identity and external adapter

| Run | Status / pinned commit | Coverage and check | Result and limit |
| --- | --- | --- | --- |
| B016 | Complete for assigned source; `5b4148c0e24030494fca8609e0180ab3a4b0fc9d` | Entire `services/domain_company.py`, `domain_registry.py`, `domain_skin.py`, `domains.py`; compared `app.py:504–637,716–737,2025–2026`. Isolated skin probe rejected path traversal and invalid domain separators, wrote/read both CSS variants, and deleted them. Normal domain deletion checks active jobs in a transaction; counterexample domain normalization parity below. | F09. Delete logic enumerates tables and ID columns dynamically; actual foreign-key/cascade completeness cannot be established without a current schema. It runs `delete_skin` only after committing database deletion, so a filesystem failure can leave skin files after domain removal; assess operational severity in I07. Domain service and inline app code diverge. |
| B018 | Complete for assigned source and isolated SQLite adapter checks; same commit | Entire `integrations/opengsc_adapter.py`; synthetic daily GSC observations for two sites showed site filtering and a bounded two-day report interval. A legacy inventory lacking `site_id` returned an unrelated page for site A. Normal latest available date, missing/zero distinctions and read-only connection observed from source and B007 probe. | F07/F08 below. Actual external OpenGSC schema and production date/time values unavailable; I06 must determine which legacy branches are reachable. Other adapter queries consistently filter by site or domain when their schema supplies the key. |

| Finding | Status / severity / confidence | Trigger, consequence and evidence | Limit / correction target |
| --- | --- | --- | --- |
| F07 — average rank labelled latest | Confirmed code path; medium; high confidence | `integrations/opengsc_adapter.py:335–348` selects `ROUND(AVG(position),1) latest_position` for each query/page over the bounded window. Synthetic positions 1 (yesterday) and 9 (today) produced `latest_position=5.0`; the latest observation is 9. This value feeds `services/report_data.py` and report keyword evidence. | Use a defined most-recent-day ranking or label the result as window average, with aggregation semantics explained. Current external schema not inspected. |
| F08 — unscoped legacy keyword inventory | Confirmed conditional code path; medium; high confidence | `integrations/opengsc_adapter.py:66–91` omits the site filter if the inventory lacks `site_id`, despite being called with a requested site. A synthetic inventory with only a site B page returned that page for site A. This can mix domains in callers of `gsc_keyword_rows`. | Reachability depends on the actual OpenGSC view schema, which is outside audit scope and unavailable. Fail closed or derive a verifiable site scope for schema variants without `site_id`; I06 owns live contract. |
| F09 — web/worker domain identities diverge | Confirmed code paths; medium; high confidence | `app.py:504–519` retains Unicode/trailing dot and accepts an underscore; `services/domain_registry.py:11–18` uses `domain_hostname`, which converts IDNA to ASCII, removes a trailing dot and rejects invalid labels. Isolated extraction produced `bücher.example` in the web path versus `xn--bcher-kva.example` in the worker path. Web-created domain rows/jobs can be unresolvable by worker `get_site`; invalid aliases can create inconsistent identities. | Actual route/worker interleaving and current domain rows remain C01/I02. Use one canonical identity at both boundaries and on persisted rows. |

### Stage 2 — main application route windows

Read all assigned `app.py` windows against the pinned source; Flask was not installed in the isolated probe runtime. All routes pass through the central `configure_security(app)` hook by registration, with public endpoint exceptions already recorded under B015; nested crawler/deletion/provider registration still awaits I01/I06. The table records primary file-window review, not whole-application integration completion.

| Run | Status / exact coverage | Trace and counterexample | Result / integration link |
| --- | --- | --- | --- |
| B008 | Complete for `app.py:1–400`, pinned commit | Config and DB helpers; manual AI prompt/upload; canonical discovery and GSC wrappers; tag helpers; CSV parsing; OpenGSC export. Ordinary GSC wrapper passes site ID through adapter. Counterexample a legacy inventory without `site_id` returns foreign data (F08). | Web `RESEARCH_DB` fallback differs from worker; CSV upload helper caps individual file at 2 MiB, whereas research CSV route later reads whole upload without a bound. C01/C06/C07/I06 remain. |
| B009 | Complete for `app.py:401–800`, same commit | Inline audit persistence and job enqueue; domain sync/create; index/new-domain/sources/settings routes. Ordinary new-domain POST enqueues discovery; counterexample Unicode domain is persisted in web form but worker normalizes to IDNA (F09). | `audit_worker` has no in-scope caller discovered beyond its definition; its duplicate persistence chain is an unreachable candidate, not proven dead. Reconcile C02. `report_files(domain)` ranks foreign-domain filenames lower but still returns them to the authenticated domain report listing; assess desired management isolation in I01. |
| B010 | Complete for `app.py:801–1200`, same commit | Password settings, manual AI setup/analysis enqueue, pages/keyword/wanted/research views and mutations. Ordinary list queries filter by route domain; counterexample `pages?q=pricing` returns no `/pricing` due to regex pattern `%pricing%` (F11). | F11. Per-domain management is not independently authorized; global management boundary applies. Manual AI parameter cap visible, provider behavior remains B038–B040/I05. |
| B011 | Complete for `app.py:1201–1608`, same commit | Research bulk/upload/edit/delete, page workspace/notes, wanted assignment, taxonomy and keyword actions. Normal page note write checks page/domain. Counterexample crafted foreign `keyword_id` on research-delete strips foreign keyword tags while retaining its keyword row (F10). | F10 also affects bulk tag, taxonomy page assignment and keyword wanted page target. Reconcile with B063/B065/B066/I01 and current foreign keys. |
| B012 | Complete for `app.py:1609–2000`, same commit | GEO/AEO runs, signals, report routes, public view/access/replies/exports, report workflow and notes. Ordinary report-session load checks `(domain, report_id)` and public export resolves the report domain. Counterexample GEO/AEO page JSON looks up `page_id` without domain (F10); signal-state writes likewise lack a page-domain check. | F02/F03/F10. `base.html` hides management navigation for `public_report`; full-report template conditions admin editing on that endpoint. Historical snapshot is copied before view preparation; mutable human notes are loaded separately. C04/I01/I04 remain. |
| B013 | Complete for `app.py:2001–2118`, same commit | Report file download, nested registrations and API/domain job status/control endpoints; direct script startup call. Ordinary domain job route checks job domain before mutating; API job routes use global management auth. Counterexample direct Gunicorn `app:app` bypasses `__main__` schema validation, as B002 notes. | Nested crawler, deletion and DataForSEO routes require I01 route disposition; file download is management-only and uses `send_from_directory`. Current startup invocation remains I07. |

| Finding | Status / severity / confidence | Reproduction and consequence | Limit / correction target |
| --- | --- | --- | --- |
| F10 — route-domain checks omitted on several child-record operations | Confirmed SQL code paths; medium; high confidence | `app.py:1315–1320` deletes `research_keyword_tag` by `keyword_id` before the domain-filtered keyword delete. Temporary SQLite probe used route A with a keyword owned by B: B's keyword remained but its tag was removed. `app.py:1235–1244` bulk-tags unfiltered IDs; `1514–1546` applies a domain A page tag to any submitted page ID; `1572–1586` assigns a wanted keyword to any page ID; `1673–1688` reads the latest audit by page ID without checking page domain; `1692–1709` saves signal state for any page ID. | This is cross-domain data integrity and contextual disclosure under authenticated management, not an unauthenticated tenant boundary. Repeat representative cases against actual routes/constraints in I01; add domain checks to each child selection/mutation. |
| F11 — page search never matches ordinary query | Confirmed query behavior; low; high confidence | `app.py:936–943` feeds `'%'+q+'%'` to custom `sqlite_regexp`, which calls `re.search` rather than SQL LIKE. A temporary SQLite probe with `/pricing` found one row for `pricing` and zero for `%pricing%`. | The result is a broken pages filter, not data loss. Use a consistent REGEXP expression or LIKE operator; full route UI remains B065. |

### Stage 3 — discovery and frontier

| Run | Status / pinned commit | Coverage and check | Result and limit |
| --- | --- | --- | --- |
| B024 | Complete for assigned source and isolated traversal probe; `5b4148c0e24030494fca8609e0180ab3a4b0fc9d` | Entire `services/page_discovery.py` and `services/sitemap_reconciliation.py`. Normal sitemap URL entries normalize to the requested hostname, preserve source/lastmod, deduplicate, and retain child errors; discovery state publication verifies worker lease in the same transaction when worker ID is supplied. Counterexample an index with 50 empty child sitemaps and `max_urls=1` performed 51 fetches; no page entries were collected. | F04 (decoded gzip size) and F12 (fetch count). A failed root raises; a failed child is recorded. Sync upserts pages and retains prior rows rather than deleting a last good set. Read-only route readiness avoids request-time network calls. Live HTTP and current source-evidence tables remain I03. |
| B026 | Complete for assigned source, static; same commit | Entire `services/crawl_frontier.py`; normal candidate normalization removes tracking params, rejects foreign hosts and categorizes eligible/deferred/excluded URLs. Initial selection ranks operator choices then distributes categories, with a bounded target. Background selection applies daily/weekly page budgets, retry and due-date predicates, then template caps. Counterexample a custom-port same-host URL normalizes to HTTPS default port; this changes URL identity and is a policy choice whose consequences require C05. | No confirmed new defect in this source window. Policy update reconciles nonterminal inventory; operator-selected URLs intentionally override exclusions. Actual scheduling/restart effects and schema constraints remain B029–B031/I03. |

| Finding | Status / severity / confidence | Trigger, consequence and evidence | Limit / correction target |
| --- | --- | --- | --- |
| F12 — sitemap traversal lacks a fetched-source budget | Confirmed behavior; medium; high confidence | `services/page_discovery.py:169–181,215–229` bounds depth and collected page entries, but a sitemap index can list arbitrarily many distinct children. `seen_sitemaps` only avoids repeats, and the `max_urls` guard sees zero entries if every child is empty or malformed. An isolated execution of the actual traversal function with one index, 50 empty children, `max_urls=1` made 51 stubbed fetches. A remote site can therefore consume unbounded requests/time within the depth limit. | Probe used synthetic responses and no network. Add a separate bound for sitemap sources and total bytes/time, and record truncation as incomplete coverage rather than silently treating the page budget as a fetch budget. |

### Stage 3 — crawler source windows

| Run | Status / exact coverage | Trace and counterexample | Result and remaining work |
| --- | --- | --- | --- |
| B028 | Complete for `crawlers/seo.py:1–400`, pinned commit | `PageParser`, bounded fetch wrapper, seed/sitemap and ten-page selection. Normal fetch delegates URL/IP/body boundary to `SafeFetcher`; robots parser only asserts a block after a successful 2xx robots response. Counterexample malformed initial port escapes its `SafeFetchError` catch (F05), though normal URL identity rejects bad ports earlier. | Compressed response handling calls `gzip.decompress` after fetching; whether urllib3 already decoded the transport needs I03. Supporting file availability and duplicate captures carried to C05. |
| B029 | Complete for `crawlers/seo.py:401–800`, same commit | Content fingerprints, canonical/redirect duplicate classification, sitemap/inventory persistence and first half of page persistence. Ordinary substantial exact duplicates require at least 100 words and 40 distinct tokens; thin pages retain separate identity. Counterexample many child sitemaps drive F12 via `_sync_url_inventory`. | No new independent defect in this window; final `persist_page` transaction and the crawler loop are B030. Current uniqueness/index semantics remain I03. |
| B030 | Complete for `crawlers/seo.py:801–1200`, same commit | Page issue/evidence/resource outcome writes, agent-readiness fetches, frontier loop and control checks. Normal loop checks pause/cancel before selecting each next page, records response hash/observed time, and persists frontier counts. Counterexample cancellation during a current page fetch still permits `persist_page` and state writes (F14). | F13/F14. `persist_page` fetches llms files for every successful page while holding a write transaction. HTML capture time and separate GEO/AEO capture remain C05/I03. |
| B031 | Complete for `crawlers/seo.py:1201–1519`, same commit; whole 1–1519 reconciled | Final run status, failure path and nested crawler routes. Ordinary crawl/status endpoint scopes run ID to domain; ten-page selection enforces same host, URL cap and policy-driven robots option. Counterexample a job cancelled after the last pre-fetch control check can have its `crawl_run` status overwritten by finalization (F14). | F14; nested route authentication derives from app's global hook, full I01 disposition pending. No live worker or target site was used. |

| Finding | Status / severity / confidence | Trigger, consequence and evidence | Limit / correction target |
| --- | --- | --- | --- |
| F13 — network fetches occur inside per-page SQLite write transaction | Confirmed code path; high operational risk; high confidence | `crawlers/seo.py:670–925` inserts/updates page, issue and inventory rows, then at lines 885–886 fetches two remote llms files via `inspect_agent_readiness_sources`, before `con.commit()` at line 919. `crawl_worker:1104–1115` invokes this on a shared research DB connection for each page. A slow target can hold the write lock through both fetches, block unrelated app/worker writes, and repeat on every page. | Source establishes transaction order; lock duration/load was not benchmarked on the deployed DB. Fetch once outside the write transaction, then persist bounded evidence atomically. Similar network-inside-transaction risk in initial inventory is conditional on earlier writes; verify I03. |
| F14 — cancellation/recovery does not fence crawler evidence and final run state | Confirmed code path; high; high confidence | `crawlers/seo.py:1035–1039` checks job control only before taking a page. A pause/cancel or lease recovery during fetch does not stop `persist_page` (`1104–1115`), frontier/inventory writes, or unconditional final `UPDATE crawl_run ... WHERE id=?` (`1239–1252`). `jobs/store.py:313–352` marks a running crawl cancelled, but the old worker can later replace crawl status with completed/partial, particularly on the last page; the durable job terminal fence does not protect these tables. | Interleaved live worker timing and specific schema constraints remain I02/I03. Fence the write transaction and finalization against active worker/lease/status and preserve the cancellation state. Related to F06, but affects crawl evidence and the run status independently. |

### Stage 3 — resource contract and GEO/AEO scoring

| Run | Status / pinned commit | Coverage and check | Result and limit |
| --- | --- | --- | --- |
| B032 | Complete for assigned source; `5b4148c0e24030494fca8609e0180ab3a4b0fc9d` | Entire `services/resource_outcome.py`, `templates/crawl.html`, `templates/ten_page_select.html`; crawler writes in `persist_page`. Normal textual body ≤1 MiB is marked retained with original-byte hash; UI displays status, failure counts and controls. Counterexample ISO-8859-1 `caf\xe9` stored as `caf�` despite `body_retained=True` (F15). | F15. Source shows the 10-page form and server cap; actual rendered interactions and DB schema remain I03. |
| B033 | Complete for `audits/geo_aeo/engine.py:1–400`, same commit | URL validation, second SafeFetcher capture, HTML extraction, supporting robots/sitemap fetch, initial GEO checks. Normal unavailable network robots fetch returns UNKNOWN in GEO. Counterexample an HTTP 403 robots response yields a non-None status, empty rules and a PASS for permission (F16). | F16. Different crawler and audit captures can differ in time/headers, C05. Third-party page rendering and providers untested. |
| B034 | Complete for `audits/geo_aeo/engine.py:401–571`, same commit; whole engine reconciled | Remaining GEO/AEO rules, weighted summary, 56+60 assertion, report assembly. Normal UNKNOWN/MANUAL_REVIEW excluded from weighted score and counted in coverage; an isolated actual `summarize` probe returned score 100 and coverage 33 from one PASS, one UNKNOWN, one MANUAL_REVIEW and one NOT_APPLICABLE. | Scoring arithmetic held, but score must be read with coverage. F17 concerns its presentation. Many structural heuristic checks remain subject to manual validation; no live-page accuracy claim. |
| B035 | Complete for assigned source; same commit | Entire `audits/geo_aeo/service.py`, `services/applicability_policy.py`, `services/audit_execution.py`, `services/page_types.py`. Normal service maps captures/findings to persisted audit pages, signals and domain summary, and policy can mark optional checks NOT_APPLICABLE in report view. Counterexample cancellation during capture led to persisted completed audit (F06). | F06. `app.py` carries a duplicate inline persistence chain with no discovered caller; C02 must reconcile reachability. Report-view policy alters signal statuses after engine scores are persisted; whether displayed scores and check counts conflict needs B043–B046/I04. |
| B036 | Complete for assigned source, static; same commit | Entire `static/page-geo-aeo.js` and `templates/geo_aeo.html`, `geo_aeo_integrated.html`, `geo_aeo_report.html`; corresponding `app.py` routes. JS escapes server strings before `innerHTML`; Jinja autoescaping covers templates. Ordinary no-run view says no structured audit. Counterexample score summary template omits evaluation coverage (F17). | F10 domain-scope route data may populate page JS from foreign page ID; actual browser rendering unavailable. I01/I03 reconcile route semantics and score representation. |

| Finding | Status / severity / confidence | Trigger, consequence and evidence | Limit / correction target |
| --- | --- | --- | --- |
| F15 — retained response body is lossy | Confirmed function behavior; medium evidence-integrity risk; high confidence | `services/resource_outcome.py:49–80` hashes raw bytes but stores textual `raw_body` using `decode('utf-8', errors='replace')` regardless of declared charset, marking it retained. An isolated `response_evidence` call with `text/html; charset=iso-8859-1` and `b'caf\xe9'` produced stored `caf�` and `body_retained=True`; the stored body cannot reproduce the hash or original text. | Applies to non-UTF-8 text in the retention path; full export consumption remains I03/I04. Preserve original bytes in a bounded encoding or decode according to charset while marking transformed text separately. |
| F16 — robots permission can pass on HTTP error | Confirmed code path; medium; high confidence | `audits/geo_aeo/engine.py:111–135,246–248,359–366` retains a 403 status with no usable rules; `_robots_blocks('', path)` returns false and `evaluate` emits PASS for “robots.txt permits the page” because only `None` status becomes UNKNOWN. Technical indexability likewise treats `robots_blocks=False` as permission. | No live robots server was contacted. The code's own crawler treats non-2xx robots fetch as unavailable (`crawlers/seo.py:401–412`); classify this audit evidence as unknown/failed rather than proven permission. |
| F17 — score presented without evaluation coverage | Confirmed presentation behavior; medium; high confidence | `engine.py:525–538` correctly separates weighted score from coverage; one PASS and two unevaluated applicable checks yield 100 score with 33% coverage in an isolated execution. `templates/geo_aeo_integrated.html:9–17` and `geo_aeo_report.html:4–8` show score/counts without that coverage, and the persisted summary stores only scores/counts. A client/operator may read a high number as broad positive evidence. | Actual production score distributions unknown. Display evaluated/eligible counts and coverage near each score, with unavailable/manual items explicit; reconcile main report presentation in I04. |

### Stage 4 — manual AI source and comparison

| Run | Status / exact coverage | Trace and counterexample | Result and remaining work |
| --- | --- | --- | --- |
| B038 | Complete for `reports/cross_model.py:1–448`, pinned commit `5b4148c0e24030494fca8609e0180ab3a4b0fc9d` | Citation parsing, controlled-domain classification, optional remote judge, concept metrics, response/comparison persistence and rollups. Normal two successful answers can be compared after a configured judge response; missing answers yield `insufficient_valid_responses`. Search found no import/caller outside the module and ownership registry. | This appears dormant in the current app; no current client report conclusion should be attributed to its outputs. Judge correctness and provider comparability are unverified; C03/I05 will reconcile routes and data tables. |
| B039 | Complete for `reports/manual_ai_analysis.py`, `reports/question_governance.py`, `services/manual_ai_payload.py`, `services/manual_ai_report.py`; same commit | Manual report projection deliberately takes retrieval-enabled state2 for each of two phases and three providers, retaining raw responses and counting parsed results against 24 expected answers. Analysis builds its packet from the stored source snapshot; the job fences lease ownership at publication. Question governance offers approval and execution matrix but has no discovered caller. | F18 concerns response changes and stale analysis publication. Parser tolerates fenced/embedded JSON; strict normalization in web report remains C03/B044. Live provider calls and semantic quality untested. |
| B040 | Complete for `services/manual_ai_sources.py` and `templates/manual_ai_responses.html`, same commit | Four states and three provider responses persist under domain; form display uses Jinja escaping, and analysis text is escaped before markdown client handling. Ordinary changed questions increment question-set version. Counterexample changing only a response retains prior `analysis_status='success'` and analysis text while the UI displays current responses beside that analysis. | F18. UI scripts and report projection still need I05 end-to-end rendering; no provider secrets or responses were submitted. |

| Finding | Status / severity / confidence | Trigger, consequence and evidence | Limit / correction target |
| --- | --- | --- | --- |
| F18 — manual AI analysis is not tied to response revision | Confirmed code path and isolated storage probe; medium; high confidence | `services/manual_ai_sources.py:86–117` increments version only for prompt changes and preserves successful analysis when response text changes; an isolated SQLite execution changed `answer-v1` to `answer-v2` while leaving `analysis of v1` and success. `app.py:881–901` queues a snapshot; `jobs/workflows.py:407–435` checks worker ownership but updates current `manual_ai_source` by domain without matching source revision. An older in-flight result can therefore replace analysis for newer responses. `templates/manual_ai_responses.html:153–165` and `full_report.html:1083–1085` display success and current question-set version with that stale analysis. | Actual concurrency timing and deployed UI not exercised. Persist a source content revision, invalidate analysis when any relevant input changes, and compare the revision at publication. Preserve the historical run result separately. |

### Stage 4 — source selection and paid extension

| Run | Status / exact coverage | Trace and counterexample | Result and remaining work |
| --- | --- | --- | --- |
| B041 | Complete for `integrations/dataforseo/connector.py`, `extension.py`, `reports/extended_sources.py`, `services/source_inventory.py`; pinned commit | Paid calls require credentials, project enablement and global/env kill switch immediately before network; API responses and errors record usage. The extension exposes a manual pull with at most two calls under default settings; report enrichment delegates to OpenGSC and does not call DataForSEO. Counterexample a connected source is selected despite an operator unchecking it (F19). | No external paid API called; provider response and billing behavior unverified. The local call count is for one manual invocation, not a durable spending cap. Historical snapshots lack run linkage (B046). |
| B042 | Complete for `templates/dataforseo.html` and `templates/sources.html`; same commit | The extension displays credential presence, enablement, kill switch, limits and aggregate usage without showing secrets; source form offers checkboxes and custom inventory rows. Counterexample unchecking a connected GSC/DataForSEO source cannot deselect it under `save_domain_sources`. | F19. Forms rely on app's global security hook for CSRF/auth; I01 handles route-wide context. “Connected” describes credentials/property presence, not necessarily completed provider evidence. |

| Finding | Status / severity / confidence | Trigger, consequence and evidence | Limit / correction target |
| --- | --- | --- | --- |
| F19 — connected sources cannot be deselected | Confirmed code path; medium; high confidence | `services/source_inventory.py:101,172` computes selected as `stored.selected OR connected` and persists `int(key in selected or connected)`. A user unchecks a connected source in `templates/sources.html:119–143`; save still writes selected=1, and `jobs/workflows.py:565–571` snapshots that key as selected. DataForSEO credentials alone qualify as connected even if the project extension is disabled (`source_inventory.py:48–51`; `connector.py:62–67`). | DataForSEO is not automatically pulled by the report workflow, so this primarily misstates selection/provenance. Separate connection state from operator choice; do not infer report use from credentials alone. |
| F20 — manual AI completeness can disagree across report layers | Confirmed code path; medium; high confidence | `services/manual_ai_payload.py` accepts embedded/fenced JSON, and `services/manual_ai_report.py:44–85` counts parsed results. `reports/web_report.py:758–808` reparses active raw fields with a narrower parser that accepts only direct JSON or a whole fenced block. A provider paste with prose followed by valid JSON can count toward source `complete=True` while report view recalculates `complete=False`. | Reproduce the exact payload through report view in C03/I04. Use one parser and store parse result/status in the immutable observation rather than interpreting raw evidence differently on read. |

### Stage 4 — report assembly and immutable observations

| Run | Status / exact coverage | Trace and counterexample | Result and remaining work |
| --- | --- | --- | --- |
| B043 | Complete for `reports/web_report.py:1–400` including continuation of `create_report_session` through 417; pinned commit | Monitoring inventory and client configuration are copied into each report; the normal session insert stores a JSON snapshot and optionally advances the living pointer. Counterexample `_auto_update_recommendations` commits tracking changes before the staged session insert and worker publication fence (F21). | No deployed DB transaction replay. Recommendation decisions and source identities need I04 reconciliation. |
| B044 | Complete for `reports/web_report.py:401–800`; same commit | Historical reads attach derived change history from stored sessions; report families group normalized audit signals and source rows. Current manual AI normalization reparses raw responses more narrowly than source projection (F20). Counterexample a response with embedded JSON can switch completeness status between layers. | Historical comparisons are bounded to 250 sessions and read-time derived; actual semantic validity of model responses is not established. |
| B045 | Complete for `reports/web_report.py:801–961`; whole file reconciled | View applies snapshotted policy, assembles families, root causes, monitoring coverage and report quality; ordinary audit status and missing evidence remain distinct in rollups. Counterexample high GEO score with low evaluated coverage (F17) can be carried into overview without that coverage. | Value prioritization and history are assigned B047–B048. Rendering and export parity remain B050–B061/I04. |
| B046 | Complete for entire `services/report_data.py`; same commit | Audit anchor uses latest completed/partial domain run, then selects crawl with matching execution ID when present; isolated concurrency probe already established F01, where requested execution A assembles latest audit B. Counterexample old manually pulled DataForSEO snapshots are included by domain only, with no report execution/time bound (F22). | `observation_provenance.inputs_linked` reports audit/crawl matching but does not prove matching requested refresh; GSC windows are separate. Full worker integration and race remain I02/I04. |

| Finding | Status / severity / confidence | Trigger, consequence and evidence | Limit / correction target |
| --- | --- | --- | --- |
| F21 — staged report mutates live recommendation state before publication | Confirmed code path; medium; high confidence | `reports/web_report.py:329–349,398–417` calls `_auto_update_recommendations`, which commits live `recommendation_tracking` changes before the report session insert and before `publish_report_if_owned` fences current publication (`jobs/workflows.py:565–584`). A losing/cancelled worker can mark an implemented item verified or reopen a verified item based on its staged audit even though that observation never becomes current. | Requires existing tracked findings and an ownership race; no deployed race executed. Apply tracking transitions only in the owned publication transaction or derive status for the current published observation. |
| F22 — prior paid snapshots appear in later unrelated reports | Confirmed query path; medium; high confidence | `services/report_data.py:67–74` loads the latest 20 DataForSEO snapshots for the domain without `report_run_id` or capture cutoff. Manual pull `integrations/dataforseo/extension.py:45–53` calls connector without a run ID, so the rows have NULL linkage; `reports/web_report.py:849–859` puts the newest date into metadata and `_seo_family:628` includes the list. A later report can present old paid evidence regardless of current source choice or run. | UI does display endpoint and capture date (`templates/full_report.html:1201`), limiting ambiguity, and no scheduled paid fetch occurs. Explicitly distinguish historical supplemental evidence from current-run inputs and honor selection/capture windows. |

### Stage 5 — history and prioritization

| Run | Status / exact coverage | Trace and counterexample | Result and remaining work |
| --- | --- | --- | --- |
| B047 | Complete for entire `reports/prioritization.py` and `reports/pulse_history.py`; pinned commit | Confirmed FAIL/PARTIAL get severity, prevalence and observed search exposure; missing traffic contributes zero and is flagged as partial input. Page history compares exact paths, records unavailable/review separately and deduplicates repeated audit IDs. Counterexamples: a foreign hostname with the same `/pricing` suffix supplies full exposure to an owned page (F24); a later session reusing an earlier audit replaces it in its original array position, reversing chronological movement (F25). | Isolated production-function probes; no external GSC records. Executive wording and exported history still need I04. |
| B048 | Complete for entire `reports/report_intelligence.py`; same commit | Normalization keeps UNKNOWN as unavailable, issue rollups count only FAIL/PARTIAL, root causes retain check evidence and source coverage marks missing separately. `validate_report` generates errors and `blocking=True` for duplicated executive findings or incoherent linked runs, but nothing consumes the blocking flag before publication (F23). | Confidence is based on presence of an evidence string/reference, not independent truth; semantic audit validation requires human review. C07/I04 will compare displayed/exported derived statuses. |

| Finding | Status / severity / confidence | Trigger, consequence and evidence | Limit / correction target |
| --- | --- | --- | --- |
| F23 — report-quality blocking errors do not block publication | Confirmed call path; medium; high confidence | `reports/report_intelligence.py:520–559` returns `blocking=bool(errors)`, including missing GSC period or incoherent provenance. `reports/web_report.py:959` computes it only when preparing a read view, while `create_report_session:352–417` stores the snapshot and `jobs/workflows.py:565–584` publishes without checking this result. `report_quality` appears only in export and view code, with no gate. | This is a validation contract gap, not proof a current production report has errors. Validate the staged snapshot before advancing the current pointer; show warnings separately from blocking errors. |
| F24 — exposure matching can borrow traffic from another host | Confirmed function behavior; medium prioritization risk; high confidence | `reports/prioritization.py:54–117` falls back from exact URL to `page.endswith(path)` across all GSC rows. An isolated call with failing `https://owned.example.com/pricing` and only `https://foreign.example.com/pricing` carrying 1,000 impressions returned `exposure=1.0`, `matched_pages=1`. Its score then increases for traffic the affected page never received. | Reachability depends on GSC property data containing such another host and a missing exact URL match; no live data inspected. Match normalized host and path against the domain/property, with ambiguity reported rather than summed. |
| F25 — reused audit deduplication reorders history | Confirmed function behavior; medium; high confidence | `reports/pulse_history.py:154–174` replaces the first occurrence of an audit ID with its latest report session while leaving its original position. Production-function probe with sessions audit A FAIL, B PASS, then A FAIL produced history `[latest A: new_issue, B: resolved]`, implying an improvement after the latest A instead of the actual chronological order. Report `web_report.py:420–437` feeds sessions in ascending creation time. | A repeated audit/session association is needed; F01 makes stale/latest audit reuse plausible, but deployed frequency unknown. Deduplicate first, then sort by retained session time, or key history to immutable observation identity and compare actual audit chronology. |

### Stage 5 — export and PDF

| Run | Status / exact coverage | Trace and counterexample | Result and remaining work |
| --- | --- | --- | --- |
| B050 | Complete for `reports/__init__.py` and entire `reports/full_pdf.py`; pinned commit | PDF uses saved report data and escapes paragraph markup; includes concise executive findings, GSC, crawl and GEO/AEO tables. Counterexample its “Priority Findings” selection includes UNKNOWN and MANUAL_REVIEW alongside FAIL/PARTIAL (F27), while HTML separates review/unavailable. It also displays scores without evaluation coverage (F17). | No PDF rendering against a full deployed report; locale parity is B051–B052/C07. The PDF explicitly says the HTML has deeper evidence. |
| B053 | Complete for `reports/observation_export.py`, `services/report_collaboration.py`, `static/analysis-markdown.js`, `static/collapsible-notes.js`; same commit | Canonical JSON embeds the saved snapshot and derived view; renderers reuse it, markdown JS escapes HTML before adding supported syntax, and collaboration notes/replies are stored separately from immutable report sessions. Counterexample CSV writes source-controlled cell values without spreadsheet formula neutralization (F26). | Actual public route authorization and current overlay remain I01/I04. CSV is a projection rather than lossless canonical data; JSON is the full export. |

| Finding | Status / severity / confidence | Trigger, consequence and evidence | Limit / correction target |
| --- | --- | --- | --- |
| F26 — CSV export permits spreadsheet formulas in source fields | Confirmed output; medium conditional; high confidence | `reports/observation_export.py:123–134` passes URL/decision fields directly to `csv.DictWriter`. An isolated `csv_bytes` call with URL `=HYPERLINK("https://example.org","click")` produced a CSV cell starting with `=HYPERLINK` (quoted by CSV syntax). A spreadsheet opening the exported file may evaluate it as a formula. | No spreadsheet application executed; behavior varies by importer. Prefix cells beginning with formula metacharacters after whitespace/control normalization, preserving raw values in JSON. |
| F27 — PDF groups unevaluated signals under priority findings | Confirmed selection; medium evidence-meaning risk; high confidence | `reports/full_pdf.py:299–313` selects `FAIL`, `PARTIAL`, `UNKNOWN`, and `MANUAL_REVIEW` and labels the entire section “Priority Findings.” In contrast, `reports/web_report.py:577–588` separates confirmed priority, review and unavailable. A reader may treat unevaluated signals as defects, especially because the PDF's 20-row cap can displace confirmed findings. | Rows do show each status; no generated PDF visually inspected. Split sections and reserve priority quota for confirmed issues. |

### Stage 5 — presentation locale

| Run | Status / exact coverage | Trace and counterexample | Result and remaining work |
| --- | --- | --- | --- |
| B051 | Complete for `reports/localization.py:1–495`; pinned commit | English and Spanish are resolved from query/cookie/Accept-Language. Spanish translation is applied to rendered text nodes, selected accessible attributes, and PDF paragraphs. The HTML walker excludes scripts, code, preformatted evidence, URL/verbatim blocks and analysis markdown; unknown text remains unchanged. Duplicate literal keys checked by AST have identical translations. | No full browser/PDF visual review; C07 compares source evidence and locale views. Dynamic text patterns can remain English without changing stored observation. |
| B052 | Complete for `reports/localization_es_detectors.py:1–259`; same commit | Detector title, recommendation and explanation dictionaries map authored strings to Spanish; raw observations are not rewritten in storage. Static duplicate-key scan found none in this file. Counterexample a detector string absent from the catalog stays English by `translate_text` fallback, with status semantics unchanged. | Translation quality needs a bilingual reviewer; no semantic inversion established from static mapping. |

**Export gate correction to F23:** `templates/full_report.html:896` disables only the visible PDF button when `report_quality.blocking`; direct `app.py:1963–2004` export/PDF endpoints do not enforce that flag, and JSON/CSV/XML/Markdown links remain available. F23 therefore applies to publication and direct export, while the UI gives a narrower “Export blocked” signal.

### Stage 5 — report template, presentation pass in progress

B055–B060 are not yet closed. The current pass inspected the executive and export controls, source/coverage sections, audit evidence tables, report-quality panel, and workflow JavaScript in `templates/full_report.html:870–1230,1280–1300,1890–1970`; remaining CSS and script windows still require the assigned per-run review. The executive view separates confirmed, review and unavailable checks, but the workflow exclusion control has an independent persistence defect:

| Finding | Status / severity / confidence | Trigger, consequence and evidence | Limit / correction target |
| --- | --- | --- | --- |
| F28 — report exclusion action disappears on reload and export | Confirmed caller/search path; medium; high confidence | `templates/full_report.html:1928–1958` sends exclusion IDs and removes the element from the current DOM. `app.py:1843–1866` persists rows via `services/report_collaboration.py:33–57`. A source search found no read of `report_exclusion` in app, report assembly, export or templates; subsequent `report_session_view:1924–1957` recreates the whole report from its stored snapshot, and `_send_observation_export:1968–1985` exports it without exclusions. The UI promise “Include … in report” therefore applies only to the current page session. | No browser interaction performed. Decide whether exclusions should be a per-view overlay or a newly versioned report artifact; load and apply them consistently to visible report and each export, while retaining the raw immutable observation. |

### Stage 5 — navigation and shared browser helpers

| Run | Status / exact coverage | Trace and counterexample | Result and remaining work |
| --- | --- | --- | --- |
| B061 | Complete for `templates/public_report_access.html` and `templates/reports.html`; pinned commit | Password form uses the server CSRF token, and report list shows active job controls plus historical sessions. Counterexample it calls the newest session “Current pulse” even when the publication pointer still references the older observation (F30). | Password/session boundary findings F02/F03 remain I01. Client URL is hardcoded to the deployed hostname; environment parity I07. |
| B063 | Complete for `static/nav-keyword-links.js`, `sortable.js`, `taxonomy.js`, and `templates/base.html` (shared navigation, route helpers and script inclusion); same commit | Keyword links encode query parameters; sortable rows operate on existing DOM and note IDs. Counterexample `taxonomy.js` embeds server-returned tag names and IDs into toolbar `innerHTML` without escaping (F29), while other tag chips use `textContent`. | Browser execution was not performed. Base layout/auth context remains I01/I07. |
| B064 | Complete for `templates/domain_delete.html`, `domain_new.html`, `domain_settings.html`, `empty.html`; same commit | Delete confirmation shows domain and active-work block, domain creation states optional source onboarding, settings identify company/questions, empty state names missing OpenGSC volume. Counterexample UI deletion state must still be checked against route enforcement; B016 did so, I02 handles in-flight work races. | No new independent defect in these source windows; real rendered layout remains untested. |

| Finding | Status / severity / confidence | Trigger, consequence and evidence | Limit / correction target |
| --- | --- | --- | --- |
| F29 — taxonomy toolbar inserts stored tag names as HTML | Confirmed static browser path; high conditional; high confidence | `static/taxonomy.js:78–85` interpolates `data.tags.map(t => '<option value="'+t.id+'">'+t.name+'</option>')` into `toolbar.innerHTML`; tags are operator-created via `app.py:1494–1546` and returned by lookup. A tag containing markup can escape the option/select context and execute or inject UI when any keyword/page table loads. Adjacent tag badges use safe `textContent`, but do not protect the toolbar. | Browser exploit not executed; exact parser behavior depends on payload. Construct option nodes with `document.createElement` and `.textContent`/`.value`, and validate IDs server side. |
| F30 — newest staged session is labeled current before publication | Confirmed route/template path; high integrity risk; high confidence | `jobs/workflows.py:565–584` creates a `publish=False` report session before the owned publication step. `app.py:1732–1745` passes `list_report_sessions` ordered by created time, and `templates/reports.html:32–40` calls `report_sessions[0]` “Current pulse,” with admin and public links. `load_current_report_session` is never called by app routes. During the staging window, or after a withheld/failed publication, the UI exposes an unpublished observation as current despite saying the previous observation remains visible. | Timing and actual session access under password policy remain I01/I04. Use `domain_report.current_report_id` for current navigation; keep staged sessions inaccessible or labeled unpublished until owned publication. |

### Stage 5 — operator workspaces

| Run | Status / exact coverage | Trace and counterexample | Result and remaining work |
| --- | --- | --- | --- |
| B065 | Complete for `templates/keyword_workspace.html`, `keywords.html`, `keywords_dashboard.html`, `overview.html`; pinned commit | Keyword workspace separates observed ranking pages from intended wanted target, with tags/note editor. Overview counts selected sources, inheriting F19; ranking labels “Latest” inherit the window-average F07. The keyword dashboard explicitly says it is empty. | No new independent issue in these templates; UI route/metric parity is I06. |
| B066 | Complete for `templates/page.html`, `page_workspace.html`, `pages.html`, `research.html`; same commit | Page inventory includes zero-ranking pages and note/wanted controls; research has filters, selected/page/all bulk actions. Counterexample “Select all” shows the current total domain count even under filters and server `scope=all` processes the whole domain (F31). Pages search inherits F11. | The older `page.html` has placeholder GEO/AEO/combined content; route reachability and intended legacy status remain I07. No browser form submission performed. |
| B067 | Complete for `templates/tools.html`, `wanted.html`; same commit | Tool links target inspection routes and wanted keyword form assigns a chosen page; regex help matches backend's REGEXP contract, unlike pages search. Cross-domain page-id guard omission remains F10. | No new independent defect; link availability and handler errors remain I01/I06. |

| Finding | Status / severity / confidence | Trigger, consequence and evidence | Limit / correction target |
| --- | --- | --- | --- |
| F31 — filtered research “Select all” acts on unfiltered domain | Confirmed route/template contract; high for destructive delete; high confidence | `templates/research.html:43–58,147–185` renders filtered rows but uses `total`, not `filtered_total`, for “Select all”; JS sets hidden `scope=all`. `app.py:1208–1261` handles `scope=all` in bulk save/tag/delete by querying every `research_keyword WHERE domain=?`, without applying q/show/hide filters. An operator viewing a filtered subset can click “Select all” and delete/move/tag every research keyword in the domain. | UI confirmation says the total count, which may help an attentive operator, but the filtered context and phrase are misleading. Use an explicit “all domain keywords” action distinct from “all matching filters,” or pass a validated filter snapshot to the server. |

### Comparison ledger — cross-file contracts

| Run | Status / evidence | Result and limit |
| --- | --- | --- |
| C02 | Complete for caller/reachability comparison at pinned commit. `app.py:435–479` defines an inline audit persistence/worker chain, but `start_audit_run` only enqueues; `jobs/handlers.py` dispatches `jobs/workflows.py:281` to `services/audit_execution.run_audit_pages`. Search of all scoped production call sites found no call of `app.audit_worker` or `app.store_structured_audit`. | The inline chain is dormant under current routes; its transaction/summary differences cannot affect the active audit without a new caller. Active path F06 remains. No second live database replay was warranted because the required “each reachable path” has one path. |
| C03 | Complete for current storage/projection comparison; actual parser isolated probe. Six retrieval-enabled response fields containing `Provider note: {"results":[{},{},{},{}]}` each parse as `embedded_json` with four results in `services.manual_ai_payload`, totaling 24, while AST-extracted actual `web_report._normalize_manual_ai_snapshot` reports six runs, zero valid JSON, zero answers and `complete=False`. `question_governance` and `cross_model` have no discovered app/workflow caller; four states remain stored, only state2 from each phase enters current report. | F18/F20. No live model analysis; absent provider response is unavailable evidence and is not counted as agreement. Historical legacy shape handled separately. |
| C04 | Complete for production caller and publication-identity trace, with isolated interleaving from F01. Only `jobs/workflows.py:573` calls `create_report_session`, explicitly `publish=False`; only the same workflow calls `publish_report_if_owned`. `jobs/publication.py:13–93` atomically checks job lease, report's domain/execution ID and pointer update. The default `publish=True` path has no current production caller. | The ownership fence prevents A from advancing the pointer after lease loss, but F01 proves A can assemble B's latest coherent audit/crawl pair, and F30 exposes staged sessions through the list. Live multiworker scheduling is still I02/I04. |
| C07 | In progress: isolated config comparison. With `RESEARCH_DB` unset, `app.py:38` resolves `/data/dashboard/research.db`, while `jobs/workflows.py:21` and `jobs/worker.py:24` resolve `/data/audit/research.db`; with explicit `RESEARCH_DB`, they match. `Dockerfile:13–16` sets `/data/audit/research.db`, so the shipped image avoids this divergence unless its environment is explicitly unset or modules are launched outside it. | Remaining startup, skin, deletion and filesystem checks belong to I07 before closing C07. No migrations executed. |
