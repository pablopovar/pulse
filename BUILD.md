
Completed or partly implemented:

- Sitemap discovery across alternate filenames and formats.
- `llms.txt` / `llms-full.txt` discovery work.
- Crawler frontier and duplicate-handling changes.
- Background crawl recovery logic.
- Report observation-date display.
- Quick-link editing for operators.
- Benefit-to-fix explanation.
- “New issue pages” → “Discovered pages”.
- Database backup and Purple Dog Walkers report-data reset.

Still unfinished:

1. **Crawler output quality**
   - Correctly classify HTML, text, XML, JSON, PDFs, images, and other resources.
   - Prevent non-HTML resources from disappearing during audit processing.
   - Preserve failed/unsupported resources in the report with an explicit reason.
   - Export crawler results as XML, JSON, CSV, and Markdown datasets.

2. **Crawler job reliability**
   - Diagnose jobs that disappear after ownership loss.
   - Ensure the UI shows terminal failure instead of silently removing the job.
   - Make retries and worker ownership transitions visible and recoverable.
   - Add regression tests for worker death, lease expiry, and duplicate handlers.

3. **Sitemap audit**
   - Traverse sitemap indexes and child sitemaps.
   - Reconcile sitemap URLs against internal links.
   - Detect redirects, 4xx/5xx URLs, noindex URLs, robots-blocked URLs, canonical mismatches, stale `lastmod`, and non-HTML resources.
   - Correct the report’s “Sitemap inventory: Not Selected” contradiction.

4. **`llms.txt` audit**
   - Parse both `/llms.txt` and `/llms-full.txt`.
   - Record availability, status, content type, size, parse result, and freshness.
   - Distinguish valid guidance from merely present files.
   - Include results in the crawler dataset and report evidence.

5. **Applicability model**
   - Separate domain-wide checks from page-level checks.
   - Add operator toggles for optional detector families:
     - Comparisons and tables
     - FAQs and procedural content
     - External citations
     - Quantified-claim support
   - Prevent “not applicable” from becoming a failure.
   - Report domain-wide technical findings once rather than once per page.

6. **Page-type classification**
   - Classify service pages, blog posts, blog indexes, privacy/legal pages, application pages, thank-you pages, contact pages, homepages, and utility pages.
   - Apply page-type-specific rubrics.
   - Allow operator overrides for ambiguous pages.

7. **Indexability and robots handling**
   - Fix the “Ignore robots.txt” setting.
   - Distinguish intentional `noindex` pages from accidental indexability defects.
   - Exclude intentional utility pages from inappropriate content-quality scoring.
   - Show robots, canonical, sitemap, and noindex decisions together.

8. **Report evidence quality**
   - Correct the stale/freshness contradiction.
   - Preserve incomplete AI-provider collection prominently.
   - Label irrelevant/noisy GSC queries instead of presenting them as meaningful.
   - Separate observation, interpretation, and recommendation.
   - Rework “High confidence” so it does not mean merely “the detector repeated itself.”

9. **Benefit-to-fix**
   - Replace or supplement the numerical value-to-fix score with a model-generated explanation.
   - Base the explanation on scope, severity, confidence, exposure, and leverage.
   - Explicitly state uncertainty and avoid implying traffic or revenue forecasts.
   - Keep the underlying calculation available for internal ranking.

10. **Executive summary**
    - Re-audit the headline verdict and highest-value actions after applicability fixes.
    - Prevent blanket detector failures from driving domain-level conclusions.
    - Distinguish “observed on this cohort” from “site-wide conclusion.”

11. **Report exports**
    - Export the complete report dataset, not only the visual report:
      - JSON
      - CSV
      - XML
      - Markdown
    - Include crawl decisions, response metadata, source provenance, detector applicability, and observation dates.

12. **Surface-by-surface report audit**
    - Audit each expanded report section for unsupported claims and misleading labels.
    - Start with:
      1. Executive summary
      2. Observation dates and freshness
      3. Crawl coverage
      4. Sitemap and URL provenance
      5. Page-level findings
      6. AI/GEO evidence
      7. Recommendations and benefit-to-fix

The best next task is the crawler/output reliability cluster: non-HTML handling, disappearing jobs, and dataset exports. Those are foundational; the report audit will remain unreliable until they are fixed.
