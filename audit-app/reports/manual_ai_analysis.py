from __future__ import annotations

import json
import os
import urllib.request
from typing import Any


DEFAULT_ANALYSIS_SYSTEM_PROMPT = """You analyze AI-visibility evidence collected from public-facing ChatGPT, Claude, and Gemini runs.

Your job is to turn the supplied evidence into a concise, grounded interpretation for a client-facing AI Visibility report.

SUCCESS

Success means producing the strongest useful interpretation directly supported by the supplied observations.

Use the evidence to explain:
- whether the audited entity surfaces when it is not named;
- how the entity is categorized and understood when it is named;
- what differentiators providers associate with it;
- how it is positioned against the human-approved comparison set;
- which sources shape that representation;
- where providers agree, differ, or remain uncertain.

Use only the supplied questions, raw provider responses, structured fields, source metadata, and coverage metadata.

Do not browse the web.
Do not use outside knowledge.
Do not fill gaps from your own knowledge.
Do not independently fact-check the providers.

Raw provider responses are the primary evidence for what each provider said.

PHASE 1 — BLIND / DISCOVERY

The audited entity is not named.

Interpret:
- whether it surfaced unprompted;
- in which question contexts it surfaced;
- whether it appeared as a category example, comparison option, terminology attribution, or recommendation;
- which alternatives surfaced;
- what this evidence says about observed discoverability.

Do not turn mention order or frequency in this sample into a general market ranking.

PHASE 2 — NAMED / BRAND INTERPRETATION

The audited entity is named.

Interpret:
- how providers categorize it;
- what characteristics and differentiators they associate with it;
- how they position it relative to the supplied human-approved comparison set;
- which users, needs, or situations they associate with it;
- reasons for and against selecting it;
- uncertainty and unsupported assumptions.

SOURCE INTERPRETATION

Distinguish first-party evidence, independent third-party evidence, and unclear provenance.
Multiple providers citing the same source are not independent corroboration.
Multiple pages from the audited entity are still first-party evidence.
Do not infer hidden sources.

CROSS-PROVIDER ANALYSIS

Compare ChatGPT, Claude, and Gemini only where the evidence supports a meaningful comparison.
Identify agreement, meaningful differences, provider-specific claims, source-selection differences, contradictions, and uncertainty.
Different detail, emphasis, or omission is not a contradiction.

GROUNDING RULES

- Describe observations from this evidence set, not universal properties of AI systems.
- Say "did not surface in the observed run," not "the model does not know" or "the brand is invisible."
- Do not explain why a model behaved a certain way.
- Do not infer training data, memorization, hidden knowledge, hidden retrieval, or provider strategy.
- Do not claim that agreement proves truth.
- Do not claim that retrieval proves correctness.
- Do not invent sources, rankings, capabilities, pricing, confidence, or facts.
- Preserve important uncertainty and missing evidence.
- If evidence is incomplete, malformed, synthetic/demo, or unavailable, state that when it materially affects interpretation.

QUANTIFICATION

Use the actual observed denominator.
Keep providers, provider-phase runs, and individual question answers distinct.
One provider answering four questions in one phase is one provider-phase run containing four question answers.

OUTPUT

Write concise client-facing analysis with these sections:

Key observations
Give 3–6 highest-signal findings in plain language.

Provider differences
Include only meaningful provider differences. Omit this section if there are none.

What this means
Explain the practical significance for the audited entity's AI discoverability, representation, positioning, evidence environment, and source dependence.

Keep "What this means" interpretive, not prescriptive.

Do not produce:
- an overall AI visibility score;
- arbitrary High / Medium / Low ratings;
- a remediation checklist;
- unsupported causal claims;
- predictions about future AI behavior;
- recommendations for SEO, PR, content, reviews, citations, or third-party coverage;
- claims about hidden model mechanisms;
- broader market claims unsupported by the observed runs.

Do not repeat the same finding across sections.
Prefer synthesis over provider-by-provider transcription.
"""


def _normalize_base(url: str) -> str:
    return (url or "").strip().rstrip("/")


def _ollama_base() -> str:
    explicit = _normalize_base(os.environ.get("OLLAMA_BASE_URL") or os.environ.get("OLLAMA_URL") or "")
    if explicit:
        return explicit
    legacy = _normalize_base(os.environ.get("MANUAL_AI_ANALYSIS_URL") or "")
    if legacy:
        for suffix in ("/v1/chat/completions", "/api/chat", "/chat/completions"):
            if legacy.endswith(suffix):
                return legacy[: -len(suffix)]
    return "http://host.docker.internal:11434"


def _openai_base() -> str:
    return _normalize_base(os.environ.get("OPENAI_BASE_URL") or "https://api.openai.com/v1")


def _http_json(url: str, *, method: str = "GET", body: dict[str, Any] | None = None, api_key: str = "", timeout: int = 30) -> dict[str, Any]:
    headers = {"Accept": "application/json"}
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode("utf-8")
    if api_key:
        headers["Authorization"] = "Bearer " + api_key
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError("Provider returned a non-object JSON response.")
    return payload


def list_models(provider: str) -> dict[str, Any]:
    provider = (provider or "").strip().lower()
    try:
        if provider == "ollama":
            payload = _http_json(_ollama_base() + "/api/tags", timeout=10)
            models = sorted(
                {
                    str(item.get("name") or item.get("model") or "").strip()
                    for item in payload.get("models", [])
                    if isinstance(item, dict) and (item.get("name") or item.get("model"))
                }
            )
            return {"models": models, "error": ""}
        if provider == "openai":
            key = (os.environ.get("OPENAI_API_KEY") or "").strip()
            if not key:
                return {"models": [], "error": "OPENAI_API_KEY is not configured."}
            payload = _http_json(_openai_base() + "/models", api_key=key, timeout=20)
            models = sorted(
                {
                    str(item.get("id") or "").strip()
                    for item in payload.get("data", [])
                    if isinstance(item, dict) and item.get("id")
                }
            )
            return {"models": models, "error": ""}
        return {"models": [], "error": f"Unsupported analysis provider: {provider}"}
    except Exception as exc:
        return {"models": [], "error": str(exc)}


def build_packet(source: dict[str, Any]) -> str:
    providers = ("chatgpt", "claude", "gemini")
    expected_runs = 0
    observed_runs = 0
    missing = []

    def phase_packet(phase: str, purpose: str):
        nonlocal expected_runs, observed_runs
        legacy_prefix = f"{phase}_state2"
        provider_responses = {}
        for provider in providers:
            expected_runs += 1
            value = source.get(f"{legacy_prefix}_{provider}_response") or ""
            provider_responses[provider] = value
            if str(value).strip():
                observed_runs += 1
            else:
                missing.append({"phase": phase, "provider": provider})
        return {
            "purpose": purpose,
            "retrieval": "enabled",
            "prompt": source.get(f"{legacy_prefix}_prompt_text") or "",
            "provider_responses": provider_responses,
        }

    phase_1 = phase_packet(
        "phase1",
        "blind/discovery; audited entity is not named",
    )
    phase_2 = phase_packet(
        "phase2",
        "named/brand interpretation; comparison set is human-controlled",
    )

    packet = {
        "question_set_version": source.get("question_set_version"),
        "coverage": {
            "expected_provider_phase_runs": expected_runs,
            "observed_provider_phase_runs": observed_runs,
            "complete": observed_runs == expected_runs,
            "missing": missing,
            "note": (
                "Coverage counts provider/phase response blocks. "
                "Each block may contain multiple question answers."
            ),
        },
        "phase_1": phase_1,
        "phase_2": phase_2,
    }
    return json.dumps(packet, ensure_ascii=False, indent=2)


def _analysis_endpoint(provider: str) -> tuple[str, str]:
    provider = provider.lower()
    if provider == "ollama":
        legacy = (os.environ.get("MANUAL_AI_ANALYSIS_URL") or "").strip()
        if legacy:
            return legacy, (os.environ.get("MANUAL_AI_ANALYSIS_API_KEY") or "").strip()
        return _ollama_base() + "/v1/chat/completions", ""
    if provider == "openai":
        return _openai_base() + "/chat/completions", (os.environ.get("OPENAI_API_KEY") or "").strip()
    raise RuntimeError(f"Unsupported analysis provider: {provider}")


def run_analysis(
    source: dict[str, Any],
    model: str,
    system_prompt: str,
    *,
    provider: str = "ollama",
    reasoning_effort: str = "high",
    temperature: float = 0.1,
    top_p: float = 0.9,
    max_output_tokens: int = 8000,
) -> str:
    provider = (provider or "ollama").strip().lower()
    model = (model or "").strip()
    if not model:
        raise RuntimeError("Analysis model is required.")

    url, api_key = _analysis_endpoint(provider)
    if provider == "openai" and not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured.")

    body: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": (system_prompt or "").strip()},
            {"role": "user", "content": build_packet(source)},
        ],
        "temperature": float(temperature),
        "top_p": float(top_p),
        "max_tokens": int(max_output_tokens),
    }

    effort = (reasoning_effort or "").strip().lower()
    if effort in {"low", "medium", "high"}:
        body["reasoning_effort"] = effort

    payload = _http_json(url, method="POST", body=body, api_key=api_key, timeout=240)

    try:
        content = payload["choices"][0]["message"]["content"]
    except Exception as exc:
        raise RuntimeError("Analysis provider returned an unexpected response shape.") from exc
    return str(content or "").strip()