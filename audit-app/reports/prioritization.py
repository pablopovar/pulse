from __future__ import annotations

import math
import re
from collections import defaultdict
from difflib import SequenceMatcher
from typing import Any

SEVERITY_FACTOR = {"CRITICAL": 4.0, "HIGH": 3.0, "MEDIUM": 2.0, "LOW": 1.0, "": 1.0}
STATUS_FACTOR = {
    "FAIL": 1.0,
    "PARTIAL": 0.65,
    "MANUAL_REVIEW": 0.0,
    "DATA_UNAVAILABLE": 0.0,
    "PASS": 0.0,
    "NOT_APPLICABLE": 0.0,
    # Legacy snapshots may still contain UNKNOWN. Treat it as unavailable data,
    # not as a detected defect.
    "UNKNOWN": 0.0,
}
SCORING_VERSION = "value-to-fix-v3"

# Report-presentation aliases only. Raw observations remain intact.
CHECK_ALIASES = {
    "indexing permitted": "Page is technically indexable",
    "page is technically indexable": "Page is technically indexable",
    "search snippets are permitted": "Search snippets are permitted",
    "snippet generation permitted": "Search snippets are permitted",
    "one clear h1": "One clear H1",
    "single primary heading": "One clear H1",
    "canonical url declared": "Canonical URL declared",
    "canonical relationship is explicit": "Canonical URL declared",
    "relevant structured data is available": "Relevant structured data is available",
    "machine readable structured data present": "Relevant structured data is available",
    "structured data is syntactically valid": "Structured data is syntactically valid",
    "json ld parses successfully": "Structured data is syntactically valid",
    "mobile viewport declared": "Mobile viewport declared",
    "responsive viewport is declared": "Mobile viewport declared",
    "all images declare alt behavior": "Image text alternatives",
    "informative images have text alternatives": "Image text alternatives",
    "image text alternatives": "Image text alternatives",
}


def _norm(text: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def canonical_check_title(title: str | None) -> str:
    text = (title or "").strip()
    return CHECK_ALIASES.get(_norm(text), text)


def traffic_by_page(data: dict[str, Any]) -> dict[str, float]:
    totals: dict[str, float] = defaultdict(float)
    for row in data.get("keywords") or []:
        page = str(row.get("page") or "").strip()
        if not page:
            continue
        try:
            totals[page] += float(row.get("impressions") or 0)
        except Exception:
            pass
    return dict(totals)


def _affected_page_exposure(details: list[dict[str, Any]], data: dict[str, Any]) -> dict[str, Any]:
    page_traffic = traffic_by_page(data)
    if not page_traffic:
        return {"exposure": 0.0, "affected_pages": 0, "matched_pages": 0}

    max_imp = max(page_traffic.values(), default=0.0)
    if max_imp <= 0:
        return {"exposure": 0.0, "affected_pages": 0, "matched_pages": 0}

    affected_refs: dict[str, tuple[str, str]] = {}
    for d in details:
        status = str(d.get("observed_status") or "").strip().upper()
        if status not in {"FAIL", "PARTIAL"}:
            continue
        url = str(d.get("url") or d.get("source_url") or "").strip()
        path = str(d.get("path") or "").strip()
        ref = url or path
        if not ref:
            continue
        affected_refs.setdefault(ref, (url, path))

    if not affected_refs:
        return {"exposure": 0.0, "affected_pages": 0, "matched_pages": 0}

    normalized = []
    matched_pages = 0
    for url, path in affected_refs.values():
        matched_impressions = 0.0
        if url and url in page_traffic:
            matched_impressions = float(page_traffic[url] or 0.0)
        elif path:
            matched_impressions = sum(
                float(imp or 0.0)
                for page, imp in page_traffic.items()
                if str(page).endswith(path)
            )

        if matched_impressions > 0:
            matched_pages += 1
            normalized.append(
                min(1.0, math.log1p(matched_impressions) / math.log1p(max_imp))
            )
        else:
            normalized.append(0.0)

    return {
        "exposure": sum(normalized) / len(normalized),
        "affected_pages": len(affected_refs),
        "matched_pages": matched_pages,
    }


def _detail_exposure(details: list[dict[str, Any]], data: dict[str, Any]) -> float:
    return float(_affected_page_exposure(details, data)["exposure"])


def value_to_fix_components(check: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
    severity_name = str(check.get("severity") or "").upper()
    status_name = str(check.get("status") or "").upper()
    severity = SEVERITY_FACTOR.get(severity_name, 1.0)
    status = STATUS_FACTOR.get(status_name, 0.0)
    affected = float(check.get("pages_affected") or 0)
    tested = float(check.get("pages_tested") or 0)
    prevalence = affected / tested if tested else 0.0
    page_traffic = traffic_by_page(data)
    traffic_available = bool(page_traffic)
    exposure_info = (
        _affected_page_exposure(check.get("details") or [], data)
        if traffic_available
        else {"exposure": 0.0, "affected_pages": 0, "matched_pages": 0}
    )
    exposure = float(exposure_info["exposure"])
    score = severity * status * (1.0 + 2.0 * exposure) * (1.0 + prevalence)
    return {
        "scoring_version": SCORING_VERSION,
        "severity": severity_name or "UNSPECIFIED",
        "severity_factor": severity,
        "status": status_name or "DATA_UNAVAILABLE",
        "status_factor": status,
        "prevalence": round(prevalence, 3),
        "traffic_available": traffic_available,
        "traffic_exposure": round(exposure, 3),
        "traffic_affected_pages": int(exposure_info["affected_pages"]),
        "traffic_matched_pages": int(exposure_info["matched_pages"]),
        "partial_inputs": not traffic_available,
        "formula": "severity_factor × status_factor × (1 + 2×traffic_exposure) × (1 + prevalence)",
        "score": round(score, 3),
    }


def value_to_fix(check: dict[str, Any], data: dict[str, Any]) -> float:
    return float(value_to_fix_components(check, data)["score"])


def merge_duplicate_checks(checks: list[dict[str, Any]], data: dict[str, Any]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for check in checks:
        grouped[canonical_check_title(check.get("title"))].append(check)
    merged = []
    for title, rows in grouped.items():
        details = []
        keys = []
        for row in rows:
            details.extend(row.get("details") or [])
            if row.get("signal_key"):
                keys.append(row["signal_key"])
        seen = set()
        deduped = []
        for d in details:
            marker = (d.get("page_id"), d.get("path"), d.get("signal_key"), d.get("observed_status"))
            if marker in seen:
                continue
            seen.add(marker)
            deduped.append(d)
        base = dict(rows[0])
        base["title"] = title
        base["signal_keys"] = sorted(set(keys))
        base["merged_check_count"] = len(rows)
        base["details"] = deduped
        affected = [d for d in deduped if str(d.get("observed_status") or "").upper() in {"FAIL", "PARTIAL"}]
        review = [d for d in deduped if str(d.get("observed_status") or "").upper() == "MANUAL_REVIEW"]
        unavailable = [d for d in deduped if str(d.get("observed_status") or "").upper() in {"UNKNOWN", "DATA_UNAVAILABLE"}]
        base["pages_affected"] = len({d.get("path") or "/" for d in affected})
        base["pages_review_required"] = len({d.get("path") or "/" for d in review})
        base["pages_data_unavailable"] = len({d.get("path") or "/" for d in unavailable})
        base["pages_tested"] = len({d.get("path") or "/" for d in deduped})
        base["traffic_exposure"] = round(_detail_exposure(deduped, data), 3)
        base["prevalence"] = round(base["pages_affected"] / base["pages_tested"], 3) if base["pages_tested"] else 0.0
        base["value_score_explanation"] = value_to_fix_components(base, data)
        base["value_score"] = base["value_score_explanation"]["score"]
        merged.append(base)
    merged.sort(key=lambda c: (-float(c.get("value_score") or 0), str(c.get("title") or "")))
    return merged


def build_high_signal_findings(data: dict[str, Any], families: list[dict[str, Any]], limit: int = 5) -> list[dict[str, Any]]:
    candidates = []
    seo = data.get("seo") or {}
    try:
        impressions = float(seo.get("impressions") or 0)
        clicks = float(seo.get("clicks") or 0)
        ctr = clicks / impressions if impressions else 0.0
    except Exception:
        impressions = clicks = ctr = 0.0
    if impressions >= 100 and ctr < 0.01:
        candidates.append({
            "title": "Search visibility is not turning into visits",
            "message": f"The site generated {int(impressions):,} search impressions but only {int(clicks):,} clicks. People are seeing the site in search far more often than they are choosing it.",
            "value_score": 20.0 + math.log1p(impressions),
            "source": "Google Search Console",
        })
    fmap = {f.get("id"): f for f in families}
    trust = fmap.get("evidence-trust") or {}
    broad_trust = [c for c in trust.get("priority_findings") or [] if c.get("pages_tested") and c.get("pages_affected", 0) / c["pages_tested"] >= 0.5]
    if broad_trust:
        pages = max(c.get("pages_affected") or 0 for c in broad_trust)
        candidates.append({
            "title": "The main gap is evidence and trust, not visibility",
            "message": f"Confirmed evidence-related findings affect as many as {pages} tested pages. Important claims are not consistently supported in a way a reader or AI system can independently evaluate.",
            "value_score": 18.0 + max(float(c.get("value_score") or 0) for c in broad_trust),
            "source": "Evidence & Trust",
        })
    for family in families:
        if family.get("kind") not in {"audit", "onsite"}:
            continue
        for check in family.get("priority_findings") or []:
            affected = int(check.get("pages_affected") or 0)
            tested = int(check.get("pages_tested") or 0)
            if not affected:
                continue
            title = str(check.get("title") or "Site-wide issue")
            msg = f"{title} is a repeated site-wide pattern: {affected} of {tested} tested pages are affected." if tested > 1 and affected > 1 else f"{title} needs attention on {affected} tested page."
            candidates.append({"title": title, "message": msg, "value_score": float(check.get("value_score") or 0), "source": family.get("name") or ""})
    out, seen = [], set()
    for item in sorted(candidates, key=lambda x: -float(x["value_score"])):
        key = _norm(item["title"])
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
        if len(out) >= max(1, min(5, limit)):
            break
    return out


METHODOLOGY = (
    "The report separates confirmed observations, review-required items, not-applicable checks, and unavailable data. "
    "Only FAIL and PARTIAL count as confirmed issues. Page-level observations are rolled up into check-level and root-cause findings while raw evidence remains available in the interactive report. "
    "Value to fix prioritizes confirmed issues using severity, observed search exposure when available, and site-wide prevalence. Manual review and unavailable data do not receive defect scores."
)

GLOSSARY = [
    ("GEO", "How well content can be understood, selected, and cited by generative systems."),
    ("AEO", "How clearly the site provides extractable answers to questions and intents."),
    ("AIO / AI visibility", "What AI systems actually say, cite, omit, or attribute about the entity."),
    ("Manual review", "A check that cannot be established automatically and requires a human determination; it is not a confirmed defect."),
    ("Data unavailable", "A source or observation required for the check was not available; it is not a failed check."),
    ("Value to fix", "severity × status factor × (1 + 2×traffic exposure) × (1 + site-wide prevalence). Traffic exposure is the mean normalized search visibility of the pages where the finding is actually FAIL/PARTIAL; prevalence is measured separately. If search exposure is unavailable, the report marks the score as based on partial inputs and uses zero traffic exposure rather than inventing it."),
]


def overlap_candidates(titles: list[str], threshold: float = 0.72) -> list[dict[str, Any]]:
    normed = [(t, _norm(t)) for t in titles if t]
    rows = []
    for i, (a, na) in enumerate(normed):
        for b, nb in normed[i + 1:]:
            if a == b:
                continue
            ta, tb = set(na.split()), set(nb.split())
            jac = len(ta & tb) / len(ta | tb) if ta | tb else 0.0
            seq = SequenceMatcher(None, na, nb).ratio()
            aliased = canonical_check_title(a) == canonical_check_title(b)
            score = max(jac, seq, 1.0 if aliased else 0.0)
            if score >= threshold:
                rows.append({"a": a, "b": b, "similarity": round(score, 3), "explicit_alias": aliased})
    rows.sort(key=lambda x: (-x["similarity"], x["a"], x["b"]))
    return rows