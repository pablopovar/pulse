# Pulse App — current-state audit plan and per-run tasks

Repository: `pablopovar/pulse`  
Pinned commit: `5b4148c0e24030494fca8609e0180ab3a4b0fc9d`  
Revision: 18 October 2026. Status: plan only; defect audits have not been executed.

## Objective and scope

Assess current Pulse App behavior for defects, omissions, inconsistent contracts, overlapping implementations, security boundaries, evidence integrity and report accuracy. Deliver findings without implementing fixes.

Review only `pulse-app/`. Exclude `pulse-app/tests/` entirely, including fixtures; `pulse-app/db/migrations/`; the migration runner `pulse-app/db/migrate.py`; and test configuration `pulse-app/pytest.ini`. All repository paths outside `pulse-app/`, including OpenGSC internals and root deployment files, remain excluded. Empty package initializers remain omitted. README and report-contract documents are context.

Current database access, schema assumptions, table ownership, constraints and indexes remain in scope through runtime code and, if available, a read-only schema inspection of the existing database. Do not infer actual database state from source alone. No historical migration review, migration execution, fresh-install certification, upgrade-safety assessment or test-suite audit is included. Inspect startup invocation and failure propagation at its call site without tracing excluded migration internals. Existing tests may optionally be run as supporting evidence, but their source is not an audit target and they are not a completion requirement. Do not follow excluded files without an explicit scope amendment.

Inventory: **88 primary audit files; 56 primary runs; eight comparison runs; eight integration/reconciliation runs**. Original B IDs are preserved. Retired runs: B004, B005, B006, B014, B017, B020, B022, B025, B027, B037, B049. They require no work and do not count as unfinished runs. This document contains the complete task list; no companion file is required.

## Execution rules and outputs

1. Confirm the pinned commit before each run; record source drift separately. Work against isolated copies of existing-state data and synthetic inputs; do not run migrations or mutate production data.
2. Read every listed file/window. Include enclosing definitions and relevant in-scope callers as context. At the last window of a split file, reconcile the whole file. Compare interfaces even when their implementation is assigned to a later run.
3. Trace input → authentication and validation → service → database/external/filesystem effects → response or presentation. Record domain boundaries, failures, time, provenance and ownership.
4. For each run record status (planned/in progress/blocked/complete), commit, exact coverage, caller links, checks and results, findings, limitations and outstanding questions. Static reading is not a runtime pass.
5. Findings require severity, confidence, file and line, trigger, affected behavior, evidence and reproduction where feasible. Separate confirmed defects, suspected defects, intentional differences and unreachable-code candidates. Consolidate duplicate findings.
6. Use small isolated runtime probes where useful; record commands and actual outcomes. Mock external contracts locally without relying on excluded test fixtures. Avoid live provider charges and external writes.
7. Primary runs execute in listed order. Then complete C01–C08 and I01–I07; I08 is the final gate. All runs below start as **planned**.

Every primary run must produce an evidence-backed review note and ledger entry. A blocked check must remain explicitly qualified. The final output is a consolidated findings report, completed coverage record, remaining uncertainties and corrected architecture description.

## Architecture and critical provenance

Flask routes enforce management/client access and serve domain, research, source and report workspaces. Routes enqueue durable SQLite jobs; a lease-owning worker performs discovery, crawling, GEO/AEO scoring, optional AI analysis and report publication. Pulse's OpenGSC adapter reads an external database; DataForSEO and AI clients call external providers. These external implementations are outside scope.

The crawler and GEO/AEO engine independently fetch pages. Report collection chooses the latest eligible domain audit and its matching crawl; refresh does not supply expected run IDs to collection. Comparison C04 must establish whether concurrent refreshes can mix current-job identity. Reports are first staged, then published with ownership checks. Historical evidence snapshots coexist with separately loaded notes, interpretation, navigation and presentation logic; their immutability must be checked separately.

Manual AI answers are collected outside Pulse, pasted and parsed, projected into reports and optionally interpreted by a background analysis job. Verify actual phase/state/provider/question denominators and reachability of alternate governance code. Domain creation, sync/deletion, research/taxonomy, provider settings, discussion and filesystem skins are separate flows that also require review.

## Primary file-review runs
### B001 — 01. Deployment and dependencies

Files/windows:

- `pulse-app/.env.example`

Tasks:

- Review ports, mounts, startup, secrets, reproducibility, dependency supply chain and update/backup behavior.
- Trace the listed implementation’s inputs, active callers, outputs and side effects; validate its contract with adjacent components.
- Check invalid, missing, empty, stale and concurrent inputs where applicable; document concrete failure behavior and uncertainty.
- Record exact reviewed coverage, findings and any follow-up for the comparison/integration runs.

### B002 — 01. Deployment and dependencies

Files/windows:

- `pulse-app/Dockerfile`
- `pulse-app/entrypoint.sh`
- `pulse-app/requirements.txt`

Tasks:

- Review ports, mounts, startup, secrets, reproducibility, dependency supply chain and update/backup behavior.
- Trace the listed implementation’s inputs, active callers, outputs and side effects; validate its contract with adjacent components.
- Check invalid, missing, empty, stale and concurrent inputs where applicable; document concrete failure behavior and uncertainty.
- Record exact reviewed coverage, findings and any follow-up for the comparison/integration runs.

### B003 — 02. Pulse schema and storage

Files/windows:

- `pulse-app/db/__init__.py`

Tasks:

- Review schema ownership, constraints, foreign keys, WAL, read-only access and rollback.
- Trace the listed implementation’s inputs, active callers, outputs and side effects; validate its contract with adjacent components.
- Check invalid, missing, empty, stale and concurrent inputs where applicable; document concrete failure behavior and uncertainty.
- Record exact reviewed coverage, findings and any follow-up for the comparison/integration runs.

### B007 — 02. Pulse schema and storage

Files/windows:

- `pulse-app/db/ownership.py`
- `pulse-app/db/sqlite.py`

Tasks:

- Review schema ownership, constraints, foreign keys, WAL, read-only access and rollback.
- Trace the listed implementation’s inputs, active callers, outputs and side effects; validate its contract with adjacent components.
- Check invalid, missing, empty, stale and concurrent inputs where applicable; document concrete failure behavior and uncertainty.
- Record exact reviewed coverage, findings and any follow-up for the comparison/integration runs.

### B008 — 03. Pulse HTTP shell and route contracts

Files/windows:

- `pulse-app/app.py` — lines 1–400

Tasks:

- Review trace every route and helper, registration, request validation, response behavior and cross-domain identifiers. Reconcile extracted services with remaining inline code.
- Trace the listed implementation’s inputs, active callers, outputs and side effects; validate its contract with adjacent components.
- Check invalid, missing, empty, stale and concurrent inputs where applicable; document concrete failure behavior and uncertainty.
- Record exact reviewed coverage, findings and any follow-up for the comparison/integration runs.

### B009 — 03. Pulse HTTP shell and route contracts

Files/windows:

- `pulse-app/app.py` — lines 401–800

Tasks:

- Review trace every route and helper, registration, request validation, response behavior and cross-domain identifiers. Reconcile extracted services with remaining inline code.
- Trace the listed implementation’s inputs, active callers, outputs and side effects; validate its contract with adjacent components.
- Check invalid, missing, empty, stale and concurrent inputs where applicable; document concrete failure behavior and uncertainty.
- Record exact reviewed coverage, findings and any follow-up for the comparison/integration runs.

### B010 — 03. Pulse HTTP shell and route contracts

Files/windows:

- `pulse-app/app.py` — lines 801–1200

Tasks:

- Review trace every route and helper, registration, request validation, response behavior and cross-domain identifiers. Reconcile extracted services with remaining inline code.
- Trace the listed implementation’s inputs, active callers, outputs and side effects; validate its contract with adjacent components.
- Check invalid, missing, empty, stale and concurrent inputs where applicable; document concrete failure behavior and uncertainty.
- Record exact reviewed coverage, findings and any follow-up for the comparison/integration runs.

### B011 — 03. Pulse HTTP shell and route contracts

Files/windows:

- `pulse-app/app.py` — lines 1201–1600

Tasks:

- Review trace every route and helper, registration, request validation, response behavior and cross-domain identifiers. Reconcile extracted services with remaining inline code.
- Trace the listed implementation’s inputs, active callers, outputs and side effects; validate its contract with adjacent components.
- Check invalid, missing, empty, stale and concurrent inputs where applicable; document concrete failure behavior and uncertainty.
- Record exact reviewed coverage, findings and any follow-up for the comparison/integration runs.

### B012 — 03. Pulse HTTP shell and route contracts

Files/windows:

- `pulse-app/app.py` — lines 1601–2000

Tasks:

- Review trace every route and helper, registration, request validation, response behavior and cross-domain identifiers. Reconcile extracted services with remaining inline code.
- Trace the listed implementation’s inputs, active callers, outputs and side effects; validate its contract with adjacent components.
- Check invalid, missing, empty, stale and concurrent inputs where applicable; document concrete failure behavior and uncertainty.
- Record exact reviewed coverage, findings and any follow-up for the comparison/integration runs.

### B013 — 03. Pulse HTTP shell and route contracts

Files/windows:

- `pulse-app/app.py` — lines 2001–2118

Tasks:

- Review trace every route and helper, registration, request validation, response behavior and cross-domain identifiers. Reconcile extracted services with remaining inline code.
- Trace the listed implementation’s inputs, active callers, outputs and side effects; validate its contract with adjacent components.
- Check invalid, missing, empty, stale and concurrent inputs where applicable; document concrete failure behavior and uncertainty.
- Record exact reviewed coverage, findings and any follow-up for the comparison/integration runs.

### B015 — 04. Pulse security and client access

Files/windows:

- `pulse-app/services/public_report_access.py`
- `pulse-app/services/security_boundary.py`

Tasks:

- Review management authentication, proxy assertions, CSRF, public capabilities, optional passwords, revocation, exports and static/skin exceptions.
- Trace the listed implementation’s inputs, active callers, outputs and side effects; validate its contract with adjacent components.
- Check invalid, missing, empty, stale and concurrent inputs where applicable; document concrete failure behavior and uncertainty.
- Record exact reviewed coverage, findings and any follow-up for the comparison/integration runs.

### B016 — 05. Pulse domain lifecycle and presentation settings

Files/windows:

- `pulse-app/services/domain_company.py`
- `pulse-app/services/domain_registry.py`
- `pulse-app/services/domain_skin.py`
- `pulse-app/services/domains.py`

Tasks:

- Review domain normalization, import/suppression, deletion cleanup, company identity and custom CSS handling.
- Trace the listed implementation’s inputs, active callers, outputs and side effects; validate its contract with adjacent components.
- Check invalid, missing, empty, stale and concurrent inputs where applicable; document concrete failure behavior and uncertainty.
- Record exact reviewed coverage, findings and any follow-up for the comparison/integration runs.

### B018 — 06. Pulse OpenGSC adapter

Files/windows:

- `pulse-app/integrations/opengsc_adapter.py`

Tasks:

- Review read-only SQL schema compatibility, missing tables, time windows, normalization and correct site/domain scoping.
- Trace the listed implementation’s inputs, active callers, outputs and side effects; validate its contract with adjacent components.
- Check invalid, missing, empty, stale and concurrent inputs where applicable; document concrete failure behavior and uncertainty.
- Record exact reviewed coverage, findings and any follow-up for the comparison/integration runs.

### B019 — 07. Pulse durable job lifecycle

Files/windows:

- `pulse-app/jobs/__init__.py`
- `pulse-app/jobs/handlers.py`
- `pulse-app/jobs/store.py`
- `pulse-app/jobs/worker.py`

Tasks:

- Review atomic claim, leases, retries, heartbeat ownership, pause/resume/cancel and crash recovery; distinguish job state from workflow state.
- Trace the listed implementation’s inputs, active callers, outputs and side effects; validate its contract with adjacent components.
- Check invalid, missing, empty, stale and concurrent inputs where applicable; document concrete failure behavior and uncertainty.
- Record exact reviewed coverage, findings and any follow-up for the comparison/integration runs.

### B021 — 08. Pulse workflow and publication

Files/windows:

- `pulse-app/jobs/publication.py`
- `pulse-app/jobs/workflows.py`

Tasks:

- Review stage transitions, idempotency, publication withholding, bounded crawl scope, ownership fencing, current/baseline pointers and background scheduling.
- Trace the listed implementation’s inputs, active callers, outputs and side effects; validate its contract with adjacent components.
- Check invalid, missing, empty, stale and concurrent inputs where applicable; document concrete failure behavior and uncertainty.
- Record exact reviewed coverage, findings and any follow-up for the comparison/integration runs.

### B023 — 09. Pulse URL and outbound HTTP boundary

Files/windows:

- `pulse-app/services/safe_fetcher.py`
- `pulse-app/services/url_policy.py`

Tasks:

- Review sSRF, DNS rebinding, redirects, private addresses, timeout/body limits, canonical identity and hostname equivalence.
- Trace the listed implementation’s inputs, active callers, outputs and side effects; validate its contract with adjacent components.
- Check invalid, missing, empty, stale and concurrent inputs where applicable; document concrete failure behavior and uncertainty.
- Record exact reviewed coverage, findings and any follow-up for the comparison/integration runs.

### B024 — 10. Pulse page discovery and reconciliation

Files/windows:

- `pulse-app/services/page_discovery.py`
- `pulse-app/services/sitemap_reconciliation.py`

Tasks:

- Review nested sitemap parsing, gzip/text inventories, depth/size limits, source provenance, unavailable evidence, reconciliation and request-time IO.
- Trace the listed implementation’s inputs, active callers, outputs and side effects; validate its contract with adjacent components.
- Check invalid, missing, empty, stale and concurrent inputs where applicable; document concrete failure behavior and uncertainty.
- Record exact reviewed coverage, findings and any follow-up for the comparison/integration runs.

### B026 — 11. Pulse crawl selection and frontier

Files/windows:

- `pulse-app/services/crawl_frontier.py`

Tasks:

- Review eligibility versus discovery, ranking, page classes, budgets, delayed work, persistent frontier and duplicate decisions.
- Trace the listed implementation’s inputs, active callers, outputs and side effects; validate its contract with adjacent components.
- Check invalid, missing, empty, stale and concurrent inputs where applicable; document concrete failure behavior and uncertainty.
- Record exact reviewed coverage, findings and any follow-up for the comparison/integration runs.

### B028 — 12. Pulse crawler and evidence

Files/windows:

- `pulse-app/crawlers/seo.py` — lines 1–400

Tasks:

- Review fetch/parse/persist, robots failures, redirects, conditional requests, fingerprints, retained evidence, coverage and cooperative job controls.
- Trace the listed implementation’s inputs, active callers, outputs and side effects; validate its contract with adjacent components.
- Check invalid, missing, empty, stale and concurrent inputs where applicable; document concrete failure behavior and uncertainty.
- Record exact reviewed coverage, findings and any follow-up for the comparison/integration runs.

### B029 — 12. Pulse crawler and evidence

Files/windows:

- `pulse-app/crawlers/seo.py` — lines 401–800

Tasks:

- Review fetch/parse/persist, robots failures, redirects, conditional requests, fingerprints, retained evidence, coverage and cooperative job controls.
- Trace the listed implementation’s inputs, active callers, outputs and side effects; validate its contract with adjacent components.
- Check invalid, missing, empty, stale and concurrent inputs where applicable; document concrete failure behavior and uncertainty.
- Record exact reviewed coverage, findings and any follow-up for the comparison/integration runs.

### B030 — 12. Pulse crawler and evidence

Files/windows:

- `pulse-app/crawlers/seo.py` — lines 801–1200

Tasks:

- Review fetch/parse/persist, robots failures, redirects, conditional requests, fingerprints, retained evidence, coverage and cooperative job controls.
- Trace the listed implementation’s inputs, active callers, outputs and side effects; validate its contract with adjacent components.
- Check invalid, missing, empty, stale and concurrent inputs where applicable; document concrete failure behavior and uncertainty.
- Record exact reviewed coverage, findings and any follow-up for the comparison/integration runs.

### B031 — 12. Pulse crawler and evidence

Files/windows:

- `pulse-app/crawlers/seo.py` — lines 1201–1519

Tasks:

- Review fetch/parse/persist, robots failures, redirects, conditional requests, fingerprints, retained evidence, coverage and cooperative job controls.
- Trace the listed implementation’s inputs, active callers, outputs and side effects; validate its contract with adjacent components.
- Check invalid, missing, empty, stale and concurrent inputs where applicable; document concrete failure behavior and uncertainty.
- Record exact reviewed coverage, findings and any follow-up for the comparison/integration runs.

### B032 — 12. Pulse crawler and evidence

Files/windows:

- `pulse-app/services/resource_outcome.py`
- `pulse-app/templates/crawl.html`
- `pulse-app/templates/ten_page_select.html`

Tasks:

- Review fetch/parse/persist, robots failures, redirects, conditional requests, fingerprints, retained evidence, coverage and cooperative job controls.
- Trace the listed implementation’s inputs, active callers, outputs and side effects; validate its contract with adjacent components.
- Check invalid, missing, empty, stale and concurrent inputs where applicable; document concrete failure behavior and uncertainty.
- Record exact reviewed coverage, findings and any follow-up for the comparison/integration runs.

### B033 — 13. Pulse GEO/AEO audit and scoring

Files/windows:

- `pulse-app/audits/geo_aeo/engine.py` — lines 1–400

Tasks:

- Review independent second page capture, signal evidence, unknown versus fail, weighting, applicability, page classification, aggregation and reference validity.
- Trace the listed implementation’s inputs, active callers, outputs and side effects; validate its contract with adjacent components.
- Check invalid, missing, empty, stale and concurrent inputs where applicable; document concrete failure behavior and uncertainty.
- Record exact reviewed coverage, findings and any follow-up for the comparison/integration runs.

### B034 — 13. Pulse GEO/AEO audit and scoring

Files/windows:

- `pulse-app/audits/geo_aeo/engine.py` — lines 401–571

Tasks:

- Review independent second page capture, signal evidence, unknown versus fail, weighting, applicability, page classification, aggregation and reference validity.
- Trace the listed implementation’s inputs, active callers, outputs and side effects; validate its contract with adjacent components.
- Check invalid, missing, empty, stale and concurrent inputs where applicable; document concrete failure behavior and uncertainty.
- Record exact reviewed coverage, findings and any follow-up for the comparison/integration runs.

### B035 — 13. Pulse GEO/AEO audit and scoring

Files/windows:

- `pulse-app/audits/geo_aeo/service.py`
- `pulse-app/services/applicability_policy.py`
- `pulse-app/services/audit_execution.py`
- `pulse-app/services/page_types.py`

Tasks:

- Review independent second page capture, signal evidence, unknown versus fail, weighting, applicability, page classification, aggregation and reference validity.
- Trace the listed implementation’s inputs, active callers, outputs and side effects; validate its contract with adjacent components.
- Check invalid, missing, empty, stale and concurrent inputs where applicable; document concrete failure behavior and uncertainty.
- Record exact reviewed coverage, findings and any follow-up for the comparison/integration runs.

### B036 — 13. Pulse GEO/AEO audit and scoring

Files/windows:

- `pulse-app/static/page-geo-aeo.js`
- `pulse-app/templates/geo_aeo.html`
- `pulse-app/templates/geo_aeo_integrated.html`
- `pulse-app/templates/geo_aeo_report.html`

Tasks:

- Review independent second page capture, signal evidence, unknown versus fail, weighting, applicability, page classification, aggregation and reference validity.
- Trace the listed implementation’s inputs, active callers, outputs and side effects; validate its contract with adjacent components.
- Check invalid, missing, empty, stale and concurrent inputs where applicable; document concrete failure behavior and uncertainty.
- Record exact reviewed coverage, findings and any follow-up for the comparison/integration runs.

### B038 — 14. Pulse manual AI evidence and analysis

Files/windows:

- `pulse-app/reports/cross_model.py`

Tasks:

- Review raw pasted evidence, parsing, phase/state/provider denominators, question governance, provider settings, prompt grounding and stale-analysis protection.
- Trace the listed implementation’s inputs, active callers, outputs and side effects; validate its contract with adjacent components.
- Check invalid, missing, empty, stale and concurrent inputs where applicable; document concrete failure behavior and uncertainty.
- Record exact reviewed coverage, findings and any follow-up for the comparison/integration runs.

### B039 — 14. Pulse manual AI evidence and analysis

Files/windows:

- `pulse-app/reports/manual_ai_analysis.py`
- `pulse-app/reports/question_governance.py`
- `pulse-app/services/manual_ai_payload.py`
- `pulse-app/services/manual_ai_report.py`

Tasks:

- Review raw pasted evidence, parsing, phase/state/provider denominators, question governance, provider settings, prompt grounding and stale-analysis protection.
- Trace the listed implementation’s inputs, active callers, outputs and side effects; validate its contract with adjacent components.
- Check invalid, missing, empty, stale and concurrent inputs where applicable; document concrete failure behavior and uncertainty.
- Record exact reviewed coverage, findings and any follow-up for the comparison/integration runs.

### B040 — 14. Pulse manual AI evidence and analysis

Files/windows:

- `pulse-app/services/manual_ai_sources.py`
- `pulse-app/templates/manual_ai_responses.html`

Tasks:

- Review raw pasted evidence, parsing, phase/state/provider denominators, question governance, provider settings, prompt grounding and stale-analysis protection.
- Trace the listed implementation’s inputs, active callers, outputs and side effects; validate its contract with adjacent components.
- Check invalid, missing, empty, stale and concurrent inputs where applicable; document concrete failure behavior and uncertainty.
- Record exact reviewed coverage, findings and any follow-up for the comparison/integration runs.

### B041 — 15. Pulse source selection and paid integration

Files/windows:

- `pulse-app/integrations/dataforseo/connector.py`
- `pulse-app/integrations/dataforseo/extension.py`
- `pulse-app/reports/extended_sources.py`
- `pulse-app/services/source_inventory.py`

Tasks:

- Review selected versus available sources, provider errors, kill switch, credential handling, cost behavior and captured provenance.
- Trace the listed implementation’s inputs, active callers, outputs and side effects; validate its contract with adjacent components.
- Check invalid, missing, empty, stale and concurrent inputs where applicable; document concrete failure behavior and uncertainty.
- Record exact reviewed coverage, findings and any follow-up for the comparison/integration runs.

### B042 — 15. Pulse source selection and paid integration

Files/windows:

- `pulse-app/templates/dataforseo.html`
- `pulse-app/templates/sources.html`

Tasks:

- Review selected versus available sources, provider errors, kill switch, credential handling, cost behavior and captured provenance.
- Trace the listed implementation’s inputs, active callers, outputs and side effects; validate its contract with adjacent components.
- Check invalid, missing, empty, stale and concurrent inputs where applicable; document concrete failure behavior and uncertainty.
- Record exact reviewed coverage, findings and any follow-up for the comparison/integration runs.

### B043 — 16. Pulse report collection and immutable sessions

Files/windows:

- `pulse-app/reports/web_report.py` — lines 1–400

Tasks:

- Review crawl/audit execution linkage, source dates, snapshot content, historical stability, current pointer and monitoring inventory.
- Trace the listed implementation’s inputs, active callers, outputs and side effects; validate its contract with adjacent components.
- Check invalid, missing, empty, stale and concurrent inputs where applicable; document concrete failure behavior and uncertainty.
- Record exact reviewed coverage, findings and any follow-up for the comparison/integration runs.

### B044 — 16. Pulse report collection and immutable sessions

Files/windows:

- `pulse-app/reports/web_report.py` — lines 401–800

Tasks:

- Review crawl/audit execution linkage, source dates, snapshot content, historical stability, current pointer and monitoring inventory.
- Trace the listed implementation’s inputs, active callers, outputs and side effects; validate its contract with adjacent components.
- Check invalid, missing, empty, stale and concurrent inputs where applicable; document concrete failure behavior and uncertainty.
- Record exact reviewed coverage, findings and any follow-up for the comparison/integration runs.

### B045 — 16. Pulse report collection and immutable sessions

Files/windows:

- `pulse-app/reports/web_report.py` — lines 801–961

Tasks:

- Review crawl/audit execution linkage, source dates, snapshot content, historical stability, current pointer and monitoring inventory.
- Trace the listed implementation’s inputs, active callers, outputs and side effects; validate its contract with adjacent components.
- Check invalid, missing, empty, stale and concurrent inputs where applicable; document concrete failure behavior and uncertainty.
- Record exact reviewed coverage, findings and any follow-up for the comparison/integration runs.

### B046 — 16. Pulse report collection and immutable sessions

Files/windows:

- `pulse-app/services/report_data.py`

Tasks:

- Review crawl/audit execution linkage, source dates, snapshot content, historical stability, current pointer and monitoring inventory.
- Trace the listed implementation’s inputs, active callers, outputs and side effects; validate its contract with adjacent components.
- Check invalid, missing, empty, stale and concurrent inputs where applicable; document concrete failure behavior and uncertainty.
- Record exact reviewed coverage, findings and any follow-up for the comparison/integration runs.

### B047 — 17. Pulse findings, history and prioritization

Files/windows:

- `pulse-app/reports/prioritization.py`
- `pulse-app/reports/pulse_history.py`

Tasks:

- Review finding identity, missing versus resolved, comparisons, confidence, root-cause deduplication, priority and unsupported business claims.
- Trace the listed implementation’s inputs, active callers, outputs and side effects; validate its contract with adjacent components.
- Check invalid, missing, empty, stale and concurrent inputs where applicable; document concrete failure behavior and uncertainty.
- Record exact reviewed coverage, findings and any follow-up for the comparison/integration runs.

### B048 — 17. Pulse findings, history and prioritization

Files/windows:

- `pulse-app/reports/report_intelligence.py`

Tasks:

- Review finding identity, missing versus resolved, comparisons, confidence, root-cause deduplication, priority and unsupported business claims.
- Trace the listed implementation’s inputs, active callers, outputs and side effects; validate its contract with adjacent components.
- Check invalid, missing, empty, stale and concurrent inputs where applicable; document concrete failure behavior and uncertainty.
- Record exact reviewed coverage, findings and any follow-up for the comparison/integration runs.

### B050 — 18. Pulse report presentation and export

Files/windows:

- `pulse-app/reports/__init__.py`
- `pulse-app/reports/full_pdf.py`

Tasks:

- Review hTML/JS escaping, discussions, permissions, PDF/dataset parity, locale transformations, skin isolation and historical navigation.
- Trace the listed implementation’s inputs, active callers, outputs and side effects; validate its contract with adjacent components.
- Check invalid, missing, empty, stale and concurrent inputs where applicable; document concrete failure behavior and uncertainty.
- Record exact reviewed coverage, findings and any follow-up for the comparison/integration runs.

### B051 — 18. Pulse report presentation and export

Files/windows:

- `pulse-app/reports/localization.py`

Tasks:

- Review hTML/JS escaping, discussions, permissions, PDF/dataset parity, locale transformations, skin isolation and historical navigation.
- Trace the listed implementation’s inputs, active callers, outputs and side effects; validate its contract with adjacent components.
- Check invalid, missing, empty, stale and concurrent inputs where applicable; document concrete failure behavior and uncertainty.
- Record exact reviewed coverage, findings and any follow-up for the comparison/integration runs.

### B052 — 18. Pulse report presentation and export

Files/windows:

- `pulse-app/reports/localization_es_detectors.py`

Tasks:

- Review hTML/JS escaping, discussions, permissions, PDF/dataset parity, locale transformations, skin isolation and historical navigation.
- Trace the listed implementation’s inputs, active callers, outputs and side effects; validate its contract with adjacent components.
- Check invalid, missing, empty, stale and concurrent inputs where applicable; document concrete failure behavior and uncertainty.
- Record exact reviewed coverage, findings and any follow-up for the comparison/integration runs.

### B053 — 18. Pulse report presentation and export

Files/windows:

- `pulse-app/reports/observation_export.py`
- `pulse-app/services/report_collaboration.py`
- `pulse-app/static/analysis-markdown.js`
- `pulse-app/static/collapsible-notes.js`

Tasks:

- Review hTML/JS escaping, discussions, permissions, PDF/dataset parity, locale transformations, skin isolation and historical navigation.
- Trace the listed implementation’s inputs, active callers, outputs and side effects; validate its contract with adjacent components.
- Check invalid, missing, empty, stale and concurrent inputs where applicable; document concrete failure behavior and uncertainty.
- Record exact reviewed coverage, findings and any follow-up for the comparison/integration runs.

### B054 — 18. Pulse report presentation and export

Files/windows:

- `pulse-app/static/skins/default.css`

Tasks:

- Review hTML/JS escaping, discussions, permissions, PDF/dataset parity, locale transformations, skin isolation and historical navigation.
- Trace the listed implementation’s inputs, active callers, outputs and side effects; validate its contract with adjacent components.
- Check invalid, missing, empty, stale and concurrent inputs where applicable; document concrete failure behavior and uncertainty.
- Record exact reviewed coverage, findings and any follow-up for the comparison/integration runs.

### B055 — 18. Pulse report presentation and export

Files/windows:

- `pulse-app/templates/full_report.html` — lines 1–400

Tasks:

- Review hTML/JS escaping, discussions, permissions, PDF/dataset parity, locale transformations, skin isolation and historical navigation.
- Trace the listed implementation’s inputs, active callers, outputs and side effects; validate its contract with adjacent components.
- Check invalid, missing, empty, stale and concurrent inputs where applicable; document concrete failure behavior and uncertainty.
- Record exact reviewed coverage, findings and any follow-up for the comparison/integration runs.

### B056 — 18. Pulse report presentation and export

Files/windows:

- `pulse-app/templates/full_report.html` — lines 401–800

Tasks:

- Review hTML/JS escaping, discussions, permissions, PDF/dataset parity, locale transformations, skin isolation and historical navigation.
- Trace the listed implementation’s inputs, active callers, outputs and side effects; validate its contract with adjacent components.
- Check invalid, missing, empty, stale and concurrent inputs where applicable; document concrete failure behavior and uncertainty.
- Record exact reviewed coverage, findings and any follow-up for the comparison/integration runs.

### B057 — 18. Pulse report presentation and export

Files/windows:

- `pulse-app/templates/full_report.html` — lines 801–1200

Tasks:

- Review hTML/JS escaping, discussions, permissions, PDF/dataset parity, locale transformations, skin isolation and historical navigation.
- Trace the listed implementation’s inputs, active callers, outputs and side effects; validate its contract with adjacent components.
- Check invalid, missing, empty, stale and concurrent inputs where applicable; document concrete failure behavior and uncertainty.
- Record exact reviewed coverage, findings and any follow-up for the comparison/integration runs.

### B058 — 18. Pulse report presentation and export

Files/windows:

- `pulse-app/templates/full_report.html` — lines 1201–1600

Tasks:

- Review hTML/JS escaping, discussions, permissions, PDF/dataset parity, locale transformations, skin isolation and historical navigation.
- Trace the listed implementation’s inputs, active callers, outputs and side effects; validate its contract with adjacent components.
- Check invalid, missing, empty, stale and concurrent inputs where applicable; document concrete failure behavior and uncertainty.
- Record exact reviewed coverage, findings and any follow-up for the comparison/integration runs.

### B059 — 18. Pulse report presentation and export

Files/windows:

- `pulse-app/templates/full_report.html` — lines 1601–2000

Tasks:

- Review hTML/JS escaping, discussions, permissions, PDF/dataset parity, locale transformations, skin isolation and historical navigation.
- Trace the listed implementation’s inputs, active callers, outputs and side effects; validate its contract with adjacent components.
- Check invalid, missing, empty, stale and concurrent inputs where applicable; document concrete failure behavior and uncertainty.
- Record exact reviewed coverage, findings and any follow-up for the comparison/integration runs.

### B060 — 18. Pulse report presentation and export

Files/windows:

- `pulse-app/templates/full_report.html` — lines 2001–2044

Tasks:

- Review hTML/JS escaping, discussions, permissions, PDF/dataset parity, locale transformations, skin isolation and historical navigation.
- Trace the listed implementation’s inputs, active callers, outputs and side effects; validate its contract with adjacent components.
- Check invalid, missing, empty, stale and concurrent inputs where applicable; document concrete failure behavior and uncertainty.
- Record exact reviewed coverage, findings and any follow-up for the comparison/integration runs.

### B061 — 18. Pulse report presentation and export

Files/windows:

- `pulse-app/templates/public_report_access.html`
- `pulse-app/templates/reports.html`

Tasks:

- Review hTML/JS escaping, discussions, permissions, PDF/dataset parity, locale transformations, skin isolation and historical navigation.
- Trace the listed implementation’s inputs, active callers, outputs and side effects; validate its contract with adjacent components.
- Check invalid, missing, empty, stale and concurrent inputs where applicable; document concrete failure behavior and uncertainty.
- Record exact reviewed coverage, findings and any follow-up for the comparison/integration runs.

### B062 — 19. Pulse research and operator UI

Files/windows:

- `pulse-app/static/app.css`

Tasks:

- Review keyword/page assignment, CSV imports/exports, taxonomy, notes, sorting, navigation and empty/error/loading states.
- Trace the listed implementation’s inputs, active callers, outputs and side effects; validate its contract with adjacent components.
- Check invalid, missing, empty, stale and concurrent inputs where applicable; document concrete failure behavior and uncertainty.
- Record exact reviewed coverage, findings and any follow-up for the comparison/integration runs.

### B063 — 19. Pulse research and operator UI

Files/windows:

- `pulse-app/static/nav-keyword-links.js`
- `pulse-app/static/sortable.js`
- `pulse-app/static/taxonomy.js`
- `pulse-app/templates/base.html`

Tasks:

- Review keyword/page assignment, CSV imports/exports, taxonomy, notes, sorting, navigation and empty/error/loading states.
- Trace the listed implementation’s inputs, active callers, outputs and side effects; validate its contract with adjacent components.
- Check invalid, missing, empty, stale and concurrent inputs where applicable; document concrete failure behavior and uncertainty.
- Record exact reviewed coverage, findings and any follow-up for the comparison/integration runs.

### B064 — 19. Pulse research and operator UI

Files/windows:

- `pulse-app/templates/domain_delete.html`
- `pulse-app/templates/domain_new.html`
- `pulse-app/templates/domain_settings.html`
- `pulse-app/templates/empty.html`

Tasks:

- Review keyword/page assignment, CSV imports/exports, taxonomy, notes, sorting, navigation and empty/error/loading states.
- Trace the listed implementation’s inputs, active callers, outputs and side effects; validate its contract with adjacent components.
- Check invalid, missing, empty, stale and concurrent inputs where applicable; document concrete failure behavior and uncertainty.
- Record exact reviewed coverage, findings and any follow-up for the comparison/integration runs.

### B065 — 19. Pulse research and operator UI

Files/windows:

- `pulse-app/templates/keyword_workspace.html`
- `pulse-app/templates/keywords.html`
- `pulse-app/templates/keywords_dashboard.html`
- `pulse-app/templates/overview.html`

Tasks:

- Review keyword/page assignment, CSV imports/exports, taxonomy, notes, sorting, navigation and empty/error/loading states.
- Trace the listed implementation’s inputs, active callers, outputs and side effects; validate its contract with adjacent components.
- Check invalid, missing, empty, stale and concurrent inputs where applicable; document concrete failure behavior and uncertainty.
- Record exact reviewed coverage, findings and any follow-up for the comparison/integration runs.

### B066 — 19. Pulse research and operator UI

Files/windows:

- `pulse-app/templates/page.html`
- `pulse-app/templates/page_workspace.html`
- `pulse-app/templates/pages.html`
- `pulse-app/templates/research.html`

Tasks:

- Review keyword/page assignment, CSV imports/exports, taxonomy, notes, sorting, navigation and empty/error/loading states.
- Trace the listed implementation’s inputs, active callers, outputs and side effects; validate its contract with adjacent components.
- Check invalid, missing, empty, stale and concurrent inputs where applicable; document concrete failure behavior and uncertainty.
- Record exact reviewed coverage, findings and any follow-up for the comparison/integration runs.

### B067 — 19. Pulse research and operator UI

Files/windows:

- `pulse-app/templates/tools.html`
- `pulse-app/templates/wanted.html`

Tasks:

- Review keyword/page assignment, CSV imports/exports, taxonomy, notes, sorting, navigation and empty/error/loading states.
- Trace the listed implementation’s inputs, active callers, outputs and side effects; validate its contract with adjacent components.
- Check invalid, missing, empty, stale and concurrent inputs where applicable; document concrete failure behavior and uncertainty.
- Record exact reviewed coverage, findings and any follow-up for the comparison/integration runs.

## Comparison runs

These deliberately revisit implementations. Use their listed prerequisites and compare related files in small subpasses.

## C01. Web/worker domain parity

Compare normalization, imported site fields, case/IDNA/ports, suppression and sync side effects. Exercise the same domain fixtures through both paths. Record intended differences; do not assume matching names imply identical contracts.

Prerequisite primary coverage: B008, B009, B010, B011, B012, B013, B016, B021, B023.

Files:
- `pulse-app/app.py`
- `pulse-app/services/domain_registry.py`
- `pulse-app/services/url_policy.py`
- `pulse-app/jobs/workflows.py`

Completion: document actual callers, intended divergence, fixture results and remaining uncertainty. Status: planned.

## C02. Audit persistence duplication and reachability

Trace audit_worker and both persistence/aggregation implementations. Establish callers across all scoped source, decorators and callbacks before calling a chain dead. Compare SQL, transactions, errors and summary denominators.

Prerequisite primary coverage: B008, B009, B010, B011, B012, B013, B019, B021, B035.

Files:
- `pulse-app/app.py`
- `pulse-app/services/audit_execution.py`
- `pulse-app/jobs/handlers.py`
- `pulse-app/jobs/workflows.py`

Completion: document actual callers, intended divergence, fixture results and remaining uncertainty. Status: planned.

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

Completion: document actual callers, intended divergence, fixture results and remaining uncertainty. Status: planned.

## C04. Publication mechanisms and execution identity

Enumerate every caller of create_report_session and publish_report_if_owned, across in-scope production code. Test publish=True versus staged publication. Interleave two domain refreshes and prove collection uses the intended execution, not merely a coherent latest audit/crawl pair.

Prerequisite primary coverage: B021, B043, B044, B045, B046.

Files:
- `pulse-app/reports/web_report.py`
- `pulse-app/jobs/publication.py`
- `pulse-app/jobs/workflows.py`
- `pulse-app/services/report_data.py`

Completion: document actual callers, intended divergence, fixture results and remaining uncertainty. Status: planned.

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

Completion: document actual callers, intended divergence, fixture results and remaining uncertainty. Status: planned.

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

Completion: document actual callers, intended divergence, fixture results and remaining uncertainty. Status: planned.

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

Completion: document actual callers, intended divergence, fixture results and remaining uncertainty. Status: planned.

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

Completion: document actual callers, intended divergence, fixture results and remaining uncertainty. Status: planned.

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

Prerequisites: B001–B003, B007, B016, C07.

Tasks: Inspect actual configuration resolution in web and worker paths, especially RESEARCH_DB defaults. Compare current schema assumptions with a read-only schema dump if supplied; otherwise qualify database-state uncertainty. Probe skin/export paths, traversal, permissions, atomic writes, concurrent access and cleanup/deletion using temporary directories. Do not run or review migration implementations.

Output: evidence, actual probe results, affected route/job rows, findings and unverified cases. Status: planned.

### I08 — Final reconciliation

Prerequisites: All retained B runs, C01–C08, I01–I07.

Tasks: Confirm every retained file/window has an outcome, all route rows and seven handlers have dispositions, and every contract check below has evidence or a recorded gap. Reconcile duplication and reachability claims, remove duplicate findings and update architecture based on verified behavior. State runtime/database access limits. Do not claim test-suite quality, upgrade safety, fresh-install reliability or certification of outside components.

Output: evidence, actual probe results, affected route/job rows, findings and unverified cases. Status: planned.

## Required report-contract checks

Read `pulse-app/reports/REPORT_CONTRACT.md` as required context. Ranges below refer only to retained runs; retired IDs never add work.

| Requirement | Owning review |
| --- | --- |
| FAIL/PARTIAL versus MANUAL_REVIEW/NOT_APPLICABLE/DATA_UNAVAILABLE; legacy UNKNOWN normalization | B033–B037, B043–B049, I04 |
| Exact page/check identity; missing assessment is not resolution; material-event history and unique-page movements | B047–B049, I04 |
| Implemented versus verified recommendations, root-cause evidence retention and required finding fields | B043–B049, I04 |
| Current/baseline pointer versus immutable observations; completed unchanged monitoring runs | B021–B022, B043–B046, C04, I02, I04 |
| Coverage states and timestamps; GA4 versus Clarity; bounded GSC dates/click labels | B018, B041–B049, I06 |
| Same-execution provenance and limits for legacy data; expected current execution under concurrency | B021–B022, B043–B046, C04, I02–I03 |
| Value-to-fix-v2 factors, missing exposure and zero nonissue scores | B047–B049, I04 |
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
