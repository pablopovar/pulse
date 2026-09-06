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
            "observed_at": observed_at,
            "report_id": report_id,
            "audit_run_id": (snapshot.get("audit") or {}).get("id"),
        }
    return out


def classify_change(current: dict[str, Any], previous: dict[str, Any] | None) -> str:
    if previous is None:
        return "new"
    cs = normalize_status(current.get("status"))
    ps = normalize_status(previous.get("status"))
    if cs == "NOT_APPLICABLE" and ps != "NOT_APPLICABLE":
        return "no_longer_applicable"
    if "DATA_UNAVAILABLE" in {cs, ps}:
        return "unchanged" if cs == ps else "not_comparable"
    if cs == ps:
        if is_issue(cs):
            ca = int(current.get("pages_affected") or 0)
            pa = int(previous.get("pages_affected") or 0)
            if ca < pa:
                return "improved"
            if ca > pa:
                return "worsened"
        if cs == "MANUAL_REVIEW":
            cr = int(current.get("pages_review_required") or 0)
            pr = int(previous.get("pages_review_required") or 0)
            if cr < pr:
                return "improved"
            if cr > pr:
                return "worsened"
        return "unchanged"
    if ps in {"FAIL", "PARTIAL"} and cs == "PASS":
        return "resolved"
    if cs in STATUS_ORDER and ps in STATUS_ORDER:
        if STATUS_ORDER[cs] > STATUS_ORDER[ps]:
            return "improved"
        if STATUS_ORDER[cs] < STATUS_ORDER[ps]:
            return "worsened"
    return "not_comparable"


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
            observation["change"] = classify_change(observation, previous)
            history[key].append(observation)

    for rows in history.values():
        if not rows:
            continue
        current = rows[-1]
        current_status = current.get("status")
        state_since = current.get("observed_at")
        for row in reversed(rows[:-1]):
            if row.get("status") != current_status:
                break
            state_since = row.get("observed_at") or state_since
        current["state_since"] = state_since
    return dict(history)


def attach_history_to_check(check: dict[str, Any], history: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    key = finding_key(str(check.get("category") or ""), str(check.get("title") or ""))
    rows = list(history.get(key) or [])
    check["finding_key"] = key
    check["history"] = rows
    check["history_count"] = len(rows)
    if rows:
        latest = rows[-1]
        previous = rows[-2] if len(rows) > 1 else None
        check["latest_change"] = latest.get("change") or "new"
        check["observed_at"] = latest.get("observed_at") or ""
        check["state_since"] = latest.get("state_since") or latest.get("observed_at") or ""
        check["previous_observation"] = previous
    else:
        check["latest_change"] = "new"
        check["observed_at"] = ""
        check["state_since"] = ""
        check["previous_observation"] = None
    return check


def pulse_summary(history: dict[str, list[dict[str, Any]]]) -> dict[str, int]:
    counts = defaultdict(int)
    seen_logical = set()
    for rows in history.values():
        if not rows:
            continue
        latest = rows[-1]
        logical_key = (
            str(latest.get("family") or "").strip().lower(),
            canonical_check_title(latest.get("title") or "").strip().lower(),
        )
        if logical_key in seen_logical:
            continue
        seen_logical.add(logical_key)
        counts[str(latest.get("change") or "new")] += 1
    return {
        "improved": counts["improved"],
        "worsened": counts["worsened"],
        "resolved": counts["resolved"],
        "new": counts["new"],
        "unchanged": counts["unchanged"],
        "not_comparable": counts["not_comparable"],
        "no_longer_applicable": counts["no_longer_applicable"],
    }
