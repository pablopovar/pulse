from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


def _connect(path: Path):
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


def _exists(con, name: str) -> bool:
    return bool(con.execute(
        "SELECT 1 FROM sqlite_master WHERE name=? LIMIT 1", (name,)
    ).fetchone())


def _rows(con, sql: str, params=()):
    return [dict(r) for r in con.execute(sql, params).fetchall()]


def _row(con, sql: str, params=()):
    r = con.execute(sql, params).fetchone()
    return dict(r) if r else None


def _safe_json(value, fallback):
    if not value:
        return fallback
    try:
        return json.loads(value)
    except Exception:
        return fallback


def enrich_report_data(data: dict[str, Any], seo_db: Path, site_id: str | None, domain: str):
    data.update({
        "ai_visibility_questions": [],
        "ai_visibility_checks": [],
        "rank_tracking": [],
        "backlinks": [],
        "ref_domains": [],
        "backlink_summary": None,
        "domain_metrics": None,
        "competitor_keywords": [],
        "clarity": None,
        "site_audit": None,
        "site_audit_pages": [],
        "sitemap_urls": [],
        "site_health": None,
    })

    if not seo_db.exists():
        return data

    with _connect(seo_db) as con:
        if site_id and _exists(con, "TrackedQuestion") and _exists(con, "AeoCheck"):
            data["ai_visibility_questions"] = _rows(
                con,
                'SELECT id,question,createdAt,lastCheckedAt,lastResults '
                'FROM "TrackedQuestion" WHERE siteId=? ORDER BY question',
                (site_id,),
            )
            checks = _rows(
                con,
                """
                SELECT
                    q.question,
                    c.engine,c.checkedAt,c.cited,c.url,c.snippet,c.error,
                    c.status,c.rank,c.model,c.searched,c.answerText,c.citations
                FROM "AeoCheck" c
                JOIN "TrackedQuestion" q ON q.id=c.questionId
                WHERE q.siteId=?
                ORDER BY c.checkedAt DESC,q.question,c.engine
                """,
                (site_id,),
            )
            for row in checks:
                row["citations_list"] = _safe_json(row.get("citations"), [])
            data["ai_visibility_checks"] = checks

        if site_id and _exists(con, "TrackedKeyword"):
            data["rank_tracking"] = _rows(
                con,
                """
                SELECT keyword,device,country,lang,lastCheckedAt,lastPosition,
                       prevPosition,bestPosition,lastUrl
                FROM "TrackedKeyword"
                WHERE siteId=?
                ORDER BY keyword
                """,
                (site_id,),
            )

        if site_id and _exists(con, "Backlink"):
            data["backlinks"] = _rows(
                con,
                """
                SELECT url,title,isAlive,aliveChecked,aliveStatus,xrStatus,xrChecked,addedAt
                FROM "Backlink" WHERE siteId=? ORDER BY addedAt DESC
                """,
                (site_id,),
            )

        if _exists(con, "RefDomainRow"):
            data["ref_domains"] = _rows(
                con,
                """
                SELECT target,refDomain,provider,dr,linksToTarget,dofollow,
                       firstSeen,lost,lostAt,source,fetchedAt
                FROM "RefDomainRow"
                WHERE target=? COLLATE NOCASE
                ORDER BY lost ASC,dr DESC,refDomain
                """,
                (domain,),
            )

        if _exists(con, "BacklinkSnapshot"):
            data["backlink_summary"] = _row(
                con,
                """
                SELECT target,date,provider,refDomains,backlinks,dofollowPct,source,createdAt
                FROM "BacklinkSnapshot"
                WHERE target=? COLLATE NOCASE
                ORDER BY date DESC LIMIT 1
                """,
                (domain,),
            )

        if _exists(con, "DomainMetricCache"):
            data["domain_metrics"] = _row(
                con,
                """
                SELECT domain,provider,dr,refDomains,backlinks,orgTraffic,orgKeywords,
                       orgCost,source,checkedAt
                FROM "DomainMetricCache"
                WHERE domain=? COLLATE NOCASE
                ORDER BY checkedAt DESC LIMIT 1
                """,
                (domain,),
            )

        if site_id and _exists(con, "CompetitorKeyword"):
            data["competitor_keywords"] = _rows(
                con,
                """
                SELECT competitor,keyword,country,position,volume,difficulty,url,source,fetchedAt
                FROM "CompetitorKeyword"
                WHERE siteId=?
                ORDER BY competitor,volume DESC,keyword
                """,
                (site_id,),
            )

        if site_id and _exists(con, "ClaritySnapshot"):
            data["clarity"] = _row(
                con,
                """
                SELECT fetchedAt,periodDays,data
                FROM "ClaritySnapshot"
                WHERE siteId=?
                ORDER BY fetchedAt DESC LIMIT 1
                """,
                (site_id,),
            )

        if site_id and _exists(con, "SiteAudit"):
            data["site_audit"] = _row(
                con,
                """
                SELECT id,status,stage,progress,attempt,startedAt,finishedAt,
                       pagesCrawled,summary,error
                FROM "SiteAudit"
                WHERE siteId=?
                ORDER BY startedAt DESC LIMIT 1
                """,
                (site_id,),
            )
            if data["site_audit"] and _exists(con, "SiteAuditPage"):
                data["site_audit_pages"] = _rows(
                    con,
                    """
                    SELECT url,httpStatus,redirectTo,contentType,title,metaDescription,
                           h1Count,canonical,noindex,internalLinks,externalLinks,imagesNoAlt,
                           wordCount,loadMs,depth,issues,evidence,brokenLinks
                    FROM "SiteAuditPage"
                    WHERE auditId=?
                    ORDER BY url
                    """,
                    (data["site_audit"]["id"],),
                )

        if site_id and _exists(con, "SitemapUrl"):
            data["sitemap_urls"] = _rows(
                con,
                """
                SELECT url,lastmod,firstSeenAt,lastSeenAt,inventoryStatus,changeStatus,
                       googleStatus,googleCoverage,googleReason,googleChecked,
                       contentHttpStatus,contentTitle,contentCheckedAt,lastmodReliability
                FROM "SitemapUrl"
                WHERE siteId=?
                ORDER BY url
                """,
                (site_id,),
            )

        if site_id and _exists(con, "SiteHealth"):
            data["site_health"] = _row(
                con,
                """
                SELECT checkedAt,sslData,safeBrowsing,vitals,virusTotal
                FROM "SiteHealth"
                WHERE siteId=?
                """,
                (site_id,),
            )

    return data
