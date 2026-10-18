# Pulse App — audit handoff and execution plan

Repository: `pablopovar/pulse`  
Pinned commit: `5b4148c0e24030494fca8609e0180ab3a4b0fc9d`  
Revision: 18 October 2026. Status: plan only; defect audits have not been executed.

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
