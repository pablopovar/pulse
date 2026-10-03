# Report contract v4

The client-facing product is one living domain pulse. SEO, onsite, AI, and future monitoring systems continuously contribute observations to that domain. Immutable observation snapshots are retained as evidence, but they are not separate client reports.

The current pulse answers two questions at the same time:

1. What is the latest known state now?
2. How did each individual finding get to that state?

## Status semantics

These states are distinct and must never be collapsed into a single issue bucket:

- `PASS` — the observed condition passed.
- `FAIL` — a confirmed detected failure.
- `PARTIAL` — a confirmed detected condition that is only partially satisfied.
- `MANUAL_REVIEW` — automation cannot establish the result; a human determination is required. This is not a defect.
- `NOT_APPLICABLE` — the check does not apply to this page/domain. This is not a defect.
- `DATA_UNAVAILABLE` — required source/evidence/integration data is unavailable. This is not a defect.

Legacy `UNKNOWN` values are normalized to `DATA_UNAVAILABLE` at report presentation/history time.

`Confirmed issues` counts include only `FAIL` and `PARTIAL`.

## Finding contract

A material finding must expose:

- current status
- latest movement
- date of the latest material movement
- material-event history
- current affected scope
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

`implemented` does not mean `verified`. Verification requires a later observation that shows the relevant condition changed.

## Per-finding pulse history

Every exact page/check identity retains its own lifecycle. `/about` and `/about-us` are different pages. If a page stops being assessed, its history stops; its absence is not a resolution and does not invalidate comparisons for pages that remain.

A current finding can therefore show, for example:

`FAIL 46/46 -> PARTIAL 31/46 -> PARTIAL 18/46 -> PASS 0/46`

Every completed run remains an immutable report observation. Inside a check, however, the client-visible history adds a row only for a material event. Repeated unchanged confirmations do not overwrite the last movement or its date.

Each material history row records, where available:

- observation timestamp
- immutable snapshot ID
- audit run ID
- status
- severity
- pages affected
- pages awaiting manual review
- pages with unavailable data
- pages tested
- movement relative to the preceding observation of the same exact page/check

Movement is classified as:

- `new_issue`
- `improved`
- `worsened`
- `resolved`
- `mixed`
- `requires_review`
- `evidence_unavailable`
- `no_longer_applicable`

Changed page sets are lifecycle/coverage facts, never a global comparison failure. Only the same exact page and check are compared. Manual review is not ordered between pass and fail: any transition into or out of it requires human determination.

The top movement strip counts unique currently assessed pages by their retained latest material movement. A page with both positive and negative movements is counted once as `mixed`. It does not display or accumulate unchanged confirmations.

Every successfully completed monitoring run creates a new immutable observation, even when every comparable check is unchanged. A run still in progress does not replace the last completed observation.

There is no monthly report mode. Month, week, day, baseline, and custom periods are filters over the same continuous observation history rather than separate report entities.

## Immutable observations and living state

`report_session` records remain immutable evidence snapshots. `domain_report` represents the one living report for the domain and points at the current observation plus the original baseline observation.

Creating a new observation:

1. stores the complete current evidence snapshot;
2. advances the living domain pulse to that observation;
3. leaves every earlier observation intact;
4. makes prior observations available beneath each finding as history.

The report UI calls old snapshots "observations" rather than separate reports.

## Root-cause grouping

Page-level evidence remains intact. Presentation may group related checks under one root-cause finding when they reflect one shared template, component, configuration, or content-system problem. The grouped finding must retain its supporting check list and page evidence.

Examples:

- page-type schema checks -> Sitewide schema and page-type configuration
- heading/H1 hierarchy checks -> Heading structure and page-template hierarchy
- FAQ/question/answer-block checks -> Content is not consistently structured for answer retrieval
- claim/source/methodology checks -> Claims and evidence are not consistently substantiated

## Data coverage

Missing integrations are reported under Monitoring Coverage, not as failed checks. GA4 and Microsoft Clarity are separate sources and one may never imply the other. Current monitored source classes include GSC, GA4, Microsoft Clarity, backlink data, rank tracking, sitemap inventory, and Manual AI Responses.

Coverage states are `connected`, `missing`, `stale`, `failed`, or `not_selected`. Connected observations carry a source timestamp when one is available.

Google Search Console performance uses the last 28 fully available GSC days. The start and end dates are stored in the immutable report. GSC clicks are called search clicks, never visits.

## Observation provenance

Every newly generated report identifies its audit run, crawl run, durable execution, source timestamps, and GSC period. Audit and crawl inputs must come from the same execution. Cancelled or unrelated later crawls may not be attached because they happen to be the latest row. Legacy snapshots without this linkage are labelled incomplete and cross-source conclusions are limited.

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

## AI-analysis language

Model-prior recall is evidence only that the entity surfaced in the observed model-prior response. It must not be described as proof of training-data awareness, ingestion, memorization, or source inclusion.

Model-prior and retrieval-enabled observations remain distinct. Retrieval does not prove correctness. Cross-provider agreement does not prove truth. Missing provider runs are excluded from denominators.

AI monitoring follows the same pulse principle: provider/state/question observations are historical variables. No arbitrary monthly reset is implied.

## Monitoring cadence

Checks may be tagged with whatever cadence is operationally appropriate, including frequent monitoring, daily, weekly, monthly, quarterly, or on-demand. Cadence controls when a new observation is collected; it does not create a new report.

## Report-quality validation

Before export, the report checks for:

- confirmed-issue count mismatches
- affected page counts larger than tested page counts
- duplicate executive findings
- high-priority findings without inspectable evidence
- missing monitoring sources
- unbounded GSC totals
- incoherent audit/crawl executions
- manual-review movement classified as improvement or worsening
- Clarity inferred as GA4
- connected sources without observation timestamps

Errors are export blockers in the report UI; warnings remain visible for review.
