from __future__ import annotations

import ast
from pathlib import Path

import pytest

from db.migrate import migrate_up
from reports.web_report import create_report_session
from services.manual_ai_sources import load_manual_ai_source, save_manual_ai_source
from services.report_collaboration import (
    DiscussionDisabled,
    add_public_reply,
    add_reply,
    load_human_interpretation,
    load_report_notes,
    save_human_interpretation,
    save_report_note,
    set_exclusions,
)

APP = Path(__file__).resolve().parents[1]


def test_extracted_flask_routes_do_not_execute_sql():
    route_names = {
        "domain_sources",
        "save_source_company_name",
        "manual_ai_source",
        "public_report_note_reply",
        "public_report",
        "report_workflow_exclusion",
        "save_report_human_interpretation",
        "save_report_note",
        "save_report_note_reply",
        "report_notes_json",
    }
    tree = ast.parse((APP / "app.py").read_text())
    offenders = {}
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name not in route_names:
            continue
        hits = [
            child.lineno
            for child in ast.walk(node)
            if isinstance(child, ast.Call)
            and isinstance(child.func, ast.Attribute)
            and child.func.attr == "execute"
        ]
        if hits:
            offenders[node.name] = hits
    assert offenders == {}


def test_report_collaboration_service_round_trip(tmp_path):
    db = tmp_path / "pulse.db"
    migrate_up(db)
    report_id = create_report_session(
        db,
        "example.com",
        {"domain": "example.com", "audit_signals": []},
        publish=True,
    )

    note = save_report_note(db, "example.com", "finding:1", "Owner note", True)
    assert note["has_note"] is True
    reply = add_public_reply(db, report_id, "finding:1", "Client reply")
    assert reply["author_role"] == "client"
    notes = load_report_notes(db, "example.com")
    assert notes["finding:1"]["content"] == "Owner note"
    assert notes["finding:1"]["replies"][0]["content"] == "Client reply"

    updated_at = save_human_interpretation(
        db, "example.com", report_id, "Human interpretation"
    )
    interpretation = load_human_interpretation(db, "example.com", report_id)
    assert interpretation == {
        "content": "Human interpretation",
        "updated_at": updated_at,
    }

    assert set_exclusions(
        db,
        "example.com",
        action="exclude",
        targets=[("check", "check-1", -1)],
    ) == 1


def test_disabled_report_discussion_is_enforced(tmp_path):
    db = tmp_path / "pulse.db"
    migrate_up(db)
    save_report_note(db, "example.com", "finding:1", "", False)
    with pytest.raises(DiscussionDisabled):
        add_reply(
            db,
            "example.com",
            "finding:1",
            "Not allowed",
            author_role="client",
        )


def test_manual_ai_source_storage_behavior_is_preserved(tmp_path):
    db = tmp_path / "pulse.db"
    migrate_up(db)

    def prompt_factory(domain, phase, state):
        return f"{domain}:{phase}:{state}"

    current = load_manual_ai_source(
        db,
        "example.com",
        prompt_factory=prompt_factory,
        default_analysis_prompt="Analyze",
    )
    prompts = {
        f"{phase}_{state}": current[f"{phase}_{state}_prompt_text"]
        for phase in ("phase1", "phase2")
        for state in ("state1", "state2")
    }
    responses = {
        f"{phase}_{state}_{provider}": f"raw:{phase}:{state}:{provider}"
        for phase in ("phase1", "phase2")
        for state in ("state1", "state2")
        for provider in ("chatgpt", "claude", "gemini")
    }

    version = save_manual_ai_source(
        db,
        "example.com",
        prompts=prompts,
        responses=responses,
        current=current,
        default_analysis_prompt="Analyze",
    )
    assert version == 1

    loaded = load_manual_ai_source(
        db,
        "example.com",
        prompt_factory=prompt_factory,
        default_analysis_prompt="Analyze",
    )
    assert loaded["phase2_state2_chatgpt_response"] == "raw:phase2:state2:chatgpt"
    assert loaded["question_set_version"] == 1
