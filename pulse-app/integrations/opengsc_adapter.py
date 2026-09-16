from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from db.sqlite import connect_sqlite


class OpenGSCAdapter:
    """Read-only boundary around the OpenGSC SQLite schema.

    Pulse services consume normalized Python dictionaries from this adapter and
    should not depend on OpenGSC-owned table or view names directly.
    """

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)

    def available(self) -> bool:
        return self.db_path.exists()

    def _connect(self):
        if not self.available():
            raise FileNotFoundError(self.db_path)
        return connect_sqlite(self.db_path, readonly=True)

    @staticmethod
    def _exists(con, name: str, kind: str | None = None) -> bool:
        if kind:
            return bool(con.execute(
                "SELECT 1 FROM sqlite_master WHERE name=? AND type=? LIMIT 1", (name, kind)
            ).fetchone())
        return bool(con.execute("SELECT 1 FROM sqlite_master WHERE name=? LIMIT 1", (name,)).fetchone())

    @staticmethod
    def _rows(con, sql: str, params=()) -> list[dict[str, Any]]:
        return [dict(r) for r in con.execute(sql, params).fetchall()]

    @staticmethod
    def _row(con, sql: str, params=()) -> dict[str, Any] | None:
        row = con.execute(sql, params).fetchone()
        return dict(row) if row else None

    @staticmethod
    def _safe_json(value, fallback):
        if not value:
            return fallback
        try:
            return json.loads(value)
        except Exception:
            return fallback

    def list_sites(self) -> list[dict[str, Any]]:
        if not self.available():
            return []
        with self._connect() as con:
            if not self._exists(con, "Site"):
                return []
            return self._rows(
                con,
                'SELECT id,url,siteId,archivedAt FROM "Site" WHERE archivedAt IS NULL ORDER BY url',
            )

    def gsc_keyword_rows(self, site_id: str | None) -> list[dict[str, Any]]:
        if not site_id or not self.available():
            return []
        with self._connect() as con:
            cols = {row["name"] for row in con.execute("PRAGMA table_info(gsc_keyword_inventory)").fetchall()}
            if not cols:
                return []
            keyword_col = "query" if "query" in cols else "keyword" if "keyword" in cols else None
            if not keyword_col or "page" not in cols:
                return []
            latest_col = "latest_position" if "latest_position" in cols else None
            impressions_col = "total_impressions" if "total_impressions" in cols else "impressions" if "impressions" in cols else None
            clicks_col = "total_clicks" if "total_clicks" in cols else "clicks" if "clicks" in cols else None
            parts = [
                f"{keyword_col} AS keyword",
                "page AS page",
                f"{latest_col} AS latest_position" if latest_col else "NULL AS latest_position",
                f"{impressions_col} AS impressions" if impressions_col else "0 AS impressions",
                f"{clicks_col} AS clicks" if clicks_col else "0 AS clicks",
            ]
            sql = "SELECT " + ", ".join(parts) + " FROM gsc_keyword_inventory"
            params: list[Any] = []
            if "site_id" in cols:
                sql += " WHERE site_id=?"
                params.append(site_id)
            return self._rows(con, sql, params)

    def domain_seo(self, site_id: str | None):
        if not site_id or not self.available():
            return None, []
        with self._connect() as con:
            summary = None
            if self._exists(con, "gsc_keyword_observation", "table"):
                summary = self._row(
                    con,
                    """
                    SELECT COUNT(*) AS observations,
                           COUNT(DISTINCT query) AS keywords,
                           COUNT(DISTINCT page) AS pages,
                           COALESCE(SUM(impressions),0) AS impressions,
                           COALESCE(SUM(clicks),0) AS clicks,
                           ROUND(MIN(position),1) AS best_position,
                           ROUND(MAX(position),1) AS worst_position
                    FROM gsc_keyword_observation WHERE site_id=?
                    """,
                    (site_id,),
                )
            recent = []
            if self._exists(con, "gsc_keyword_inventory"):
                recent = self._rows(
                    con,
                    """
                    SELECT query,page,impressions,clicks,
                           ROUND(best_position,1) AS best_position,
                           ROUND(latest_position,1) AS latest_position,
                           status,first_seen,last_seen
                    FROM gsc_keyword_inventory
                    WHERE site_id=?
                    ORDER BY CASE status
                               WHEN 'active_7d' THEN 1
                               WHEN 'active_30d' THEN 2
                               WHEN 'stale_90d' THEN 3
                               ELSE 4 END,
                             impressions DESC,best_position ASC
                    LIMIT 20
                    """,
                    (site_id,),
                )
        return summary, recent

    def landing_page_rows(self, site_id: str | None, q: str = "") -> list[dict[str, Any]]:
        if not site_id or not self.available():
            return []
        with self._connect() as con:
            if not self._exists(con, "gsc_keyword_inventory"):
                return []
            sql = """
                SELECT page,
                       COUNT(DISTINCT query) AS keywords,
                       COALESCE(SUM(impressions),0) AS impressions,
                       COALESCE(SUM(clicks),0) AS clicks,
                       ROUND(MIN(best_position),1) AS best_position,
                       ROUND(AVG(avg_position),1) AS avg_position,
                       MAX(last_seen) AS last_seen
                FROM gsc_keyword_inventory
                WHERE site_id=?
            """
            params: list[Any] = [site_id]
            if q:
                sql += " AND (page LIKE ? OR query LIKE ?)"
                like = f"%{q}%"
                params.extend([like, like])
            sql += " GROUP BY page ORDER BY impressions DESC,best_position ASC,page"
            return self._rows(con, sql, params)

    def page_detail(self, site_id: str | None, page_url: str):
        if not site_id or not self.available():
            return [], None
        with self._connect() as con:
            if not self._exists(con, "gsc_keyword_inventory"):
                return [], None
            keywords = self._rows(
                con,
                """
                SELECT query,observations,impressions,clicks,
                       ROUND(best_position,1) AS best_position,
                       ROUND(avg_position,1) AS avg_position,
                       ROUND(latest_position,1) AS latest_position,
                       ROUND(worst_position,1) AS worst_position,
                       status,first_seen,last_seen
                FROM gsc_keyword_inventory
                WHERE site_id=? AND page=?
                ORDER BY impressions DESC,best_position ASC
                """,
                (site_id, page_url),
            )
            summary = self._row(
                con,
                """
                SELECT COUNT(DISTINCT query) AS keywords,
                       COALESCE(SUM(impressions),0) AS impressions,
                       COALESCE(SUM(clicks),0) AS clicks,
                       ROUND(MIN(best_position),1) AS best_position,
                       ROUND(AVG(avg_position),1) AS avg_position,
                       MAX(last_seen) AS last_seen
                FROM gsc_keyword_inventory
                WHERE site_id=? AND page=?
                """,
                (site_id, page_url),
            )
            return keywords, summary

    def keyword_rows(self, site_id: str | None) -> list[dict[str, Any]]:
        if not site_id or not self.available():
            return []
        with self._connect() as con:
            if not self._exists(con, "gsc_keyword_inventory"):
                return []
            return self._rows(
                con,
                """
                SELECT query,page,ROUND(latest_position,1) AS ranking
                FROM gsc_keyword_inventory
                WHERE site_id=?
                ORDER BY CASE WHEN latest_position IS NULL THEN 1 ELSE 0 END,
                         latest_position ASC,query COLLATE NOCASE ASC,page ASC
                """,
                (site_id,),
            )

    def domain_export(self, site_id: str | None) -> dict[str, list[dict[str, Any]]]:
        empty = {"keywords": [], "landing_pages": [], "page_keywords": []}
        if not site_id or not self.available():
            return empty
        with self._connect() as con:
            if not self._exists(con, "gsc_keyword_inventory"):
                return empty
            return {
                "keywords": self._rows(
                    con,
                    """
                    SELECT query AS keyword,
                           ROUND(MIN(best_position),1) AS best_ranking,
                           ROUND(MIN(latest_position),1) AS latest_ranking,
                           SUM(impressions) AS impressions,SUM(clicks) AS clicks,
                           MIN(first_seen) AS first_seen,MAX(last_seen) AS last_seen,
                           COUNT(DISTINCT page) AS landing_pages
                    FROM gsc_keyword_inventory WHERE site_id=?
                    GROUP BY query
                    ORDER BY CASE WHEN MIN(latest_position) IS NULL THEN 1 ELSE 0 END,
                             MIN(latest_position) ASC,query COLLATE NOCASE ASC
                    """,
                    (site_id,),
                ),
                "landing_pages": self._rows(
                    con,
                    """
                    SELECT page AS landing_page,COUNT(DISTINCT query) AS keywords,
                           SUM(impressions) AS impressions,SUM(clicks) AS clicks,
                           ROUND(MIN(best_position),1) AS best_ranking,
                           ROUND(AVG(avg_position),1) AS avg_ranking,
                           MIN(first_seen) AS first_seen,MAX(last_seen) AS last_seen
                    FROM gsc_keyword_inventory WHERE site_id=?
                    GROUP BY page ORDER BY impressions DESC,best_ranking ASC,landing_page ASC
                    """,
                    (site_id,),
                ),
                "page_keywords": self._rows(
                    con,
                    """
                    SELECT page AS landing_page,query AS keyword,
                           ROUND(best_position,1) AS best_ranking,
                           ROUND(avg_position,1) AS avg_ranking,
                           ROUND(latest_position,1) AS latest_ranking,
                           ROUND(worst_position,1) AS worst_ranking,
                           impressions,clicks,status,first_seen,last_seen
                    FROM gsc_keyword_inventory WHERE site_id=?
                    ORDER BY landing_page ASC,latest_ranking ASC,keyword COLLATE NOCASE ASC
                    """,
                    (site_id,),
                ),
            }

    def detected_source_state(self, site_id: str | None) -> dict[str, dict[str, Any]]:
        out: dict[str, dict[str, Any]] = {}
        if not site_id or not self.available():
            return out
        with self._connect() as con:
            if self._exists(con, "ClaritySnapshot") and con.execute(
                'SELECT 1 FROM "ClaritySnapshot" WHERE siteId=? LIMIT 1', (site_id,)
            ).fetchone():
                out["ga4"] = {"connected": True, "detail": "Analytics/Clarity snapshot available"}
            if self._exists(con, "AeoCheck") and self._exists(con, "TrackedQuestion"):
                engines = con.execute(
                    'SELECT DISTINCT c.engine FROM "AeoCheck" c JOIN "TrackedQuestion" q ON q.id=c.questionId WHERE q.siteId=?',
                    (site_id,),
                ).fetchall()
                found = {str(r["engine"]).lower() for r in engines if r["engine"]}
                for key in ("chatgpt", "claude", "gemini"):
                    if key in found:
                        out[key] = {"connected": True, "detail": f"Stored {key.title()} observations available"}
        return out

    def report_core(self, site_id: str | None) -> dict[str, Any]:
        data: dict[str, Any] = {"seo": None, "keywords": []}
        if not site_id or not self.available():
            return data
        with self._connect() as con:
            if self._exists(con, "gsc_keyword_observation"):
                data["seo"] = self._row(
                    con,
                    """
                    SELECT COUNT(DISTINCT query) AS keywords,
                           COUNT(DISTINCT page) AS pages,
                           COALESCE(SUM(impressions),0) AS impressions,
                           COALESCE(SUM(clicks),0) AS clicks,
                           ROUND(MIN(position),1) AS best_position,
                           ROUND(MAX(position),1) AS worst_position,
                           MIN(date) AS first_date,MAX(date) AS last_date
                    FROM gsc_keyword_observation WHERE site_id=?
                    """,
                    (site_id,),
                )
            if self._exists(con, "gsc_keyword_inventory"):
                data["keywords"] = self._rows(
                    con,
                    """
                    SELECT query,page,COALESCE(impressions,0) impressions,
                           COALESCE(clicks,0) clicks,ROUND(best_position,1) best_position,
                           ROUND(latest_position,1) latest_position,status,first_seen,last_seen
                    FROM gsc_keyword_inventory WHERE site_id=?
                    ORDER BY impressions DESC,best_position ASC,query LIMIT 100
                    """,
                    (site_id,),
                )
        return data

    def enrich_report(self, data: dict[str, Any], site_id: str | None, domain: str) -> dict[str, Any]:
        data.update({
            "ai_visibility_questions": [], "ai_visibility_checks": [], "rank_tracking": [],
            "backlinks": [], "ref_domains": [], "backlink_summary": None, "domain_metrics": None,
            "competitor_keywords": [], "clarity": None, "site_audit": None, "site_audit_pages": [],
            "sitemap_urls": [], "site_health": None,
        })
        if not self.available():
            return data
        with self._connect() as con:
            if site_id and self._exists(con, "TrackedQuestion") and self._exists(con, "AeoCheck"):
                data["ai_visibility_questions"] = self._rows(
                    con,
                    'SELECT id,question,createdAt,lastCheckedAt,lastResults FROM "TrackedQuestion" WHERE siteId=? ORDER BY question',
                    (site_id,),
                )
                checks = self._rows(
                    con,
                    """
                    SELECT q.question,c.engine,c.checkedAt,c.cited,c.url,c.snippet,c.error,
                           c.status,c.rank,c.model,c.searched,c.answerText,c.citations
                    FROM "AeoCheck" c JOIN "TrackedQuestion" q ON q.id=c.questionId
                    WHERE q.siteId=? ORDER BY c.checkedAt DESC,q.question,c.engine
                    """,
                    (site_id,),
                )
                for row in checks:
                    row["citations_list"] = self._safe_json(row.get("citations"), [])
                data["ai_visibility_checks"] = checks

            if site_id and self._exists(con, "TrackedKeyword"):
                data["rank_tracking"] = self._rows(
                    con,
                    'SELECT keyword,device,country,lang,lastCheckedAt,lastPosition,prevPosition,bestPosition,lastUrl FROM "TrackedKeyword" WHERE siteId=? ORDER BY keyword',
                    (site_id,),
                )
            if site_id and self._exists(con, "Backlink"):
                data["backlinks"] = self._rows(
                    con,
                    'SELECT url,title,isAlive,aliveChecked,aliveStatus,xrStatus,xrChecked,addedAt FROM "Backlink" WHERE siteId=? ORDER BY addedAt DESC',
                    (site_id,),
                )
            if self._exists(con, "RefDomainRow"):
                data["ref_domains"] = self._rows(
                    con,
                    'SELECT target,refDomain,provider,dr,linksToTarget,dofollow,firstSeen,lost,lostAt,source,fetchedAt FROM "RefDomainRow" WHERE target=? COLLATE NOCASE ORDER BY lost ASC,dr DESC,refDomain',
                    (domain,),
                )
            if self._exists(con, "BacklinkSnapshot"):
                data["backlink_summary"] = self._row(
                    con,
                    'SELECT target,date,provider,refDomains,backlinks,dofollowPct,source,createdAt FROM "BacklinkSnapshot" WHERE target=? COLLATE NOCASE ORDER BY date DESC LIMIT 1',
                    (domain,),
                )
            if self._exists(con, "DomainMetricCache"):
                data["domain_metrics"] = self._row(
                    con,
                    'SELECT domain,provider,dr,refDomains,backlinks,orgTraffic,orgKeywords,orgCost,source,checkedAt FROM "DomainMetricCache" WHERE domain=? COLLATE NOCASE ORDER BY checkedAt DESC LIMIT 1',
                    (domain,),
                )
            if site_id and self._exists(con, "CompetitorKeyword"):
                data["competitor_keywords"] = self._rows(
                    con,
                    'SELECT competitor,keyword,country,position,volume,difficulty,url,source,fetchedAt FROM "CompetitorKeyword" WHERE siteId=? ORDER BY competitor,volume DESC,keyword',
                    (site_id,),
                )
            if site_id and self._exists(con, "ClaritySnapshot"):
                data["clarity"] = self._row(
                    con,
                    'SELECT fetchedAt,periodDays,data FROM "ClaritySnapshot" WHERE siteId=? ORDER BY fetchedAt DESC LIMIT 1',
                    (site_id,),
                )
            if site_id and self._exists(con, "SiteAudit"):
                data["site_audit"] = self._row(
                    con,
                    'SELECT id,status,stage,progress,attempt,startedAt,finishedAt,pagesCrawled,summary,error FROM "SiteAudit" WHERE siteId=? ORDER BY startedAt DESC LIMIT 1',
                    (site_id,),
                )
                if data["site_audit"] and self._exists(con, "SiteAuditPage"):
                    data["site_audit_pages"] = self._rows(
                        con,
                        'SELECT url,httpStatus,redirectTo,contentType,title,metaDescription,h1Count,canonical,noindex,internalLinks,externalLinks,imagesNoAlt,wordCount,loadMs,depth,issues,evidence,brokenLinks FROM "SiteAuditPage" WHERE auditId=? ORDER BY url',
                        (data["site_audit"]["id"],),
                    )
            if site_id and self._exists(con, "SitemapUrl"):
                data["sitemap_urls"] = self._rows(
                    con,
                    'SELECT url,lastmod,firstSeenAt,lastSeenAt,inventoryStatus,changeStatus,googleStatus,googleCoverage,googleReason,googleChecked,contentHttpStatus,contentTitle,contentCheckedAt,lastmodReliability FROM "SitemapUrl" WHERE siteId=? ORDER BY url',
                    (site_id,),
                )
            if site_id and self._exists(con, "SiteHealth"):
                data["site_health"] = self._row(
                    con,
                    'SELECT checkedAt,sslData,safeBrowsing,vitals,virusTotal FROM "SiteHealth" WHERE siteId=?',
                    (site_id,),
                )
        return data
