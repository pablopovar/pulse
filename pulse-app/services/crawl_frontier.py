from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from services.url_policy import domain_hostname, normalize_hostname


TRACKING_PARAMS = {
    "fbclid", "gclid", "dclid", "msclkid", "mc_cid", "mc_eid", "ref", "source",
}
TRACKING_PREFIXES = ("utm_", "pk_", "mtm_")
UTILITY_SEGMENTS = {
    "login", "signin", "sign-in", "register", "account", "cart", "checkout",
    "wp-admin", "wp-login", "search", "print", "attachment", "feed", "feeds",
}
CORE_TERMS = {
    "about", "company", "contact", "leadership", "team", "investors", "investor",
    "projects", "project", "assets", "asset", "products", "product", "services",
    "service", "solutions", "sustainability", "governance", "disclosures", "technical",
    "operations", "corporate", "indigenous", "partners", "partnerships",
}
NEWS_TERMS = {"news", "press", "release", "releases", "updates", "blog"}
DOCUMENT_SUFFIXES = (".pdf", ".doc", ".docx", ".xls", ".xlsx")

CLASS_PRIORITY = {
    "core_page": 900,
    "supporting_evidence": 700,
    "document_disclosure": 650,
    "article": 560,
    "news_release": 520,
    "corporate_media": 480,
    "webcast": 350,
    "unknown": 250,
    "archive_taxonomy": 40,
    "pagination_navigation": 20,
    "utility": 0,
    "excluded": -1000,
}

INITIAL_BUDGETS = {
    "core_page": 12,
    "news_release": 4,
    "article": 3,
    "corporate_media": 2,
    "supporting_evidence": 3,
    "document_disclosure": 2,
    "webcast": 0,
    "unknown": 2,
}

DEFAULT_POLICY = {
    "initial_target": 15,
    "max_urls_per_batch": 10,
    "delay_ms": 2000,
    "batch_cooldown_seconds": 21600,
    "daily_page_budget": 40,
    "weekly_page_budget": 200,
    "max_consecutive_failures": 3,
    "max_retry_count": 3,
    "max_crawl_depth": 5,
    "allowed_patterns_json": "[]",
    "excluded_patterns_json": "[]",
    "included_sitemaps_json": "[]",
    "background_enabled": 1,
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def equivalent_host(left: str, right: str) -> bool:
    def bare(value: str) -> str:
        host = normalize_hostname(value)
        return host[4:] if host.startswith("www.") else host

    try:
        return bare(left) == bare(right)
    except Exception:
        return False


def normalize_candidate_url(value: str, domain: str) -> str | None:
    """Return the one crawl identity used by the frontier.

    The configured domain wins over an equivalent www host, fragments and known
    tracking parameters are removed, and remaining query parameters are sorted.
    Meaningful query parameters are retained so they can be classified rather
    than silently merged.
    """

    raw = str(value or "").strip()
    if not raw:
        return None
    if raw.startswith("/"):
        raw = f"https://{domain_hostname(domain)}{raw}"
    try:
        parsed = urlsplit(raw if "://" in raw else "https://" + raw)
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
            return None
        wanted = domain_hostname(domain)
        if not equivalent_host(parsed.hostname, wanted):
            return None
        path = re.sub(r"/{2,}", "/", parsed.path or "/")
        pairs = []
        for key, value in parse_qsl(parsed.query, keep_blank_values=True):
            lowered = key.lower()
            if lowered in TRACKING_PARAMS or lowered.startswith(TRACKING_PREFIXES):
                continue
            pairs.append((key, value))
        query = urlencode(sorted(pairs), doseq=True)
        return urlunsplit(("https", wanted, path, query, ""))
    except Exception:
        return None


def infer_classification(url: str, source_sitemap: str = "") -> str:
    source = source_sitemap.lower()
    path = urlsplit(url).path.lower()
    segments = [segment for segment in path.split("/") if segment]
    if "news-release" in source or "news-release" in path or "/press-release" in path:
        return "news_release"
    if "page-sitemap" in source:
        return "core_page"
    if "post-sitemap" in source:
        return "article"
    if "corporate-media" in source:
        return "corporate_media"
    if "article" in source:
        return "article"
    if "webcast" in source:
        return "webcast"
    if "category" in source or any(x in segments for x in {"category", "tag", "author"}):
        return "archive_taxonomy"
    if path.endswith(DOCUMENT_SUFFIXES) or any(x in segments for x in {"reports", "filings", "disclosures"}):
        return "document_disclosure"
    if any(x in segments for x in CORE_TERMS) or len(segments) <= 1:
        return "core_page"
    if any(x in segments for x in NEWS_TERMS):
        return "news_release"
    if any(x in segments for x in {"evidence", "research", "resources", "responsibility"}):
        return "supporting_evidence"
    return "unknown"


def eligibility_decision(url: str, classification: str) -> tuple[str, str]:
    parsed = urlsplit(url)
    path = parsed.path.lower()
    segments = [x for x in path.split("/") if x]
    query_keys = {key.lower() for key, _ in parse_qsl(parsed.query, keep_blank_values=True)}

    if path.endswith(("/feed", "/feed/", ".rss", ".atom", ".xml")):
        return "excluded", "feed_or_machine_document"
    if any(segment in UTILITY_SEGMENTS for segment in segments):
        return "excluded", "utility_or_account_page"
    if classification == "archive_taxonomy":
        return "excluded", "taxonomy_archive_default"
    if "page" in query_keys or any("page" in key for key in query_keys):
        return "excluded", "pagination_query"
    if re.search(r"/page/\d+/?$", path):
        return "excluded", "pagination_path"
    if parsed.query and len(parse_qsl(parsed.query, keep_blank_values=True)) > 3:
        return "deferred", "complex_parameter_variant"
    return "eligible", "useful_content_candidate"


def _matches_patterns(url: str, patterns) -> bool:
    for pattern in patterns or []:
        if not pattern:
            continue
        try:
            if re.search(pattern, url):
                return True
        except re.error:
            if str(pattern) in url:
                return True
    return False


def _event_family(url: str) -> str:
    slug = urlsplit(url).path.strip("/").split("/")[-1].lower()
    tokens = re.findall(r"[a-z0-9]+", slug)
    stage_words = {
        "announce", "announces", "announced", "proposed", "proposal", "pricing", "priced",
        "complete", "completes", "completed", "completion", "update", "updated", "of", "the",
    }
    meaningful = [token for token in tokens if token not in stage_words and not re.fullmatch(r"20\d{2}", token)]
    return "-".join(meaningful)


def _template_key(row) -> tuple[str, str, str]:
    segments = [segment for segment in urlsplit(row["url"]).path.lower().split("/") if segment]
    first = segments[0] if segments else "homepage"
    return row["classification"], row["source_sitemap"] or row["source"], first


def priority_score(
    url: str,
    classification: str,
    *,
    source: str = "unknown",
    sitemap_priority: float | None = None,
    operator_selected: bool = False,
    crawl_depth: int = 0,
) -> int:
    parsed = urlsplit(url)
    segments = [x.lower() for x in parsed.path.split("/") if x]
    score = CLASS_PRIORITY.get(classification, 0)
    if not segments:
        score += 10_000
    if operator_selected:
        score += 20_000
    if source == "primary_navigation":
        score += 2_000
    elif source == "sitemap":
        score += 250
    elif source == "internal_link":
        score += 100
    if sitemap_priority is not None:
        score += int(max(0.0, min(1.0, float(sitemap_priority))) * 200)
    score -= max(0, int(crawl_depth)) * 40
    score -= max(0, len(segments) - 2) * 30
    if any(re.fullmatch(r"20\d{2}", segment) for segment in segments):
        score -= 80
    lowered_path = parsed.path.lower()
    if any(term in lowered_path for term in ("completed", "completes", "final-results", "definitive")):
        score += 90
    if any(term in lowered_path for term in ("proposed", "announces-pricing", "preliminary")):
        score -= 40
    return score


def get_policy(con, domain: str) -> dict:
    row = con.execute(
        "SELECT * FROM domain_crawl_policy WHERE domain=? COLLATE NOCASE", (domain,)
    ).fetchone()
    if row:
        return dict(row)
    return {"domain": domain, **DEFAULT_POLICY, "updated_at": None}


def update_policy(con, domain: str, values: dict) -> dict:
    con.execute(
        "INSERT OR IGNORE INTO domain_crawl_policy(domain,updated_at) VALUES (?,?)",
        (domain, now()),
    )
    integer_fields = {
        "initial_target": (1, 100),
        "max_urls_per_batch": (1, 500),
        "delay_ms": (0, 60_000),
        "batch_cooldown_seconds": (0, 604_800),
        "daily_page_budget": (0, 100_000),
        "weekly_page_budget": (0, 500_000),
        "max_consecutive_failures": (1, 100),
        "max_retry_count": (0, 100),
        "max_crawl_depth": (0, 100),
    }
    updates = {}
    for field, (minimum, maximum) in integer_fields.items():
        if field in values:
            updates[field] = max(minimum, min(maximum, int(values[field])))
    if "background_enabled" in values:
        updates["background_enabled"] = int(bool(values["background_enabled"]))
    for field in ("allowed_patterns_json", "excluded_patterns_json", "included_sitemaps_json"):
        if field in values:
            raw = values[field]
            if isinstance(raw, str):
                raw = [line.strip() for line in raw.splitlines() if line.strip()]
            updates[field] = json.dumps(list(raw or []), separators=(",", ":"))
    if updates:
        assignments = ",".join(f"{field}=?" for field in updates)
        con.execute(
            f"UPDATE domain_crawl_policy SET {assignments},updated_at=? WHERE domain=? COLLATE NOCASE",
            [*updates.values(), now(), domain],
        )
    return get_policy(con, domain)


def upsert_inventory_url(
    con,
    domain: str,
    raw_url: str,
    *,
    source: str,
    source_sitemap: str = "",
    sitemap_lastmod: str = "",
    sitemap_priority: float | None = None,
    crawl_depth: int = 0,
    operator_selected: bool = False,
) -> int | None:
    url = normalize_candidate_url(raw_url, domain)
    if not url:
        return None
    classification = infer_classification(url, source_sitemap)
    eligibility, reason = eligibility_decision(url, classification)
    policy_row = con.execute(
        "SELECT allowed_patterns_json,excluded_patterns_json FROM domain_crawl_policy WHERE domain=? COLLATE NOCASE",
        (domain,),
    ).fetchone()
    if policy_row:
        try:
            excluded_patterns = json.loads(policy_row["excluded_patterns_json"] or "[]")
        except Exception:
            excluded_patterns = []
        try:
            allowed_patterns = json.loads(policy_row["allowed_patterns_json"] or "[]")
        except Exception:
            allowed_patterns = []
        if _matches_patterns(url, excluded_patterns):
            eligibility, reason = "excluded", "domain_excluded_pattern"
        elif allowed_patterns and not _matches_patterns(url, allowed_patterns):
            eligibility, reason = "deferred", "outside_domain_allowed_patterns"
    if operator_selected:
        eligibility, reason = "eligible", "operator_selected"
    score = priority_score(
        url,
        classification,
        source=source,
        sitemap_priority=sitemap_priority,
        operator_selected=operator_selected,
        crawl_depth=crawl_depth,
    )
    ts = now()
    con.execute(
        """
        INSERT INTO crawl_url_inventory(
            domain,url,source,source_sitemap,classification,eligibility,
            decision_reason,priority_score,sitemap_lastmod,sitemap_priority,
            crawl_depth,operator_selected,discovered_at,updated_at
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(domain,url) DO UPDATE SET
            source=CASE
                WHEN excluded.source='operator' THEN 'operator'
                WHEN crawl_url_inventory.source='operator' THEN crawl_url_inventory.source
                ELSE excluded.source END,
            source_sitemap=CASE WHEN excluded.source_sitemap<>'' THEN excluded.source_sitemap ELSE crawl_url_inventory.source_sitemap END,
            classification=CASE WHEN crawl_url_inventory.classification='unknown' THEN excluded.classification ELSE crawl_url_inventory.classification END,
            eligibility=CASE WHEN excluded.operator_selected=1 THEN 'eligible' ELSE crawl_url_inventory.eligibility END,
            decision_reason=CASE WHEN excluded.operator_selected=1 THEN 'operator_selected' ELSE crawl_url_inventory.decision_reason END,
            priority_score=MAX(crawl_url_inventory.priority_score,excluded.priority_score),
            sitemap_lastmod=CASE WHEN excluded.sitemap_lastmod<>'' THEN excluded.sitemap_lastmod ELSE crawl_url_inventory.sitemap_lastmod END,
            sitemap_priority=COALESCE(excluded.sitemap_priority,crawl_url_inventory.sitemap_priority),
            crawl_depth=MIN(crawl_url_inventory.crawl_depth,excluded.crawl_depth),
            operator_selected=MAX(crawl_url_inventory.operator_selected,excluded.operator_selected),
            updated_at=excluded.updated_at
        """,
        (
            domain, url, source, source_sitemap, classification, eligibility, reason,
            score, sitemap_lastmod or "", sitemap_priority, max(0, int(crawl_depth)),
            int(bool(operator_selected)), ts, ts,
        ),
    )
    row = con.execute(
        "SELECT id FROM crawl_url_inventory WHERE domain=? COLLATE NOCASE AND url=?",
        (domain, url),
    ).fetchone()
    return int(row["id"]) if row else None


def select_initial_inventory(con, domain: str, target: int) -> list:
    target = max(1, min(100, int(target)))
    rows = con.execute(
        """
        SELECT * FROM crawl_url_inventory
        WHERE domain=? COLLATE NOCASE AND eligibility='eligible'
        ORDER BY operator_selected DESC,priority_score DESC,url
        """,
        (domain,),
    ).fetchall()
    selected = [row for row in rows if row["operator_selected"]][:target]
    selected_ids = {row["id"] for row in selected}
    selected_event_families = {
        _event_family(row["url"])
        for row in selected
        if row["classification"] == "news_release"
    }
    groups: dict[str, list] = {}
    for row in rows:
        groups.setdefault(row["classification"], []).append(row)

    allocation = [
        ("core_page", min(12, max(8 if target >= 10 else target, round(target * 0.60)))),
        ("news_release", 2 if target >= 12 else 1),
        ("article", 2 if target >= 14 else 1),
        ("corporate_media", 1 if target >= 15 else 0),
        ("supporting_evidence", 1 if target >= 16 else 0),
        ("document_disclosure", 1 if target >= 18 else 0),
    ]
    for classification, wanted in allocation:
        already = sum(row["classification"] == classification for row in selected)
        for row in groups.get(classification, []):
            if row["id"] in selected_ids or already >= wanted or len(selected) >= target:
                continue
            if classification == "news_release":
                family = _event_family(row["url"])
                if family and family in selected_event_families:
                    continue
                selected_event_families.add(family)
            selected.append(row)
            selected_ids.add(row["id"])
            already += 1

    counts: dict[str, int] = {}
    for row in selected:
        counts[row["classification"]] = counts.get(row["classification"], 0) + 1
    for row in rows:
        classification = row["classification"]
        if row["id"] in selected_ids or len(selected) >= target:
            continue
        if counts.get(classification, 0) >= INITIAL_BUDGETS.get(classification, 1):
            continue
        selected.append(row)
        selected_ids.add(row["id"])
        counts[classification] = counts.get(classification, 0) + 1

    if len(selected) < target:
        for row in rows:
            if row["id"] not in selected_ids:
                selected.append(row)
                selected_ids.add(row["id"])
            if len(selected) >= target:
                break
    return sorted(selected[:target], key=lambda row: (-row["priority_score"], row["url"]))


def remaining_background_inventory(con, domain: str, limit: int) -> list:
    policy = get_policy(con, domain)
    retry_limit = int(policy["max_retry_count"])
    current = datetime.now(timezone.utc)
    ts = current.isoformat(timespec="seconds")
    day_start = (current - timedelta(days=1)).isoformat(timespec="seconds")
    week_start = (current - timedelta(days=7)).isoformat(timespec="seconds")
    used_day = con.execute(
        """
        SELECT COUNT(*) AS n FROM crawl_page cp JOIN crawl_run cr ON cr.id=cp.crawl_run_id
        WHERE cr.domain=? COLLATE NOCASE AND cp.created_at>=?
        """,
        (domain, day_start),
    ).fetchone()["n"]
    used_week = con.execute(
        """
        SELECT COUNT(*) AS n FROM crawl_page cp JOIN crawl_run cr ON cr.id=cp.crawl_run_id
        WHERE cr.domain=? COLLATE NOCASE AND cp.created_at>=?
        """,
        (domain, week_start),
    ).fetchone()["n"]
    day_remaining = max(0, int(policy["daily_page_budget"]) - int(used_day))
    week_remaining = max(0, int(policy["weekly_page_budget"]) - int(used_week))
    effective_limit = min(max(1, int(limit)), day_remaining, week_remaining)
    if effective_limit <= 0:
        return []
    candidates = con.execute(
        """
        SELECT * FROM crawl_url_inventory
        WHERE domain=? COLLATE NOCASE
          AND eligibility='eligible'
          AND retry_count<=?
          AND (next_crawl_at IS NULL OR next_crawl_at<=?)
          AND (last_crawled_at IS NULL OR classification='core_page')
        ORDER BY
          CASE WHEN last_crawled_at IS NULL THEN 0 ELSE 1 END,
          priority_score DESC,
          COALESCE(sitemap_lastmod,'') DESC,
          url
        LIMIT ?
        """,
        (domain, retry_limit, ts, min(1000, effective_limit * 10)),
    ).fetchall()
    selected = []
    pattern_counts: dict[tuple[str, str, str], int] = {}
    for row in candidates:
        key = _template_key(row)
        limited = row["classification"] in {
            "news_release", "article", "corporate_media", "archive_taxonomy", "unknown"
        }
        if limited and pattern_counts.get(key, 0) >= 3:
            continue
        selected.append(row)
        pattern_counts[key] = pattern_counts.get(key, 0) + 1
        if len(selected) >= effective_limit:
            break
    return selected


def queue_frontier(con, run_id: int, rows, reason: str) -> int:
    ts = now()
    count = 0
    for row in rows:
        count += con.execute(
            """
            INSERT OR IGNORE INTO crawl_frontier(
                crawl_run_id,url_inventory_id,state,reason,priority_score,queued_at,updated_at
            ) VALUES (?,?,'queued',?,?,?,?)
            """,
            (run_id, int(row["id"]), reason, int(row["priority_score"]), ts, ts),
        ).rowcount
    return count


def frontier_counts(con, run_id: int) -> dict[str, int]:
    counts = {key: 0 for key in ("queued", "fetching", "completed", "unchanged", "failed", "skipped", "cancelled")}
    for row in con.execute(
        "SELECT state,COUNT(*) AS n FROM crawl_frontier WHERE crawl_run_id=? GROUP BY state",
        (run_id,),
    ):
        counts[row["state"]] = int(row["n"])
    return counts


def schedule_next_crawl(con, inventory_id: int, classification: str, *, changed: bool) -> None:
    days = 7 if classification == "core_page" else 30 if changed else 90
    due = (datetime.now(timezone.utc) + timedelta(days=days)).isoformat(timespec="seconds")
    con.execute(
        "UPDATE crawl_url_inventory SET next_crawl_at=?,updated_at=? WHERE id=?",
        (due, now(), inventory_id),
    )
