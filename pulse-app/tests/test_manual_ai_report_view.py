from reports.web_report import prepare_report_view


def test_four_state_manual_ai_source_remains_available():
    snapshot = {
        "domain": "example.com",
        "audit_signals": [],
        "manual_ai_snapshot": {
            "available": True,
            "question_set_version": 4,
            "provider_runs": 2,
            "answer_count": 8,
            "expected_answer_count": 8,
            "valid_json_providers": 2,
            "analysis_status": "success",
            "analysis_text": "Observed differences only.",
            "phases": [
                {
                    "phase": "phase1",
                    "states": [
                        {
                            "state": "state1",
                            "providers": [
                                {"provider": "chatgpt", "parsed": {"results": []}, "result_count": 4},
                                {"provider": "claude", "parsed": {"results": []}, "result_count": 4},
                            ],
                        }
                    ],
                }
            ],
        },
    }

    report = prepare_report_view(snapshot)
    manual_ai = report["manual_ai_snapshot"]

    assert manual_ai["available"] is True
    assert manual_ai["provider_runs"] == 2
    assert manual_ai["provider_count"] == 2
    assert manual_ai["answer_count"] == 8
    assert manual_ai["expected_answer_count"] == 8
    assert manual_ai["complete"] is True


def test_legacy_top_level_provider_shape_still_works():
    snapshot = {
        "domain": "example.com",
        "audit_signals": [],
        "manual_ai_snapshot": {
            "providers": [
                {"provider": "gemini", "parsed": {"results": []}, "result_count": 4},
            ],
        },
    }

    report = prepare_report_view(snapshot)
    manual_ai = report["manual_ai_snapshot"]

    assert manual_ai["available"] is True
    assert manual_ai["provider_runs"] == 1
    assert manual_ai["provider_count"] == 1
    assert manual_ai["answer_count"] == 4
    assert manual_ai["complete"] is True
