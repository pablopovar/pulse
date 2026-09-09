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
    assert [x["change"] for x in rows] == ["new", "improved", "resolved"]
    assert rows[-1]["state_since"] == "2026-09-01T12:00:00+00:00"


def test_same_status_with_more_affected_pages_is_worsened():
    previous = {"status": "PARTIAL", "pages_affected": 2}
    current = {"status": "PARTIAL", "pages_affected": 5}
    assert classify_change(current, previous) == "worsened"


def test_manual_review_is_not_treated_as_failure_history():
    previous = {"status": "MANUAL_REVIEW", "pages_review_required": 4}
    current = {"status": "MANUAL_REVIEW", "pages_review_required": 2}
    assert classify_change(current, previous) == "improved"


def test_history_attaches_to_current_check():
    history = build_finding_history([
        record("r1", "2026-09-01T10:00:00+00:00", [("/", "FAIL")]),
        record("r2", "2026-09-01T11:00:00+00:00", [("/", "PARTIAL")]),
    ])
    check = {"title": "Contact and accountability information", "category": "Authority & Trust"}
    attach_history_to_check(check, history)
    assert check["history_count"] == 2
    assert check["latest_change"] == "improved"
    assert check["previous_observation"]["status"] == "FAIL"

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
    assert summary["unchanged"] == 0

    check = {
        "title": "Contact and accountability information",
        "category": "Authority & Trust",
    }
    attach_history_to_check(check, history)
    assert check["latest_change"] == "unchanged"
    assert check["since_baseline_change"] == "resolved"
    assert check["history_count"] == 3


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
    assert summary["improved"] == 2
    assert summary["unchanged"] == 0


def test_family_summary_uses_baseline_current_semantics():
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
    assert summary["Identity & Authority"]["unchanged"] == 0

