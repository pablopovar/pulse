from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any


VALID_STATUSES = {
    "PASS",
    "FAIL",
    "PARTIAL",
    "MANUAL_REVIEW",
    "NOT_APPLICABLE",
    "DATA_UNAVAILABLE",
}
ISSUE_STATUSES = {"FAIL", "PARTIAL"}
REVIEW_STATUSES = {"MANUAL_REVIEW"}
NON_ISSUE_STATUSES = {"PASS", "NOT_APPLICABLE", "DATA_UNAVAILABLE"}

# UNKNOWN is a legacy transport value. At presentation/comparison time it means
# that the application could not establish a result from the available data.
LEGACY_STATUS_ALIASES = {"UNKNOWN": "DATA_UNAVAILABLE", "": "DATA_UNAVAILABLE"}

STATUS_ORDER = {
    "FAIL": 0,
    "PARTIAL": 1,
    "MANUAL_REVIEW": 2,
    "DATA_UNAVAILABLE": 3,
    "PASS": 4,
    "NOT_APPLICABLE": 5,
}

RECOMMENDATION_STATES = {
    "open",
    "in_progress",
    "implemented",
    "verified",
    "reopened",
    "accepted_risk",
}

ROOT_CAUSE_RULES = [
    (
        "schema-page-type",
        "Sitewide schema and page-type configuration",
        {
            "markup matches the page type",
            "page-type schema is appropriate",
            "web page or site type declared",
            "primary subject relationship declared",
            "responsible entity structured",
            "relevant structured data is available",
            "structured data matches visible content",
        },
    ),
    (
        "heading-structure",
        "Heading structure and page-template hierarchy",
        {
            "one clear h1",
            "heading hierarchy is sequential",
            "sections use h2 headings",
            "interior hierarchy is visible",
            "heading order is programmatic",
        },
    ),
    (
        "answer-structure",
        "Content is not consistently structured for answer retrieval",
        {
            "common follow-up questions addressed",
            "faq content is visible",
            "question-led headings",
            "multiple relevant question forms",
            "sections support fragment linking",
            "headed answer blocks",
            "answers follow question headings",
        },
    ),
    (
        "evidence-support",
        "Claims and evidence are not consistently substantiated",
        {
            "references or methodology section",
            "quantified claims supported",
            "source attribution language",
            "claims retain attribution context",
            "examples or first-hand evidence",
            "external supporting sources",
        },
    ),
    (
        "image-alternatives",
        "Image accessibility metadata is incomplete",
        {"image text alternatives"},
    ),
    (
        "indexability",
        "Indexability and crawl-control configuration",
        {
            "page is technically indexable",
            "robots.txt permits the page",
            "search snippets are permitted",
            "canonical url declared",
            "successful html response",
        },
    ),
    (
        "accessible-controls",
        "Interactive controls need accessibility fixes",
        {
            "buttons have accessible names",
            "form controls have accessible names",
            "link purpose is understandable",
            "skip navigation is offered",
        },
    ),
    (
        "identity-contact",
        "Organization identity and accountability signals are incomplete",
        {
            "organization or person identified",
            "contact and accountability information",
            "contact path reachable",
            "named experts or leadership",
        },
    ),
]

DEFAULT_OWNER_BY_FAMILY = {
    "Identity & Authority": "Communications / Brand",
    "Evidence & Trust": "Communications / Editorial",
    "Content & Answer Readiness": "Content / Editorial",
    "Machine Readability & Eligibility": "SEO / Web",
    "Onsite Audit": "Web / Engineering",
    "SEO Audit": "SEO / Growth",
    "AI Visibility": "Communications / Marketing",
}


def normalize_status(value: Any) -> str:
    status = str(value or "").strip().upper()
    status = LEGACY_STATUS_ALIASES.get(status, status)
    return status if status in VALID_STATUSES else "DATA_UNAVAILABLE"


def is_issue(value: Any) -> bool:
    return normalize_status(value) in ISSUE_STATUSES


def is_review(value: Any) -> bool:
    return normalize_status(value) in REVIEW_STATUSES


def rollup_status(statuses: list[Any]) -> str:
    normalized = [normalize_status(x) for x in statuses]
    if not normalized:
        return "DATA_UNAVAILABLE"
    if "FAIL" in normalized:
        return "FAIL"
    if "PARTIAL" in normalized:
        return "PARTIAL"
    if "MANUAL_REVIEW" in normalized:
        return "MANUAL_REVIEW"
    if "DATA_UNAVAILABLE" in normalized:
        return "DATA_UNAVAILABLE"
    if "PASS" in normalized:
        return "PASS"
    return "NOT_APPLICABLE"


def status_counts(checks: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(normalize_status(c.get("status")) for c in checks)
    return {
        "confirmed_issues": counts["FAIL"] + counts["PARTIAL"],
        "review_required": counts["MANUAL_REVIEW"],
        "data_unavailable": counts["DATA_UNAVAILABLE"],
        "not_applicable": counts["NOT_APPLICABLE"],
        "passed": counts["PASS"],
        "fail": counts["FAIL"],
        "partial": counts["PARTIAL"],
    }


def root_cause_key(title: str) -> tuple[str, str]:
    normalized = str(title or "").strip().lower()
    for key, label, titles in ROOT_CAUSE_RULES:
        if normalized in titles:
            return key, label
    return "check:" + normalized.replace(" ", "-"), str(title or "Issue")


def _evidence_refs(check: dict[str, Any], limit: int = 8) -> list[dict[str, Any]]:
    refs = []
    seen = set()
    for detail in check.get("details") or []:
        evidence = str(detail.get("evidence") or "").strip()
        url = str(detail.get("source_url") or detail.get("url") or "").strip()
        page = str(detail.get("path") or "").strip()
        marker = (page, url, evidence)
        if marker in seen or not any(marker):
            continue
        seen.add(marker)
        refs.append({"page": page, "url": url, "evidence": evidence})
        if len(refs) >= limit:
            break
    return refs


def confidence_for_check(check: dict[str, Any]) -> str:
    status = normalize_status(check.get("status"))
    if status in {"MANUAL_REVIEW", "DATA_UNAVAILABLE"}:
        return "low"
    if _evidence_refs(check):
        return "high"
    return "medium"


def evidence_type_for_check(check: dict[str, Any]) -> str:
    status = normalize_status(check.get("status"))
    if status == "MANUAL_REVIEW":
        return "manual_review_required"
    if status == "DATA_UNAVAILABLE":
        return "data_unavailable"
    details = check.get("details") or []
    if any(d.get("source_url") for d in details):
        return "page_observation_with_source"
    return "page_observation"


def monitoring_cadence_for_check(check: dict[str, Any]) -> str:
    status = normalize_status(check.get("status"))
    severity = str(check.get("severity") or "").upper()
    if status == "MANUAL_REVIEW":
        return "quarterly"
    if severity in {"CRITICAL", "HIGH"} or is_issue(status):
        return "monthly"
    return "quarterly"


def recommendation_object(check: dict[str, Any], family_name: str = "") -> dict[str, Any]:
    affected = int(check.get("pages_affected") or 0)
    tested = int(check.get("pages_tested") or 0)
    status = normalize_status(check.get("status"))
    existing = str(check.get("recommendation") or "").strip()
    scope = f"{affected} of {tested} tested pages" if tested else "Current tested scope"
    action = existing or (
        "Review the supporting evidence and correct the shared underlying condition, then rerun this check."
        if is_issue(status)
        else "Review the supporting evidence and record a human determination."
    )
    states = [str(d.get("workflow_status") or "").strip().lower() for d in check.get("details") or []]
    states = [s for s in states if s in RECOMMENDATION_STATES]
    state = states[0] if states else "open"
    return {
        "problem": str(check.get("title") or "Finding"),
        "why_it_matters": (
            f"This is a {str(check.get('severity') or 'reported').lower()} finding affecting {scope}."
            if is_issue(status)
            else "A human determination is required before this item can be treated as a confirmed defect."
        ),
        "recommended_action": action,
        "affected_scope": scope,
        "verification_method": (
            f"Rerun '{check.get('title') or 'this check'}' and confirm the affected scope is reduced or the status becomes PASS."
        ),
        "owner": DEFAULT_OWNER_BY_FAMILY.get(family_name) or None,
        "status": state,
    }


def enrich_check(check: dict[str, Any], family_name: str = "") -> dict[str, Any]:
    check["status"] = normalize_status(check.get("status"))
    check["is_confirmed_issue"] = is_issue(check["status"])
    check["is_review_required"] = is_review(check["status"])
    check["confidence"] = confidence_for_check(check)
    check["evidence_type"] = evidence_type_for_check(check)
    check["evidence_refs"] = _evidence_refs(check)
    check["recommendation_object"] = recommendation_object(check, family_name)
    check["monitoring_cadence"] = monitoring_cadence_for_check(check)
    return check


def group_root_causes(families: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for family in families:
        if family.get("kind") not in {"audit", "onsite"}:
            continue
        for category in family.get("categories_data") or []:
            for check in category.get("checks") or []:
                if not is_issue(check.get("status")):
                    continue
                key, label = root_cause_key(str(check.get("title") or ""))
                group = grouped.setdefault(key, {
                    "id": key,
                    "title": label,
                    "checks": [],
                    "families": set(),
                    "pages": set(),
                    "value_score": 0.0,
                    "severity": "",
                })
                group["checks"].append(check)
                group["families"].add(family.get("name") or "")
                group["value_score"] = max(group["value_score"], float(check.get("value_score") or 0))
                for detail in check.get("details") or []:
                    if is_issue(detail.get("observed_status")):
                        group["pages"].add(detail.get("path") or "/")
                severity = str(check.get("severity") or "")
                severity_order = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1, "": 0}
                if severity_order.get(severity, 0) > severity_order.get(group["severity"], 0):
                    group["severity"] = severity

    out = []
    for group in grouped.values():
        checks = group.pop("checks")
        families_set = group.pop("families")
        pages = group.pop("pages")
        representative = max(checks, key=lambda c: float(c.get("value_score") or 0))
        recommendation = recommendation_object(representative, next(iter(families_set), ""))
        recommendation["problem"] = group["title"]
        recommendation["affected_scope"] = f"{len(pages)} affected page{'s' if len(pages) != 1 else ''}"
        group.update({
            "supporting_checks": [
                {
                    "title": c.get("title"),
                    "family": next((f.get("name") for f in families if any(c is x for cat in f.get("categories_data") or [] for x in cat.get("checks") or [])), ""),
                    "status": normalize_status(c.get("status")),
                    "pages_affected": c.get("pages_affected"),
                    "pages_tested": c.get("pages_tested"),
                    "confidence": c.get("confidence"),
                    "signal_key": c.get("signal_key"),
                }
                for c in checks
            ],
            "family_names": sorted(x for x in families_set if x),
            "pages_affected": len(pages),
            "recommendation_object": recommendation,
            "confidence": "high" if all(c.get("confidence") == "high" for c in checks) else "medium",
        })
        out.append(group)
    out.sort(key=lambda x: (-float(x.get("value_score") or 0), -int(x.get("pages_affected") or 0), x.get("title") or ""))
    return out


def data_coverage(data: dict[str, Any]) -> list[dict[str, Any]]:
    inventory = {str(x.get("key") or ""): x for x in data.get("source_inventory") or []}

    def source_state(key: str, label: str, present: bool, detail: str = "", observed_at: str = "") -> dict[str, Any]:
        stored = inventory.get(key) or {}
        status_text = str(stored.get("status") or "").lower()
        selected = bool(stored.get("selected"))
        if "failed" in status_text or "error" in status_text:
            state = "failed"
        elif "stale" in status_text:
            state = "stale"
        elif present:
            state = "connected"
        elif not selected and ("not selected" in status_text or not stored):
            state = "not_selected"
        else:
            state = "missing"
        return {
            "key": key,
            "label": label,
            "state": state,
            "detail": detail or stored.get("detail") or "",
            "observed_at": observed_at or "",
        }

    def latest(rows: list[dict[str, Any]], *keys: str) -> str:
        values = [str(row.get(key) or "") for row in rows for key in keys if row.get(key)]
        return max(values) if values else ""

    seo = data.get("seo") or {}
    manual_ai = data.get("manual_ai_source") or data.get("manual_ai") or {}
    rows = [
        source_state("gsc", "Google Search Console", bool(seo.get("period_start") and seo.get("period_end")), observed_at=seo.get("period_end") or ""),
        source_state("ga4", "Google Analytics 4", bool(data.get("ga4")), observed_at=str((data.get("ga4") or {}).get("observed_at") or "")),
        source_state("clarity", "Microsoft Clarity", bool(data.get("clarity")), observed_at=str((data.get("clarity") or {}).get("createdAt") or (data.get("clarity") or {}).get("date") or "")),
        source_state("backlinks", "Backlink authority data", bool(data.get("backlinks") or data.get("ref_domains") or data.get("domain_metrics")), observed_at=(data.get("backlink_summary") or {}).get("createdAt") or (data.get("backlink_summary") or {}).get("date") or (data.get("domain_metrics") or {}).get("checkedAt") or latest(data.get("ref_domains") or [], "fetchedAt")),
        source_state("rank_tracking", "Rank tracking", bool(data.get("rank_tracking")), observed_at=latest(data.get("rank_tracking") or [], "lastCheckedAt")),
        source_state("sitemap", "Sitemap inventory", bool(data.get("sitemap_urls")), observed_at=latest(data.get("sitemap_urls") or [], "lastSeenAt", "fetchedAt")),
        source_state("manual_ai", "Manual AI Responses", bool(manual_ai.get("available")), observed_at=str(manual_ai.get("run_at_utc") or manual_ai.get("updated_at") or manual_ai.get("created_at") or "")),
    ]
    return rows


def monitoring_coverage_summary(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(r.get("state") for r in rows)
    return {"connected": counts["connected"], "missing": counts["missing"], "stale": counts["stale"], "failed": counts["failed"], "not_selected": counts["not_selected"]}


def _signal_index(snapshot: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    index = {}
    for signal in snapshot.get("audit_signals") or []:
        title = str(signal.get("title") or signal.get("signal_key") or "").strip().lower()
        page = str(signal.get("path") or signal.get("url") or "/").strip()
        if not title:
            continue
        index[(title, page)] = signal
    return index


def compare_snapshots(current: dict[str, Any], previous: dict[str, Any] | None) -> dict[str, Any]:
    if not previous:
        return {"available": False, "page_changes": [], "summary": {}}
    cur = _signal_index(current)
    old = _signal_index(previous)
    keys = sorted(set(cur) | set(old))
    changes = []
    for key in keys:
        c = cur.get(key)
        p = old.get(key)
        if c is None or p is None:
            change = ("new_issue" if is_issue(c.get("observed_status")) else "new_page") if c is not None else "no_longer_assessed"
            row = c or p
            changes.append({"check": key[0], "page": key[1], "change": change, "current": normalize_status(c.get("observed_status")) if c else None, "previous": normalize_status(p.get("observed_status")) if p else None, "row": row})
            continue
        cs = normalize_status(c.get("observed_status"))
        ps = normalize_status(p.get("observed_status"))
        if "MANUAL_REVIEW" in {cs, ps}:
            change = "requires_review"
        elif cs == "NOT_APPLICABLE" and ps != "NOT_APPLICABLE":
            change = "no_longer_applicable"
        elif "DATA_UNAVAILABLE" in {cs, ps}:
            change = "evidence_unavailable"
        elif cs == ps:
            change = "unchanged"
        elif ps in ISSUE_STATUSES and cs == "PASS":
            change = "resolved"
        elif ps == "FAIL" and cs == "PARTIAL":
            change = "improved"
        elif ps == "PARTIAL" and cs == "FAIL":
            change = "worsened"
        elif ps == "PASS" and is_issue(cs):
            change = "worsened"
        else:
            change = "requires_review"
        changes.append({"check": key[0], "page": key[1], "change": change, "current": cs, "previous": ps, "row": c})

    counts = Counter(x["change"] for x in changes)
    pages = defaultdict(list)
    for change in changes:
        pages[change["page"]].append(change["change"])
    pages_improved = sum(1 for vals in pages.values() if any(v in {"improved", "resolved"} for v in vals) and not any(v == "worsened" for v in vals))
    pages_regressed = sum(1 for vals in pages.values() if any(v == "worsened" for v in vals))
    summary = {
        "findings_resolved": counts["resolved"],
        "findings_improved": counts["improved"],
        "findings_worsened": counts["worsened"],
        "new_findings": counts["new_issue"],
        "unchanged_findings": counts["unchanged"],
        "requires_review": counts["requires_review"],
        "evidence_unavailable": counts["evidence_unavailable"],
        "no_longer_assessed": counts["no_longer_assessed"],
        "no_longer_applicable": counts["no_longer_applicable"],
        "pages_improved": pages_improved,
        "pages_regressed": pages_regressed,
    }
    regressions = [x for x in changes if x["change"] == "worsened" and normalize_status(x.get("current")) in ISSUE_STATUSES]
    regressions.sort(key=lambda x: str((x.get("row") or {}).get("severity") or ""))
    return {"available": True, "page_changes": changes, "summary": summary, "regression_alerts": regressions[:20]}


def family_trend_point(snapshot: dict[str, Any], family_definitions: list[dict[str, Any]]) -> dict[str, Any]:
    signals = snapshot.get("audit_signals") or []
    point = {"observed_at": ((snapshot.get("audit") or {}).get("completed_at") or (snapshot.get("audit") or {}).get("started_at") or "")}
    for family in family_definitions:
        if family.get("kind") not in {"audit", "onsite"}:
            continue
        cats = set(family.get("categories") or [])
        statuses = [normalize_status(s.get("observed_status")) for s in signals if s.get("category") in cats]
        point[family.get("id")] = rollup_status(statuses)
    ai_rows = snapshot.get("ai_visibility_checks") or []
    point["ai-visibility"] = "PASS" if ai_rows else "DATA_UNAVAILABLE"
    seo = snapshot.get("seo") or {}
    point["seo-audit"] = "PASS" if (seo.get("keywords") or seo.get("impressions") or snapshot.get("keywords")) else "DATA_UNAVAILABLE"
    return point


def build_trends(history: list[dict[str, Any]], family_definitions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [family_trend_point(s, family_definitions) for s in history]


def ai_metrics(data: dict[str, Any]) -> dict[str, Any]:
    rows = list(data.get("ai_visibility_checks") or [])
    if not rows:
        return {"available": False}
    total = len(rows)
    cited = sum(1 for r in rows if (str(r.get("status") or "").lower() == "cited") or r.get("cited"))
    mentioned = sum(1 for r in rows if str(r.get("status") or "").lower() == "mentioned")
    domain = str(data.get("domain") or "").lower()
    first_party = 0
    citation_count = 0
    for row in rows:
        for citation in row.get("citations_list") or []:
            citation_count += 1
            if str(citation.get("domain") or "").lower() == domain:
                first_party += 1
    return {
        "available": True,
        "brand_mention_rate": round((cited + mentioned) * 100 / total, 1) if total else 0.0,
        "citation_rate": round(cited * 100 / total, 1) if total else 0.0,
        "first_party_citation_rate": round(first_party * 100 / citation_count, 1) if citation_count else None,
        "competitor_mention_rate": None,
        "factual_consistency": None,
        "note": "Competitor mention rate and factual consistency require structured claim extraction and are not inferred from raw prose.",
    }


def validate_report(data: dict[str, Any], families: list[dict[str, Any]], root_causes: list[dict[str, Any]]) -> dict[str, Any]:
    warnings = []
    errors = []
    seen_titles = Counter(str(x.get("title") or "").strip().lower() for x in data.get("high_signal_findings") or [])
    dupes = [title for title, count in seen_titles.items() if title and count > 1]
    if dupes:
        errors.append("Duplicate executive findings: " + ", ".join(dupes))
    for family in families:
        snapshot = family.get("snapshot") or {}
        if snapshot.get("confirmed_issues", 0) != len(family.get("priority_findings") or []):
            errors.append(f"{family.get('name')}: confirmed-issue count does not match rendered priority findings.")
        for category in family.get("categories_data") or []:
            for check in category.get("checks") or []:
                if int(check.get("pages_affected") or 0) > int(check.get("pages_tested") or 0):
                    errors.append(f"{check.get('title')}: affected page count exceeds tested page count.")
                if is_issue(check.get("status")) and str(check.get("severity") or "").upper() in {"CRITICAL", "HIGH"} and not check.get("evidence_refs"):
                    warnings.append(f"{check.get('title')}: high-priority finding has no inspectable evidence reference.")
                if normalize_status(check.get("status")) == "MANUAL_REVIEW" and check.get("latest_change") in {"improved", "worsened", "resolved", "new_issue"}:
                    errors.append(f"{check.get('title')}: manual review was incorrectly classified as material movement.")
    coverage = data.get("data_coverage") or []
    missing = [x.get("label") for x in coverage if x.get("state") == "missing"]
    if missing:
        warnings.append("Missing monitoring sources: " + ", ".join(missing))
    seo = data.get("seo") or {}
    if (seo.get("impressions") or seo.get("clicks") or seo.get("keywords")) and not (seo.get("period_start") and seo.get("period_end")):
        errors.append("Google Search Console totals do not identify a bounded reporting period.")
    ga4 = next((x for x in coverage if x.get("key") == "ga4"), {})
    clarity = next((x for x in coverage if x.get("key") == "clarity"), {})
    if data.get("clarity") and ga4.get("state") == "connected" and not data.get("ga4"):
        errors.append("Microsoft Clarity data was incorrectly represented as Google Analytics 4 data.")
    for source in coverage:
        if source.get("state") == "connected" and not source.get("observed_at"):
            warnings.append(f"{source.get('label')}: connected source has no observation timestamp.")
    provenance = data.get("observation_provenance") or (data.get("report_metadata") or {}).get("observation_provenance") or {}
    if provenance.get("audit_run_id") and provenance.get("crawl_run_id"):
        if provenance.get("legacy_unlinked"):
            warnings.append("Legacy report: audit and crawl inputs were not linked to one durable execution; cross-source conclusions are limited.")
        elif not provenance.get("inputs_linked"):
            errors.append("Audit and crawl inputs do not belong to one coherent observation execution.")
    return {"errors": errors, "warnings": warnings, "blocking": bool(errors), "root_cause_count": len(root_causes)}
