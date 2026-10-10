from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import urlsplit
from services.url_policy import crawl_url_identity
from services.url_policy import site_page_identity


def _page_identity(value: str) -> str:
    """Compare sitemap and crawl URLs as site pages, not literal spellings.

    A sitemap may legitimately omit a trailing slash while the server's final
    URL includes it.  That is not an uncrawled page.
    """
    try:
        host = urlsplit(value).hostname or ""
        return site_page_identity(value, host) or crawl_url_identity(value)
    except Exception:
        return crawl_url_identity(value)

def reconcile_sitemap_urls(sitemap_entries, crawl_pages, inventory_urls=(), *, now=None):
    """Return evidence rows without turning applicability into a page failure."""
    pages = {}
    for row in crawl_pages or []:
        for value in (row.get("url"), row.get("requested_url"), row.get("final_url"), row.get("canonical")):
            if value:
                pages[_page_identity(str(value))] = row
    inventory = {}
    for row in inventory_urls or []:
        for value in (row.get("url"), row.get("final_url"), row.get("canonical_url"), row.get("duplicate_of_url")):
            if value:
                inventory[_page_identity(str(value))] = row
    observed = now or datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows = []
    for entry in sitemap_entries or []:
        url = str(entry.get("url") if isinstance(entry, dict) else getattr(entry, "url", ""))
        identity = _page_identity(url)
        page = pages.get(identity) or {}
        inv = inventory.get(identity) or {}
        status = page.get("status_code")
        canonical = page.get("canonical") or ""
        reasons = []
        if status and 300 <= int(status) < 400: reasons.append("redirect_in_sitemap")
        if status and int(status) >= 400: reasons.append("error_status_in_sitemap")
        if page.get("robots_allowed") is False: reasons.append("robots_blocked_in_sitemap")
        if page.get("robots_meta") and "noindex" in str(page.get("robots_meta")).lower(): reasons.append("noindex_in_sitemap")
        if canonical and _page_identity(canonical) != identity: reasons.append("canonical_mismatch")
        if page and page.get("resource_type") and page.get("resource_type") != "html": reasons.append("non_html_sitemap_resource")
        if not page and not inv: reasons.append("not_crawled")
        if inv and inv.get("source") and "sitemap" not in str(inv.get("source")):
            reasons.append("internal_url_missing_from_sitemap")
        rows.append({"url": url, "source_sitemap": entry.get("source_sitemap", "") if isinstance(entry, dict) else getattr(entry, "source_sitemap", ""), "lastmod": entry.get("lastmod", "") if isinstance(entry, dict) else getattr(entry, "lastmod", ""), "observed_at": observed, "status_code": status, "canonical": canonical, "resource_type": page.get("resource_type", ""), "findings": reasons})
    return rows
