from __future__ import annotations

from dataclasses import dataclass

import pytest

from db.migrate import migrate_up
from db.sqlite import connect_sqlite
from services.page_discovery import (
    discover_sitemap_urls,
    get_discovery_state,
    set_discovery_state,
    sync_site_pages,
)


@dataclass
class Resp:
    content: bytes


class FakeFetcher:
    def __init__(self, mapping):
        self.mapping = dict(mapping)
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append(url)
        value = self.mapping[url]
        if isinstance(value, BaseException):
            raise value
        return Resp(value.encode() if isinstance(value, str) else value)


def sitemap(*urls):
    body = "".join(f"<url><loc>{u}</loc></url>" for u in urls)
    return f'<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{body}</urlset>'


def sitemap_index(*urls):
    body = "".join(f"<sitemap><loc>{u}</loc></sitemap>" for u in urls)
    return f'<?xml version="1.0"?><sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{body}</sitemapindex>'


def test_sitemap_index_and_nested_sitemap():
    fetcher = FakeFetcher({
        "https://example.com/sitemap.xml": sitemap_index(
            "https://example.com/a.xml", "https://example.com/nested.xml"
        ),
        "https://example.com/a.xml": sitemap(
            "https://example.com/", "https://example.com/about/"
        ),
        "https://example.com/nested.xml": sitemap_index("https://example.com/b.xml"),
        "https://example.com/b.xml": sitemap("https://example.com/contact?x=1#frag"),
    })
    urls, errors = discover_sitemap_urls(
        "https://example.com/sitemap.xml", "example.com", fetcher=fetcher
    )
    assert urls == {
        "https://example.com/",
        "https://example.com/about",
        "https://example.com/contact",
    }
    assert errors == []


def test_duplicate_urls_are_deduplicated():
    fetcher = FakeFetcher({
        "https://example.com/sitemap.xml": sitemap(
            "https://example.com/a", "https://example.com/a/", "https://example.com/a#x"
        )
    })
    urls, _ = discover_sitemap_urls(
        "https://example.com/sitemap.xml", "example.com", fetcher=fetcher
    )
    assert urls == {"https://example.com/a"}


def test_malformed_root_xml_fails():
    fetcher = FakeFetcher({"https://example.com/sitemap.xml": "<broken"})
    with pytest.raises(Exception):
        discover_sitemap_urls(
            "https://example.com/sitemap.xml", "example.com", fetcher=fetcher
        )


def test_failed_child_is_reported_without_losing_siblings():
    fetcher = FakeFetcher({
        "https://example.com/sitemap.xml": sitemap_index(
            "https://example.com/good.xml", "https://example.com/bad.xml"
        ),
        "https://example.com/good.xml": sitemap("https://example.com/good"),
        "https://example.com/bad.xml": RuntimeError("child unavailable"),
    })
    urls, errors = discover_sitemap_urls(
        "https://example.com/sitemap.xml", "example.com", fetcher=fetcher
    )
    assert urls == {"https://example.com/good"}
    assert any("child unavailable" in item for item in errors)


def test_recursion_limit_stops_deeper_children():
    fetcher = FakeFetcher({
        "https://example.com/sitemap.xml": sitemap_index("https://example.com/1.xml"),
        "https://example.com/1.xml": sitemap_index("https://example.com/2.xml"),
        "https://example.com/2.xml": sitemap("https://example.com/deep"),
    })
    urls, errors = discover_sitemap_urls(
        "https://example.com/sitemap.xml", "example.com", fetcher=fetcher, max_depth=1
    )
    assert urls == set()
    assert any("recursion limit" in item for item in errors)


def test_url_limit_is_enforced():
    fetcher = FakeFetcher({
        "https://example.com/sitemap.xml": sitemap(
            *[f"https://example.com/p/{i}" for i in range(10)]
        )
    })
    urls, _ = discover_sitemap_urls(
        "https://example.com/sitemap.xml", "example.com", fetcher=fetcher, max_urls=3
    )
    assert len(urls) == 3


def test_empty_sitemap_returns_empty_set():
    fetcher = FakeFetcher({"https://example.com/sitemap.xml": sitemap()})
    urls, errors = discover_sitemap_urls(
        "https://example.com/sitemap.xml", "example.com", fetcher=fetcher
    )
    assert urls == set()
    assert errors == []


def test_failed_refresh_preserves_last_successful_state(tmp_path):
    db = tmp_path / "pulse.db"
    migrate_up(db)
    set_discovery_state(
        db,
        "example.com",
        "ready",
        job_id="old",
        sitemap_source="https://example.com/sitemap.xml",
        sitemap_count=10,
        ranking_count=2,
        successful=True,
    )
    before = get_discovery_state(db, "example.com")
    set_discovery_state(db, "example.com", "failed", job_id="new", error="network")
    after = get_discovery_state(db, "example.com")
    assert after["status"] == "failed"
    assert after["last_successful_at"] == before["last_successful_at"]
    assert after["sitemap_count"] == 10
    assert after["ranking_count"] == 2


def test_sync_upserts_without_deleting_existing_pages(tmp_path):
    research = tmp_path / "research.db"
    opengsc = tmp_path / "missing-opengsc.db"
    migrate_up(research)
    with connect_sqlite(research) as con:
        con.execute(
            "INSERT INTO site_page(domain,url,path,source,discovered_at,updated_at) VALUES ('example.com','https://example.com/old','/old','sitemap','x','x')"
        )
        con.commit()
    fetcher = FakeFetcher({
        "https://example.com/sitemap.xml": sitemap("https://example.com/new")
    })
    outcome = sync_site_pages(
        "example.com",
        research_db=research,
        opengsc_db=opengsc,
        site_id=None,
        fetcher=fetcher,
    )
    assert outcome["sitemap_count"] == 1
    with connect_sqlite(research, readonly=True) as con:
        urls = {row[0] for row in con.execute("SELECT url FROM site_page WHERE domain='example.com'")}
    assert urls == {"https://example.com/old", "https://example.com/new"}
