from __future__ import annotations

import gzip
import hashlib
import io
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Callable, Iterable
from services.safe_fetcher import SafeFetchError, safe_fetcher
from services.page_discovery import discover_domain_sitemap, discover_sitemap_urls
from services.page_discovery import discover_domain_sitemap_inventory
from services.crawl_frontier import (
    frontier_counts,
    get_policy,
    normalize_candidate_url,
    queue_frontier,
    remaining_background_inventory,
    schedule_next_crawl,
    select_initial_inventory,
    upsert_inventory_url,
    update_policy,
)
from services.url_policy import (
    crawl_url_identity as normalize_url,
    path_with_query as path_for_url,
    safe_url_join,
    same_hostname,
)
from jobs.store import cancel_job, enqueue_job, get_job, job_control_state, pause_job, resume_job


USER_AGENT = "PB-SEO-Crawler/0.1 (+website audit; single-domain; polite)"
ROBOTS_USER_AGENT = "PB-SEO-Crawler"
DEFAULT_PAGE_CAP = 100
DEFAULT_DELAY_MS = 250
MAX_BYTES = 5 * 1024 * 1024
TIMEOUT = 15
RESEARCH_DB_PATH = Path(os.environ.get("RESEARCH_DB", "/data/audit/research.db"))


def utcnow():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def same_site(url: str, domain: str) -> bool:
    return same_hostname(url, domain)


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title_parts = []
        self.in_title = False
        self.text_parts = []
        self.in_script = False
        self.in_style = False
        self.meta = {}
        self.links = []
        self.images = []
        self.h1 = []
        self.h2 = []
        self._heading = None
        self._heading_parts = []
        self.canonical = None
        self.hreflang = []
        self.lang = None
        self.schema_types = set()
        self.jsonld_parts = []
        self.in_jsonld = False

    def handle_starttag(self, tag, attrs):
        attrs = {str(k).lower(): (v or "") for k, v in attrs}
        tag = tag.lower()

        if tag == "html":
            self.lang = attrs.get("lang") or self.lang
        elif tag == "title":
            self.in_title = True
        elif tag == "script":
            self.in_script = True
            if "ld+json" in attrs.get("type", "").lower():
                self.in_jsonld = True
                self.jsonld_parts = []
        elif tag == "style":
            self.in_style = True
        elif tag in ("h1", "h2"):
            self._heading = tag
            self._heading_parts = []
        elif tag == "meta":
            name = (attrs.get("name") or attrs.get("property") or "").strip().lower()
            if name:
                self.meta.setdefault(name, attrs.get("content", "").strip())
        elif tag == "a":
            href = attrs.get("href", "").strip()
            if href:
                self.links.append((href, attrs.get("rel", "")))
        elif tag == "img":
            self.images.append({
                "src": attrs.get("src", "").strip(),
                "alt": attrs.get("alt", None),
            })
        elif tag == "link":
            rel = attrs.get("rel", "").lower()
            href = attrs.get("href", "").strip()
            if "canonical" in rel and href:
                self.canonical = href
            if "alternate" in rel and attrs.get("hreflang") and href:
                self.hreflang.append({
                    "lang": attrs.get("hreflang"),
                    "href": href,
                })

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag == "title":
            self.in_title = False
        elif tag == "script":
            if self.in_jsonld:
                raw = "".join(self.jsonld_parts).strip()
                if raw:
                    self._extract_schema(raw)
            self.in_jsonld = False
            self.in_script = False
        elif tag == "style":
            self.in_style = False
        elif tag in ("h1", "h2") and self._heading == tag:
            text = " ".join("".join(self._heading_parts).split())
            if text:
                (self.h1 if tag == "h1" else self.h2).append(text)
            self._heading = None
            self._heading_parts = []

    def handle_data(self, data):
        if self.in_title:
            self.title_parts.append(data)
        if self.in_jsonld:
            self.jsonld_parts.append(data)
        if self._heading:
            self._heading_parts.append(data)
        if not self.in_script and not self.in_style:
            self.text_parts.append(data)

    def _extract_schema(self, raw):
        try:
            value = json.loads(raw)
        except Exception:
            return

        def walk(obj):
            if isinstance(obj, dict):
                t = obj.get("@type")
                if isinstance(t, str):
                    self.schema_types.add(t)
                elif isinstance(t, list):
                    self.schema_types.update(str(x) for x in t if x)
                for v in obj.values():
                    walk(v)
            elif isinstance(obj, list):
                for v in obj:
                    walk(v)

        walk(value)

    def result(self):
        text = " ".join(" ".join(self.text_parts).split())
        words = re.findall(r"\b[\w'-]+\b", text, flags=re.UNICODE)
        return {
            "title": " ".join("".join(self.title_parts).split()),
            "description": self.meta.get("description", ""),
            "robots_meta": self.meta.get("robots", ""),
            "viewport": self.meta.get("viewport", ""),
            "og_title": self.meta.get("og:title", ""),
            "og_description": self.meta.get("og:description", ""),
            "og_image": self.meta.get("og:image", ""),
            "canonical": self.canonical,
            "lang": self.lang,
            "h1": self.h1,
            "h2": self.h2,
            "word_count": len(words),
            "links": self.links,
            "images": self.images,
            "hreflang": self.hreflang,
            "schema_types": sorted(self.schema_types),
            "visible_text": text,
        }


def fetch(url: str, method="GET", conditional_headers=None):
    started = time.perf_counter()
    try:
        response = safe_fetcher.fetch(
            url,
            method=method,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml,text/xml,text/plain;q=0.9,*/*;q=0.1",
                "Accept-Encoding": "gzip",
                **(conditional_headers or {}),
            },
            max_response_bytes=MAX_BYTES,
            allowed_content_types={
                "text/html", "application/xhtml+xml", "application/xml", "text/xml",
                "text/plain", "application/gzip", "application/x-gzip", "application/octet-stream",
            },
        )
        body = response.content
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        if response.headers.get("content-encoding", "").lower() == "gzip":
            try:
                body = gzip.decompress(body)
            except Exception:
                pass
        return {
            "ok": 200 <= response.status_code < 400,
            "status": response.status_code,
            "final_url": response.url,
            "content_type": response.headers.get("content-type", ""),
            "content_length": len(body),
            "elapsed_ms": elapsed_ms,
            "headers": dict(response.headers),
            "redirect_chain": [
                {"source_url": hop.source_url, "status_code": hop.status_code, "target_url": hop.target_url}
                for hop in response.history
            ],
            "body": body,
            "error": None if 200 <= response.status_code < 400 else f"HTTP {response.status_code}",
        }
    except SafeFetchError as exc:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return {
            "ok": False, "status": None, "final_url": url, "content_type": "",
            "content_length": 0, "elapsed_ms": elapsed_ms, "headers": {},
            "redirect_chain": [], "body": b"", "error": str(exc),
        }


def decode_body(body: bytes, content_type: str):
    charset = "utf-8"
    m = re.search(r"charset=([^\s;]+)", content_type or "", flags=re.I)
    if m:
        charset = m.group(1).strip("\"'")
    try:
        return body.decode(charset, errors="replace")
    except Exception:
        return body.decode("utf-8", errors="replace")


def parse_sitemap(url: str, domain: str, seen=None, depth=0):
    # Compatibility wrapper. Sitemap traversal lives in services.page_discovery.
    urls, _errors = discover_sitemap_urls(
        url,
        domain,
        max_depth=max(0, 5 - int(depth or 0)),
    )
    return sorted(urls)

UTILITY_SEGMENTS = {
    "privacy","privacy-policy","terms","terms-of-service","login","signin","sign-in",
    "register","account","cart","checkout","wp-admin","feed","search","sitemap",
    "404","cookie-policy","cookies"
}

def _candidate_reason(url, base_url, homepage_links, sitemap_urls):
    if normalize_url(url).rstrip("/") == normalize_url(base_url).rstrip("/"):
        return "Homepage"
    p = urllib.parse.urlsplit(url)
    segments = [x for x in p.path.split("/") if x]
    if url in homepage_links:
        return "Linked from homepage"
    if len(segments) == 1:
        return "Top-level page"
    if url in sitemap_urls:
        return "Sitemap page"
    return "Discovered page"

def _candidate_score(url, base_url, homepage_links, sitemap_urls):
    normalized = normalize_url(url)
    if normalized.rstrip("/") == normalize_url(base_url).rstrip("/"):
        return 10000
    p = urllib.parse.urlsplit(normalized)
    segments = [x.lower() for x in p.path.split("/") if x]
    if any(seg in UTILITY_SEGMENTS for seg in segments):
        return -10000
    score = 0
    if normalized in homepage_links:
        score += 1000
    if normalized in sitemap_urls:
        score += 300
    score += max(0, 220 - len(segments) * 45)
    important = {
        "about","services","service","products","product","contact","faq","pricing",
        "locations","location","team","company","solutions","industries","portfolio",
        "projects","resources"
    }
    if any(seg in important for seg in segments):
        score += 180
    if any(re.fullmatch(r"20\d{2}", seg) for seg in segments):
        score -= 80
    if len(segments) >= 4:
        score -= 100
    return score

def ten_page_candidates(base_url: str, domain: str, limit_candidates=60):
    base_url = normalize_url(base_url.rstrip("/") + "/")
    sitemap_urls = [normalize_url(x) for x in discover_seed_urls(base_url, domain)]
    sitemap_set = set(sitemap_urls)

    homepage_links = set()
    result = fetch(base_url)
    ctype = result.get("content_type","").lower()
    if result.get("body") and ("text/html" in ctype or "application/xhtml+xml" in ctype or not ctype):
        parser = PageParser()
        try:
            parser.feed(decode_body(result["body"], result["content_type"]))
            for href, _rel in parser.result().get("links", []):
                try:
                    target = normalize_url(safe_url_join(base_url, href))
                except Exception:
                    continue
                if same_site(target, domain):
                    homepage_links.add(target)
        except Exception:
            pass

    pool = {base_url}
    pool.update(homepage_links)
    pool.update(sitemap_set)

    ranked = []
    for url in pool:
        score = _candidate_score(url, base_url, homepage_links, sitemap_set)
        if score > -1000:
            ranked.append((score, url))
    ranked.sort(key=lambda x: (-x[0], x[1]))

    rows = []
    for idx, (score, url) in enumerate(ranked[:limit_candidates]):
        rows.append({
            "url": url,
            "path": path_for_url(url),
            "score": score,
            "reason": _candidate_reason(url, base_url, homepage_links, sitemap_set),
            "selected": idx < 10,
        })
    return rows

def discover_seed_urls(base_url: str, domain: str):
    try:
        urls, _source, _warnings = discover_domain_sitemap(domain)
        out = [normalize_url(url) for url in sorted(urls)]
    except Exception:
        out = [normalize_url(base_url.rstrip("/") + "/")]
    seen = set()
    unique = []
    for url in out:
        if url not in seen:
            seen.add(url)
            unique.append(url)
    return unique

def build_robot_parser(base_url: str):
    # Fetch robots.txt with the same HTTP client/user-agent used for page crawling.
    #
    # RobotFileParser.read() performs its own urllib request. If a CDN/WAF
    # returns 401/403 to that different request, RobotFileParser interprets it
    # as "disallow all", creating false site-wide robots blocks.
    #
    # Only a successfully retrieved 2xx robots.txt is parsed. A failed or
    # ambiguous robots fetch is unavailable evidence, never a block.
    p = urllib.parse.urlsplit(base_url)
    robots_url = urllib.parse.urlunsplit((p.scheme, p.netloc, "/robots.txt", "", ""))

    result = fetch(robots_url)
    status = result.get("status")

    if not result.get("ok") or not status or not (200 <= status < 300):
        detail = result.get("error") or (f"HTTP {status}" if status else "robots.txt unavailable")
        return None, robots_url, detail

    try:
        body = decode_body(result.get("body") or b"", result.get("content_type") or "")
        rp = urllib.robotparser.RobotFileParser()
        rp.set_url(robots_url)
        rp.parse(body.splitlines())
        return rp, robots_url, None
    except Exception as exc:
        return None, robots_url, f"robots.txt parse failed: {exc}"


def _content_fingerprints(parsed):
    text = re.sub(r"\s+", " ", str(parsed.get("visible_text") or "")).strip().lower()
    if not text:
        return "", ""
    exact = hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()
    tokens = re.findall(r"[a-z0-9]+", text)
    vector = [0] * 64
    for token in tokens:
        value = int.from_bytes(hashlib.blake2b(token.encode(), digest_size=8).digest(), "big")
        for bit in range(64):
            vector[bit] += 1 if value & (1 << bit) else -1
    simhash = sum((1 << bit) for bit, weight in enumerate(vector) if weight >= 0)
    return exact, f"{simhash:016x}"


def _hamming(left: str, right: str) -> int:
    try:
        return (int(left, 16) ^ int(right, 16)).bit_count()
    except Exception:
        return 64


def _failure_kind(result) -> str:
    status = result.get("status")
    error = str(result.get("error") or "").lower()
    if status == 429:
        return "rate_limited"
    if status and status >= 500:
        return "server_failure"
    if "timed out" in error or "timeout" in error:
        return "timed_out"
    if "refused" in error:
        return "connection_refused"
    if "robots" in error:
        return "blocked"
    if status and status >= 400:
        return "http_error"
    return "fetch_failure" if error else ""


def _sync_url_inventory(con, domain, base_url, selected_urls=None, max_depth=5):
    warnings = []
    sitemap_source = ""
    try:
        entries, sitemap_source, warnings = discover_domain_sitemap_inventory(
            domain, max_depth=max_depth
        )
    except Exception as exc:
        entries = []
        warnings = [str(exc)]

    policy = get_policy(con, domain)
    try:
        included_sitemaps = json.loads(policy["included_sitemaps_json"] or "[]")
    except Exception:
        included_sitemaps = []
    upsert_inventory_url(con, domain, base_url, source="homepage", crawl_depth=0)
    for entry in entries:
        if included_sitemaps:
            try:
                included = any(re.search(pattern, entry.source_sitemap) for pattern in included_sitemaps if pattern)
            except re.error:
                included = any(pattern in entry.source_sitemap for pattern in included_sitemaps if pattern)
            if not included:
                continue
        upsert_inventory_url(
            con,
            domain,
            entry.url,
            source="sitemap",
            source_sitemap=entry.source_sitemap,
            sitemap_lastmod=entry.lastmod,
            sitemap_priority=entry.priority,
        )
    for url in selected_urls or []:
        upsert_inventory_url(
            con, domain, url, source="operator", operator_selected=True
        )
    con.commit()
    return len(entries), sitemap_source, warnings



def add_issue(con, run_id, page_url, key, severity, title, detail=""):
    con.execute(
        """INSERT OR IGNORE INTO crawl_issue
           (crawl_run_id,page_url,issue_key,severity,title,detail)
           VALUES (?,?,?,?,?,?)""",
        (run_id, page_url, key, severity, title, detail),
    )


def best_effort_site_page(con, domain, url):
    try:
        cols = {r["name"] for r in con.execute("PRAGMA table_info(site_page)").fetchall()}
    except Exception:
        return
    if not {"domain", "url", "path"}.issubset(cols):
        return
    exists = con.execute(
        "SELECT id FROM site_page WHERE domain=? AND url=? LIMIT 1",
        (domain, url),
    ).fetchone()
    if not exists:
        try:
            con.execute(
                "INSERT INTO site_page(domain,path,url) VALUES (?,?,?)",
                (domain, path_for_url(url), url),
            )
        except Exception:
            pass


def persist_page(con, run_id, domain, requested_url, robots_allowed, result, parsed, inventory_id=None):
    status = result["status"]
    final_url = result["final_url"] or requested_url
    robots_meta = (parsed.get("robots_meta") or "").lower()
    fingerprint, simhash = _content_fingerprints(parsed)
    prior = None
    if inventory_id is not None:
        prior = con.execute(
            "SELECT * FROM crawl_url_inventory WHERE id=?", (inventory_id,)
        ).fetchone()
    if status == 304 and prior:
        fingerprint = prior["content_fingerprint"]
        simhash = prior["content_simhash"]
    unchanged = bool(status == 304 or (fingerprint and prior and prior["content_fingerprint"] == fingerprint))
    canonical_url = prior["canonical_url"] if status == 304 and prior else ""
    if parsed.get("canonical"):
        try:
            canonical_url = normalize_candidate_url(
                safe_url_join(final_url, parsed["canonical"]), domain
            ) or ""
        except Exception:
            canonical_url = ""
    duplicate_of = ""
    if canonical_url and canonical_url != normalize_candidate_url(final_url, domain):
        duplicate_of = canonical_url
    elif fingerprint:
        exact = con.execute(
            """
            SELECT url FROM crawl_url_inventory
            WHERE domain=? COLLATE NOCASE AND id<>? AND content_fingerprint=?
            ORDER BY priority_score DESC,id LIMIT 1
            """,
            (domain, int(inventory_id or 0), fingerprint),
        ).fetchone()
        if exact:
            duplicate_of = exact["url"]
        elif simhash:
            candidates = con.execute(
                """
                SELECT url,content_simhash FROM crawl_url_inventory
                WHERE domain=? COLLATE NOCASE AND id<>? AND content_simhash<>''
                ORDER BY priority_score DESC LIMIT 250
                """,
                (domain, int(inventory_id or 0)),
            ).fetchall()
            near = next((row for row in candidates if _hamming(simhash, row["content_simhash"]) <= 3), None)
            if near:
                duplicate_of = near["url"]
    indexable = int(
        bool((status == 304 and prior and not prior["noindex"]) or (status and 200 <= status < 300))
        and robots_allowed
        and "noindex" not in robots_meta
    )

    links = []
    internal_count = 0
    external_count = 0
    for href, rel in parsed.get("links", []):
        try:
            target = normalize_url(safe_url_join(final_url, href))
        except Exception:
            continue
        scheme = urllib.parse.urlsplit(target).scheme
        if scheme not in ("http", "https"):
            continue
        internal = int(same_site(target, domain))
        internal_count += internal
        external_count += 1 - internal
        links.append((target, internal, rel))

    images = parsed.get("images", [])
    missing_alt = sum(1 for x in images if x.get("alt") is None or not str(x.get("alt")).strip())

    con.execute(
        """INSERT OR REPLACE INTO crawl_page(
            crawl_run_id,url,final_url,path,status_code,content_type,content_bytes,response_ms,
            title,description,canonical,robots_meta,lang,viewport,h1_json,h2_json,word_count,
            internal_links,external_links,image_count,images_missing_alt,schema_types_json,
            hreflang_json,og_title,og_description,og_image,indexable,robots_allowed,error,created_at,
            response_etag,response_last_modified,content_fingerprint,content_simhash,unchanged,
            duplicate_of_url,failure_kind,redirect_chain_json
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            run_id, requested_url, final_url, path_for_url(final_url), status,
            result["content_type"], result["content_length"], result["elapsed_ms"],
            parsed.get("title",""), parsed.get("description",""), parsed.get("canonical"),
            parsed.get("robots_meta",""), parsed.get("lang"), parsed.get("viewport",""),
            json.dumps(parsed.get("h1",[]), ensure_ascii=False),
            json.dumps(parsed.get("h2",[]), ensure_ascii=False),
            parsed.get("word_count",0), internal_count, external_count,
            len(images), missing_alt,
            json.dumps(parsed.get("schema_types",[]), ensure_ascii=False),
            json.dumps(parsed.get("hreflang",[]), ensure_ascii=False),
            parsed.get("og_title",""), parsed.get("og_description",""), parsed.get("og_image",""),
            indexable, int(bool(robots_allowed)), result.get("error"), utcnow(),
            result.get("headers", {}).get("etag", ""),
            result.get("headers", {}).get("last-modified", ""),
            fingerprint, simhash, int(unchanged), duplicate_of, _failure_kind(result),
            json.dumps(result.get("redirect_chain") or [], separators=(",", ":")),
        ),
    )

    for target, internal, rel in links:
        con.execute(
            """INSERT OR IGNORE INTO crawl_link(crawl_run_id,source_url,target_url,internal,rel)
               VALUES (?,?,?,?,?)""",
            (run_id, requested_url, target, internal, rel or ""),
        )

    # Core crawl-derived SEO issues.
    title = parsed.get("title","").strip()
    desc = parsed.get("description","").strip()
    h1s = parsed.get("h1",[])
    canonical = parsed.get("canonical")

    if status == 304:
        pass
    elif not status or status >= 400:
        add_issue(con, run_id, requested_url, "http_error", "high", "Page returned an HTTP error", str(status or result.get("error") or "fetch failed"))
    if status and status != 304 and 300 <= status < 400:
        add_issue(con, run_id, requested_url, "redirect", "medium", "Page redirects", final_url)
    if status and 200 <= status < 300:
        if not title:
            add_issue(con, run_id, requested_url, "missing_title", "high", "Missing title tag")
        elif len(title) < 20:
            add_issue(con, run_id, requested_url, "short_title", "low", "Very short title tag", f"{len(title)} characters")
        elif len(title) > 70:
            add_issue(con, run_id, requested_url, "long_title", "low", "Long title tag", f"{len(title)} characters")
        if not desc:
            add_issue(con, run_id, requested_url, "missing_description", "medium", "Missing meta description")
        if not h1s:
            add_issue(con, run_id, requested_url, "missing_h1", "medium", "Missing H1")
        elif len(h1s) > 1:
            add_issue(con, run_id, requested_url, "multiple_h1", "low", "Multiple H1 headings", str(len(h1s)))
        if not canonical:
            add_issue(con, run_id, requested_url, "missing_canonical", "medium", "Missing canonical URL")
        if not parsed.get("viewport"):
            add_issue(con, run_id, requested_url, "missing_viewport", "medium", "Missing viewport meta tag")
        if missing_alt:
            add_issue(con, run_id, requested_url, "missing_alt", "low", "Images missing alt text", f"{missing_alt} of {len(images)}")
        if not parsed.get("schema_types"):
            add_issue(con, run_id, requested_url, "no_schema", "low", "No JSON-LD schema detected")
        if parsed.get("word_count", 0) < 150:
            add_issue(con, run_id, requested_url, "thin_content", "low", "Low visible word count", str(parsed.get("word_count",0)))
        if "noindex" in robots_meta:
            add_issue(con, run_id, requested_url, "noindex", "medium", "Page has noindex directive")
        if not robots_allowed:
            add_issue(con, run_id, requested_url, "robots_blocked", "medium", "Blocked by robots.txt")

    best_effort_site_page(con, domain, final_url)
    if inventory_id is not None:
        failure = _failure_kind(result)
        if failure:
            con.execute(
                """
                UPDATE crawl_url_inventory
                SET final_url=?,http_status=?,retry_count=retry_count+1,
                    consecutive_failures=consecutive_failures+1,last_error=?,updated_at=?
                WHERE id=?
                """,
                (final_url, status, result.get("error") or failure, utcnow(), inventory_id),
            )
        else:
            eligibility = "duplicate" if duplicate_of else ("excluded" if "noindex" in robots_meta else "eligible")
            reason = "canonical_or_content_duplicate" if duplicate_of else ("noindex" if "noindex" in robots_meta else "crawled")
            con.execute(
                """
                UPDATE crawl_url_inventory
                SET final_url=?,canonical_url=?,duplicate_of_url=?,http_status=?,noindex=?,
                    etag=?,last_modified=?,content_fingerprint=?,content_simhash=?,
                    last_crawled_at=?,retry_count=0,consecutive_failures=0,last_error='',
                    eligibility=?,decision_reason=?,updated_at=?
                WHERE id=?
                """,
                (
                    final_url, canonical_url, duplicate_of, status, int("noindex" in robots_meta),
                    result.get("headers", {}).get("etag", "") or (prior["etag"] if prior else ""),
                    result.get("headers", {}).get("last-modified", "") or (prior["last_modified"] if prior else ""), fingerprint, simhash,
                    utcnow(), eligibility, reason, utcnow(), inventory_id,
                ),
            )
            if not duplicate_of:
                classification = prior["classification"] if prior else "unknown"
                schedule_next_crawl(con, inventory_id, classification, changed=not unchanged)
    con.commit()
    return {
        "links": [target for target, internal, _ in links if internal],
        "unchanged": unchanged,
        "duplicate_of": duplicate_of,
        "failure_kind": _failure_kind(result),
    }


def crawl_worker(
    run_id,
    domain,
    base_url,
    page_cap,
    delay_ms,
    obey_robots,
    db_factory,
    selected_urls=None,
    follow_links=True,
    *,
    crawl_mode="initial",
    execution_run_id=None,
    priority_urls=None,
):
    """Run one bounded crawl batch from the persistent classified frontier."""

    rp, robots_url, robots_error = build_robot_parser(base_url)
    with db_factory() as con:
        policy = get_policy(con, domain)
        existing = con.execute(
            "SELECT COUNT(*) AS n FROM crawl_frontier WHERE crawl_run_id=?", (run_id,)
        ).fetchone()["n"]
        if not existing:
            inventory_count = con.execute(
                "SELECT COUNT(*) AS n FROM crawl_url_inventory WHERE domain=? COLLATE NOCASE",
                (domain,),
            ).fetchone()["n"]
            if crawl_mode == "background" and inventory_count:
                sitemap_count, sitemap_source, warnings = inventory_count, "stored_inventory", []
            else:
                sitemap_count, sitemap_source, warnings = _sync_url_inventory(
                    con,
                    domain,
                    base_url,
                    selected_urls=list(selected_urls or []) + list(priority_urls or []),
                    max_depth=int(policy["max_crawl_depth"]),
                )
            if crawl_mode == "background":
                rows = remaining_background_inventory(con, domain, page_cap)
                reason = "background_priority_batch"
            elif selected_urls:
                marks = ",".join("?" for _ in selected_urls)
                normalized = [normalize_candidate_url(url, domain) for url in selected_urls]
                normalized = [url for url in normalized if url]
                rows = con.execute(
                    f"SELECT * FROM crawl_url_inventory WHERE domain=? AND url IN ({marks}) ORDER BY operator_selected DESC,priority_score DESC",
                    [domain, *normalized],
                ).fetchall() if normalized else []
                reason = "operator_selected"
            else:
                rows = select_initial_inventory(con, domain, page_cap)
                reason = "bounded_initial_priority"
            queue_frontier(con, run_id, rows, reason)
            con.execute(
                """
                INSERT INTO crawl_event(crawl_run_id,domain,event_type,detail_json,created_at)
                VALUES (?,?,?,?,?)
                """,
                (
                    run_id,
                    domain,
                    "frontier_initialized",
                    json.dumps({
                        "mode": crawl_mode,
                        "sitemap_count": sitemap_count,
                        "sitemap_source": sitemap_source,
                        "warnings": warnings,
                        "selected": len(rows),
                    }, separators=(",", ":")),
                    utcnow(),
                ),
            )
        counts = frontier_counts(con, run_id)
        eligible = con.execute(
            "SELECT COUNT(*) AS n FROM crawl_url_inventory WHERE domain=? AND eligibility='eligible'",
            (domain,),
        ).fetchone()["n"]
        remaining = con.execute(
            """
            SELECT COUNT(*) AS n FROM crawl_url_inventory
            WHERE domain=? AND eligibility='eligible' AND last_crawled_at IS NULL
            """,
            (domain,),
        ).fetchone()["n"]
        con.execute(
            """
            UPDATE crawl_run
            SET status='running',started_at=COALESCE(started_at,?),robots_url=?,
                crawl_mode=?,pages_eligible=?,pages_remaining=?,status_reason=?,error=NULL
            WHERE id=?
            """,
            (
                utcnow(), robots_url, crawl_mode, eligible,
                remaining, robots_error or "", run_id,
            ),
        )
        con.commit()

    processed = 0
    consecutive_failures = 0
    circuit_open = False
    max_failures = int(policy["max_consecutive_failures"])

    try:
        while processed < page_cap:
            control = job_control_state(RESEARCH_DB_PATH, execution_run_id) if execution_run_id else "running"
            if control in {"cancelled", "paused"}:
                return control

            with db_factory() as con:
                item = con.execute(
                    """
                    SELECT f.*,u.url,u.classification,u.etag,u.last_modified,u.crawl_depth
                    FROM crawl_frontier f
                    JOIN crawl_url_inventory u ON u.id=f.url_inventory_id
                    WHERE f.crawl_run_id=? AND f.state='queued'
                    ORDER BY f.priority_score DESC,f.queued_at,u.url
                    LIMIT 1
                    """,
                    (run_id,),
                ).fetchone()
                if not item:
                    break
                url = item["url"]
                con.execute(
                    """
                    UPDATE crawl_frontier
                    SET state='fetching',attempts=attempts+1,started_at=COALESCE(started_at,?),updated_at=?
                    WHERE crawl_run_id=? AND url_inventory_id=? AND state='queued'
                    """,
                    (utcnow(), utcnow(), run_id, item["url_inventory_id"]),
                )
                con.execute("UPDATE crawl_run SET current_url=? WHERE id=?", (url, run_id))
                con.commit()

            allowed = True
            if obey_robots and rp is not None:
                try:
                    allowed = rp.can_fetch(ROBOTS_USER_AGENT, url)
                except Exception:
                    allowed = True

            if not allowed:
                result = {
                    "ok": False, "status": None, "final_url": url, "content_type": "",
                    "content_length": 0, "elapsed_ms": 0, "headers": {}, "body": b"",
                    "error": "Blocked by robots.txt",
                }
                parsed = {}
            else:
                conditional = {}
                if item["etag"]:
                    conditional["If-None-Match"] = item["etag"]
                if item["last_modified"]:
                    conditional["If-Modified-Since"] = item["last_modified"]
                result = fetch(url, conditional_headers=conditional)
                content_type = result.get("content_type", "").lower()
                parsed = {}
                if result["body"] and (
                    "text/html" in content_type
                    or "application/xhtml+xml" in content_type
                    or not content_type
                ):
                    parser = PageParser()
                    try:
                        parser.feed(decode_body(result["body"], result["content_type"]))
                        parsed = parser.result()
                    except Exception as exc:
                        result["error"] = (
                            (result.get("error") + "; " if result.get("error") else "")
                            + f"HTML parse: {exc}"
                        )

            with db_factory() as con:
                persisted = persist_page(
                    con,
                    run_id,
                    domain,
                    url,
                    allowed,
                    result,
                    parsed,
                    item["url_inventory_id"],
                )
                failure_kind = persisted["failure_kind"]
                if failure_kind:
                    state = "skipped" if failure_kind == "blocked" else "failed"
                    consecutive_failures += int(failure_kind in {
                        "rate_limited", "connection_refused", "timed_out", "server_failure", "fetch_failure"
                    })
                else:
                    state = "unchanged" if persisted["unchanged"] else "completed"
                    consecutive_failures = 0

                con.execute(
                    """
                    UPDATE crawl_frontier SET state=?,reason=?,completed_at=?,updated_at=?
                    WHERE crawl_run_id=? AND url_inventory_id=?
                    """,
                    (
                        state,
                        failure_kind or ("duplicate" if persisted["duplicate_of"] else "fetched"),
                        utcnow(), utcnow(), run_id, item["url_inventory_id"],
                    ),
                )

                if follow_links:
                    current_frontier = con.execute(
                        "SELECT COUNT(*) AS n FROM crawl_frontier WHERE crawl_run_id=?", (run_id,)
                    ).fetchone()["n"]
                    for target in persisted["links"]:
                        inventory_id = upsert_inventory_url(
                            con,
                            domain,
                            target,
                            source="primary_navigation" if url.rstrip("/") == base_url.rstrip("/") else "internal_link",
                            crawl_depth=int(item["crawl_depth"]) + 1,
                        )
                        if (
                            crawl_mode == "initial"
                            and inventory_id
                            and current_frontier < page_cap
                        ):
                            candidate = con.execute(
                                "SELECT * FROM crawl_url_inventory WHERE id=? AND eligibility='eligible'",
                                (inventory_id,),
                            ).fetchone()
                            if candidate:
                                current_frontier += queue_frontier(
                                    con, run_id, [candidate], "high_value_internal_link"
                                )

                counts = frontier_counts(con, run_id)
                discovered = con.execute(
                    "SELECT COUNT(*) AS n FROM crawl_url_inventory WHERE domain=?", (domain,)
                ).fetchone()["n"]
                remaining = con.execute(
                    """
                    SELECT COUNT(*) AS n FROM crawl_url_inventory
                    WHERE domain=? AND eligibility='eligible' AND last_crawled_at IS NULL
                    """,
                    (domain,),
                ).fetchone()["n"]
                con.execute(
                    """
                    UPDATE crawl_run
                    SET pages_discovered=?,pages_crawled=?,pages_failed=?,pages_skipped=?,
                        pages_unchanged=?,pages_remaining=?,current_url=''
                    WHERE id=?
                    """,
                    (
                        discovered,
                        counts["completed"] + counts["unchanged"],
                        counts["failed"],
                        counts["skipped"],
                        counts["unchanged"],
                        remaining,
                        run_id,
                    ),
                )
                con.commit()

            processed += 1
            if failure_kind in {"rate_limited", "connection_refused"} or consecutive_failures >= max_failures:
                circuit_open = True
                break
            if delay_ms and processed < page_cap:
                time.sleep(delay_ms / 1000.0)

        with db_factory() as con:
            broken = con.execute(
                """
                SELECT DISTINCT l.source_url,l.target_url,p.status_code
                FROM crawl_link l
                LEFT JOIN crawl_page p
                  ON p.crawl_run_id=l.crawl_run_id AND p.url=l.target_url
                WHERE l.crawl_run_id=? AND l.internal=1 AND p.status_code >= 400
                """,
                (run_id,),
            ).fetchall()
            for row in broken:
                add_issue(
                    con, run_id, row["source_url"], "broken_internal_link", "high",
                    "Broken internal link", f"{row['target_url']} → HTTP {row['status_code']}"
                )
            counts = frontier_counts(con, run_id)
            failed = counts["failed"]
            remaining = con.execute(
                """
                SELECT COUNT(*) AS n FROM crawl_url_inventory
                WHERE domain=? AND eligibility='eligible' AND last_crawled_at IS NULL
                """,
                (domain,),
            ).fetchone()["n"]
            status = "partial" if failed or circuit_open else "completed"
            reason = "Host circuit breaker opened after repeated failures." if circuit_open else "Batch finished."
            cooldown_until = None
            if circuit_open:
                retry_after = 0
                try:
                    retry_after = int((result.get("headers") or {}).get("retry-after", "0"))
                except (TypeError, ValueError):
                    retry_after = 0
                cooldown_until = (
                    datetime.now(timezone.utc)
                    + timedelta(seconds=max(int(policy["batch_cooldown_seconds"]), retry_after))
                ).isoformat(timespec="seconds")
            con.execute(
                """
                UPDATE crawl_run
                SET status=?,completed_at=?,pages_crawled=?,pages_failed=?,pages_skipped=?,
                    pages_unchanged=?,pages_remaining=?,current_url='',status_reason=?,cooldown_until=?
                WHERE id=?
                """,
                (
                    status, utcnow(), counts["completed"] + counts["unchanged"], failed,
                    counts["skipped"], counts["unchanged"], remaining, reason,
                    cooldown_until, run_id,
                ),
            )
            con.commit()
        return status
    except Exception as exc:
        with db_factory() as con:
            con.execute(
                "UPDATE crawl_run SET status='failed',completed_at=?,current_url='',error=?,status_reason=? WHERE id=?",
                (utcnow(), str(exc), "Crawler exception.", run_id),
            )
            con.commit()
        raise


def register_crawler(app, research_db: Callable, get_site: Callable):
    from flask import abort, jsonify, redirect, render_template, request, url_for

    @app.route("/d/<domain>/crawl")
    def seo_crawl(domain):
        site = get_site(domain)
        with research_db() as con:
            policy = get_policy(con, site["domain"])
            runs = con.execute(
                """SELECT * FROM crawl_run WHERE domain=? ORDER BY id DESC LIMIT 20""",
                (site["domain"],),
            ).fetchall()
            latest = runs[0] if runs else None
            pages = []
            issues = []
            failure_counts = []
            if latest:
                pages = con.execute(
                    """SELECT * FROM crawl_page WHERE crawl_run_id=?
                       ORDER BY CASE WHEN status_code IS NULL THEN 1 ELSE 0 END,status_code DESC,url
                       LIMIT 500""",
                    (latest["id"],),
                ).fetchall()
                failure_counts = con.execute(
                    """
                    SELECT failure_kind,COUNT(*) AS n FROM crawl_page
                    WHERE crawl_run_id=? AND failure_kind<>''
                    GROUP BY failure_kind ORDER BY n DESC,failure_kind
                    """,
                    (latest["id"],),
                ).fetchall()
                issues = con.execute(
                    """SELECT severity,title,COUNT(*) AS count
                       FROM crawl_issue WHERE crawl_run_id=?
                       GROUP BY severity,title
                       ORDER BY CASE severity WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END,count DESC""",
                    (latest["id"],),
                ).fetchall()
            inventory_counts = {
                row["eligibility"]: int(row["n"])
                for row in con.execute(
                    """
                    SELECT eligibility,COUNT(*) AS n FROM crawl_url_inventory
                    WHERE domain=? GROUP BY eligibility
                    """,
                    (site["domain"],),
                )
            }
            exclusion_counts = con.execute(
                """
                SELECT decision_reason,COUNT(*) AS n FROM crawl_url_inventory
                WHERE domain=? AND eligibility IN ('excluded','deferred','duplicate')
                GROUP BY decision_reason ORDER BY n DESC,decision_reason
                """,
                (site["domain"],),
            ).fetchall()
            source_counts = con.execute(
                """
                SELECT source,COUNT(*) AS n FROM crawl_url_inventory
                WHERE domain=? GROUP BY source ORDER BY n DESC,source
                """,
                (site["domain"],),
            ).fetchall()
            con.commit()
        return render_template(
            "crawl.html",
            sites=get_sites_for_template(get_site, site),
            site=site,
            runs=runs,
            latest=latest,
            pages=pages,
            issues=issues,
            policy=policy,
            inventory_counts=inventory_counts,
            exclusion_counts=exclusion_counts,
            source_counts=source_counts,
            failure_counts=failure_counts,
            policy_allowed_patterns="\n".join(json.loads(policy["allowed_patterns_json"] or "[]")),
            policy_excluded_patterns="\n".join(json.loads(policy["excluded_patterns_json"] or "[]")),
            policy_included_sitemaps="\n".join(json.loads(policy["included_sitemaps_json"] or "[]")),
        )

    # The dashboard's templates normally expect a sites collection. Since the
    # crawler is registered from app.py, we attach a callable there below.
    def get_sites_for_template(_get_site, _site):
        try:
            # Flask app config receives the dashboard's real get_sites callable.
            fn = app.config.get("PB_GET_SITES")
            return fn() if fn else [_site]
        except Exception:
            return [_site]


    @app.get("/d/<domain>/crawl/ten-page")
    def ten_page_select(domain):
        site = get_site(domain)
        base_url = "https://" + site["domain"]
        candidates = ten_page_candidates(base_url, site["domain"])
        return render_template(
            "ten_page_select.html",
            sites=get_sites_for_template(get_site, site),
            site=site,
            candidates=candidates,
        )

    @app.post("/d/<domain>/crawl/ten-page/run")
    def ten_page_run(domain):
        site = get_site(domain)
        urls = []
        seen = set()
        for raw in request.form.getlist("urls"):
            try:
                url = normalize_url(raw)
            except Exception:
                continue
            if same_site(url, site["domain"]) and url not in seen:
                seen.add(url)
                urls.append(url)

        if not urls:
            return redirect(url_for("ten_page_select", domain=site["domain"]))

        urls = urls[:10]
        try:
            delay_ms = int(request.form.get("delay_ms", 2000))
        except Exception:
            delay_ms = 2000
        delay_ms = max(0, min(delay_ms, 10000))
        obey_robots = request.form.get("obey_robots", "1") != "0"

        job = enqueue_job(
            RESEARCH_DB_PATH,
            "crawl",
            domain=site["domain"],
            payload={
                "domain": site["domain"],
                "base_url": "https://" + site["domain"],
                "page_cap": len(urls),
                "delay_ms": delay_ms,
                "obey_robots": obey_robots,
                "report_scope": "ten-page",
                "selected_urls": urls,
                "follow_links": False,
            },
            max_attempts=3,
        )
        return redirect(url_for("seo_crawl", domain=site["domain"], job=job["id"]))

    @app.post("/d/<domain>/crawl/run")
    def seo_crawl_run(domain):
        site = get_site(domain)
        try:
            page_cap = int(request.form.get("page_cap", DEFAULT_PAGE_CAP))
        except Exception:
            page_cap = DEFAULT_PAGE_CAP
        page_cap = max(1, min(page_cap, 5000))

        try:
            delay_ms = int(request.form.get("delay_ms", DEFAULT_DELAY_MS))
        except Exception:
            delay_ms = DEFAULT_DELAY_MS
        delay_ms = max(0, min(delay_ms, 10000))
        obey_robots = request.form.get("obey_robots", "1") != "0"

        with research_db() as con:
            policy = get_policy(con, site["domain"])
            con.commit()
        page_cap = min(page_cap, int(policy["initial_target"]))
        job = enqueue_job(
            RESEARCH_DB_PATH,
            "crawl",
            domain=site["domain"],
            payload={
                "domain": site["domain"],
                "base_url": "https://" + site["domain"],
                "page_cap": page_cap,
                "delay_ms": delay_ms,
                "obey_robots": obey_robots,
                "report_scope": "initial",
                "selected_urls": [],
                "follow_links": True,
                "crawl_mode": "initial",
            },
            max_attempts=3,
        )
        return redirect(url_for("seo_crawl", domain=site["domain"], job=job["id"]))

    @app.post("/d/<domain>/crawl/policy")
    def seo_crawl_policy(domain):
        site = get_site(domain)
        values = {
            "initial_target": request.form.get("initial_target", 15),
            "max_urls_per_batch": request.form.get("max_urls_per_batch", 10),
            "delay_ms": request.form.get("delay_ms", 2000),
            "batch_cooldown_seconds": request.form.get("batch_cooldown_seconds", 21600),
            "daily_page_budget": request.form.get("daily_page_budget", 40),
            "weekly_page_budget": request.form.get("weekly_page_budget", 200),
            "max_consecutive_failures": request.form.get("max_consecutive_failures", 3),
            "max_retry_count": request.form.get("max_retry_count", 3),
            "max_crawl_depth": request.form.get("max_crawl_depth", 5),
            "background_enabled": request.form.get("background_enabled") == "1",
            "allowed_patterns_json": request.form.get("allowed_patterns", ""),
            "excluded_patterns_json": request.form.get("excluded_patterns", ""),
            "included_sitemaps_json": request.form.get("included_sitemaps", ""),
        }
        with research_db() as con:
            update_policy(con, site["domain"], values)
            con.commit()
        return redirect(url_for("seo_crawl", domain=site["domain"], message="Crawl policy saved."))

    def _domain_job(domain, job_id):
        site = get_site(domain)
        job = get_job(RESEARCH_DB_PATH, job_id)
        if not job or job["domain"].lower() != site["domain"].lower():
            abort(404)
        return site, job

    @app.post("/d/<domain>/crawl/jobs/<job_id>/pause")
    def seo_crawl_pause(domain, job_id):
        site, _job = _domain_job(domain, job_id)
        pause_job(RESEARCH_DB_PATH, job_id)
        return redirect(url_for("seo_crawl", domain=site["domain"]))

    @app.post("/d/<domain>/crawl/jobs/<job_id>/resume")
    def seo_crawl_resume(domain, job_id):
        site, _job = _domain_job(domain, job_id)
        resume_job(RESEARCH_DB_PATH, job_id)
        return redirect(url_for("seo_crawl", domain=site["domain"]))

    @app.post("/d/<domain>/crawl/jobs/<job_id>/cancel")
    def seo_crawl_cancel(domain, job_id):
        site, _job = _domain_job(domain, job_id)
        cancel_job(RESEARCH_DB_PATH, job_id)
        return redirect(url_for("seo_crawl", domain=site["domain"]))

    @app.get("/d/<domain>/crawl/<int:run_id>.json")
    def seo_crawl_status(domain, run_id):
        site = get_site(domain)
        with research_db() as con:
            run = con.execute(
                "SELECT * FROM crawl_run WHERE id=? AND domain=?",
                (run_id, site["domain"]),
            ).fetchone()
            if not run:
                abort(404)
            counts = con.execute(
                """SELECT severity,COUNT(*) AS count
                   FROM crawl_issue WHERE crawl_run_id=?
                   GROUP BY severity""",
                (run_id,),
            ).fetchall()
        payload = dict(run)
        payload["issues"] = {r["severity"]: r["count"] for r in counts}
        return jsonify(payload)
