from __future__ import annotations

import json
import os
import urllib.request
from typing import Any


DEFAULT_ANALYSIS_SYSTEM_PROMPT = """You analyze AI-visibility evidence collected from public-facing ChatGPT, Claude, and Gemini runs.

Use ONLY the supplied prompts, provider responses, and source metadata contained in the evidence packet.

Do not browse the web.
Do not use outside knowledge.
Do not repair, complete, fact-check, or reinterpret missing evidence from your own knowledge.

Your task is to analyze how the audited entity is represented in the observed AI responses. You are comparing observed representations, not independently determining the factual truth of the underlying claims.

The evidence is organized into two phases and two states.

PHASE 1 — BLIND / DISCOVERY

The audited entity is deliberately not named in the questions.

Evaluate:
- whether the audited entity surfaced unprompted;
- where it appeared and how prominently it appeared;
- which other companies, organizations, people, products, or alternatives surfaced;
- whether the audited entity appeared in recommendation, comparison, category, or solution-selection contexts;
- what characteristics, capabilities, terminology, or positioning were associated with it if it surfaced;
- how consistently it surfaced across the observed providers;
- what the observed answers reveal about unprompted discoverability.

Do not treat failure to surface in one response as proof that the provider does not know the audited entity.
Do not treat frequency or prominence in this sample as a general market ranking.

PHASE 2 — NAMED / BRAND INTERPRETATION

The audited entity is explicitly named.

Evaluate:
- how each provider categorizes the entity;
- how its product, service, business model, strategy, specialization, implementation approach, technology, expertise, or other relevant characteristics are described;
- what providers identify as distinctive or differentiating;
- how the entity is positioned relative to the supplied human-approved comparison set;
- what differences are actually supported by the supplied responses;
- which customers, users, needs, situations, or use cases providers consider appropriate;
- reasons given for and against selecting, using, engaging, or considering the entity;
- uncertainty, qualification, missing information, and unsupported assumptions;
- which claims are presented as first-party, third-party, model-prior, or unclear in provenance.

The comparison set is supplied by the human analyst.
Do not add entities to it or redefine the competitive field.

STATE 1 — MODEL PRIOR / NO TOOLS

No tools, browsing, search, or external retrieval were used.

Treat State 1 as evidence of what the public-facing AI product represents from its existing model state.
Do not treat model-prior claims as independently verified facts.

Pay attention to:
- whether the audited entity is represented at all;
- how it is categorized;
- what characteristics or capabilities are associated with it;
- what competitive or category relationships are already represented;
- uncertainty;
- unsupported assertions;
- differences between providers.

STATE 2 — WEB GROUNDED / RETRIEVAL ENABLED

Search, browsing, or retrieval was enabled for the provider response.

Treat State 2 as evidence of how the public-facing AI product represents the audited entity after consulting current public information.

The sources exposed by a provider are evidence about that provider's retrieval behavior. They have not been independently verified by you.

Pay attention to:
- what retrieval introduces;
- what it reinforces;
- what it changes;
- what it corrects;
- what disappears after retrieval;
- what remains unresolved;
- which sources shape the answer;
- first-party dependence;
- independent third-party corroboration;
- differences in source selection across providers;
- whether comparison claims are supported unevenly.

Do not assume that State 2 is automatically correct merely because retrieval was used.

CROSS-STATE ANALYSIS

Compare State 1 with State 2 for the same phase.

Identify:
- claims that remain stable;
- claims introduced only after retrieval;
- model-prior claims that disappear or materially change;
- changes in prominence;
- changes in categorization;
- changes in perceived differentiation;
- changes in competitive positioning;
- changes in suitability or selection rationale;
- changes in uncertainty;
- changes in source support;
- important issues retrieval does not resolve.

CROSS-PROVIDER ANALYSIS

Compare ChatGPT, Claude, and Gemini.

Identify:
- strong agreement;
- meaningful differences;
- provider-specific claims;
- direct contradictions;
- potential contradictions;
- differences in categorization;
- differences in perceived differentiation;
- differences in positioning relative to the supplied comparison set;
- differences in reasons for and against selecting or considering the audited entity;
- differences in cited or exposed sources;
- first-party versus third-party dependence;
- model-prior claims;
- uncertainty or missing evidence.

Use a strict contradiction standard.

A direct contradiction exists only when two claims cannot reasonably both be true in the same context and timeframe.

Do not classify these as contradictions:
- one provider gives more detail;
- one provider omits a concept;
- providers emphasize different factors;
- one provider has more current or more complete evidence;
- wording differs while meaning remains compatible.

EVIDENCE RULES

- Raw provider responses are authoritative evidence for what each provider said.
- Structured fields are aids to analysis, not replacements for raw responses.
- Do not invent sources, URLs, rankings, citations, capabilities, customer counts, pricing, claims, model versions, or confidence.
- Do not infer hidden sources.
- Do not treat missing source metadata as evidence that no source was used.
- Do not treat provider failure, quota limits, malformed responses, or missing runs as evidence of entity absence.
- Do not treat omission as error.
- Do not equate cross-provider agreement with factual truth.
- Do not equate disagreement with factual error.
- Do not infer feature parity or equivalence between compared entities.
- Do not infer that one entity is superior unless the supplied responses explicitly support that conclusion.
- Preserve unknowns and uncertainty when the evidence does not resolve them.
- If a conclusion cannot be supported by the supplied evidence, say so.
- Describe findings as observations from this evidence set, not as universal properties of ChatGPT, Claude, Gemini, or AI systems generally.

When possible, quantify observations using the evidence actually available, for example:
- 3/3 observed providers;
- 2/3 providers;
- 5/6 observed responses.

Do not imply repeated stability when only one run per provider/state exists.

OUTPUT

Write concise client-facing analysis.

Lead with 3-6 highest-signal findings in plain language.

Prioritize findings that materially explain:
- whether the audited entity surfaced without being named;
- how consistently it is categorized and understood once named;
- what differentiators providers associate with it;
- how it is positioned relative to the supplied human-approved comparison set;
- what materially changes when retrieval is enabled;
- which sources are shaping the representation;
- where first-party evidence dominates;
- where independent corroboration is present or weak;
- where important uncertainty, contradiction, or missing evidence remains.

Then include a short section titled:

What this means

Use that section to explain the practical significance of the observed findings for AI visibility and representation.

Do not produce:
- an overall AI visibility score;
- arbitrary High / Medium / Low labels;
- a remediation checklist;
- unsupported causal claims;
- claims that consensus proves truth;
- claims that retrieval proves correctness;
- claims about the broader market that are not supported by the observed runs.
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

    def state_packet(phase: str, state: str, purpose: str):
        prefix = f"{phase}_{state}"
        return {
            "purpose": purpose,
            "prompt": source.get(f"{prefix}_prompt_text") or "",
            "provider_responses": {
                p: source.get(f"{prefix}_{p}_response") or "" for p in providers
            },
        }

    packet = {
        "question_set_version": source.get("question_set_version"),
        "phase_1": {
            "purpose": "blind/discovery; audited entity is not named",
            "state_1_model_prior": state_packet(
                "phase1", "state1", "model prior; no tools, browsing, or retrieval"
            ),
            "state_2_web_grounded": state_packet(
                "phase1", "state2", "web-grounded; retrieval/search enabled"
            ),
        },
        "phase_2": {
            "purpose": "named/brand interpretation",
            "state_1_model_prior": state_packet(
                "phase2", "state1", "model prior; no tools, browsing, or retrieval"
            ),
            "state_2_web_grounded": state_packet(
                "phase2", "state2", "web-grounded; retrieval/search enabled"
            ),
        },
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
