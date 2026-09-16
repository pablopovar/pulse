from __future__ import annotations

import gzip
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

from db.sqlite import connect_sqlite
from integrations.opengsc_adapter import OpenGSCAdapter
from services.safe_fetcher import SafeFetcher, safe_fetcher
from services.url_policy import site_page_identity as normalize_site_page_url, url_path as site_page_path

DEFAULT_MAX_DEPTH = 5
DEFAULT_MAX_URLS = 20_000
SITEMAP_CONTENT_TYPES = {
    "application/xml", "text/xml", "text/plain", "application/gzip",
    "application/x-gzip", "application/octet-stream",
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _parse_sitemap(raw: bytes, source_url: str):
    if raw[:2] == b"\x1f\x8b" or source_url.lower().endswith(".gz"):
        raw = gzip.decompress(raw)
    return ET.fromstring(raw)


def discover_sitemap_urls(
    sitemap_url: str,
    domain: str,
    *,
    fetcher: SafeFetcher = safe_fetcher,
    max_depth: int = DEFAULT_MAX_DEPTH,
    max_urls: int = DEFAULT_MAX_URLS,
) -> tuple[set[str], list[str]]:
    """Traverse one sitemap tree and return canonical site-page URLs plus child errors.

    A failed child sitemap is recorded but does not discard URLs already obtained
    from healthy siblings. Failure of the root sitemap is raised to the caller.
    """
    seen_sitemaps: set[str] = set()
    pages: set[str] = set()
    errors: list[str] = []

    def visit(url: str, depth: int, *, root: bool = False) -> None:
        if url in seen_sitemaps:
            return
        if depth > max_depth:
            errors.append(f"recursion limit reached at {url}")
            return
        if len(pages) >= max_urls:
            return
        seen_sitemaps.add(url)
        try:
            response = fetcher.get(
                url,
                headers={"User-Agent": "Pulse/1.0"},
                max_response_bytes=5 * 1024 * 1024,
                allowed_content_types=SITEMAP_CONTENT_TYPES,
            )
            root_node = _parse_sitemap(response.content, url)
        except Exception as exc:
            if root:
                raise
            errors.append(f"{url}: {exc}")
            return

        root_name = root_node.tag.rsplit("}", 1)[-1].lower()
        locations = [(loc.text or "").strip() for loc in root_node.findall(".//{*}loc")]
        if root_name == "sitemapindex":
            for child in locations:
                if child:
                    visit(child, depth + 1)
            return

        for raw_url in locations:
            normalized = normalize_site_page_url(raw_url, domain)
            if normalized:
                pages.add(normalized)
                if len(pages) >= max_urls:
                    break

    visit(sitemap_url, 0, root=True)
    return pages, errors


def discover_domain_sitemap(
    domain: str,
    *,
    fetcher: SafeFetcher = safe_fetcher,
    max_depth: int = DEFAULT_MAX_DEPTH,
    max_urls: int = DEFAULT_MAX_URLS,
) -> tuple[set[str], str, list[str]]:
    failures: list[str] = []
    for sitemap_url in (f"https://{domain}/sitemap.xml", f"https://{domain}/sitemap_index.xml"):
        try:
            urls, child_errors = discover_sitemap_urls(
                sitemap_url,
                domain,
                fetcher=fetcher,
                max_depth=max_depth,
                max_urls=max_urls,
            )
            if urls:
                return urls, sitemap_url, child_errors
            failures.extend(child_errors)
            failures.append(f"{sitemap_url}: empty sitemap")
        except Exception as exc:
            failures.append(f"{sitemap_url}: {exc}")
    raise RuntimeError("Could not retrieve sitemap: " + " | ".join(failures))


def get_discovery_state(db_path: str | Path, domain: str) -> dict:
    with connect_sqlite(db_path, readonly=True) as con:
        row = con.execute(
            "SELECT * FROM domain_discovery_state WHERE domain=? COLLATE NOCASE", (domain,)
        ).fetchone()
    if row:
        return dict(row)
    return {
        "domain": domain, "status": "not_started", "job_id": "", "sitemap_source": "",
        "sitemap_count": 0, "ranking_count": 0, "last_successful_at": None,
        "error": "", "created_at": None, "updated_at": None,
    }


def set_discovery_state(
    db_path: str | Path,
    domain: str,
    status: str,
    *,
    job_id: str = "",
    worker_id: str | None = None,
    sitemap_source: str | None = None,
    sitemap_count: int | None = None,
    ranking_count: int | None = None,
    error: str = "",
    successful: bool = False,
) -> dict:
    """Update the current discovery projection.

    When ``worker_id`` is supplied, ownership of ``job_id`` is verified inside
    the same SQLite write transaction as the projection update. This prevents a
    stale/recovered worker from publishing ``ready`` or ``failed`` state after
    its lease has been lost. Request-side ``queued`` updates intentionally omit
    ``worker_id`` because the job has not been claimed yet.
    """
    if status not in {"not_started", "queued", "running", "ready", "failed"}:
        raise ValueError(f"invalid discovery status: {status}")
    if worker_id and not job_id:
        raise ValueError("job_id is required when worker_id is provided")

    ts = now()
    with connect_sqlite(db_path) as con:
        con.execute("BEGIN IMMEDIATE")
        if worker_id:
            owned = con.execute(
                """
                SELECT 1
                FROM durable_job
                WHERE id=?
                  AND status='running'
                  AND worker_id=?
                  AND lease_expires_at IS NOT NULL
                  AND lease_expires_at>=?
                """,
                (job_id, worker_id, ts),
            ).fetchone()
            if owned is None:
                con.rollback()
                raise RuntimeError(
                    "Durable job ownership lost before discovery-state publication."
                )

        existing = con.execute(
            "SELECT * FROM domain_discovery_state WHERE domain=? COLLATE NOCASE", (domain,)
        ).fetchone()
        prior = dict(existing) if existing else {}
        con.execute(
            """
            INSERT INTO domain_discovery_state(
                domain,status,job_id,sitemap_source,sitemap_count,ranking_count,
                last_successful_at,error,created_at,updated_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(domain) DO UPDATE SET
                status=excluded.status,
                job_id=excluded.job_id,
                sitemap_source=excluded.sitemap_source,
                sitemap_count=excluded.sitemap_count,
                ranking_count=excluded.ranking_count,
                last_successful_at=excluded.last_successful_at,
                error=excluded.error,
                updated_at=excluded.updated_at
            """,
            (
                domain, status, job_id or prior.get("job_id", ""),
                prior.get("sitemap_source", "") if sitemap_source is None else sitemap_source,
                int(prior.get("sitemap_count", 0) if sitemap_count is None else sitemap_count),
                int(prior.get("ranking_count", 0) if ranking_count is None else ranking_count),
                ts if successful else prior.get("last_successful_at"),
                error, prior.get("created_at") or ts, ts,
            ),
        )
        con.commit()
    return get_discovery_state(db_path, domain)


def sync_site_pages(
    domain: str,
    *,
    research_db: str | Path,
    opengsc_db: str | Path,
    site_id: str | None,
    fetcher: SafeFetcher = safe_fetcher,
    max_depth: int = DEFAULT_MAX_DEPTH,
    max_urls: int = DEFAULT_MAX_URLS,
) -> dict:
    """Discover pages and upsert them without deleting the last good page set."""
    sitemap_urls, sitemap_source, child_errors = discover_domain_sitemap(
        domain, fetcher=fetcher, max_depth=max_depth, max_urls=max_urls
    )
    ranking_rows = OpenGSCAdapter(opengsc_db).gsc_keyword_rows(site_id)
    ranking_urls = {
        normalized
        for row in ranking_rows
        for normalized in [normalize_site_page_url(row.get("page"), domain)]
        if normalized
    }
    ts = now()
    with connect_sqlite(research_db) as con:
        con.execute("BEGIN IMMEDIATE")
        for url in sorted(sitemap_urls):
            con.execute(
                """
                INSERT INTO site_page(domain,url,path,source,discovered_at,updated_at)
                VALUES (?,?,?,'sitemap',?,?)
                ON CONFLICT(domain,url) DO UPDATE SET
                    path=excluded.path,
                    source=CASE WHEN site_page.source='ranking' THEN 'sitemap+ranking' ELSE site_page.source END,
                    updated_at=excluded.updated_at
                """,
                (domain, url, site_page_path(url), ts, ts),
            )
        for url in sorted(ranking_urls):
            con.execute(
                """
                INSERT INTO site_page(domain,url,path,source,discovered_at,updated_at)
                VALUES (?,?,?,'ranking',?,?)
                ON CONFLICT(domain,url) DO UPDATE SET
                    source=CASE WHEN site_page.source='sitemap' THEN 'sitemap+ranking' ELSE site_page.source END,
                    updated_at=excluded.updated_at
                """,
                (domain, url, site_page_path(url), ts, ts),
            )
        con.commit()
    return {
        "sitemap_count": len(sitemap_urls),
        "ranking_count": len(ranking_urls),
        "sitemap_source": sitemap_source,
        "warnings": child_errors,
    }
