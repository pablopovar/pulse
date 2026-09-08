import ast
from pathlib import Path

from reports.web_report import create_report_session, load_report_session


def _snapshot(label):
    return {
        "domain": "example.com",
        "audit_signals": [],
        "manual_ai_source": {
            "available": True,
            "analysis_status": "success",
            "analysis_text": label,
            "provider_count": 3,
            "provider_runs": 6,
            "expected_provider_runs": 6,
            "answer_count": 24,
            "expected_answer_count": 24,
            "valid_json_providers": 6,
            "complete": True,
        },
    }


def test_old_report_manual_ai_snapshot_does_not_change_after_new_report(tmp_path):
    db = tmp_path / "report.db"

    old_id = create_report_session(db, "example.com", _snapshot("OLD OBSERVATION"))
    new_id = create_report_session(db, "example.com", _snapshot("NEW OBSERVATION"))

    assert old_id != new_id

    old_report = load_report_session(db, "example.com", old_id)
    new_report = load_report_session(db, "example.com", new_id)

    assert old_report["snapshot"]["manual_ai_snapshot"]["analysis_text"] == "OLD OBSERVATION"
    assert new_report["snapshot"]["manual_ai_snapshot"]["analysis_text"] == "NEW OBSERVATION"


def test_old_report_remains_unchanged_when_later_observation_is_created(tmp_path):
    db = tmp_path / "report.db"

    old_id = create_report_session(db, "example.com", _snapshot("FIRST"))
    before = load_report_session(db, "example.com", old_id)["snapshot"]

    create_report_session(db, "example.com", _snapshot("SECOND"))
    after = load_report_session(db, "example.com", old_id)["snapshot"]

    assert after["manual_ai_snapshot"] == before["manual_ai_snapshot"]
    assert after["report_metadata"]["pulse_updated_at"] == before["report_metadata"]["pulse_updated_at"]


def _function_calls(source, function_name):
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name:
            return {
                child.func.id
                for child in ast.walk(node)
                if isinstance(child, ast.Call) and isinstance(child.func, ast.Name)
            }
    raise AssertionError(f"function {function_name!r} not found")


def test_historical_html_route_does_not_inject_live_manual_ai_or_exclusions():
    app_source = (Path(__file__).resolve().parents[1] / "app.py").read_text()
    calls = _function_calls(app_source, "report_session_view")

    assert "manual_ai_source_for_report" not in calls
    assert "_apply_report_exclusions" not in calls
    assert "prepare_report_view" in calls


def test_historical_pdf_route_does_not_apply_live_exclusions():
    app_source = (Path(__file__).resolve().parents[1] / "app.py").read_text()
    calls = _function_calls(app_source, "report_session_pdf")

    assert "_apply_report_exclusions" not in calls
    assert "build_full_report_pdf" in calls


def test_html_and_pdf_routes_both_read_session_snapshot_directly():
    source = (Path(__file__).resolve().parents[1] / "app.py").read_text()
    tree = ast.parse(source)

    relevant = {}
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in {
            "report_session_view",
            "report_session_pdf",
        }:
            relevant[node.name] = ast.get_source_segment(source, node) or ""

    assert set(relevant) == {"report_session_view", "report_session_pdf"}
    assert 'session["snapshot"]' in relevant["report_session_view"]
    assert 'session["snapshot"]' in relevant["report_session_pdf"]
    assert "historical_snapshot" in relevant["report_session_view"]
    assert "historical_snapshot" in relevant["report_session_pdf"]
