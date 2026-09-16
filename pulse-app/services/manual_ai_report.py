from __future__ import annotations

from pathlib import Path

from db.sqlite import connect_sqlite
from services.manual_ai_payload import parse_manual_ai_payload


def load_manual_ai_source(db_path: str | Path, domain: str) -> dict:
    with connect_sqlite(db_path, readonly=True) as con:
        parent = con.execute(
            "SELECT * FROM manual_ai_source WHERE domain=? COLLATE NOCASE", (domain,)
        ).fetchone()
        rows = con.execute(
            "SELECT * FROM manual_ai_state_source WHERE domain=? COLLATE NOCASE ORDER BY phase,state",
            (domain,),
        ).fetchall()
    source = dict(parent) if parent else {
        "domain": domain,
        "question_set_version": 1,
        "analysis_status": "not_run",
        "updated_at": "",
    }
    indexed = {(row["phase"], row["state"]): dict(row) for row in rows}
    # Storage remains unchanged. The active report projection consumes only the
    # retrieval-enabled state for each of the two approved phases.
    for phase in ("phase1", "phase2"):
        row = indexed.get((phase, "state2"), {})
        prefix = f"{phase}_state2"
        source[f"{prefix}_prompt_text"] = row.get("prompt_text") or ""
        for provider in ("chatgpt", "claude", "gemini"):
            source[f"{prefix}_{provider}_response"] = row.get(f"{provider}_response") or ""
    return source


def manual_ai_source_for_report(db_path: str | Path, domain: str) -> dict:
    source = load_manual_ai_source(db_path, domain)
    phase_rows = []
    total_answers = 0
    parsed_runs = 0
    provider_runs = 0

    for phase in ("phase1", "phase2"):
        prefix = f"{phase}_state2"
        providers = []
        for provider in ("chatgpt", "claude", "gemini"):
            raw = source.get(f"{prefix}_{provider}_response") or ""
            parsed = parse_manual_ai_payload(raw).value
            results = parsed.get("results") if isinstance(parsed, dict) else None
            result_count = len(results) if isinstance(results, list) else 0
            if str(raw).strip():
                provider_runs += 1
            if parsed is not None:
                parsed_runs += 1
                total_answers += result_count
            providers.append({
                "provider": provider,
                "response": raw,
                "parsed": parsed,
                "result_count": result_count,
            })
        phase_rows.append({
            "phase": phase,
            "states": [{
                "state": "retrieval_enabled",
                "providers": providers,
                "provider_count": sum(1 for item in providers if str(item["response"]).strip()),
            }],
        })

    source["available"] = provider_runs > 0
    source["phases"] = phase_rows
    source["provider_runs"] = provider_runs
    source["expected_provider_runs"] = 6
    source["provider_count"] = len({
        item["provider"]
        for phase_row in phase_rows
        for state in phase_row["states"]
        for item in state["providers"]
        if str(item["response"]).strip()
    })
    source["answer_count"] = total_answers
    source["expected_answer_count"] = 24
    source["valid_json_providers"] = parsed_runs
    source["complete"] = provider_runs == 6 and parsed_runs == 6 and total_answers == 24
    return source
