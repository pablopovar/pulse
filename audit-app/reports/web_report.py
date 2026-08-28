from __future__ import annotations

import json
import secrets
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


FAMILIES = [
    {"id":"ai-visibility","name":"AI Visibility","departments":"IR · Communications · Corporate Affairs · Marketing","purpose":"How visible is the company in AI answers, and which sources are shaping those answers?","kind":"ai"},
    {"id":"identity-authority","name":"Identity & Authority","departments":"IR · Communications · Brand","purpose":"Can machines and external audiences clearly establish who the company is and why it is authoritative?","kind":"audit","categories":["Entity Clarity & Identity","Authority & Trust"]},
    {"id":"evidence-trust","name":"Evidence & Trust","departments":"IR · Communications · Editorial · Legal/Review","purpose":"Does the company's published information carry evidence, attribution and accountability?","kind":"audit","categories":["Evidence & Citations"]},
    {"id":"content-answer-readiness","name":"Content & Answer Readiness","departments":"Communications · Content · Editorial","purpose":"Does the company publish substantive information in a form that people, search engines and answer systems can understand and reuse?","kind":"audit","categories":["Question & Intent Alignment","Answer Extractability","Content Depth & Originality","Clarity & Readability"]},
    {"id":"machine-readability-eligibility","name":"Machine Readability & Eligibility","departments":"SEO · Content · Web","purpose":"Is the company's information technically expressed in a form search and answer systems can identify, interpret and use?","kind":"audit","categories":["Search & Answer Eligibility","Structured Data","Semantic Structure"]},
    {"id":"seo-audit","name":"SEO Audit","departments":"SEO · Growth · Marketing","purpose":"How is the site performing in organic search, where is demand, and where are the highest-value search opportunities?","kind":"seo"},
    {"id":"onsite-audit","name":"Onsite Audit","departments":"SEO · Web · Engineering","purpose":"Is the site technically crawlable, indexable, accessible and healthy?","kind":"onsite","categories":["Crawlability & Indexability","Technical Delivery & Consistency","Page Experience & Accessibility"]},
]

STATUS_RANK = {"FAIL":0,"PARTIAL":1,"UNKNOWN":2,"MANUAL_REVIEW":3,"PASS":4,"NOT_APPLICABLE":5}
SEVERITY_RANK = {"CRITICAL":0,"HIGH":1,"MEDIUM":2,"LOW":3}

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
    path.parent.mkdir(parents=True, exist_ok=True)
    con=sqlite3.connect(path); con.row_factory=sqlite3.Row
    return con

def _ensure(con):
    con.execute("CREATE TABLE IF NOT EXISTS report_session (id TEXT PRIMARY KEY,domain TEXT NOT NULL,created_at TEXT NOT NULL,snapshot_json TEXT NOT NULL)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_report_session_domain_created ON report_session(domain,created_at DESC)")
    con.commit()

def _json_default(value: Any):
    if isinstance(value,datetime): return value.isoformat()
    if isinstance(value,Path): return str(value)
    if isinstance(value,set): return sorted(value)
    raise TypeError(type(value).__name__)

def create_report_session(db_path:Path,domain:str,snapshot:dict[str,Any])->str:
    report_id=secrets.token_urlsafe(12).replace("-","").replace("_","")[:16]
    now=datetime.now(timezone.utc).isoformat(timespec="seconds")
    with _connect(db_path) as con:
        _ensure(con)
        con.execute("INSERT INTO report_session(id,domain,created_at,snapshot_json) VALUES (?,?,?,?)",(report_id,domain,now,json.dumps(snapshot,default=_json_default,separators=(",",":"))))
        con.commit()
    return report_id

def load_report_session(db_path:Path,domain:str,report_id:str):
    with _connect(db_path) as con:
        _ensure(con)
        row=con.execute("SELECT id,domain,created_at,snapshot_json FROM report_session WHERE id=? AND domain=? COLLATE NOCASE",(report_id,domain)).fetchone()
    return None if not row else {"id":row["id"],"domain":row["domain"],"created_at":row["created_at"],"snapshot":json.loads(row["snapshot_json"])}

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
    if not details: return "UNKNOWN"
    return min(((d.get("observed_status") or "UNKNOWN").upper() for d in details),key=lambda x:STATUS_RANK.get(x,99))

def _rollup_severity(details):
    vals=[(d.get("severity") or "").upper() for d in details if d.get("severity")]
    return "" if not vals else min(vals,key=lambda x:SEVERITY_RANK.get(x,99))

def _audit_family(defn,signals):
    categories=[]
    selected=[s for s in signals if s.get("category") in defn.get("categories",[])]
    for category_name in defn.get("categories",[]):
        by_check=defaultdict(list)
        for s in selected:
            if s.get("category")==category_name:
                by_check[(s.get("signal_key") or "",s.get("title") or "")].append(s)
        checks=[]
        for (signal_key,title),details in by_check.items():
            details=sorted(details,key=lambda d:d.get("path") or "")
            affected=[d for d in details if (d.get("observed_status") or "").upper() in {"FAIL","PARTIAL","UNKNOWN","MANUAL_REVIEW"}]
            sample=details[0]
            checks.append({
                "signal_key":signal_key,"title":title,"category":category_name,"family":sample.get("family") or "",
                "status":_rollup_status(details),"severity":_rollup_severity(details),"impact_rank":_impact(sample),
                "pages_affected":len({d.get("path") or "/" for d in affected}),
                "pages_tested":len({d.get("path") or "/" for d in details}),
                "recommendation":sample.get("recommendation") or "","details":details,
            })
        checks.sort(key=lambda c:(c["impact_rank"],c["title"]))
        categories.append({"name":category_name,"status":_rollup_status([{"observed_status":c["status"]} for c in checks]) if checks else "UNKNOWN","checks":checks})
    priority=[c for cat in categories for c in cat["checks"] if c["status"]!="PASS"]
    priority.sort(key=lambda c:(c["impact_rank"],STATUS_RANK.get(c["status"],99),c["category"],c["title"]))
    return {**defn,"categories_data":categories,"priority_findings":priority,
            "snapshot":{"checks":sum(len(c["checks"]) for c in categories),"affected_checks":sum(1 for c in priority),"pages":len({s.get("path") or "/" for s in selected})}}

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
            "other_domains":other.most_common(20)}

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
    out=_audit_family(defn,signals)
    out.update({"crawl":data.get("crawl"),"crawl_issues":list(data.get("crawl_issues") or []),"crawl_pages":list(data.get("crawl_pages") or []),
                "site_audit":data.get("site_audit"),"site_audit_pages":list(data.get("site_audit_pages") or []),
                "sitemap_urls":list(data.get("sitemap_urls") or []),"site_health":data.get("site_health")})
    return out

def prepare_report_view(snapshot:dict[str,Any])->dict[str,Any]:
    data=dict(snapshot); signals=list(data.get("audit_signals") or [])
    families=[]
    for defn in FAMILIES:
        if defn["kind"]=="ai": families.append(_ai_family(data,defn))
        elif defn["kind"]=="audit": families.append(_audit_family(defn,signals))
        elif defn["kind"]=="seo": families.append(_seo_family(data,defn))
        else: families.append(_onsite_family(data,defn,signals))
    data["families"]=families
    data["family_by_id"]={f["id"]:f for f in families}
    return data
