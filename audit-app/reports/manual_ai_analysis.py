from __future__ import annotations
import json, os, urllib.request
from typing import Any

DEFAULT_ANALYSIS_SYSTEM_PROMPT = """You analyze AI-visibility evidence collected from ChatGPT, Claude, and Gemini.

Use ONLY the supplied prompts and provider responses. Do not browse the web and do not add outside facts.

Phase 1 is blind/discovery. The audited entity is deliberately not named. Assess whether it surfaced unprompted, what alternatives surfaced instead, whether distinctive terminology was attributed, and what the responses reveal about discoverability.

Phase 2 is named/brand interpretation. Assess how providers describe the entity, its category, positioning, distinctive ideas or frameworks, applicability, confidence, and sources of truth.

Compare providers. Identify strong agreement, meaningful differences or direct contradictions, first-party source dependence, third-party corroboration, unsupported/model-prior claims when the supplied evidence supports that conclusion, and uncertainty or missing evidence.

Do not invent sources, rankings, claims, or confidence. Do not treat omission as contradiction.

Write concise client-facing analysis. Lead with 3-6 highest-signal findings in plain language, followed by a short section titled \"What this means\". Do not output a remediation checklist."""

def _endpoint():
    url = (os.environ.get("MANUAL_AI_ANALYSIS_URL") or os.environ.get("COMPARISON_JUDGE_URL") or "").strip()
    key = (os.environ.get("MANUAL_AI_ANALYSIS_API_KEY") or os.environ.get("COMPARISON_JUDGE_API_KEY") or "").strip()
    return url, key

def build_packet(source: dict[str, Any]) -> str:
    packet = {
        "question_set_version": source.get("question_set_version"),
        "phase_1": {"purpose": "blind/discovery; audited entity is not named", "prompt": source.get("phase1_prompt_text") or "", "provider_responses": {p: source.get(f"phase1_{p}_response") or "" for p in ("chatgpt","claude","gemini")}},
        "phase_2": {"purpose": "named/brand interpretation", "prompt": source.get("phase2_prompt_text") or "", "provider_responses": {p: source.get(f"phase2_{p}_response") or "" for p in ("chatgpt","claude","gemini")}},
    }
    return json.dumps(packet, ensure_ascii=False, indent=2)

def run_analysis(source: dict[str, Any], model: str, system_prompt: str) -> str:
    url, api_key = _endpoint()
    if not url: raise RuntimeError("Analysis endpoint is not configured. Set MANUAL_AI_ANALYSIS_URL or reuse COMPARISON_JUDGE_URL.")
    if not model.strip(): raise RuntimeError("Analysis model is required.")
    body = {"model": model.strip(), "temperature": 0, "messages": [{"role":"system","content":system_prompt.strip()},{"role":"user","content":build_packet(source)}]}
    headers = {"Content-Type":"application/json"}
    if api_key: headers["Authorization"] = "Bearer " + api_key
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=180) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    return str(payload["choices"][0]["message"]["content"]).strip()
