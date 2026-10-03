from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from xml.sax.saxutils import escape

from db.migrate import migrate_up
from db.sqlite import connect_sqlite
from crawlers.seo import best_effort_site_page
from services.crawl_frontier import (
    normalize_candidate_url,
    select_initial_inventory,
    upsert_inventory_url,
)
from services.page_discovery import discover_sitemap_inventory
from services.page_discovery import SitemapEntry


FIXTURE = Path(__file__).parent / "fixtures" / "skeena"
DOMAIN = "skeenagoldsilver.com"


def test_crawled_url_is_added_to_auditable_site_page_inventory(tmp_path):
    db = tmp_path / "research.db"
    migrate_up(db)
    with connect_sqlite(db) as con:
        best_effort_site_page(con, "example.com", "https://example.com/about")
        con.commit()
        row = con.execute(
            "SELECT domain,path,url,source,discovered_at,updated_at FROM site_page WHERE domain=? AND url=?",
            ("example.com", "https://example.com/about"),
        ).fetchone()
    assert row is not None
    assert row["path"] == "/about"
    assert row["source"] == "crawl"
    assert row["discovered_at"]
    assert row["updated_at"]


@dataclass
class Response:
    content: bytes


class FixtureFetcher:
    def __init__(self, mapping):
        self.mapping = mapping

    def get(self, url, **_kwargs):
        return Response(self.mapping[url])


def _urlset(urls):
    body = "".join(
        f"<url><loc>{escape(url)}</loc><lastmod>2026-01-01</lastmod></url>" for url in urls
    )
    return (
        '<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        + body
        + "</urlset>"
    ).encode()


def _fixture_mapping():
    manifest = json.loads((FIXTURE / "manifest.json").read_text())
    root_url = manifest["source"]
    mapping = {root_url: (FIXTURE / "sitemap_index.xml").read_bytes()}
    representatives = {
        "page-sitemap.xml": [
            "https://skeenagoldsilver.com/",
            "https://skeenagoldsilver.com/company/",
            "https://skeenagoldsilver.com/investors/",
            "https://skeenagoldsilver.com/projects/eskay-creek/",
            "https://skeenagoldsilver.com/projects/eskay-creek/technical-details/",
            "https://skeenagoldsilver.com/sustainability/",
            "https://skeenagoldsilver.com/contact/",
        ],
        "news-release-sitemap1.xml": [
            "https://skeenagoldsilver.com/news/skeena-announces-proposed-financing/",
            "https://skeenagoldsilver.com/news/skeena-announces-pricing-of-financing/",
            "https://skeenagoldsilver.com/news/skeena-completes-financing/",
        ],
        "category-sitemap.xml": [
            "https://skeenagoldsilver.com/category/uncategorized/"
        ],
    }
    prefixes = {
        "post-sitemap.xml": "blog",
        "page-sitemap.xml": "company-page",
        "article-sitemap.xml": "articles/coverage",
        "corporate-media-sitemap.xml": "corporate-media/item",
        "news-release-sitemap1.xml": "news/release-a",
        "news-release-sitemap2.xml": "news/release-b",
        "webcast-sitemap.xml": "webcasts/event",
        "category-sitemap.xml": "category/uncategorized",
    }
    for child, count in manifest["counts"].items():
        urls = list(representatives.get(child, []))
        for index in range(count - len(urls)):
            urls.append(f"https://{DOMAIN}/{prefixes[child]}-{index}/")
        mapping[f"https://{DOMAIN}/{child}"] = _urlset(urls)
    return manifest, mapping


def test_skeena_fixture_preserves_450_entries_and_child_provenance(tmp_path):
    manifest, mapping = _fixture_mapping()
    entries, errors = discover_sitemap_inventory(
        manifest["source"], DOMAIN, fetcher=FixtureFetcher(mapping)
    )
    assert errors == []
    assert len(entries) == manifest["total"] == 450
    assert len({entry.source_sitemap for entry in entries}) == 8

    db = tmp_path / "pulse.db"
    migrate_up(db)
    with connect_sqlite(db) as con:
        for entry in entries:
            upsert_inventory_url(
                con,
                DOMAIN,
                entry.url,
                source="sitemap",
                source_sitemap=entry.source_sitemap,
                sitemap_lastmod=entry.lastmod,
                sitemap_priority=entry.priority,
            )
        initial = select_initial_inventory(con, DOMAIN, 15)
        uncategorized = con.execute(
            "SELECT eligibility,decision_reason FROM crawl_url_inventory WHERE url=?",
            (f"https://{DOMAIN}/category/uncategorized",),
        ).fetchone()
        news_count = sum(row["classification"] == "news_release" for row in initial)
        core_count = sum(row["classification"] == "core_page" for row in initial)
        initial_urls = {row["url"] for row in initial}

    assert len(initial) == 15
    assert core_count >= 8
    assert 2 <= news_count <= 4
    assert f"https://{DOMAIN}/news/skeena-completes-financing" in initial_urls
    assert f"https://{DOMAIN}/news/skeena-announces-proposed-financing" not in initial_urls
    assert f"https://{DOMAIN}/news/skeena-announces-pricing-of-financing" not in initial_urls
    assert uncategorized["eligibility"] == "excluded"
    assert uncategorized["decision_reason"] == "taxonomy_archive_default"


def test_skeena_parameter_and_www_variants_do_not_multiply_inventory(tmp_path):
    db = tmp_path / "pulse.db"
    migrate_up(db)
    variants = [
        "https://www.skeenagoldsilver.com/blog/?utm_source=x&query-15-page=2&cst=",
        "https://skeenagoldsilver.com/blog/?cst=&query-15-page=2#results",
        "https://skeenagoldsilver.com/blog/?query-15-page=2&cst=",
    ]
    normalized = {normalize_candidate_url(url, DOMAIN) for url in variants}
    assert normalized == {f"https://{DOMAIN}/blog/?cst=&query-15-page=2"}
    with connect_sqlite(db) as con:
        for url in variants:
            upsert_inventory_url(con, DOMAIN, url, source="internal_link")
        rows = con.execute(
            "SELECT url,eligibility,decision_reason FROM crawl_url_inventory WHERE domain=?",
            (DOMAIN,),
        ).fetchall()
    assert len(rows) == 1
    assert rows[0]["eligibility"] == "excluded"
    assert rows[0]["decision_reason"] == "pagination_query"


def test_initial_crawl_is_bounded_and_leaves_background_inventory(tmp_path, monkeypatch):
    from crawlers import seo

    db = tmp_path / "pulse.db"
    migrate_up(db)
    with connect_sqlite(db) as con:
        run_id = con.execute(
            """
            INSERT INTO crawl_run(domain,base_url,status,page_cap,delay_ms,obey_robots,crawl_mode)
            VALUES (?,?, 'queued',2,0,1,'initial')
            """,
            (DOMAIN, f"https://{DOMAIN}"),
        ).lastrowid
        con.commit()

    entries = [
        SitemapEntry(f"https://{DOMAIN}/company-page-{index}", f"https://{DOMAIN}/page-sitemap.xml")
        for index in range(5)
    ]
    monkeypatch.setattr(
        seo,
        "discover_domain_sitemap_inventory",
        lambda *_args, **_kwargs: (entries, f"https://{DOMAIN}/sitemap_index.xml", []),
    )
    monkeypatch.setattr(seo, "build_robot_parser", lambda _url: (None, f"https://{DOMAIN}/robots.txt", None))
    monkeypatch.setattr(
        seo,
        "fetch",
        lambda url, **_kwargs: {
            "ok": True,
            "status": 200,
            "final_url": url,
            "content_type": "text/html",
            "content_length": 100,
            "elapsed_ms": 1,
            "headers": {},
            "body": b"<html><head><title>Evidence page</title></head><body><h1>Evidence</h1><p>Useful company evidence.</p></body></html>",
            "error": None,
        },
    )

    status = seo.crawl_worker(
        run_id,
        DOMAIN,
        f"https://{DOMAIN}",
        2,
        0,
        True,
        lambda: connect_sqlite(db),
        crawl_mode="initial",
    )
    assert status == "completed"
    with connect_sqlite(db, readonly=True) as con:
        run = con.execute("SELECT * FROM crawl_run WHERE id=?", (run_id,)).fetchone()
        inventory = con.execute(
            "SELECT COUNT(*) AS n FROM crawl_url_inventory WHERE domain=?", (DOMAIN,)
        ).fetchone()["n"]
        frontier = con.execute(
            "SELECT COUNT(*) AS n FROM crawl_frontier WHERE crawl_run_id=?", (run_id,)
        ).fetchone()["n"]
    assert inventory == 6  # homepage plus five sitemap entries
    assert frontier == 2
    assert run["pages_crawled"] == 2
    assert run["pages_remaining"] == 4
