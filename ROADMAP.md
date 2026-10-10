


automate AI questions




If AI get's an answer wrong, or it flattens a brand, product, or space, or generalizes the client's uniqueness (etc.), what can be done about it?
Could Pulse decode the reasons of a problem? Say, I don't want a *report*, I want to know why (a given problem) is happening and what can I do to *influence* it.

Competitor outranks me
AI flattens product A
AI explains product B wrong
Google isn't showing my snippets.
etc., etc.











# Pulse Roadmap

Last updated: 2026-10-05

This roadmap covers the remaining crawler, evidence, and report-quality work. It is ordered by dependency: stabilize collection and provenance before changing interpretation or presentation.

## Working rules

- Preserve the original response and source provenance for every collected URL.
- Distinguish discovered, eligible, crawled, skipped, excluded, duplicate, and failed states.
- Treat unsupported, non-HTML, and intentionally excluded resources as explicit outcomes, never as missing data.
- Keep domain-wide findings separate from page-level findings.
- Keep observations, interpretations, and recommendations distinct.
- Preserve historical report snapshots; configuration changes apply to later observations unless explicitly designed otherwise.

## Phase 1 — Collection reliability

### 1.1 Non-HTML resource handling

Ensure text/plain, XML, JSON, PDF, image, feed, and other responses are retained as crawl outcomes even when they are not eligible for HTML auditing.

Acceptance criteria:

- The URL remains visible in the crawl inventory.
- Content type, HTTP status, final URL, byte size, and failure/skip reason are retained.
- Audit processing does not silently discard the record.
- The report distinguishes “collected but not HTML-audited” from “failed”.

### 1.2 Job ownership and disappearance

Make lease expiry, worker loss, retries, and terminal failure observable in the UI and durable job history.

Acceptance criteria:

- An ownership-loss event cannot make a job disappear without a terminal state.
- A recoverable job is re-queued safely and idempotently.
- A non-recoverable job ends as failed with a user-readable reason.
- Regression tests cover worker death, lease expiry, duplicate handlers, and retry exhaustion.

### 1.3 Crawl dataset exports

Export the complete crawl/audit dataset as JSON, CSV, XML, and Markdown.

Acceptance criteria:

- Exports include URL decisions, response metadata, provenance, crawl timestamps, and audit outcomes.
- Exported records preserve unsupported and excluded resources.
- JSON is lossless; CSV is tabular and documented; XML is valid; Markdown is human-readable.
- Export filenames include domain and observation/run identity.

## Phase 2 — Discovery and sitemap coverage

### 2.1 Sitemap discovery

Check declared and conventional locations:

- `sitemap.xml`
- `sitemap.xml.gz`
- `sitemap.txt`
- `urllist.txt`
- `urls.txt`
- `atom.xml`
- `rss.xml`
- `feed.xml`
- `mrss.xml`
- `sitemap.json`

Acceptance criteria:

- `robots.txt` sitemap directives are recorded separately from guessed locations.
- Sitemap indexes and child sitemaps are traversed.
- Format, status, content type, parse result, and freshness are recorded.
- The report cannot claim “Not Selected” when sitemap inventory was used.

### 2.2 Sitemap reconciliation

Compare sitemap URLs, internal links, canonical URLs, robots rules, and crawl results.

Acceptance criteria:

- Detect redirects, 4xx/5xx URLs, noindex URLs, robots-blocked URLs, canonical mismatches, stale `lastmod`, orphan candidates, and non-HTML resources.
- Report each discrepancy once at the correct scope.

### 2.3 `llms.txt` and `llms-full.txt`

Fetch and parse both files when available.

Acceptance criteria:

- Availability, status, content type, size, parse result, and observation time are retained.
- The report distinguishes presence from quality or usefulness.
- Missing files are informational unless the operator enables a policy requiring them.

## Phase 3 — Applicability and page understanding

### 3.1 Page-type classification

Classify homepages, service pages, blog posts, blog indexes, contact pages, application pages, privacy/legal pages, thank-you pages, and utility pages.

Acceptance criteria:

- Classification is visible with evidence and confidence.
- Operators can override ambiguous classifications.
- Rubrics are page-type-aware.

### 3.2 Domain-wide versus page-level checks

Move response/site policies—HSTS, compression, caching, and similar checks—to domain-wide findings.

Acceptance criteria:

- A site-wide defect is not multiplied across every page.
- Page-level checks remain attached to the affected page.
- Optional families such as comparison, FAQ, procedural language, citations, and quantified-claim support can be enabled or marked not applicable.

### 3.3 Robots and indexability intent

Fix the “Ignore robots.txt” setting and distinguish intentional noindex pages from accidental indexability defects.

Acceptance criteria:

- The effective robots policy is recorded for every crawl.
- Intentional utility/noindex pages are not treated as ordinary service pages.
- Canonical, robots, sitemap, and indexability evidence appear together.

## Phase 4 — Evidence and report integrity

### 4.1 Observation freshness

Show source observation dates prominently and avoid contradictory freshness claims.

Acceptance criteria:

- Every external source has an observed-at date or an explicit unavailable marker.
- Historical snapshots are not described as freshly queried.
- Incomplete AI-provider coverage remains prominent wherever conclusions generalize.

### 4.2 Executive-summary hardening

Re-audit the headline verdict and highest-value actions after applicability corrections.

Acceptance criteria:

- Cohort findings are not presented as domain-wide conclusions without sufficient coverage.
- “High confidence” reflects evidence validity and applicability, not repetition alone.
- Noisy or irrelevant search queries are labeled as such.

### 4.3 Benefit-to-fix explanations

Use a qualitative explanation alongside any internal ranking.

Acceptance criteria:

- The explanation references scope, severity, confidence, exposure, and leverage.
- It does not imply a traffic or revenue forecast.
- Uncertainty and assumptions remain visible.

## Phase 5 — Surface-by-surface audit

Audit the expanded report one section at a time, using the corrected dataset:

1. Executive summary
2. Observation dates and freshness
3. Crawl coverage and URL provenance
4. Sitemap and discovery coverage
5. Page-level findings
6. AI/GEO evidence
7. Recommendations and Benefit-to-fix
8. Exported datasets

Each section should record: observed fact, interpretation, suspected bullshit, correction, and regression test.

## Suggested execution order

1. Non-HTML resource handling
2. Job ownership/disappearance
3. Dataset exports
4. Sitemap discovery and reconciliation
5. `llms.txt` parsing
6. Page-type and applicability model
7. Robots/indexability intent
8. Evidence and executive-summary corrections
9. Surface-by-surface report audit

## Status legend

- **Not started** — no implementation or verification yet.
- **In progress** — implementation or investigation underway.
- **Needs verification** — implementation exists but runtime behavior is not yet proven.
- **Complete** — implementation, tests, and relevant runtime verification are complete.
