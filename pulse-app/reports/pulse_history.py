from __future__ import annotations

from collections import defaultdict
from typing import Any

from reports.prioritization import canonical_check_title
from reports.report_intelligence import is_issue, is_review, normalize_status, rollup_status


SEVERITY_ORDER = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1, "": 0}
STATUS_ORDER = {
    "FAIL": 0,
    "PARTIAL": 1,
    "MANUAL_REVIEW": 2,
    "DATA_UNAVAILABLE": 3,
    "PASS": 4,
    "NOT_APPLICABLE": 5,
}


def finding_key(category: str, title: str) -> str:
    return f"{str(category or '').strip().lower()}::{canonical_check_title(title).strip().lower()}"


def _rollup_severity(rows: list[dict[str, Any]]) -> str:
    best = ""
    for row in rows:
        sev = str(row.get("severity") or "").upper()
        if SEVERITY_ORDER.get(sev, 0) > SEVERITY_ORDER.get(best, 0):
            best = sev
    return best


def _snapshot_observations(snapshot: dict[str, Any], *, report_id: str, observed_at: str) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for raw in snapshot.get("audit_signals") or []:
        row = dict(raw)
        row["observed_status"] = normalize_status(row.get("observed_status"))
        title = canonical_check_title(row.get("title") or row.get("signal_key") or "")
        category = str(row.get("category") or "")
        if not title:
            continue
        grouped[finding_key(category, title)].append(row)

    out: dict[str, dict[str, Any]] = {}
    for key, rows in grouped.items():
        title = canonical_check_title(rows[0].get("title") or rows[0].get("signal_key") or "")
        category = str(rows[0].get("category") or "")
        family = str(rows[0].get("family") or "")
        statuses = [r.get("observed_status") for r in rows]
        affected = {str(r.get("path") or r.get("url") or "/") for r in rows if is_issue(r.get("observed_status"))}
        reviews = {str(r.get("path") or r.get("url") or "/") for r in rows if is_review(r.get("observed_status"))}
        unavailable = {
            str(r.get("path") or r.get("url") or "/")
            for r in rows
            if normalize_status(r.get("observed_status")) == "DATA_UNAVAILABLE"
        }
        tested = {str(r.get("path") or r.get("url") or "/") for r in rows}
        page_statuses: dict[str, str] = {}
        for row in rows:
            page = str(row.get("path") or row.get("url") or "/")
            status = normalize_status(row.get("observed_status"))
            existing = page_statuses.get(page)
            if existing is None or STATUS_ORDER.get(status, 0) < STATUS_ORDER.get(existing, 0):
                page_statuses[page] = status
        out[key] = {
            "finding_key": key,
            "title": title,
            "category": category,
            "family": family,
            "status": rollup_status(statuses),
            "severity": _rollup_severity(rows),
            "pages_affected": len(affected),
            "pages_review_required": len(reviews),
            "pages_data_unavailable": len(unavailable),
            "pages_tested": len(tested),
            "tested_pages": sorted(tested),
            "affected_pages": sorted(affected),
            "page_statuses": page_statuses,
            "observed_at": observed_at,
            "report_id": report_id,
            "audit_run_id": (snapshot.get("audit") or {}).get("id"),
        }
    return out


MATERIAL_CHANGES = {"resolved", "improved", "worsened", "new_issue", "mixed"}


def _page_change(current_status: str, previous_status: str | None) -> str:
    """Compare one check on one exact page identity.

    A changed crawl cohort is lifecycle information, not a comparison result.
    /about and /about-us therefore remain separate histories.
    """
    if previous_status is None:
        return "new_issue" if is_issue(current_status) else "new_page"
    current_status = normalize_status(current_status)
    previous_status = normalize_status(previous_status)
    if current_status == previous_status:
        return "unchanged"
    if "MANUAL_REVIEW" in {current_status, previous_status}:
        return "requires_review"
    if "DATA_UNAVAILABLE" in {current_status, previous_status}:
        return "evidence_unavailable"
    if current_status == "NOT_APPLICABLE" or previous_status == "NOT_APPLICABLE":
        return "no_longer_applicable"
    if previous_status in {"FAIL", "PARTIAL"} and current_status == "PASS":
        return "resolved"
    if previous_status == "FAIL" and current_status == "PARTIAL":
        return "improved"
    if previous_status == "PARTIAL" and current_status == "FAIL":
        return "worsened"
    if previous_status == "PASS" and is_issue(current_status):
        return "worsened"
    return "requires_review"


def _rollup_page_changes(changes: list[str]) -> str:
    material = {change for change in changes if change in MATERIAL_CHANGES}
    negative = material & {"worsened", "new_issue"}
    positive = material & {"resolved", "improved"}
    if negative and positive:
        return "mixed"
    if "worsened" in material:
        return "worsened"
    if "new_issue" in material:
        return "new_issue"
    if "resolved" in material:
        return "resolved"
    if "improved" in material:
        return "improved"
    if "requires_review" in changes:
        return "requires_review"
    if "evidence_unavailable" in changes:
        return "evidence_unavailable"
    if "no_longer_applicable" in changes:
        return "no_longer_applicable"
    if "new_page" in changes:
        return "new_page"
    return "unchanged"


def classify_change(current: dict[str, Any], previous: dict[str, Any] | None) -> str:
    """Compatibility wrapper: compare only pages assessed in the current run."""
    current_pages = dict(current.get("page_statuses") or {})
    previous_pages = dict((previous or {}).get("page_statuses") or {})
    return _rollup_page_changes([
        _page_change(status, previous_pages.get(page))
        for page, status in current_pages.items()
    ])


def _dedupe_audit_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    position_by_run: dict[str, int] = {}

    for record in records:
        snapshot = record.get("snapshot") or {}
        audit_run_id = str((snapshot.get("audit") or {}).get("id") or "").strip()

        if not audit_run_id:
            deduped.append(record)
            continue

        if audit_run_id in position_by_run:
            deduped[position_by_run[audit_run_id]] = record
        else:
            position_by_run[audit_run_id] = len(deduped)
            deduped.append(record)

    return deduped


def build_finding_history(records: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    history: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in _dedupe_audit_records(records):
        snapshot = record.get("snapshot") or {}
        observed_at = str(
            (snapshot.get("audit") or {}).get("completed_at")
            or (snapshot.get("audit") or {}).get("started_at")
            or record.get("created_at")
            or ""
        )
        observations = _snapshot_observations(
            snapshot,
            report_id=str(record.get("id") or ""),
            observed_at=observed_at,
        )
        for key, observation in observations.items():
            previous = history[key][-1] if history[key] else None
            prior_pages = dict((previous or {}).get("page_statuses") or {})
            current_pages = dict(observation.get("page_statuses") or {})
            observation["page_changes"] = {
                page: _page_change(status, prior_pages.get(page))
                for page, status in current_pages.items()
            }
            observation["newly_observed_pages"] = sorted(set(current_pages) - set(prior_pages))
            observation["no_longer_assessed_pages"] = sorted(set(prior_pages) - set(current_pages))
            observation["change"] = _rollup_page_changes(list(observation["page_changes"].values()))
            history[key].append(observation)

    for rows in history.values():
        last_material = None
        for row in rows:
            if row.get("change") in MATERIAL_CHANGES:
                last_material = row
            row["last_material_change"] = (last_material or {}).get("change") or ""
            row["last_material_changed_at"] = (last_material or {}).get("observed_at") or ""
    return dict(history)


def attach_history_to_check(check: dict[str, Any], history: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    key = finding_key(str(check.get("category") or ""), str(check.get("title") or ""))
    rows = list(history.get(key) or [])
    check["finding_key"] = key
    material_rows = [row for row in rows if row.get("change") in MATERIAL_CHANGES]
    check["history"] = material_rows
    check["history_count"] = len(material_rows)
    check["observation_count"] = len(rows)
    if rows:
        latest = rows[-1]
        check["latest_change"] = latest.get("last_material_change") or latest.get("change") or "new_page"
        check["last_movement_at"] = latest.get("last_material_changed_at") or latest.get("observed_at") or ""
        check["newly_observed_pages"] = latest.get("newly_observed_pages") or []
        check["no_longer_assessed_pages"] = latest.get("no_longer_assessed_pages") or []
    else:
        check["latest_change"] = "new_page"
        check["last_movement_at"] = ""
        check["newly_observed_pages"] = []
        check["no_longer_assessed_pages"] = []
    return check



def _summary_result(counts: dict[str, int]) -> dict[str, int]:
    return {
        "improved": int(counts.get("improved") or 0),
        "worsened": int(counts.get("worsened") or 0),
        "resolved": int(counts.get("resolved") or 0),
        "new": int(counts.get("new_issue") or 0),
        "mixed": int(counts.get("mixed") or 0),
    }


def pulse_summary(history: dict[str, list[dict[str, Any]]]) -> dict[str, int]:
    """Count unique pages by their retained last material movement.

    This intentionally avoids weighted check-page totals and does not include
    unchanged confirmations.
    """
    by_page: dict[str, set[str]] = defaultdict(set)
    for rows in history.values():
        if not rows:
            continue
        currently_assessed = set((rows[-1].get("page_statuses") or {}).keys())
        retained: dict[str, str] = {}
        for observation in rows:
            for page, change in (observation.get("page_changes") or {}).items():
                if change in MATERIAL_CHANGES:
                    retained[page] = change
        for page, change in retained.items():
            if page not in currently_assessed:
                continue
            by_page[page].add(change)

    counts: dict[str, int] = defaultdict(int)
    for changes in by_page.values():
        negative = changes & {"worsened", "new_issue"}
        positive = changes & {"resolved", "improved"}
        if negative and positive:
            counts["mixed"] += 1
        elif "worsened" in changes:
            counts["worsened"] += 1
        elif "new_issue" in changes:
            counts["new_issue"] += 1
        elif "resolved" in changes:
            counts["resolved"] += 1
        elif "improved" in changes:
            counts["improved"] += 1
    return _summary_result(counts)



def family_pulse_summary(
    history: dict[str, list[dict[str, Any]]],
    family_definitions: list[dict[str, Any]] | None = None,
) -> dict[str, dict[str, int]]:
    """Apply the same retained unique-page semantics inside each family."""
    changes_by_family_page: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))

    definitions = list(family_definitions or [])
    category_to_family: dict[str, str] = {}
    alias_to_family: dict[str, str] = {}

    for family in definitions:
        name = str(family.get("name") or "").strip()
        family_id = str(family.get("id") or "").strip()
        if not name:
            continue
        alias_to_family[name.lower()] = name
        if family_id:
            alias_to_family[family_id.lower()] = name
        for category in family.get("categories") or []:
            category_to_family[str(category).strip().lower()] = name

    def resolve_family(latest: dict[str, Any]) -> str:
        raw_family = str(latest.get("family") or "").strip()
        if raw_family:
            resolved = alias_to_family.get(raw_family.lower())
            if resolved:
                return resolved
        category = str(latest.get("category") or "").strip().lower()
        if category:
            resolved = category_to_family.get(category)
            if resolved:
                return resolved
        return raw_family

    for rows in history.values():
        if not rows:
            continue

        latest = rows[-1]
        family = resolve_family(latest)
        if not family:
            continue
        retained: dict[str, str] = {}
        currently_assessed = set((latest.get("page_statuses") or {}).keys())
        for observation in rows:
            for page, change in (observation.get("page_changes") or {}).items():
                if change in MATERIAL_CHANGES:
                    retained[page] = change
        for page, change in retained.items():
            if page not in currently_assessed:
                continue
            changes_by_family_page[family][page].add(change)

    result = {}
    for family, pages in changes_by_family_page.items():
        counts: dict[str, int] = defaultdict(int)
        for changes in pages.values():
            negative = changes & {"worsened", "new_issue"}
            positive = changes & {"resolved", "improved"}
            if negative and positive:
                counts["mixed"] += 1
            elif "worsened" in changes:
                counts["worsened"] += 1
            elif "new_issue" in changes:
                counts["new_issue"] += 1
            elif "resolved" in changes:
                counts["resolved"] += 1
            elif "improved" in changes:
                counts["improved"] += 1
        result[family] = _summary_result(counts)

    for family in definitions:
        name = str(family.get("name") or "").strip()
        if name and name not in result:
            result[name] = _summary_result({})

    return result
