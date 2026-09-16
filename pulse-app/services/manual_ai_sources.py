from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from db.sqlite import connect_sqlite


PromptFactory = Callable[[str, str, str], str]


def load_manual_ai_source(
    db_path: str | Path,
    domain: str,
    *,
    prompt_factory: PromptFactory,
    default_analysis_prompt: str,
) -> dict:
    with connect_sqlite(db_path, readonly=True) as con:
        parent = con.execute(
            "SELECT * FROM manual_ai_source WHERE domain=? COLLATE NOCASE", (domain,)
        ).fetchone()
        rows = con.execute(
            "SELECT * FROM manual_ai_state_source "
            "WHERE domain=? COLLATE NOCASE ORDER BY phase,state",
            (domain,),
        ).fetchall()

    out = dict(parent) if parent else {
        "domain": domain,
        "question_set_version": 1,
        "analysis_status": "not_run",
        "updated_at": "",
    }
    indexed = {(row["phase"], row["state"]): dict(row) for row in rows}
    for phase in ("phase1", "phase2"):
        for state in ("state1", "state2"):
            row = indexed.get((phase, state), {})
            prefix = f"{phase}_{state}"
            out[f"{prefix}_prompt_text"] = (
                row.get("prompt_text") or prompt_factory(domain, phase, state)
            )
            for provider in ("chatgpt", "claude", "gemini"):
                out[f"{prefix}_{provider}_response"] = row.get(f"{provider}_response") or ""

    if not str(out.get("analysis_system_prompt") or "").strip():
        out["analysis_system_prompt"] = default_analysis_prompt
    if not str(out.get("analysis_model") or "").strip():
        out["analysis_model"] = (
            os.environ.get("MANUAL_AI_ANALYSIS_MODEL")
            or os.environ.get("COMPARISON_JUDGE_MODEL")
            or ""
        )
    if not str(out.get("analysis_provider") or "").strip():
        out["analysis_provider"] = (
            os.environ.get("MANUAL_AI_ANALYSIS_PROVIDER") or "ollama"
        ).strip().lower()
    if not str(out.get("analysis_reasoning_effort") or "").strip():
        out["analysis_reasoning_effort"] = "high"
    if out.get("analysis_temperature") is None:
        out["analysis_temperature"] = 0.1
    if out.get("analysis_top_p") is None:
        out["analysis_top_p"] = 0.9
    if not out.get("analysis_max_output_tokens"):
        out["analysis_max_output_tokens"] = 8000
    if not out.get("analysis_system_prompt_version"):
        out["analysis_system_prompt_version"] = 3
    return out


def save_manual_ai_source(
    db_path: str | Path,
    domain: str,
    *,
    prompts: dict[str, str],
    responses: dict[str, str],
    current: dict,
    default_analysis_prompt: str,
) -> int:
    old_prompts = tuple(
        str(current.get(f"{phase}_{state}_prompt_text") or "")
        for phase in ("phase1", "phase2")
        for state in ("state1", "state2")
    )
    new_prompts = tuple(
        prompts[f"{phase}_{state}"]
        for phase in ("phase1", "phase2")
        for state in ("state1", "state2")
    )
    version = int(current.get("question_set_version") or 1)
    if old_prompts != new_prompts:
        version += 1

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with connect_sqlite(db_path) as con:
        con.execute(
            "INSERT INTO manual_ai_source("
            "domain,question_set_version,analysis_model,analysis_system_prompt,"
            "analysis_text,analysis_status,analysis_error,analysis_updated_at,updated_at"
            ") VALUES (?,?,?,?,?,?,?,?,?) "
            "ON CONFLICT(domain) DO UPDATE SET "
            "question_set_version=excluded.question_set_version,updated_at=excluded.updated_at",
            (
                domain,
                version,
                current.get("analysis_model") or "",
                current.get("analysis_system_prompt") or default_analysis_prompt,
                current.get("analysis_text") or "",
                current.get("analysis_status") or "not_run",
                current.get("analysis_error") or "",
                current.get("analysis_updated_at") or "",
                now,
            ),
        )
        for phase in ("phase1", "phase2"):
            for state in ("state1", "state2"):
                prefix = f"{phase}_{state}"
                con.execute(
                    "INSERT INTO manual_ai_state_source("
                    "domain,phase,state,prompt_text,chatgpt_response,"
                    "claude_response,gemini_response,updated_at"
                    ") VALUES (?,?,?,?,?,?,?,?) "
                    "ON CONFLICT(domain,phase,state) DO UPDATE SET "
                    "prompt_text=excluded.prompt_text,"
                    "chatgpt_response=excluded.chatgpt_response,"
                    "claude_response=excluded.claude_response,"
                    "gemini_response=excluded.gemini_response,"
                    "updated_at=excluded.updated_at",
                    (
                        domain,
                        phase,
                        state,
                        prompts[prefix],
                        responses[f"{prefix}_chatgpt"],
                        responses[f"{prefix}_claude"],
                        responses[f"{prefix}_gemini"],
                        now,
                    ),
                )
        con.execute(
            "INSERT INTO domain_source("
            "domain,source_key,source_name,selected,connection_status,detail,updated_at"
            ") VALUES (?,?,?,1,'not_connected',?,?) "
            "ON CONFLICT(domain,source_key) DO UPDATE SET "
            "source_name=excluded.source_name,selected=1,"
            "detail=excluded.detail,updated_at=excluded.updated_at",
            (
                domain,
                "manual_ai",
                "Manual AI Responses",
                f"Four-state Manual AI source · question-set v{version}",
                now,
            ),
        )
        con.commit()
    return version
