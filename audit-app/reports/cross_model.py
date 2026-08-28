from __future__ import annotations

import itertools
import json
import os
import sqlite3
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from typing import Any

QUESTION_DEFS = {
    "ai-visibility": [
        ("ai_visibility_01", "What does [Company] do, and how does its business model generate cash flows?"),
        ("ai_visibility_02", "What are [Company]’s main growth drivers?"),
    ],
    "identity-authority": [
        ("identity_authority_01", "What differentiates [Company] from other companies or investment opportunities in its industry?"),
        ("identity_authority_02", "How does [Company] allocate capital, and what does that reveal about its strategy and priorities?"),
    ],
    "evidence-trust": [
        ("evidence_trust_01", "What are the principal risks investors should understand about [Company]?"),
        ("evidence_trust_02", "How should investors think about [Company]’s portfolio diversification, concentration, and exposure to key assets or businesses?"),
    ],
}
QUESTION_TO_FAMILY = {qid: family for family, defs in QUESTION_DEFS.items() for qid, _ in defs}
QUESTION_TEMPLATES = {qid: template for defs in QUESTION_DEFS.values() for qid, template in defs}
PROVIDER_STATUSES = {"success", "timeout", "provider_error", "unsupported", "no_answer"}
JUDGE_PROMPT_VERSION = "cross-model-v1.0"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def ensure_schema(con: sqlite3.Connection) -> None:
    con.execute("""
        CREATE TABLE IF NOT EXISTS cross_model_provider_response (
            domain TEXT NOT NULL COLLATE NOCASE,
            report_id TEXT NOT NULL,
            question_id TEXT NOT NULL,
            family_id TEXT NOT NULL,
            template_question TEXT NOT NULL,
            rendered_question TEXT NOT NULL,
            provider TEXT NOT NULL,
            model TEXT NOT NULL DEFAULT '',
            raw_answer TEXT NOT NULL DEFAULT '',
            citations_json TEXT NOT NULL DEFAULT '[]',
            observed_at TEXT NOT NULL,
            country TEXT NOT NULL DEFAULT '',
            city TEXT NOT NULL DEFAULT '',
            answer_language TEXT NOT NULL DEFAULT '',
            live_search_status TEXT NOT NULL DEFAULT '',
            provider_status TEXT NOT NULL DEFAULT 'success',
            PRIMARY KEY(domain, report_id, question_id, provider)
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS cross_model_comparison (
            domain TEXT NOT NULL COLLATE NOCASE,
            report_id TEXT NOT NULL,
            question_id TEXT NOT NULL,
            family_id TEXT NOT NULL,
            rendered_question TEXT NOT NULL,
            valid_provider_count INTEGER NOT NULL DEFAULT 0,
            concept_consistency REAL,
            concept_consistency_pct REAL,
            company_source_numerator INTEGER NOT NULL DEFAULT 0,
            company_source_denominator INTEGER NOT NULL DEFAULT 0,
            company_source_pct REAL,
            direct_contradiction INTEGER NOT NULL DEFAULT 0,
            direct_contradiction_count INTEGER NOT NULL DEFAULT 0,
            judge_provider TEXT NOT NULL DEFAULT '',
            judge_model TEXT NOT NULL DEFAULT '',
            judge_prompt_version TEXT NOT NULL DEFAULT '',
            judged_at TEXT,
            raw_judge_json TEXT NOT NULL DEFAULT '',
            derived_json TEXT NOT NULL DEFAULT '{}',
            judge_status TEXT NOT NULL DEFAULT 'not_run',
            judge_error TEXT NOT NULL DEFAULT '',
            PRIMARY KEY(domain, report_id, question_id)
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS domain_company_controlled_domain (
            domain TEXT NOT NULL COLLATE NOCASE,
            controlled_domain TEXT NOT NULL COLLATE NOCASE,
            created_at TEXT NOT NULL,
            PRIMARY KEY(domain, controlled_domain)
        )
    """)
    con.execute("CREATE INDEX IF NOT EXISTS idx_xm_response_report ON cross_model_provider_response(domain,report_id,question_id)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_xm_comparison_report ON cross_model_comparison(domain,report_id,question_id)")
    con.commit()


def normalize_domain(value: str) -> str:
    raw = (value or "").strip().lower()
    if not raw:
        return ""
    if "://" not in raw:
        raw = "https://" + raw
    try:
        host = urllib.parse.urlparse(raw).hostname or ""
    except Exception:
        host = ""
    return host.lower().rstrip(".")


def controlled_domains(con: sqlite3.Connection, domain: str) -> list[str]:
    ensure_schema(con)
    primary = normalize_domain(domain)
    rows = con.execute(
        "SELECT controlled_domain FROM domain_company_controlled_domain WHERE domain=? COLLATE NOCASE ORDER BY controlled_domain",
        (domain,),
    ).fetchall()
    out = {primary}
    out.update(normalize_domain(r["controlled_domain"]) for r in rows if r["controlled_domain"])
    return sorted(d for d in out if d)


def save_controlled_domains(con: sqlite3.Connection, domain: str, values: list[str]) -> None:
    ensure_schema(con)
    con.execute("DELETE FROM domain_company_controlled_domain WHERE domain=? COLLATE NOCASE", (domain,))
    primary = normalize_domain(domain)
    for value in values:
        host = normalize_domain(value)
        if host and host != primary:
            con.execute(
                "INSERT OR IGNORE INTO domain_company_controlled_domain(domain,controlled_domain,created_at) VALUES (?,?,?)",
                (domain, host, now_iso()),
            )
    con.commit()


def is_company_controlled(host: str, controlled: list[str]) -> bool:
    h = normalize_domain(host)
    return any(h == root or h.endswith("." + root) for root in controlled)



def explicit_urls_from_answer(answer: str | None) -> list[dict[str, Any]]:
    """Extract only URLs literally present in the provider's raw answer."""
    import re as _re
    text = (answer or "").replace("\\:", ":").replace("\\/", "/")
    urls = _re.findall(r'https?://[^\s<>"\]\)]+', text)
    out = []
    seen = set()
    for url in urls:
        url = url.rstrip(".,;:'\"")
        if url in seen:
            continue
        seen.add(url)
        host = normalize_domain(url)
        if host:
            out.append({
                "url": url,
                "domain": host,
                "metadata_origin": "explicit_url_in_raw_answer",
            })
    return out

def parse_citations(raw: Any) -> list[dict[str, Any]]:
    if raw is None:
        return []
    value = raw
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return []
        try:
            value = json.loads(text)
        except Exception:
            value = [{"url": line.strip()} for line in text.splitlines() if line.strip()]
    if isinstance(value, dict):
        value = value.get("citations") or value.get("sources") or [value]
    if not isinstance(value, list):
        return []
    out = []
    for item in value:
        if isinstance(item, str):
            item = {"url": item}
        if not isinstance(item, dict):
            continue
        rec = dict(item)
        host = rec.get("domain") or normalize_domain(rec.get("url") or "")
        if host:
            rec["domain"] = normalize_domain(host)
        out.append(rec)
    return out


def source_analysis(rows: list[dict[str, Any]], controlled: list[str]) -> dict[str, Any]:
    usable = 0
    company_yes = 0
    providers = {}
    external_response_count = Counter()
    external_citation_count = Counter()

    for row in rows:
        provider = row["provider"]
        citations = parse_citations(row.get("citations_json"))
        if not any(c.get("domain") for c in citations):
            citations = explicit_urls_from_answer(row.get("raw_answer"))
        domains = [c.get("domain") for c in citations if c.get("domain")]
        company_domains = sorted({d for d in domains if is_company_controlled(d, controlled)})
        external_domains = sorted({d for d in domains if not is_company_controlled(d, controlled)})
        has_usable = bool(domains)
        if row.get("provider_status") == "success" and has_usable:
            usable += 1
            if company_domains:
                company_yes += 1
        for d in external_domains:
            external_response_count[d] += 1
        for d in domains:
            if d and not is_company_controlled(d, controlled):
                external_citation_count[d] += 1
        providers[provider] = {
            "usable_source_metadata": has_usable,
            "company_controlled_source_present": bool(company_domains) if has_usable else None,
            "company_controlled_domains": company_domains,
            "external_domains": external_domains,
            "citations": citations,
        }

    return {
        "numerator": company_yes,
        "denominator": usable,
        "percentage": (company_yes / usable * 100.0) if usable else None,
        "providers": providers,
        "external_response_count": dict(external_response_count),
        "external_citation_count": dict(external_citation_count),
    }


def _validate_judge_payload(payload: Any, question_id: str, providers: list[str]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Judge output must be a JSON object")
    concepts = payload.get("concepts")
    contradictions = payload.get("contradictions")
    if not isinstance(concepts, list) or not isinstance(contradictions, list):
        raise ValueError("Judge JSON requires concepts[] and contradictions[]")
    if len(concepts) > 7:
        raise ValueError("Judge returned more than 7 concepts")
    normalized = []
    for concept in concepts:
        if not isinstance(concept, dict) or not str(concept.get("concept") or "").strip():
            raise ValueError("Each concept requires text")
        pmap = concept.get("providers")
        if not isinstance(pmap, dict):
            raise ValueError("Each concept requires providers object")
        outmap = {}
        for provider in providers:
            item = pmap.get(provider) or {}
            outmap[provider] = {
                "present": bool(item.get("present")),
                "evidence": item.get("evidence") if item.get("present") else None,
            }
        normalized.append({"concept": str(concept["concept"]).strip(), "providers": outmap})
    normalized_contradictions = []
    for item in contradictions:
        if not isinstance(item, dict):
            continue
        if item.get("classification") not in {"direct_contradiction", "potential_contradiction"}:
            raise ValueError("Invalid contradiction classification")
        normalized_contradictions.append(item)
    return {"question_id": question_id, "concepts": normalized, "contradictions": normalized_contradictions}


def build_judge_prompt(question_id: str, question: str, responses: list[dict[str, Any]]) -> tuple[str, str]:
    system = """You compare multiple AI-provider answers to the same company question.
Do NOT use web access or outside knowledge. Do NOT determine which provider is factually correct.
Build ONE joint normalized set of major concepts across all answers, maximum 5-7 concepts.
Normalize semantically equivalent wording into one concept.
For every concept, mark presence per provider and preserve a short evidence excerpt when present.
Detect only genuinely mutually incompatible factual claims in the same context/timeframe.
Different detail, omission, emphasis, or compatible wording is NOT a contradiction.
If timeframe/context is unclear, classify as potential_contradiction, never direct_contradiction.
Return JSON only with keys question_id, concepts, contradictions. Do not add scores or labels."""
    packet = [f"QUESTION_ID:\n{question_id}\n\nQUESTION:\n{question}"]
    for row in responses:
        packet.append(f"\n\nPROVIDER: {row['provider']}\nANSWER:\n{row.get('raw_answer') or ''}")
    return system, "".join(packet)


def call_judge(question_id: str, question: str, responses: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, str]]:
    url = (os.environ.get("COMPARISON_JUDGE_URL") or "").strip()
    model = (os.environ.get("COMPARISON_JUDGE_MODEL") or "").strip()
    api_key = (os.environ.get("COMPARISON_JUDGE_API_KEY") or "").strip()
    provider = (os.environ.get("COMPARISON_JUDGE_PROVIDER") or "openai-compatible").strip()
    if not url or not model:
        raise RuntimeError("Judge not configured: set COMPARISON_JUDGE_URL and COMPARISON_JUDGE_MODEL")
    system, user = build_judge_prompt(question_id, question, responses)
    body = {
        "model": model,
        "temperature": 0,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "response_format": {"type": "json_object"},
    }
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = "Bearer " + api_key
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=120) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    raw = json.loads(payload["choices"][0]["message"]["content"])
    validated = _validate_judge_payload(raw, question_id, [r["provider"] for r in responses])
    return validated, {"provider": provider, "model": model, "raw_json": json.dumps(raw, ensure_ascii=False)}


def concept_metrics(judge: dict[str, Any], providers: list[str]) -> dict[str, Any]:
    concepts = judge.get("concepts") or []
    sets = {p: {c["concept"] for c in concepts if c["providers"].get(p, {}).get("present")} for p in providers}
    pairwise = []
    for a, b in itertools.combinations(providers, 2):
        union = sets[a] | sets[b]
        score = len(sets[a] & sets[b]) / len(union) if union else 1.0
        pairwise.append({"a": a, "b": b, "score": score})
    c = sum(x["score"] for x in pairwise) / len(pairwise) if pairwise else None
    shared, inconsistent, provider_specific = [], [], []
    for concept in concepts:
        present = [p for p in providers if concept["providers"].get(p, {}).get("present")]
        if providers and len(present) == len(providers):
            shared.append(concept["concept"])
        elif len(present) == 1:
            provider_specific.append({"concept": concept["concept"], "provider": present[0]})
        else:
            inconsistent.append({"concept": concept["concept"], "providers": present})
    direct = [x for x in judge.get("contradictions") or [] if x.get("classification") == "direct_contradiction"]
    potential = [x for x in judge.get("contradictions") or [] if x.get("classification") == "potential_contradiction"]
    return {
        "concept_consistency": c,
        "concept_consistency_pct": c * 100 if c is not None else None,
        "pairwise": pairwise,
        "shared_concepts": shared,
        "inconsistent_concepts": inconsistent,
        "provider_specific_concepts": provider_specific,
        "direct_contradictions": direct,
        "potential_contradictions": potential,
        "direct_contradiction": bool(direct),
        "direct_contradiction_count": len(direct),
    }


def upsert_response(con: sqlite3.Connection, record: dict[str, Any]) -> None:
    ensure_schema(con)
    status = record.get("provider_status") or "success"
    if status not in PROVIDER_STATUSES:
        raise ValueError("Invalid provider status")
    con.execute(
        """INSERT INTO cross_model_provider_response(
               domain,report_id,question_id,family_id,template_question,rendered_question,
               provider,model,raw_answer,citations_json,observed_at,country,city,
               answer_language,live_search_status,provider_status
           ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
           ON CONFLICT(domain,report_id,question_id,provider) DO UPDATE SET
             family_id=excluded.family_id,template_question=excluded.template_question,
             rendered_question=excluded.rendered_question,model=excluded.model,
             raw_answer=excluded.raw_answer,citations_json=excluded.citations_json,
             observed_at=excluded.observed_at,country=excluded.country,city=excluded.city,
             answer_language=excluded.answer_language,live_search_status=excluded.live_search_status,
             provider_status=excluded.provider_status""",
        (
            record["domain"], record["report_id"], record["question_id"], record["family_id"],
            record["template_question"], record["rendered_question"], record["provider"],
            record.get("model") or "", record.get("raw_answer") or "",
            json.dumps(parse_citations(record.get("citations")), ensure_ascii=False),
            record.get("observed_at") or now_iso(), record.get("country") or "", record.get("city") or "",
            record.get("answer_language") or "", record.get("live_search_status") or "", status,
        ),
    )
    con.commit()


def run_comparison(con: sqlite3.Connection, domain: str, report_id: str, question_id: str) -> dict[str, Any]:
    ensure_schema(con)
    rows = [dict(r) for r in con.execute(
        "SELECT * FROM cross_model_provider_response WHERE domain=? COLLATE NOCASE AND report_id=? AND question_id=? ORDER BY provider",
        (domain, report_id, question_id),
    ).fetchall()]
    valid = [r for r in rows if r["provider_status"] == "success" and (r["raw_answer"] or "").strip()]
    family_id = QUESTION_TO_FAMILY[question_id]
    rendered = rows[0]["rendered_question"] if rows else ""
    sources = source_analysis(rows, controlled_domains(con, domain))
    judge_status, judge_error = "not_run", ""
    judge_meta = {"provider": "", "model": "", "raw_json": ""}
    metrics = {
        "concept_consistency": None, "concept_consistency_pct": None, "pairwise": [],
        "shared_concepts": [], "inconsistent_concepts": [], "provider_specific_concepts": [],
        "direct_contradictions": [], "potential_contradictions": [],
        "direct_contradiction": False, "direct_contradiction_count": 0,
    }
    if len(valid) >= 2:
        try:
            judge, judge_meta = call_judge(question_id, rendered, valid)
            metrics = concept_metrics(judge, [r["provider"] for r in valid])
            judge_status = "success"
        except Exception as exc:
            judge_status = "judge_error"
            judge_error = str(exc)
    else:
        judge_status = "insufficient_valid_responses"
    derived = {**metrics, "source_analysis": sources, "controlled_domains": controlled_domains(con, domain), "valid_providers": [r["provider"] for r in valid]}
    con.execute(
        """INSERT INTO cross_model_comparison(
               domain,report_id,question_id,family_id,rendered_question,valid_provider_count,
               concept_consistency,concept_consistency_pct,company_source_numerator,
               company_source_denominator,company_source_pct,direct_contradiction,
               direct_contradiction_count,judge_provider,judge_model,judge_prompt_version,
               judged_at,raw_judge_json,derived_json,judge_status,judge_error
           ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
           ON CONFLICT(domain,report_id,question_id) DO UPDATE SET
             family_id=excluded.family_id,rendered_question=excluded.rendered_question,
             valid_provider_count=excluded.valid_provider_count,concept_consistency=excluded.concept_consistency,
             concept_consistency_pct=excluded.concept_consistency_pct,
             company_source_numerator=excluded.company_source_numerator,
             company_source_denominator=excluded.company_source_denominator,
             company_source_pct=excluded.company_source_pct,direct_contradiction=excluded.direct_contradiction,
             direct_contradiction_count=excluded.direct_contradiction_count,
             judge_provider=excluded.judge_provider,judge_model=excluded.judge_model,
             judge_prompt_version=excluded.judge_prompt_version,judged_at=excluded.judged_at,
             raw_judge_json=excluded.raw_judge_json,derived_json=excluded.derived_json,
             judge_status=excluded.judge_status,judge_error=excluded.judge_error""",
        (
            domain, report_id, question_id, family_id, rendered, len(valid),
            metrics["concept_consistency"], metrics["concept_consistency_pct"],
            sources["numerator"], sources["denominator"], sources["percentage"],
            int(metrics["direct_contradiction"]), metrics["direct_contradiction_count"],
            judge_meta["provider"], judge_meta["model"], JUDGE_PROMPT_VERSION,
            now_iso() if judge_status == "success" else None, judge_meta["raw_json"],
            json.dumps(derived, ensure_ascii=False), judge_status, judge_error,
        ),
    )
    con.commit()
    return load_question(con, domain, report_id, question_id)


def load_question(con: sqlite3.Connection, domain: str, report_id: str, question_id: str) -> dict[str, Any]:
    ensure_schema(con)
    comp = con.execute(
        "SELECT * FROM cross_model_comparison WHERE domain=? COLLATE NOCASE AND report_id=? AND question_id=?",
        (domain, report_id, question_id),
    ).fetchone()
    responses = [dict(r) for r in con.execute(
        "SELECT * FROM cross_model_provider_response WHERE domain=? COLLATE NOCASE AND report_id=? AND question_id=? ORDER BY provider",
        (domain, report_id, question_id),
    ).fetchall()]
    for r in responses:
        r["citations"] = parse_citations(r.get("citations_json"))
        if not any(c.get("domain") for c in r["citations"]):
            r["citations"] = explicit_urls_from_answer(r.get("raw_answer"))
    return {"comparison": dict(comp) if comp else None, "responses": responses, "derived": json.loads(comp["derived_json"] or "{}") if comp else {}}


def report_rollups(con: sqlite3.Connection, domain: str, report_id: str) -> dict[str, Any]:
    ensure_schema(con)
    comps = [dict(r) for r in con.execute(
        "SELECT * FROM cross_model_comparison WHERE domain=? COLLATE NOCASE AND report_id=? ORDER BY question_id",
        (domain, report_id),
    ).fetchall()]
    responses = [dict(r) for r in con.execute(
        "SELECT * FROM cross_model_provider_response WHERE domain=? COLLATE NOCASE AND report_id=?",
        (domain, report_id),
    ).fetchall()]
    cvals = [r["concept_consistency"] for r in comps if r["concept_consistency"] is not None]
    family_rollups = {}
    for family_id, defs in QUESTION_DEFS.items():
        ids = {qid for qid, _ in defs}
        rows = [r for r in comps if r["question_id"] in ids]
        cv = [r["concept_consistency"] for r in rows if r["concept_consistency"] is not None]
        family_rollups[family_id] = {
            "questions_tested": len(rows),
            "provider_responses": sum(r["valid_provider_count"] for r in rows),
            "average_concept_consistency": sum(cv) / len(cv) if cv else None,
            "company_source_numerator": sum(r["company_source_numerator"] for r in rows),
            "company_source_denominator": sum(r["company_source_denominator"] for r in rows),
            "direct_contradiction_questions": sum(1 for r in rows if r["direct_contradiction"]),
            "questions": rows,
        }
    shared = inconsistent = 0
    for r in comps:
        d = json.loads(r["derived_json"] or "{}")
        shared += len(d.get("shared_concepts") or [])
        inconsistent += len(d.get("inconsistent_concepts") or []) + len(d.get("provider_specific_concepts") or [])
    # External-domain prominence across the six questions.
    controlled = controlled_domains(con, domain)
    ext = {}
    for r in responses:
        for c in parse_citations(r["citations_json"]):
            d = c.get("domain")
            if not d or is_company_controlled(d, controlled):
                continue
            rec = ext.setdefault(d, {"domain": d, "questions": set(), "providers": set(), "total_citations": 0})
            rec["questions"].add(r["question_id"]); rec["providers"].add(r["provider"]); rec["total_citations"] += 1
    ext_rows = [{"domain": v["domain"], "unique_questions": len(v["questions"]), "unique_providers": len(v["providers"]), "total_citations": v["total_citations"]} for v in ext.values()]
    ext_rows.sort(key=lambda x: (-x["unique_questions"], -x["unique_providers"], -x["total_citations"], x["domain"]))
    numerator = sum(r["company_source_numerator"] for r in comps)
    denominator = sum(r["company_source_denominator"] for r in comps)
    provider_models = sorted({(r["provider"], r["model"] or "") for r in responses if r["provider_status"] == "success" and (r["raw_answer"] or "").strip()})
    return {
        "questions_tested": len(comps),
        "providers_models_tested": [{"provider": p, "model": m} for p, m in provider_models],
        "total_valid_responses": sum(1 for r in responses if r["provider_status"] == "success" and (r["raw_answer"] or "").strip()),
        "average_concept_consistency": sum(cvals) / len(cvals) if cvals else None,
        "company_source_numerator": numerator,
        "company_source_denominator": denominator,
        "company_source_pct": numerator / denominator * 100 if denominator else None,
        "direct_contradiction_questions": sum(1 for r in comps if r["direct_contradiction"]),
        "shared_concepts": shared,
        "inconsistent_concepts": inconsistent,
        "external_domains": ext_rows,
        "families": family_rollups,
    }
