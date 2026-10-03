from reports.pulse_history import (
    attach_history_to_check,
    build_finding_history,
    classify_change,
    family_pulse_summary,
    pulse_summary,
)


def signal(status, path, title="Contact and accountability information", category="Authority & Trust"):
    return {
        "title": title,
        "category": category,
        "family": "identity",
        "observed_status": status,
        "severity": "HIGH",
        "path": path,
    }


def record(report_id, when, statuses):
    return {
        "id": report_id,
        "created_at": when,
        "snapshot": {
            "audit": {"id": int(report_id[-1]), "completed_at": when},
            "audit_signals": [signal(status, path) for path, status in statuses],
        },
    }


def test_history_tracks_scope_and_direction():
    history = build_finding_history([
        record("r1", "2026-09-01T10:00:00+00:00", [("/", "FAIL"), ("/about", "FAIL")]),
        record("r2", "2026-09-01T11:00:00+00:00", [("/", "FAIL"), ("/about", "PASS")]),
        record("r3", "2026-09-01T12:00:00+00:00", [("/", "PASS"), ("/about", "PASS")]),
    ])
    rows = next(iter(history.values()))
    assert [x["pages_affected"] for x in rows] == [2, 1, 0]
    assert [x["change"] for x in rows] == ["new_issue", "resolved", "resolved"]


def test_same_status_with_more_affected_pages_is_worsened():
    previous = {"page_statuses": {"/a": "PARTIAL"}}
    current = {"page_statuses": {"/a": "PARTIAL", "/b": "PARTIAL"}}
    assert classify_change(current, previous) == "new_issue"


def test_smaller_page_set_compares_only_same_exact_pages():
    previous = {
        "status": "FAIL",
        "pages_affected": 6,
        "pages_tested": 15,
        "page_statuses": {f"/page-{n}": "FAIL" for n in range(15)},
    }
    current = {
        "status": "FAIL",
        "pages_affected": 4,
        "pages_tested": 4,
        "page_statuses": {f"/page-{n}": "FAIL" for n in range(4)},
    }
    assert classify_change(current, previous) == "unchanged"


def test_smaller_page_set_can_resolve_pages_that_still_exist():
    previous = {
        "status": "PARTIAL",
        "pages_affected": 1,
        "pages_tested": 15,
        "page_statuses": {f"/page-{n}": "PARTIAL" for n in range(15)},
    }
    current = {
        "status": "PASS",
        "pages_affected": 0,
        "pages_tested": 4,
        "page_statuses": {f"/page-{n}": "PASS" for n in range(4)},
    }
    assert classify_change(current, previous) == "resolved"


def test_manual_review_is_not_treated_as_failure_history():
    previous = {"page_statuses": {"/": "PASS"}}
    current = {"page_statuses": {"/": "MANUAL_REVIEW"}}
    assert classify_change(current, previous) == "requires_review"


def test_history_attaches_to_current_check():
    history = build_finding_history([
        record("r1", "2026-09-01T10:00:00+00:00", [("/", "FAIL")]),
        record("r2", "2026-09-01T11:00:00+00:00", [("/", "PARTIAL")]),
    ])
    check = {"title": "Contact and accountability information", "category": "Authority & Trust"}
    attach_history_to_check(check, history)
    assert check["history_count"] == 2
    assert check["latest_change"] == "improved"

def test_repeated_confirmation_does_not_erase_resolved_baseline_movement():
    history = build_finding_history([
        record("r1", "2026-09-01T10:00:00+00:00", [("/", "FAIL"), ("/about", "FAIL")]),
        record("r2", "2026-09-01T11:00:00+00:00", [("/", "PASS"), ("/about", "PASS")]),
        record("r3", "2026-09-01T12:00:00+00:00", [("/", "PASS"), ("/about", "PASS")]),
    ])
    rows = next(iter(history.values()))
    assert rows[-1]["change"] == "unchanged"

    summary = pulse_summary(history)
    assert summary["resolved"] == 2

    check = {
        "title": "Contact and accountability information",
        "category": "Authority & Trust",
    }
    attach_history_to_check(check, history)
    assert check["latest_change"] == "resolved"
    assert check["last_movement_at"] == "2026-09-01T11:00:00+00:00"
    assert check["history_count"] == 2
    assert check["observation_count"] == 3


def test_repeated_confirmation_does_not_erase_improved_scope():
    history = build_finding_history([
        record("r1", "2026-09-01T10:00:00+00:00", [
            ("/", "FAIL"), ("/about", "FAIL"), ("/contact", "FAIL")
        ]),
        record("r2", "2026-09-01T11:00:00+00:00", [
            ("/", "FAIL"), ("/about", "PASS"), ("/contact", "PASS")
        ]),
        record("r3", "2026-09-01T12:00:00+00:00", [
            ("/", "FAIL"), ("/about", "PASS"), ("/contact", "PASS")
        ]),
    ])

    summary = pulse_summary(history)
    assert summary["resolved"] == 2


def test_family_summary_retains_latest_material_page_movement():
    history = build_finding_history([
        record("r1", "2026-09-01T10:00:00+00:00", [("/", "FAIL"), ("/about", "FAIL")]),
        record("r2", "2026-09-01T11:00:00+00:00", [("/", "PASS"), ("/about", "PASS")]),
        record("r3", "2026-09-01T12:00:00+00:00", [("/", "PASS"), ("/about", "PASS")]),
    ])
    families = [{
        "id": "identity-authority",
        "name": "Identity & Authority",
        "categories": ["Authority & Trust"],
    }]

    summary = family_pulse_summary(history, families)
    assert summary["Identity & Authority"]["resolved"] == 2


def test_removed_about_and_new_about_us_are_separate_lifecycles():
    history = build_finding_history([
        record("r1", "2026-09-01T10:00:00+00:00", [("/about", "FAIL")]),
        record("r2", "2026-09-01T11:00:00+00:00", [("/about-us", "FAIL")]),
    ])
    rows = next(iter(history.values()))
    assert rows[-1]["newly_observed_pages"] == ["/about-us"]
    assert rows[-1]["no_longer_assessed_pages"] == ["/about"]
    assert rows[-1]["page_changes"] == {"/about-us": "new_issue"}
