from reports.pulse_history import attach_history_to_check, build_finding_history, classify_change


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
