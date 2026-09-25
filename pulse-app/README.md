# Audit App

This directory contains the project's own SEO / GEO / AEO audit application.

OpenGSC is kept separately under `../opengsc-repo/`.

## Runtime

The root `docker-compose.yml` is authoritative.

- OpenGSC: port 4017
- Audit App: port 4018

## Structure

- `app.py` — current Flask application shell
- `audits/geo_aeo/` — GEO/AEO capture and scoring
- `crawlers/` — crawl/discovery functionality
- `integrations/dataforseo/` — DataForSEO integration
- `services/` — application services
- `templates/` and `static/` — UI

## OpenGSC integration

For now the Audit App keeps the existing direct read-only SQLite integration.

The `opengsc-data` Docker volume is mounted writable into OpenGSC and read-only into the Audit App.

## Crawl model

Pulse uses two independent crawl speeds:

- An initial priority crawl selects the configured 10–20 highest-value eligible pages from a classified URL inventory. Report refresh waits only for this bounded batch.
- Background evidence crawls run as separate delayed durable jobs. They consume small batches, observe daily/weekly budgets, preserve the frontier across restarts, and enrich later reports.

Sitemap indexes are traversed as inventories. The originating child sitemap, content classification, eligibility decision, priority score, and exclusion/defer reason are stored in `crawl_url_inventory`; a sitemap entry is not automatically a crawl instruction.

Operators can configure crawl policy and inspect/pause/resume/cancel runs from **Tools → Crawler**. Cancellation is durable and a cancelled job is not reclaimed after a worker restart.

## Database upgrade

Apply migrations before restarting either the web process or worker:

```bash
python -m db.migrate up --db "${RESEARCH_DB:-/data/audit/research.db}"
python -m db.migrate status --db "${RESEARCH_DB:-/data/audit/research.db}"
```

Migration `0007_crawl_frontier_and_job_controls.sql` adds the crawl inventory/frontier, domain crawl policies, delayed background jobs, page fingerprints, crawl observability, and persistent pause/cancel fields.
