from __future__ import annotations

from datetime import datetime, timezone

def reconcile_sitemap_urls(sitemap_entries, crawl_pages, inventory_urls=(), *, now=None):
    """Return evidence rows without turning applicability into a page failure."""
    pages = {str(row.get("url") or row.get("requested_url") or ""): row for row in crawl_pages or []}
    inventory = {str(row.get("url") or ""): row for row in inventory_urls or []}
    observed = now or datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows = []
    for entry in sitemap_entries or []:
        url = str(entry.get("url") if isinstance(entry, dict) else getattr(entry, "url", ""))
        page = pages.get(url) or {}
        inv = inventory.get(url) or {}
        status = page.get("status_code")
        canonical = page.get("canonical") or ""
        reasons = []
        if status and 300 <= int(status) < 400: reasons.append("redirect_in_sitemap")
        if status and int(status) >= 400: reasons.append("error_status_in_sitemap")
        if page.get("robots_allowed") is False: reasons.append("robots_blocked_in_sitemap")
        if page.get("robots_meta") and "noindex" in str(page.get("robots_meta")).lower(): reasons.append("noindex_in_sitemap")
        if canonical and canonical != url: reasons.append("canonical_mismatch")
        if page and page.get("resource_type") and page.get("resource_type") != "html": reasons.append("non_html_sitemap_resource")
        if not page and not inv: reasons.append("not_crawled")
        if inv and inv.get("source") and "sitemap" not in str(inv.get("source")):
            reasons.append("internal_url_missing_from_sitemap")
        rows.append({"url": url, "source_sitemap": entry.get("source_sitemap", "") if isinstance(entry, dict) else getattr(entry, "source_sitemap", ""), "lastmod": entry.get("lastmod", "") if isinstance(entry, dict) else getattr(entry, "lastmod", ""), "observed_at": observed, "status_code": status, "canonical": canonical, "resource_type": page.get("resource_type", ""), "findings": reasons})
    return rows
