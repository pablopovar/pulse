from __future__ import annotations

from services.sitemap_reconciliation import reconcile_sitemap_urls


def test_sitemap_without_trailing_slash_matches_crawled_final_url():
    rows = reconcile_sitemap_urls(
        [{"url": "https://example.test/about", "source_sitemap": "https://example.test/sitemap.xml"}],
        [{"url": "https://example.test/about/", "status_code": 200, "resource_type": "html"}],
        [],
    )
    assert rows[0]["status_code"] == 200
    assert "not_crawled" not in rows[0]["findings"]


def test_sitemap_keeps_actual_redirect_finding():
    rows = reconcile_sitemap_urls(
        [{"url": "https://example.test/old"}],
        [{"url": "https://example.test/old/", "status_code": 301, "resource_type": "html"}],
        [],
    )
    assert "redirect_in_sitemap" in rows[0]["findings"]
