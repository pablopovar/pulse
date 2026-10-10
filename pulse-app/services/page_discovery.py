from __future__ import annotations

import gzip
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
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
    "application/x-gzip", "application/octet-stream", "application/json",
}
ROOT_INVENTORY_PATHS = (
    "sitemap.xml", "sitemap_index.xml", "sitemap.xml.gz", "sitemap.txt",
    "urllist.txt", "urls.txt", "atom.xml", "rss.xml", "feed.xml",
    "mrss.xml", "sitemap.json",
)


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _decode_inventory(raw: bytes, source_url: str) -> bytes:
    if raw[:2] == b"\x1f\x8b" or source_url.lower().endswith(".gz"):
        return gzip.decompress(raw)
    return raw


def _parse_non_xml_inventory(raw: bytes, source_url: str) -> list[str] | None:
    """Parse explicit URL lists. JSON is a pragmatic inventory format, not a sitemap standard."""
    text = raw.decode("utf-8", errors="replace").strip()
    if source_url.lower().endswith(".json") or text.startswith(("[", "{")):
        try:
            value = json.loads(text)
        except json.JSONDecodeError:
            return []
        found: list[str] = []
        def walk(item):
            if isinstance(item, str) and item.startswith(("http://", "https://")):
                found.append(item)
            elif isinstance(item, list):
                for child in item:
                    walk(child)
            elif isinstance(item, dict):
                for child in item.values():
                    walk(child)
        walk(value)
        return found
    if source_url.lower().endswith((".txt", "/urls", "/urllist")):
        return [line.strip() for line in text.splitlines() if line.strip().startswith(("http://", "https://"))]
    return None


@dataclass(frozen=True)
class SitemapEntry:
    url: str
    source_sitemap: str
    lastmod: str = ""
    priority: float | None = None


def inspect_agent_readiness_sources(
    domain: str, *, fetcher: SafeFetcher = safe_fetcher
) -> list[dict]:
    """Collect llms.txt evidence without treating it as crawl authority or ranking input."""
    observations = []
    for name in ("llms.txt", "llms-full.txt"):
        url = f"https://{domain}/{name}"
        try:
            response = fetcher.get(
                url,
                headers={"User-Agent": "Pulse/1.0"},
                max_response_bytes=1024 * 1024,
                allowed_content_types={"text/plain", "text/markdown", "text/html", "application/octet-stream"},
            )
            text = response.content.decode("utf-8", errors="replace")
            links = re.findall(r"https?://[^\s)>\]]+", text)
            headings = re.findall(r"^#{1,6}\s+(.+?)\s*$", text, flags=re.M)
            sections = re.split(r"^#{1,6}\s+.+$", text, flags=re.M)
            empty_sections = sum(1 for section in sections[1:] if not section.strip())
            malformed = bool(re.search(r"^#{1,6}[^\s#]", text, flags=re.M) or text.count("```") % 2)
            parse_status = "malformed" if malformed else ("valid_markdown" if text.lstrip().startswith("#") else "plain_text")
            headers = dict(getattr(response, "headers", {}) or {})
            observations.append({
                "name": name, "url": url, "status": "available", "http_status": getattr(response, "status_code", 200), "bytes": len(response.content),
                "content_type": getattr(response, "headers", {}).get("content-type", ""),
                "headers": headers,
                "sha256": hashlib.sha256(response.content).hexdigest(),
                "observed_at": now(), "parse_status": parse_status,
                "headings": headings[:200], "section_count": len(headings), "empty_sections": empty_sections,
                "malformed_markdown_indicators": malformed,
                "duplicate_links": len(links) - len(set(links)), "off_domain_links": sorted({link for link in links if domain not in link})[:200], "links": sorted(set(links))[:500], "content": text, "error": "",
            })
        except Exception as exc:
            error_text = str(exc)
            error_name = exc.__class__.__name__.lower()
            if "404" in error_text or "not found" in error_text.lower():
                source_status = "absent"
            elif "large" in error_name or "size" in error_name or "large" in error_text.lower():
                source_status = "oversized"
            elif "content" in error_name or "content type" in error_text.lower():
                source_status = "unsupported_content_type"
            else:
                source_status = "fetch_failed"
            observations.append({
                "name": name, "url": url, "status": source_status, "bytes": 0,
                "http_status": getattr(getattr(exc, "response", None), "status_code", None), "content_type": "", "headers": {}, "sha256": "", "observed_at": now(),
                "parse_status": "unavailable", "headings": [], "links": [], "content": "", "error": str(exc),
            })
    return observations


def discover_sitemap_inventory(
    sitemap_url: str,
    domain: str,
    *,
    fetcher: SafeFetcher = safe_fetcher,
    max_depth: int = DEFAULT_MAX_DEPTH,
    max_urls: int = DEFAULT_MAX_URLS,
) -> tuple[list[SitemapEntry], list[str]]:
    """Traverse a sitemap tree without discarding child-sitemap provenance."""

    seen_sitemaps: set[str] = set()
    entries: dict[str, SitemapEntry] = {}
    errors: list[str] = []

    def visit(url: str, depth: int, *, root: bool = False) -> None:
        if url in seen_sitemaps:
            return
        if depth > max_depth:
            errors.append(f"recursion limit reached at {url}")
            return
        if len(entries) >= max_urls:
            return
        seen_sitemaps.add(url)
        try:
            response = fetcher.get(
                url,
                headers={"User-Agent": "Pulse/1.0"},
                max_response_bytes=5 * 1024 * 1024,
                allowed_content_types=SITEMAP_CONTENT_TYPES,
            )
            raw = _decode_inventory(response.content, url)
            listed_urls = _parse_non_xml_inventory(raw, url)
            root_node = None if listed_urls is not None else ET.fromstring(raw)
        except Exception as exc:
            if root:
                raise
            errors.append(f"{url}: {exc}")
            return

        if listed_urls is not None:
            for item_url in listed_urls:
                normalized = normalize_site_page_url(item_url, domain)
                if normalized:
                    entries.setdefault(normalized, SitemapEntry(normalized, url))
                if len(entries) >= max_urls:
                    break
            return

        root_name = root_node.tag.rsplit("}", 1)[-1].lower()
        if root_name == "sitemapindex":
            for sitemap in root_node.findall(".//{*}sitemap"):
                loc = sitemap.find("{*}loc")
                child = (loc.text or "").strip() if loc is not None else ""
                if child:
                    visit(child, depth + 1)
            return

        # Standard sitemap urlsets plus RSS/Atom feeds. Feed entries are only
        # inventory leads; they do not receive sitemap-specific priority data.
        items = root_node.findall(".//{*}url")
        feed_items = root_node.findall(".//{*}item") + root_node.findall(".//{*}entry")
        for item in items + feed_items:
            loc = item.find("{*}loc")
            if loc is None:
                loc = item.find("{*}link")
            if loc is not None and not (loc.text or "").strip():
                href = loc.attrib.get("href", "")
                if href:
                    loc = ET.Element("loc")
                    loc.text = href
            normalized = normalize_site_page_url(
                (loc.text or "").strip() if loc is not None else "", domain
            )
            if not normalized:
                continue
            lastmod_node = item.find("{*}lastmod")
            priority_node = item.find("{*}priority")
            try:
                priority = float((priority_node.text or "").strip()) if priority_node is not None else None
            except ValueError:
                priority = None
            entries.setdefault(
                normalized,
                SitemapEntry(
                    url=normalized,
                    source_sitemap=url,
                    lastmod=(lastmod_node.text or "").strip() if lastmod_node is not None else "",
                    priority=priority,
                ),
            )
            if len(entries) >= max_urls:
                break

    visit(sitemap_url, 0, root=True)
    return list(entries.values()), errors


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
    entries, errors = discover_sitemap_inventory(
        sitemap_url,
        domain,
        fetcher=fetcher,
        max_depth=max_depth,
        max_urls=max_urls,
    )
    return {entry.url for entry in entries}, errors


def discover_domain_sitemap_inventory(
    domain: str,
    *,
    fetcher: SafeFetcher = safe_fetcher,
    max_depth: int = DEFAULT_MAX_DEPTH,
    max_urls: int = DEFAULT_MAX_URLS,
) -> tuple[list[SitemapEntry], str, list[str]]:
    failures: list[str] = []
    root_failures: list[str] = []
    entries: dict[str, SitemapEntry] = {}
    sources: list[str] = []
    for path in ROOT_INVENTORY_PATHS:
        sitemap_url = f"https://{domain}/{path}"
        try:
            discovered, child_errors = discover_sitemap_inventory(
                sitemap_url,
                domain,
                fetcher=fetcher,
                max_depth=max_depth,
                max_urls=max_urls,
            )
            if discovered:
                sources.append(sitemap_url)
                for entry in discovered:
                    entries.setdefault(entry.url, entry)
                failures.extend(child_errors)
                if len(entries) >= max_urls:
                    break
                continue
            failures.extend(child_errors)
            root_failures.append(f"{sitemap_url}: empty sitemap")
        except Exception as exc:
            root_failures.append(f"{sitemap_url}: {exc}")
    if entries:
        return list(entries.values()), " + ".join(sources), failures
    raise RuntimeError("Could not retrieve sitemap: " + " | ".join(failures + root_failures))


def discover_domain_sitemap(
    domain: str,
    *,
    fetcher: SafeFetcher = safe_fetcher,
    max_depth: int = DEFAULT_MAX_DEPTH,
    max_urls: int = DEFAULT_MAX_URLS,
) -> tuple[set[str], str, list[str]]:
    entries, source, errors = discover_domain_sitemap_inventory(
        domain,
        fetcher=fetcher,
        max_depth=max_depth,
        max_urls=max_urls,
    )
    return {entry.url for entry in entries}, source, errors


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


def get_domain_readiness(db_path: str | Path, domain: str) -> dict:
    """Return the durable, read-only page-discovery state used by request views."""

    with connect_sqlite(db_path, readonly=True) as con:
        row = con.execute(
            "SELECT COUNT(*) AS n FROM site_page WHERE domain=? COLLATE NOCASE",
            (domain,),
        ).fetchone()
    pages = int(row["n"] if row else 0)
    discovery = get_discovery_state(db_path, domain)
    status = str(discovery.get("status") or "not_started")
    if pages:
        label = "Ready"
    elif status == "queued":
        label = "Discovery queued"
    elif status == "running":
        label = "Discovering"
    elif status == "failed":
        label = "Discovery failed"
    else:
        label = "Discovery not started"
    return {
        "ready": pages > 0,
        "label": label,
        "pages": pages,
        "status": status,
        "error": str(discovery.get("error") or ""),
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
