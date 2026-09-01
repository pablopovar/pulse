# Report contract v2

The report is a client-facing view over observed SEO/onsite and AI data. Historical report sessions are immutable evidence snapshots; the current domain report is the latest snapshot plus its comparison history.

## Status semantics

These states are distinct and must never be collapsed into a single issue bucket:

- `PASS` — the observed condition passed.
- `FAIL` — a confirmed detected failure.
- `PARTIAL` — a confirmed detected condition that is only partially satisfied.
- `MANUAL_REVIEW` — automation cannot establish the result; a human determination is required. This is not a defect.
- `NOT_APPLICABLE` — the check does not apply to this page/domain. This is not a defect.
- `DATA_UNAVAILABLE` — required source/evidence/integration data is unavailable. This is not a defect.

Legacy `UNKNOWN` values are normalized to `DATA_UNAVAILABLE` at report presentation/comparison time.

`Checks needing attention` / `Confirmed issues` counts include only `FAIL` and `PARTIAL`.

## Finding contract

A material finding must expose:

- problem
- why_it_matters
- recommended_action
- affected_scope
- verification_method
- optional owner
- confidence
- evidence_type
- inspectable evidence references
- recommendation workflow status

Recommendation workflow states:

- `open`
- `in_progress`
- `implemented`
- `verified`
- `reopened`
- `accepted_risk`

`implemented` does not mean `verified`. Verification requires a subsequent observation that shows the relevant condition changed.

## Root-cause grouping

Page-level evidence remains intact. Presentation may group related checks under one root-cause finding when they reflect one shared template, component, configuration, or content-system problem. The grouped finding must retain its supporting check list and page evidence.

Examples:

- page-type schema checks -> Sitewide schema and page-type configuration
- heading/H1 hierarchy checks -> Heading structure and page-template hierarchy
- FAQ/question/answer-block checks -> Content is not consistently structured for answer retrieval
- claim/source/methodology checks -> Claims and evidence are not consistently substantiated

## Data coverage

Missing integrations are reported under Monitoring Coverage, not as failed checks. Current monitored source classes include GSC, GA4/audience context, backlink data, rank tracking, sitemap inventory, and Manual AI Responses.

Coverage states are `connected`, `missing`, `stale`, or `failed`.

## Value to fix

Scoring version: `value-to-fix-v2`.

Formula:

`severity_factor × status_factor × (1 + 2×traffic_exposure) × (1 + prevalence)`

Status factors:

- FAIL = 1.00
- PARTIAL = 0.65
- MANUAL_REVIEW = 0
- DATA_UNAVAILABLE = 0
- PASS = 0
- NOT_APPLICABLE = 0

When page-level search exposure is unavailable, `traffic_exposure` is set to zero and the score is explicitly marked as based on partial inputs. Missing traffic is never invented.

## Immutable snapshots and monthly comparison

Every new report session stores the exact collected report input object plus:

- snapshot version
- report timestamp
- scoring version
- methodology version
- analysis prompt version
- AI question-set version
- source coverage
- report mode
- comparison metadata

For each check/page pair, month-over-month state is classified as one of:

- `improved`
- `worsened`
- `unchanged`
- `new`
- `resolved`
- `not_comparable`
- `no_longer_applicable`

A monthly delta stores counts for resolved, improved, worsened, new, unchanged, not-comparable, no-longer-applicable, pages improved, and pages regressed.

## Report modes

- `baseline` — the first comprehensive report.
- `monthly` — later snapshots emphasize changes, unresolved priorities, regressions, no-movement items, and Top Actions. Detailed evidence remains in the interactive report; print/PDF presentation suppresses much of the lower-level detail.

## AI-analysis language

Model-prior recall is evidence only that the entity surfaced in the observed model-prior response. It must not be described as proof of training-data awareness, ingestion, memorization, or source inclusion.

Model-prior and retrieval-enabled observations remain distinct. Retrieval does not prove correctness. Cross-provider agreement does not prove truth. Missing provider runs are excluded from denominators.

## Monitoring cadence

Checks may be tagged `monthly`, `quarterly`, or `on_demand`. Current report logic defaults confirmed defects and critical/high checks to monthly monitoring and review-required items to quarterly monitoring.

## Report-quality validation

Before export, the report checks for:

- confirmed-issue count mismatches
- affected page counts larger than tested page counts
- duplicate executive findings
- high-priority findings without inspectable evidence
- missing monitoring sources

Errors are export blockers in the report UI; warnings remain visible for review.
