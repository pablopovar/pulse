from __future__ import annotations

import json
import secrets
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from db.sqlite import connect_sqlite
from typing import Any

from reports.prioritization import (
    GLOSSARY,
    METHODOLOGY,
    SCORING_VERSION,
    build_high_signal_findings,
    canonical_check_title,
    merge_duplicate_checks,
    value_to_fix,
    value_to_fix_components,
)
from reports.pulse_history import attach_history_to_check, build_finding_history, family_pulse_summary, pulse_summary
from reports.report_intelligence import (
    RECOMMENDATION_STATES,
    ai_metrics,
    data_coverage,
    enrich_check,
    group_root_causes,
    is_issue,
    is_review,
    monitoring_coverage_summary,
    normalize_status,
    root_cause_key,
    rollup_status,
    status_counts,
    validate_report,
)


FAMILIES = [
    {"id":"ai-visibility","name":"AI Visibility","departments":"IR · Communications · Corporate Affairs · Marketing","purpose":"How visible is the company in AI answers, and which sources are shaping those answers?","kind":"ai"},
    {"id":"identity-authority","name":"Identity & Authority","departments":"IR · Communications · Brand","purpose":"Can machines and external audiences clearly establish who the company is and why it is authoritative?","kind":"audit","categories":["Entity Clarity & Identity","Authority & Trust"]},
    {"id":"evidence-trust","name":"Evidence & Trust","departments":"IR · Communications · Editorial · Legal/Review","purpose":"Does the company's published information carry evidence, attribution and accountability?","kind":"audit","categories":["Evidence & Citations"]},
    {"id":"content-answer-readiness","name":"Content & Answer Readiness","departments":"Communications · Content · Editorial","purpose":"Does the company publish substantive information in a form that people, search engines and answer systems can understand and reuse?","kind":"audit","categories":["Question & Intent Alignment","Answer Extractability","Content Depth & Originality","Clarity & Readability"]},
    {"id":"machine-readability-eligibility","name":"Machine Readability & Eligibility","departments":"SEO · Content · Web","purpose":"Is the company's information technically expressed in a form search and answer systems can identify, interpret and use?","kind":"audit","categories":["Search & Answer Eligibility","Structured Data","Semantic Structure"]},
    {"id":"seo-audit","name":"SEO Audit","departments":"SEO · Growth · Marketing","purpose":"How is the site performing in organic search, where is demand, and where are the highest-value search opportunities?","kind":"seo"},
    {"id":"onsite-audit","name":"Onsite Audit","departments":"SEO · Web · Engineering","purpose":"Is the site technically crawlable, indexable, accessible and healthy?","kind":"onsite","categories":["Crawlability & Indexability","Technical Delivery & Consistency","Page Experience & Accessibility"]},
]

STATUS_RANK = {"FAIL":0,"PARTIAL":1,"MANUAL_REVIEW":2,"DATA_UNAVAILABLE":3,"PASS":4,"NOT_APPLICABLE":5}
SEVERITY_RANK = {"CRITICAL":0,"HIGH":1,"MEDIUM":2,"LOW":3}
METHODOLOGY_VERSION = "report-methodology-pulse-v1"
SNAPSHOT_VERSION = "report-snapshot-v3"

# Lower = greater expected return from fixing. This is deliberately independent of severity.
IMPACT_ORDER = {
    "Page is technically indexable":10,"Indexing permitted":10,"Successful HTML response":10,
    "robots.txt permits the page":11,"Search snippets are permitted":12,"Snippet generation permitted":12,
    "One clear H1":13,"Single primary heading":13,"Canonical URL declared":14,"Canonical relationship is explicit":14,
    "Primary user intent is satisfied":15,"Organization or person identified":16,"Primary topic is unambiguous":17,
    "Answers follow question headings":18,"Opening provides a direct orientation":19,
    "Relevant structured data is available":20,"Machine-readable structured data present":20,
    "Structured data is syntactically valid":21,"JSON-LD parses successfully":21,"Responsible entity structured":22,
    "Official profiles connected":23,"External supporting sources":24,"Claims are factually verified":25,
    "Quantified claims supported":26,"Source attribution language":27,"Named author on editorial content":28,
    "Author expertise is substantiated":29,"Content depth fits page purpose":30,"Examples or first-hand evidence":31,
    "Originality and added value":32,"Question-led headings":33,"Key facts are concrete":34,"Definitions are explicit":35,
    "Claims retain attribution context":36,"Headed answer blocks":37,"Heading hierarchy is sequential":38,
    "Sections use H2 headings":39,"Related information is linked":40,"Markup matches the page type":45,
    "Core structured properties are populated":46,"Structured data matches visible content":47,
    "Page-type schema is appropriate":48,"Substantive server-rendered text":50,"Internal discovery paths":51,
    "Transfer compression observed":55,"Caching policy declared":56,"HSTS on HTTPS":57,
    "Mobile viewport declared":58,"Responsive viewport is declared":58,"All images declare alt behavior":60,
    "Informative images have text alternatives":60,"Image text alternatives":60,"Link purpose is understandable":61,
    "Form controls have accessible names":62,"Buttons have accessible names":63,"Color contrast is sufficient":64,
    "Mobile interaction works":65,"Observed AI visibility is measured separately":90,
}


def _connect(path: Path):
    return connect_sqlite(path, readonly=False)



def _ensure(con):
    # Compatibility hook only. Schema is owned by versioned migrations.
    return None



def _json_default(value: Any):
    if isinstance(value,datetime): return value.isoformat()
    if isinstance(value,Path): return str(value)
    if isinstance(value,set): return sorted(value)
    raise TypeError(type(value).__name__)


def _load_client_config(con, domain: str) -> dict[str, Any]:
    row = con.execute("SELECT * FROM client_report_config WHERE domain=? COLLATE NOCASE", (domain,)).fetchone()
    if not row:
        return {"competitors": [], "priority_pages": [], "target_topics": [], "page_groups": [], "integrations": [], "monitored_ai_prompts": []}
    def parsed(name):
        try:
            value=json.loads(row[name] or "[]")
            return value if isinstance(value,list) else []
        except Exception:
            return []
    return {
        "competitors": parsed("competitors_json"),
        "priority_pages": parsed("priority_pages_json"),
        "target_topics": parsed("target_topics_json"),
        "page_groups": parsed("page_groups_json"),
        "integrations": parsed("integrations_json"),
        "monitored_ai_prompts": parsed("monitored_ai_prompts_json"),
        "updated_at": row["updated_at"],
    }


def save_client_report_config(db_path:Path,domain:str,config:dict[str,Any])->dict[str,Any]:
    now=datetime.now(timezone.utc).isoformat(timespec="seconds")
    fields=("competitors","priority_pages","target_topics","page_groups","integrations","monitored_ai_prompts")
    values={key:(config.get(key) if isinstance(config.get(key),list) else []) for key in fields}
    with _connect(db_path) as con:
        _ensure(con)
        con.execute("""INSERT INTO client_report_config(domain,competitors_json,priority_pages_json,target_topics_json,page_groups_json,integrations_json,monitored_ai_prompts_json,updated_at)
                     VALUES (?,?,?,?,?,?,?,?)
                     ON CONFLICT(domain) DO UPDATE SET competitors_json=excluded.competitors_json,priority_pages_json=excluded.priority_pages_json,target_topics_json=excluded.target_topics_json,page_groups_json=excluded.page_groups_json,integrations_json=excluded.integrations_json,monitored_ai_prompts_json=excluded.monitored_ai_prompts_json,updated_at=excluded.updated_at""",
                    (domain,json.dumps(values["competitors"]),json.dumps(values["priority_pages"]),json.dumps(values["target_topics"]),json.dumps(values["page_groups"]),json.dumps(values["integrations"]),json.dumps(values["monitored_ai_prompts"]),now))
        con.commit()
        return _load_client_config(con,domain)


def _load_recommendation_tracking(con, domain: str) -> dict[str, dict[str, Any]]:
    rows=con.execute("SELECT finding_key,status,note,updated_at FROM recommendation_tracking WHERE domain=? COLLATE NOCASE",(domain,)).fetchall()
    return {r["finding_key"]:{"status":r["status"],"note":r["note"],"updated_at":r["updated_at"]} for r in rows}


def set_recommendation_tracking(db_path:Path,domain:str,finding_key:str,status:str,note:str="")->dict[str,Any]:
    status=str(status or "").strip().lower()
    if status not in RECOMMENDATION_STATES:
        raise ValueError(f"Invalid recommendation status: {status}")
    now=datetime.now(timezone.utc).isoformat(timespec="seconds")
    with _connect(db_path) as con:
        _ensure(con)
        con.execute("""INSERT INTO recommendation_tracking(domain,finding_key,status,note,updated_at) VALUES (?,?,?,?,?)
                     ON CONFLICT(domain,finding_key) DO UPDATE SET status=excluded.status,note=excluded.note,updated_at=excluded.updated_at""",
                    (domain,finding_key,status,note or "",now))
        con.commit()
    return {"finding_key":finding_key,"status":status,"note":note or "","updated_at":now}


def _auto_update_recommendations(con,domain:str,snapshot:dict[str,Any]):
    tracked=_load_recommendation_tracking(con,domain)
    if not tracked:
        return
    view=prepare_report_view(snapshot)
    root_statuses=defaultdict(list)
    for family in view.get("families") or []:
        if family.get("kind") not in {"audit","onsite"}:
            continue
        for category in family.get("categories_data") or []:
            for check in category.get("checks") or []:
                key,_=root_cause_key(str(check.get("title") or ""))
                root_statuses[key].append(normalize_status(check.get("status")))
    now=datetime.now(timezone.utc).isoformat(timespec="seconds")
    for key,state in tracked.items():
        statuses=root_statuses.get(key) or []
        if state.get("status")=="implemented" and statuses and all(s=="PASS" for s in statuses):
            con.execute("UPDATE recommendation_tracking SET status='verified',updated_at=? WHERE domain=? COLLATE NOCASE AND finding_key=?",(now,domain,key))
        elif state.get("status")=="verified" and any(is_issue(s) for s in statuses):
            con.execute("UPDATE recommendation_tracking SET status='reopened',updated_at=? WHERE domain=? COLLATE NOCASE AND finding_key=?",(now,domain,key))
    con.commit()


def create_report_session(db_path:Path,domain:str,snapshot:dict[str,Any],*,execution_run_id:str|None=None,publish:bool=True)->str:
    """Append an immutable observation snapshot and advance the domain's living report pointer."""
    report_id=secrets.token_urlsafe(12).replace("-","").replace("_","")[:16]
    if execution_run_id:
        with _connect(db_path) as lookup:
            row=lookup.execute("SELECT id FROM report_session WHERE execution_run_id=? LIMIT 1",(execution_run_id,)).fetchone()
            if row: return row["id"]
    now=datetime.now(timezone.utc).isoformat(timespec="seconds")
    immutable=dict(snapshot)
    immutable["manual_ai_snapshot"]=dict(
        immutable.get("manual_ai_snapshot")
        or immutable.get("manual_ai_source")
        or {}
    )
    with _connect(db_path) as con:
        _ensure(con)
        oldest=con.execute("SELECT created_at FROM report_session WHERE domain=? COLLATE NOCASE ORDER BY created_at ASC LIMIT 1",(domain,)).fetchone()
        coverage=data_coverage(immutable)
        manual_ai=dict(immutable.get("manual_ai_snapshot") or {})
        source_used=[x.get("label") for x in coverage if x.get("state")=="connected"]
        source_missing=[x.get("label") for x in coverage if x.get("state") in {"missing","failed"}]
        audit=immutable.get("audit") or {}
        audit_summary=immutable.get("audit_summary") or {}
        immutable["client_config"]=_load_client_config(con,domain)
        immutable["recommendation_tracking"]=_load_recommendation_tracking(con,domain)
        immutable["snapshot_contract"]={
            "version":SNAPSHOT_VERSION,
            "immutable":True,
            "stored_at":now,
            "contains":["inputs","check_outputs","evidence","page_set","source_inventory","scoring_version","methodology_version","ai_prompt_and_question_versions"],
        }
        immutable["report_metadata"]={
            "report_mode":"living",
            "audit_date":audit.get("completed_at") or audit.get("started_at") or now,
            "baseline_date":oldest["created_at"] if oldest else now,
            "pulse_updated_at":now,
            "pages_crawled":audit_summary.get("pages_audited") or ((immutable.get("crawl") or {}).get("pages_crawled")) or 0,
            "data_sources_used":source_used,
            "missing_sources":source_missing,
            "methodology_version":METHODOLOGY_VERSION,
            "scoring_version":SCORING_VERSION,
            "question_set_version":manual_ai.get("question_set_version") or 1,
            "analysis_prompt_version":manual_ai.get("analysis_system_prompt_version") or 1,
            "snapshot_version":SNAPSHOT_VERSION,
        }
        _auto_update_recommendations(con,domain,immutable)
        immutable["recommendation_tracking"]=_load_recommendation_tracking(con,domain)
        con.execute("BEGIN IMMEDIATE")
        con.execute("INSERT INTO report_session(id,domain,created_at,snapshot_json,execution_run_id) VALUES (?,?,?,?,?)",(report_id,domain,now,json.dumps(immutable,default=_json_default,separators=(",",":")),execution_run_id))
        if publish:
            living=con.execute("SELECT baseline_report_id FROM domain_report WHERE domain=? COLLATE NOCASE",(domain,)).fetchone()
            if living: con.execute("UPDATE domain_report SET current_report_id=?,updated_at=? WHERE domain=? COLLATE NOCASE",(report_id,now,domain))
            else: con.execute("INSERT INTO domain_report(domain,baseline_report_id,current_report_id,created_at,updated_at) VALUES (?,?,?,?,?)",(domain,report_id,report_id,now,now))
        con.commit()
    return report_id


def _session_with_history(con, row):
    if not row:
        return None
    snapshot=json.loads(row["snapshot_json"])
    history_rows=con.execute(
        "SELECT id,domain,created_at,snapshot_json FROM report_session WHERE domain=? COLLATE NOCASE AND created_at<=? ORDER BY created_at ASC LIMIT 250",
        (row["domain"],row["created_at"]),
    ).fetchall()
    records=[{"id":r["id"],"domain":r["domain"],"created_at":r["created_at"],"snapshot":json.loads(r["snapshot_json"])} for r in history_rows]
    history=build_finding_history(records)
    snapshot["finding_history"]=history
    snapshot["pulse_summary"]=pulse_summary(history)
    snapshot["family_pulse_summary"]=family_pulse_summary(history, FAMILIES)
    snapshot.setdefault("report_metadata",{})["report_mode"]="living"
    snapshot["report_metadata"]["pulse_updated_at"]=row["created_at"]
    return {"id":row["id"],"domain":row["domain"],"created_at":row["created_at"],"snapshot":snapshot}


def load_report_session(db_path:Path,domain:str,report_id:str):
    with _connect(db_path) as con:
        _ensure(con)
        row=con.execute("SELECT id,domain,created_at,snapshot_json FROM report_session WHERE id=? AND domain=? COLLATE NOCASE",(report_id,domain)).fetchone()
        return _session_with_history(con,row)


def load_current_report_session(db_path:Path,domain:str):
    with _connect(db_path) as con:
        _ensure(con)
        living=con.execute("SELECT current_report_id FROM domain_report WHERE domain=? COLLATE NOCASE",(domain,)).fetchone()
        if living:
            row=con.execute("SELECT id,domain,created_at,snapshot_json FROM report_session WHERE id=?",(living["current_report_id"],)).fetchone()
        else:
            row=con.execute("SELECT id,domain,created_at,snapshot_json FROM report_session WHERE domain=? COLLATE NOCASE ORDER BY created_at DESC LIMIT 1",(domain,)).fetchone()
        return _session_with_history(con,row)


def list_report_sessions(db_path:Path,domain:str,limit:int=12):
    with _connect(db_path) as con:
        _ensure(con)
        rows=con.execute("SELECT id,domain,created_at FROM report_session WHERE domain=? COLLATE NOCASE ORDER BY created_at DESC LIMIT ?",(domain,limit)).fetchall()
    return [dict(r) for r in rows]


def _impact(signal):
    title=signal.get("title") or ""
    if title in IMPACT_ORDER: return IMPACT_ORDER[title]
    try:
        weight=float(signal.get("weight") or 0)
        if weight: return 100-int(min(weight,99))
    except Exception: pass
    return 70


def _rollup_status(details):
    return rollup_status([d.get("observed_status") for d in details])


def _rollup_severity(details):
    vals=[(d.get("severity") or "").upper() for d in details if d.get("severity")]
    return "" if not vals else min(vals,key=lambda x:SEVERITY_RANK.get(x,99))


def _audit_family(defn,signals,data=None):
    data = data or {}
    finding_history=data.get("finding_history") or {}
    categories=[]
    selected=[s for s in signals if s.get("category") in defn.get("categories",[])]
    for category_name in defn.get("categories",[]):
        by_check=defaultdict(list)
        for s in selected:
            if s.get("category")==category_name:
                copy=dict(s)
                copy["observed_status"]=normalize_status(copy.get("observed_status"))
                by_check[(canonical_check_title(copy.get("title") or ""),)].append(copy)
        checks=[]
        for (title,),details in by_check.items():
            signal_key = details[0].get("signal_key") or ""
            details=sorted(details,key=lambda d:d.get("path") or "")
            affected=[d for d in details if is_issue(d.get("observed_status"))]
            reviews=[d for d in details if is_review(d.get("observed_status"))]
            unavailable=[d for d in details if normalize_status(d.get("observed_status"))=="DATA_UNAVAILABLE"]
            sample=details[0]
            checks.append({
                "signal_key":signal_key,"title":title,"category":category_name,"family":sample.get("family") or "",
                "status":_rollup_status(details),"severity":_rollup_severity(details),"impact_rank":_impact(sample),
                "pages_affected":len({d.get("path") or "/" for d in affected}),
                "pages_review_required":len({d.get("path") or "/" for d in reviews}),
                "pages_data_unavailable":len({d.get("path") or "/" for d in unavailable}),
                "pages_tested":len({d.get("path") or "/" for d in details}),
                "recommendation":sample.get("recommendation") or "","details":details,
            })
        checks = merge_duplicate_checks(checks, data)
        for check in checks:
            check["value_score_explanation"] = value_to_fix_components(check, data)
            check["value_score"] = value_to_fix(check, data)
            enrich_check(check,defn.get("name") or "")
            attach_history_to_check(check,finding_history)
        checks.sort(key=lambda c:(-float(c.get("value_score") or 0),STATUS_RANK.get(c.get("status"),99),c["title"]))
        categories.append({"name":category_name,"status":rollup_status([c["status"] for c in checks]),"checks":checks})
    # A logical check may be emitted into more than one category. It is still
    # one finding: count, score and render it once per family, while retaining
    # every category membership as metadata.
    logical_checks = {}
    deduped_categories = []
    for category in categories:
        kept = []
        for check in category["checks"]:
            logical_key = canonical_check_title(check.get("title") or check.get("signal_key") or "").strip().lower()
            if not logical_key:
                kept.append(check)
                continue
            existing = logical_checks.get(logical_key)
            if existing is None:
                check["category_memberships"] = [category["name"]]
                logical_checks[logical_key] = check
                kept.append(check)
            else:
                memberships = existing.setdefault("category_memberships", [existing.get("category") or category["name"]])
                if category["name"] not in memberships:
                    memberships.append(category["name"])
        if kept:
            category = dict(category)
            category["checks"] = kept
            category["status"] = rollup_status([c["status"] for c in kept])
            deduped_categories.append(category)
    categories = deduped_categories

    all_checks=list(logical_checks.values()) + [
        c for cat in categories for c in cat["checks"]
        if not canonical_check_title(c.get("title") or c.get("signal_key") or "").strip()
    ]
    priority=[c for c in all_checks if is_issue(c["status"])]
    reviews=[c for c in all_checks if is_review(c["status"])]
    unavailable=[c for c in all_checks if normalize_status(c["status"])=="DATA_UNAVAILABLE"]
    priority.sort(key=lambda c:(-float(c.get("value_score") or 0),STATUS_RANK.get(c["status"],99),c["category"],c["title"]))
    reviews.sort(key=lambda c:(SEVERITY_RANK.get(c.get("severity"),99),c["category"],c["title"]))
    counts=status_counts(all_checks)
    return {**defn,"categories_data":categories,"priority_findings":priority,"review_findings":reviews,"unavailable_findings":unavailable,
            "snapshot":{"checks":len(all_checks),"affected_checks":counts["confirmed_issues"],"confirmed_issues":counts["confirmed_issues"],"review_required":counts["review_required"],"data_unavailable":counts["data_unavailable"],"not_applicable":counts["not_applicable"],"passed":counts["passed"],"pages":len({s.get("path") or "/" for s in selected})}}


def _ai_family(data,defn):
    rows=list(data.get("ai_visibility_checks") or [])
    counts=Counter((r.get("status") or ("cited" if r.get("cited") else "absent")).lower() for r in rows)
    engines=sorted({r.get("engine") for r in rows if r.get("engine")})
    cited=[r for r in rows if (r.get("status") or "").lower()=="cited" or r.get("cited")]
    mentioned=[r for r in rows if (r.get("status") or "").lower()=="mentioned"]
    other=Counter()
    for r in rows:
        for c in r.get("citations_list") or []:
            d=c.get("domain")
            if d and d.lower()!=(data.get("domain") or "").lower(): other[d]+=1
    engine_summary=[]
    for engine in engines:
        er=[r for r in rows if r.get("engine")==engine]
        ec=Counter((r.get("status") or ("cited" if r.get("cited") else "absent")).lower() for r in er)
        engine_summary.append({"engine":engine,"tested":len(er),"cited":ec["cited"],"mentioned":ec["mentioned"],"absent":ec["absent"]})
    return {**defn,"overview":{"questions_tested":len({r.get("question") for r in rows if r.get("question")}),"systems_tested":len(engines),"checks":len(rows),"cited":counts["cited"],"mentioned":counts["mentioned"],"absent":counts["absent"],"citation_frequency":round(len(cited)*100/len(rows),1) if rows else 0,"company_pages_cited":len({r.get("url") for r in cited if r.get("url")}),"live_search_checks":sum(1 for r in rows if r.get("searched"))},
            "engine_summary":engine_summary,"answers":sorted(rows,key=lambda r:(r.get("question") or "",r.get("engine") or "")),
            "brand_visibility":{"linked_mentions":len(cited),"unlinked_mentions":len(mentioned),"company_pages":sorted({r.get("url") for r in cited if r.get("url")}),"chatgpt":next((x for x in engine_summary if x["engine"]=="chatgpt"),None),"google_ai_overview":None},
            "other_domains":other.most_common(20),"metrics":ai_metrics(data)}


def _seo_family(data,defn):
    seo=dict(data.get("seo") or {})
    try:
        seo["ctr"]=round(float(seo.get("clicks") or 0)*100/float(seo.get("impressions") or 0),2) if seo.get("impressions") else 0
    except Exception: seo["ctr"]=0
    keywords=list(data.get("keywords") or [])
    striking=[k for k in keywords if k.get("latest_position") is not None and 4<=float(k.get("latest_position") or 999)<=20]
    by_query=defaultdict(list)
    for k in keywords: by_query[k.get("query") or ""].append(k)
    cann=[{"query":q,"pages":rows} for q,rows in by_query.items() if q and len({r.get("page") for r in rows if r.get("page")})>1]
    return {**defn,"seo":seo,"keywords":keywords,"wanted":list(data.get("wanted") or []),"striking_distance":striking,
            "exact_cannibalization":cann,"rank_tracking":list(data.get("rank_tracking") or []),
            "competitor_keywords":list(data.get("competitor_keywords") or []),"backlinks":list(data.get("backlinks") or []),
            "ref_domains":list(data.get("ref_domains") or []),"backlink_summary":data.get("backlink_summary"),
            "domain_metrics":data.get("domain_metrics"),"clarity":data.get("clarity")}


def _onsite_family(data,defn,signals):
    out=_audit_family(defn,signals,data)
    out.update({"crawl":data.get("crawl"),"crawl_issues":list(data.get("crawl_issues") or []),"crawl_pages":list(data.get("crawl_pages") or []),
                "site_audit":data.get("site_audit"),"site_audit_pages":list(data.get("site_audit_pages") or []),
                "sitemap_urls":list(data.get("sitemap_urls") or []),"site_health":data.get("site_health")})
    return out


def _merge_answer_readiness_executive_findings(findings):
    cluster_titles = {
        "common follow-up questions addressed",
        "faq content is visible",
        "question-led headings",
        "multiple relevant question forms",
        "sections support fragment linking",
    }
    clustered = []
    kept = []
    for finding in findings or []:
        title = str(finding.get("title") or "").strip().lower()
        if title in cluster_titles:
            clustered.append(finding)
        else:
            kept.append(finding)
    if clustered:
        max_score = max(float(x.get("value_score") or 0) for x in clustered)
        kept.append({
            "title": "Content is not consistently structured for answer retrieval",
            "message": "Several related answer-readiness checks fail broadly across the site. Rather than a single FAQ or heading problem, the pattern indicates that much of the content is not consistently organized around clear questions, direct answers, and reusable answer blocks.",
            "value_score": max_score + 1.0,
            "source": "Content & Answer Readiness",
        })
    kept.sort(key=lambda x: -float(x.get("value_score") or 0))
    return kept[:5]


def _dedupe_executive_root_causes(findings, root_causes):
    root_by_key={r.get("id"):r for r in root_causes}
    out=[]
    seen=set()
    for finding in findings or []:
        key,label=root_cause_key(str(finding.get("title") or ""))
        if key in seen:
            continue
        seen.add(key)
        root=root_by_key.get(key)
        if root and len(root.get("supporting_checks") or [])>1:
            out.append({
                "title":root.get("title") or label,
                "message":f"One underlying pattern is supported by {len(root.get('supporting_checks') or [])} related checks and affects {root.get('pages_affected') or 0} page(s). The detailed checks remain available as supporting evidence.",
                "value_score":max(float(finding.get("value_score") or 0),float(root.get("value_score") or 0)),
                "source":" · ".join(root.get("family_names") or []),
                "root_cause_id":key,
                "confidence":root.get("confidence") or "medium",
                "evidence_type":"root_cause_group",
            })
        else:
            item=dict(finding)
            item.setdefault("confidence","medium")
            item.setdefault("evidence_type","derived_report_summary")
            out.append(item)
    out.sort(key=lambda x:-float(x.get("value_score") or 0))
    return out[:5]


def _apply_recommendation_tracking(root_causes, tracking):
    for root in root_causes:
        state=tracking.get(root.get("id") or "") or {}
        rec=root.get("recommendation_object") or {}
        if state:
            rec["status"]=state.get("status") or rec.get("status") or "open"
            rec["tracking_note"]=state.get("note") or ""
            rec["tracking_updated_at"]=state.get("updated_at") or ""
        root["recommendation_object"]=rec
    return root_causes


def _normalize_manual_ai_snapshot(manual_ai: dict[str, Any]) -> dict[str, Any]:
    """Normalize Manual AI evidence for the active two-phase report model."""
    manual_ai = dict(manual_ai or {})
    provider_rows = []

    # Current shape: phases -> states -> providers. Each provider row represents
    # one provider/state execution and may contain four question results.
    for phase in manual_ai.get("phases") or []:
        for state in phase.get("states") or []:
            provider_rows.extend(list(state.get("providers") or []))

    # Legacy snapshots stored providers at the top level. Keep them readable.
    if not provider_rows:
        provider_rows = list(manual_ai.get("providers") or [])

    provider_run_count = int(manual_ai.get("provider_runs") or len(provider_rows))
    answer_count = int(manual_ai.get("answer_count") or sum(int(p.get("result_count") or 0) for p in provider_rows))
    valid_json_provider_runs = int(
        manual_ai.get("valid_json_providers")
        if manual_ai.get("valid_json_providers") is not None
        else sum(1 for p in provider_rows if isinstance(p.get("parsed"), dict))
    )
    expected_answer_count = int(manual_ai.get("expected_answer_count") or (provider_run_count * 4))
    unique_providers = sorted({str(p.get("provider") or "").strip() for p in provider_rows if p.get("provider")})

    # Availability is evidence-based: provider execution rows are sufficient.
    # Do not invalidate a four-state source merely because the legacy top-level
    # providers array is absent.
    manual_ai["available"] = bool(provider_rows or manual_ai.get("available"))
    manual_ai["provider_runs"] = provider_run_count
    manual_ai["provider_count"] = len(unique_providers) if unique_providers else provider_run_count
    manual_ai["provider_names"] = unique_providers
    manual_ai["answer_count"] = answer_count
    manual_ai["valid_json_providers"] = valid_json_provider_runs
    manual_ai["expected_answer_count"] = expected_answer_count

    # Active AI Visibility evidence model:
    # 2 phases × 3 providers × 4 questions = 6 provider-phase runs / 24 answers.
    # Legacy State 1 evidence may remain stored but does not count.
    active_manual_ai_fields = [
        ("phase1_state2", "chatgpt"),
        ("phase1_state2", "claude"),
        ("phase1_state2", "gemini"),
        ("phase2_state2", "chatgpt"),
        ("phase2_state2", "claude"),
        ("phase2_state2", "gemini"),
    ]

    def _active_manual_ai_json(raw):
        text = str(raw or "").strip()
        if text.startswith("```") and text.endswith("```"):
            lines = text.splitlines()
            if len(lines) >= 3:
                text = "\n".join(lines[1:-1]).strip()
        try:
            value = json.loads(text)
            return value if isinstance(value, dict) else None
        except Exception:
            return None

    active_runs = 0
    active_valid_json_runs = 0
    active_answer_count = 0
    active_provider_names = set()
    active_shape_present = False

    for prefix, provider in active_manual_ai_fields:
        field_name = f"{prefix}_{provider}_response"
        raw = manual_ai.get(field_name) or ""
        if not str(raw).strip():
            continue

        active_shape_present = True
        active_runs += 1
        active_provider_names.add(provider)

        parsed = _active_manual_ai_json(raw)
        if parsed is None:
            continue

        active_valid_json_runs += 1
        results = parsed.get("results")
        if isinstance(results, list):
            active_answer_count += len(results)

    # Only apply the current 2-phase/6-run calculation when the snapshot
    # actually contains current-schema response fields. Historical/legacy
    # snapshots must remain readable using their persisted provider rows/counts.
    if active_shape_present:
        manual_ai["provider_runs"] = active_runs
        manual_ai["expected_provider_runs"] = 6
        manual_ai["provider_count"] = len(active_provider_names)
        manual_ai["provider_names"] = sorted(active_provider_names)
        manual_ai["answer_count"] = active_answer_count
        manual_ai["valid_json_providers"] = active_valid_json_runs
        manual_ai["expected_answer_count"] = 24
        manual_ai["complete"] = bool(
            active_runs == 6
            and active_valid_json_runs == 6
            and active_answer_count == 24
        )
    else:
        # Legacy snapshots already had their counts normalized above.
        manual_ai["complete"] = bool(
            manual_ai.get("available")
            and int(manual_ai.get("provider_runs") or 0) > 0
            and int(manual_ai.get("answer_count") or 0)
                >= int(manual_ai.get("expected_answer_count") or 0)
        )

    return manual_ai


def prepare_report_view(snapshot:dict[str,Any])->dict[str,Any]:
    data=dict(snapshot)
    signals=[]
    for raw in data.get("audit_signals") or []:
        signal=dict(raw)
        signal["observed_status"]=normalize_status(signal.get("observed_status"))
        signals.append(signal)
    data["audit_signals"]=signals
    families=[]
    for defn in FAMILIES:
        if defn["kind"]=="ai": families.append(_ai_family(data,defn))
        elif defn["kind"]=="audit": families.append(_audit_family(defn,signals,data))
        elif defn["kind"]=="seo": families.append(_seo_family(data,defn))
        else: families.append(_onsite_family(data,defn,signals))
    manual_ai = _normalize_manual_ai_snapshot(
        dict(data.get("manual_ai_snapshot") or data.get("manual_ai_source") or {})
    )
    data["manual_ai_snapshot"] = manual_ai
    data["manual_ai"] = manual_ai
    data["families"]=families
    data["family_by_id"]={f["id"]:f for f in families}
    roots=group_root_causes(families)
    roots=_apply_recommendation_tracking(roots,data.get("recommendation_tracking") or {})
    data["root_causes"]=roots
    data["top_actions"]=roots[:10]
    data["review_required_findings"]=[c for f in families if f.get("kind") in {"audit","onsite"} for c in f.get("review_findings") or []]
    data["data_unavailable_checks"]=[c for f in families if f.get("kind") in {"audit","onsite"} for c in f.get("unavailable_findings") or []]
    coverage=data.get("data_coverage") or data_coverage(data)
    data["data_coverage"]=coverage
    data["monitoring_coverage"]=monitoring_coverage_summary(coverage)
    data["high_signal_findings"] = build_high_signal_findings(data, families, limit=5)
    data["high_signal_findings"] = _merge_answer_readiness_executive_findings(data.get("high_signal_findings"))
    data["high_signal_findings"] = _dedupe_executive_root_causes(data.get("high_signal_findings"),roots)
    data["methodology"] = METHODOLOGY
    data["methodology_version"] = METHODOLOGY_VERSION
    data["scoring_version"] = SCORING_VERSION
    data["glossary"] = GLOSSARY
    data["technical_family_ids"] = ["seo-audit", "onsite-audit"]
    data["report_quality"] = validate_report(data,families,roots)
    data["pulse_summary"] = data.get("pulse_summary") or pulse_summary(data.get("finding_history") or {})
    return data
