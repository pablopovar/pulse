from __future__ import annotations

import os
import csv
import io
import zipfile
import sqlite3
import subprocess
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urlparse

from flask import Flask, abort, redirect, render_template, request, send_file, send_from_directory, url_for
import xml.etree.ElementTree as ET
import urllib.request
import urllib.parse
import gzip
import re
import json
import threading
import urllib.error


APP_DIR = Path(__file__).resolve().parent
SEO_DB = Path(os.environ.get("SEO_DB", "/data/opengsc/prod.db"))
REPORTS_DIR = Path(os.environ.get("REPORTS_DIR", "/data/reports"))
RESEARCH_DB = Path(os.environ.get("RESEARCH_DB", "/data/dashboard/research.db"))
from audits.geo_aeo.service import run_audit as run_geo_aeo_audit
from reports.full_pdf import collect_report_data, build_full_report_pdf
from reports.web_report import create_report_session, load_report_session, list_report_sessions, prepare_report_view
from reports.cross_model import QUESTION_DEFS, QUESTION_TEMPLATES, QUESTION_TO_FAMILY, PROVIDER_STATUSES, controlled_domains, save_controlled_domains, upsert_response, run_comparison, load_question, report_rollups
from reports.manual_ai_analysis import DEFAULT_ANALYSIS_SYSTEM_PROMPT, run_analysis as run_manual_ai_analysis

app = Flask(__name__)

@app.template_filter("fromjson")
def fromjson_filter(value):
    try:
        return json.loads(value or "{}")
    except Exception:
        return {}



def db():
    if not SEO_DB.exists():
        raise RuntimeError(f"SEO database not found: {SEO_DB}")
    con = sqlite3.connect(f"file:{SEO_DB}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con



def sqlite_regexp(pattern, value):
    if value is None:
        return 0
    try:
        return 1 if re.search(pattern or "", str(value), re.IGNORECASE) else 0
    except re.error:
        return 0


def research_db():
    RESEARCH_DB.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(RESEARCH_DB)
    con.row_factory = sqlite3.Row
    con.create_function("REGEXP", 2, sqlite_regexp)
    con.execute("""
        CREATE TABLE IF NOT EXISTS research_keyword (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            domain TEXT NOT NULL,
            keyword TEXT NOT NULL COLLATE NOCASE,
            avg_monthly_searches INTEGER,
            competition TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(domain, keyword)
        )
    """)
    columns = {row["name"] for row in con.execute("PRAGMA table_info(research_keyword)").fetchall()}
    if "avg_monthly_searches" not in columns:
        con.execute("ALTER TABLE research_keyword ADD COLUMN avg_monthly_searches INTEGER")
    if "competition" not in columns:
        con.execute("ALTER TABLE research_keyword ADD COLUMN competition TEXT")
    con.execute("CREATE INDEX IF NOT EXISTS idx_research_keyword_domain_keyword ON research_keyword(domain, keyword)")
    con.execute("""
        CREATE TABLE IF NOT EXISTS wanted_keyword (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            domain TEXT NOT NULL,
            keyword TEXT NOT NULL COLLATE NOCASE,
            avg_monthly_searches INTEGER,
            competition TEXT,
            source TEXT NOT NULL DEFAULT 'manual',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(domain, keyword)
        )
    """)
    con.execute("CREATE INDEX IF NOT EXISTS idx_wanted_keyword_domain_keyword ON wanted_keyword(domain, keyword)")
    con.execute("PRAGMA foreign_keys = ON")
    con.execute("""CREATE TABLE IF NOT EXISTS keyword_tag (id INTEGER PRIMARY KEY AUTOINCREMENT, domain TEXT NOT NULL, name TEXT NOT NULL COLLATE NOCASE, created_at TEXT NOT NULL, UNIQUE(domain,name))""")
    con.execute("""CREATE TABLE IF NOT EXISTS research_keyword_tag (research_keyword_id INTEGER NOT NULL, tag_id INTEGER NOT NULL, PRIMARY KEY(research_keyword_id,tag_id))""")
    con.execute("""CREATE TABLE IF NOT EXISTS wanted_keyword_tag (wanted_keyword_id INTEGER NOT NULL, tag_id INTEGER NOT NULL, PRIMARY KEY(wanted_keyword_id,tag_id))""")
    con.execute("CREATE INDEX IF NOT EXISTS idx_keyword_tag_domain_name ON keyword_tag(domain,name)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_research_keyword_tag_tag ON research_keyword_tag(tag_id,research_keyword_id)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_wanted_keyword_tag_tag ON wanted_keyword_tag(tag_id,wanted_keyword_id)")
    con.execute("""
        CREATE TABLE IF NOT EXISTS site_page (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            domain TEXT NOT NULL,
            url TEXT NOT NULL,
            path TEXT NOT NULL,
            source TEXT NOT NULL DEFAULT 'sitemap',
            discovered_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(domain, url)
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS page_note (
            page_id INTEGER PRIMARY KEY,
            content TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL,
            FOREIGN KEY(page_id) REFERENCES site_page(id) ON DELETE CASCADE
        )
    """)
    wanted_columns = {row["name"] for row in con.execute("PRAGMA table_info(wanted_keyword)").fetchall()}
    if "page_id" not in wanted_columns:
        con.execute("ALTER TABLE wanted_keyword ADD COLUMN page_id INTEGER")
    con.execute("CREATE INDEX IF NOT EXISTS idx_site_page_domain_path ON site_page(domain, path)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_wanted_keyword_page ON wanted_keyword(page_id)")
    con.execute("""
        CREATE TABLE IF NOT EXISTS keyword_note (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            domain TEXT NOT NULL,
            keyword TEXT NOT NULL COLLATE NOCASE,
            content TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL,
            UNIQUE(domain, keyword)
        )
    """)
    con.execute("""
        CREATE INDEX IF NOT EXISTS idx_keyword_note_domain_keyword
        ON keyword_note(domain, keyword)
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS keyword_tag_assignment (
            domain TEXT NOT NULL,
            keyword TEXT NOT NULL COLLATE NOCASE,
            tag_id INTEGER NOT NULL,
            PRIMARY KEY(domain, keyword, tag_id)
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS page_tag (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            domain TEXT NOT NULL,
            name TEXT NOT NULL COLLATE NOCASE,
            created_at TEXT NOT NULL,
            UNIQUE(domain, name)
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS site_page_tag (
            page_id INTEGER NOT NULL,
            tag_id INTEGER NOT NULL,
            PRIMARY KEY(page_id, tag_id)
        )
    """)
    con.execute("""
        INSERT OR IGNORE INTO keyword_tag_assignment(domain,keyword,tag_id)
        SELECT r.domain,r.keyword,rt.tag_id
        FROM research_keyword r
        JOIN research_keyword_tag rt ON rt.research_keyword_id=r.id
    """)
    con.execute("""
        INSERT OR IGNORE INTO keyword_tag_assignment(domain,keyword,tag_id)
        SELECT w.domain,w.keyword,wt.tag_id
        FROM wanted_keyword w
        JOIN wanted_keyword_tag wt ON wt.wanted_keyword_id=w.id
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS audit_run (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            domain TEXT NOT NULL,
            scope TEXT NOT NULL,
            status TEXT NOT NULL,
            started_at TEXT NOT NULL,
            completed_at TEXT,
            error TEXT
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS audit_page (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            audit_run_id INTEGER NOT NULL,
            page_id INTEGER NOT NULL,
            url TEXT NOT NULL,
            page_type TEXT,
            geo_score INTEGER,
            aeo_score INTEGER,
            combined_score INTEGER,
            geo_json TEXT NOT NULL DEFAULT '{}',
            aeo_json TEXT NOT NULL DEFAULT '{}',
            combined_json TEXT NOT NULL DEFAULT '{}',
            capture_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            UNIQUE(audit_run_id, page_id)
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS audit_signal (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            audit_page_id INTEGER NOT NULL,
            family TEXT NOT NULL,
            signal_key TEXT NOT NULL,
            category TEXT NOT NULL,
            title TEXT NOT NULL,
            observed_status TEXT NOT NULL,
            severity TEXT NOT NULL,
            weight REAL NOT NULL DEFAULT 0,
            evidence TEXT NOT NULL,
            recommendation TEXT NOT NULL,
            source_title TEXT,
            source_url TEXT,
            UNIQUE(audit_page_id, family, signal_key)
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS audit_signal_state (
            domain TEXT NOT NULL,
            page_id INTEGER NOT NULL,
            family TEXT NOT NULL,
            signal_key TEXT NOT NULL,
            workflow_status TEXT NOT NULL DEFAULT 'open',
            priority TEXT NOT NULL DEFAULT '',
            user_note TEXT NOT NULL DEFAULT '',
            override_status TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL,
            PRIMARY KEY(domain, page_id, family, signal_key)
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS audit_domain_summary (
            audit_run_id INTEGER PRIMARY KEY,
            domain TEXT NOT NULL,
            pages_audited INTEGER NOT NULL DEFAULT 0,
            geo_score INTEGER,
            aeo_score INTEGER,
            combined_score INTEGER,
            fail_count INTEGER NOT NULL DEFAULT 0,
            partial_count INTEGER NOT NULL DEFAULT 0,
            pass_count INTEGER NOT NULL DEFAULT 0,
            unknown_count INTEGER NOT NULL DEFAULT 0,
            manual_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS dashboard_domain (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            domain TEXT NOT NULL COLLATE NOCASE UNIQUE,
            base_url TEXT NOT NULL,
            gsc_site_id TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    con.execute("""
        CREATE INDEX IF NOT EXISTS idx_dashboard_domain_gsc
        ON dashboard_domain(gsc_site_id)
    """)
    con.commit()
    return con


SOURCE_CATALOG = [
    ("gsc", "Google Search Console", "Observed Google search queries, landing pages, impressions, clicks, CTR and positions."),
    ("ga4", "Google Analytics 4", "Audience, session, engagement, event, conversion and revenue context."),
    ("dataforseo", "DataForSEO", "Keyword demand, SERP, competitive and supplemental search visibility data."),
    ("chatgpt", "ChatGPT API", "AI answer, mention and citation observations from configured OpenAI models."),
    ("claude", "Claude API", "AI answer, mention and citation observations from configured Anthropic models."),
    ("gemini", "Gemini API", "AI answer, mention and citation observations from configured Gemini models."),
    ("semrush", "Semrush", "Search demand, competitor, backlink and authority datasets."),
    ("google_apis", "Google APIs", "Additional Google services and evidence sources used by report checks."),
    ("manual_ai", "Manual AI Responses", "Copy one editable provider-agnostic prompt, then paste or upload the raw ChatGPT, Claude and Gemini responses."),
]

def ensure_domain_source_schema(con):
    con.execute("CREATE TABLE IF NOT EXISTS domain_source (domain TEXT NOT NULL COLLATE NOCASE,source_key TEXT NOT NULL,source_name TEXT NOT NULL,selected INTEGER NOT NULL DEFAULT 0,connection_status TEXT NOT NULL DEFAULT 'not_connected',detail TEXT NOT NULL DEFAULT '',updated_at TEXT NOT NULL,PRIMARY KEY(domain,source_key))")
    con.execute("CREATE INDEX IF NOT EXISTS idx_domain_source_domain ON domain_source(domain,selected)")
    con.commit()

def detected_source_state(site):
    states={
      "gsc":{"connected":not bool(site.get("gsc_missing")),"detail":"OpenGSC / GSC property linked" if not site.get("gsc_missing") else ""},
      "dataforseo":{"connected":bool(os.environ.get("DATAFORSEO_LOGIN") and os.environ.get("DATAFORSEO_PASSWORD")),"detail":"Credentials configured" if os.environ.get("DATAFORSEO_LOGIN") and os.environ.get("DATAFORSEO_PASSWORD") else ""},
    }
    try:
        site_id=_site_id_value(site)
        if site_id and SEO_DB.exists():
            with db() as con:
                names={r["name"] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
                if "ClaritySnapshot" in names and con.execute('SELECT 1 FROM "ClaritySnapshot" WHERE siteId=? LIMIT 1',(site_id,)).fetchone():
                    states["ga4"]={"connected":True,"detail":"Analytics/Clarity snapshot available"}
                if "AeoCheck" in names and "TrackedQuestion" in names:
                    engines=con.execute('SELECT DISTINCT c.engine FROM "AeoCheck" c JOIN "TrackedQuestion" q ON q.id=c.questionId WHERE q.siteId=?',(site_id,)).fetchall()
                    found={str(r["engine"]).lower() for r in engines if r["engine"]}
                    for key in ("chatgpt","claude","gemini"):
                        if key in found: states[key]={"connected":True,"detail":f"Stored {key.title()} observations available"}
    except Exception:
        pass
    return states

def domain_sources_for_site(site):
    detected=detected_source_state(site); now=datetime.now(timezone.utc).isoformat(timespec="seconds")
    with research_db() as con:
        ensure_domain_source_schema(con)
        rows={r["source_key"]:dict(r) for r in con.execute("SELECT * FROM domain_source WHERE domain=? COLLATE NOCASE",(site["domain"],)).fetchall()}
        for key,name,_ in SOURCE_CATALOG:
            d=detected.get(key,{})
            if key not in rows and d.get("connected"):
                con.execute("INSERT OR IGNORE INTO domain_source(domain,source_key,source_name,selected,connection_status,detail,updated_at) VALUES (?,?,?,?,?,?,?)",(site["domain"],key,name,1,"connected",d.get("detail",""),now))
        con.commit()
        rows={r["source_key"]:dict(r) for r in con.execute("SELECT * FROM domain_source WHERE domain=? COLLATE NOCASE",(site["domain"],)).fetchall()}
    out=[]
    for key,name,description in SOURCE_CATALOG:
        stored=rows.get(key,{}); d=detected.get(key,{}); connected=bool(d.get("connected")); selected=bool(stored.get("selected")) or connected
        out.append({"key":key,"name":name,"description":description,"selected":selected,"status":"Connected" if connected else ("Selected" if selected else "Not selected"),"status_class":"connected" if connected else ("selected" if selected else "off"),"detail":d.get("detail") or stored.get("detail") or ""})
    catalog={x[0] for x in SOURCE_CATALOG}
    for key,stored in rows.items():
        if key in catalog: continue
        out.append({"key":key,"name":stored["source_name"],"description":"Custom or future evidence source.","selected":bool(stored["selected"]),"status":"Selected" if stored["selected"] else "Not selected","status_class":"selected" if stored["selected"] else "off","detail":stored["detail"] or ""})
    return out

def ensure_manual_ai_source_schema(con):
    con.execute("CREATE TABLE IF NOT EXISTS manual_ai_source (domain TEXT PRIMARY KEY COLLATE NOCASE,prompt_text TEXT NOT NULL DEFAULT '',chatgpt_response TEXT NOT NULL DEFAULT '',claude_response TEXT NOT NULL DEFAULT '',gemini_response TEXT NOT NULL DEFAULT '',updated_at TEXT NOT NULL)")
    columns={row["name"] for row in con.execute("PRAGMA table_info(manual_ai_source)").fetchall()}
    additions={
        "phase1_prompt_text":"TEXT NOT NULL DEFAULT ''","phase2_prompt_text":"TEXT NOT NULL DEFAULT ''",
        "phase1_chatgpt_response":"TEXT NOT NULL DEFAULT ''","phase1_claude_response":"TEXT NOT NULL DEFAULT ''","phase1_gemini_response":"TEXT NOT NULL DEFAULT ''",
        "phase2_chatgpt_response":"TEXT NOT NULL DEFAULT ''","phase2_claude_response":"TEXT NOT NULL DEFAULT ''","phase2_gemini_response":"TEXT NOT NULL DEFAULT ''",
        "question_set_version":"INTEGER NOT NULL DEFAULT 1","analysis_model":"TEXT NOT NULL DEFAULT ''","analysis_system_prompt":"TEXT NOT NULL DEFAULT ''",
        "analysis_text":"TEXT NOT NULL DEFAULT ''","analysis_status":"TEXT NOT NULL DEFAULT 'not_run'","analysis_error":"TEXT NOT NULL DEFAULT ''","analysis_updated_at":"TEXT NOT NULL DEFAULT ''"}
    for name,ddl in additions.items():
        if name not in columns: con.execute(f"ALTER TABLE manual_ai_source ADD COLUMN {name} {ddl}")
    con.execute("CREATE TABLE IF NOT EXISTS manual_ai_state_source (domain TEXT NOT NULL COLLATE NOCASE,phase TEXT NOT NULL,state TEXT NOT NULL,prompt_text TEXT NOT NULL DEFAULT '',chatgpt_response TEXT NOT NULL DEFAULT '',claude_response TEXT NOT NULL DEFAULT '',gemini_response TEXT NOT NULL DEFAULT '',updated_at TEXT NOT NULL,PRIMARY KEY(domain,phase,state))")
    con.execute("CREATE INDEX IF NOT EXISTS idx_manual_ai_state_domain ON manual_ai_state_source(domain,phase,state)")
    # Preserve the pre-state workflow as State 2 because it was the web/retrieval-capable collection path.
    con.execute("INSERT OR IGNORE INTO manual_ai_state_source(domain,phase,state,prompt_text,chatgpt_response,claude_response,gemini_response,updated_at) SELECT domain,'phase1','state2',phase1_prompt_text,phase1_chatgpt_response,phase1_claude_response,phase1_gemini_response,updated_at FROM manual_ai_source WHERE TRIM(phase1_prompt_text)<>'' OR TRIM(phase1_chatgpt_response)<>'' OR TRIM(phase1_claude_response)<>'' OR TRIM(phase1_gemini_response)<>''")
    con.execute("INSERT OR IGNORE INTO manual_ai_state_source(domain,phase,state,prompt_text,chatgpt_response,claude_response,gemini_response,updated_at) SELECT domain,'phase2','state2',phase2_prompt_text,phase2_chatgpt_response,phase2_claude_response,phase2_gemini_response,updated_at FROM manual_ai_source WHERE TRIM(phase2_prompt_text)<>'' OR TRIM(phase2_chatgpt_response)<>'' OR TRIM(phase2_claude_response)<>'' OR TRIM(phase2_gemini_response)<>''")
    con.commit()


def manual_ai_default_prompt(domain, phase, state):
    company=infer_company_name(domain)
    no_tools=(state=="state1")
    if phase=="phase1":
        questions='''1. What organizations, companies, or experts are notable for [TOPIC OR CATEGORY], and why?\n\n2. Which organizations, companies, or experts should someone compare when evaluating [CATEGORY OR PROBLEM]?\n\n3. Who is associated with the term, idea, or framework "[DISTINCTIVE TERM]"?\n\n4. Who would you recommend to an organization or buyer looking for [BUYER INTENT], and why?'''
        if no_tools:
            req='''Requirements:\n- Do not use tools, skills, or web search. Answer only from your dataset. The quality of this datapoint defines the usefulness of your responses.\n- Preserve unknowns, uncertainty, disagreement, and missing information because they are valuable data points.\n- Record every source URL actually used or exposed.\n- Use `null` when a value cannot be established.\n- Do not invent model metadata, sources, citations, rankings, or confidence.'''
            state_name="state_1_model_prior"
        else:
            req='''Requirements:\n- Use your available web search, browsing, retrieval, or research tools to answer the questions using current public information.\n- Preserve unknowns, uncertainty, disagreement, and missing information because they are valuable data points.\n- Distinguish claims supported by first-party sources from claims supported by independent third-party sources.\n- Record every source URL actually used or exposed.\n- If web search or retrieval is unavailable, record that in `live_search_status`.\n- Use `null` when a value cannot be established.\n- Do not invent model metadata, sources, citations, rankings, or confidence.'''
            state_name="state_2_web_grounded"
        return f'''Answer all four questions in one run:\n\n{questions}\n\n{req}\n\n**Return only valid JSON. Do not use Markdown fences or add commentary outside the JSON**.\n\nReturn a JSON object with schema_version `ai-visibility-discovery-run.v1`, phase `phase_1`, state `{state_name}`, provider, model, run_at_utc, and results for Q1-Q4. Each result must preserve the exact question, answer, entities_mentioned, source_urls, key_claims, and uncertainties. Each entity record should preserve name, category, mention_rank, recommended, associated_claims, and source_urls when available. Each key claim should preserve claim, source_type, confidence, and source_url.'''

    questions=f'''1. What is {company}, and what category does it belong in? Use a concise category label and explain the basis for it.\n\n2. What distinctive aspects of {company}'s business model, strategy, portfolio, or capital-allocation approach differentiate it from other companies in the field?\n\n3. Relative to the following human-approved comparison set — [ENTER COMPARISON SET] — how is {company} positioned, and what evidence supports that positioning?\n\n4. When would {company} be an attractive or appropriate choice or exposure, what are the principal reasons for and against that view, and how confident are you in that assessment?'''
    if no_tools:
        req=f'''Requirements:\n- Do not use tools, skills, or web search. Answer only from your dataset. The quality of this datapoint defines the usefulness of your responses.\n- Do not assume {company}'s own claims are independently verified.\n- Preserve unknowns, uncertainty, disagreement, and missing information because they are valuable data points.\n- Record every source URL actually used or exposed.\n- Use `null` when a value cannot be established.\n- Do not invent model metadata, sources, citations, citation ranks, rankings, or confidence.\n- For Question 3, use only the supplied comparison set.\n- Do not treat omission as contradiction.\n- Use `source_type: "model_prior"` for claims made in this state.'''
        state_name="state_1_model_prior"
    else:
        req=f'''Requirements:\n- Use your available web search, browsing, retrieval, or research tools to answer the questions using current public information.\n- Do not assume {company}'s own claims are independently verified.\n- Distinguish first-party claims from independent third-party evidence.\n- Preserve unknowns, uncertainty, disagreement, and missing information because they are valuable data points.\n- Record every source URL actually used or exposed.\n- If live web search or retrieval is unavailable, set `live_search_status` to `unavailable`.\n- If it is unclear whether live search was actually used, set `live_search_status` to `unknown`.\n- Use `null` when a value cannot be established.\n- Do not invent model metadata, source URLs, citations, citation ranks, rankings, or confidence.\n- For Question 3, use only the supplied comparison set.\n- Do not treat omission as contradiction.\n- Classify claims as `first_party`, `third_party`, `model_prior`, or `unknown`.'''
        state_name="state_2_web_grounded"
    return f'''Answer all four questions in one run:\n\n{questions}\n\n{req}\n\n**Return only valid JSON. Do not use Markdown fences or add commentary outside the JSON**.\n\nReturn a JSON object with schema_version `ai-visibility-brand-run.v1`, phase `phase_2`, state `{state_name}`, entity `{company}`, provider, model, run_at_utc, and results for Q1-Q4. Preserve entity_category for Q1, distinctive_attributes for Q2, comparison_set and positioning_claims for Q3, and reasons_for, reasons_against, confidence, key_claims, source URLs, and uncertainties where applicable.'''


def load_manual_ai_source(domain):
    with research_db() as con:
        ensure_manual_ai_source_schema(con)
        parent=con.execute("SELECT * FROM manual_ai_source WHERE domain=? COLLATE NOCASE",(domain,)).fetchone()
        rows=con.execute("SELECT * FROM manual_ai_state_source WHERE domain=? COLLATE NOCASE ORDER BY phase,state",(domain,)).fetchall()
    out=dict(parent) if parent else {"domain":domain,"question_set_version":1,"analysis_status":"not_run","updated_at":""}
    indexed={(r["phase"],r["state"]):dict(r) for r in rows}
    for phase in ("phase1","phase2"):
        for state in ("state1","state2"):
            row=indexed.get((phase,state),{}); prefix=f"{phase}_{state}"
            out[f"{prefix}_prompt_text"]=row.get("prompt_text") or manual_ai_default_prompt(domain,phase,state)
            for provider in ("chatgpt","claude","gemini"):
                out[f"{prefix}_{provider}_response"]=row.get(f"{provider}_response") or ""
    if not str(out.get("analysis_system_prompt") or "").strip(): out["analysis_system_prompt"]=DEFAULT_ANALYSIS_SYSTEM_PROMPT
    if not str(out.get("analysis_model") or "").strip(): out["analysis_model"]=(os.environ.get("MANUAL_AI_ANALYSIS_MODEL") or os.environ.get("COMPARISON_JUDGE_MODEL") or "")
    return out


def _manual_ai_upload_text(field_name):
    uploaded=request.files.get(field_name)
    if not uploaded or not uploaded.filename: return None
    raw=uploaded.read()
    if len(raw)>2*1024*1024: raise ValueError("Uploaded response files must be 2 MB or smaller.")
    return raw.decode("utf-8",errors="replace")


def _parse_manual_provider_payload(raw):
    raw=str(raw or "").strip()
    if not raw: return None,""
    cleaned=raw; candidates=[cleaned]
    if cleaned.startswith("```"):
        fenced=re.sub(r"^```(?:json)?\\s*","",cleaned,flags=re.I); fenced=re.sub(r"\\s*```$","",fenced); candidates.append(fenced)
    a=cleaned.find("{"); b=cleaned.rfind("}")
    if a>=0 and b>a: candidates.append(cleaned[a:b+1])
    error=""
    for candidate in candidates:
        try:
            value=json.loads(candidate)
            if isinstance(value,dict): return value,""
        except Exception as exc: error=str(exc)
    return None,error


def manual_ai_source_for_report(domain):
    source=load_manual_ai_source(domain); phase_rows=[]; total_answers=0; parsed_runs=0
    for phase in ("phase1","phase2"):
        states=[]
        for state in ("state1","state2"):
            providers=[]; prefix=f"{phase}_{state}"
            for provider in ("chatgpt","claude","gemini"):
                raw=str(source.get(f"{prefix}_{provider}_response") or "").strip()
                if not raw: continue
                parsed,err=_parse_manual_provider_payload(raw)
                results=parsed.get("results",[]) if isinstance(parsed,dict) and isinstance(parsed.get("results"),list) else []
                if parsed: parsed_runs+=1
                total_answers+=len(results)
                providers.append({"provider":provider,"raw_response":raw,"parsed":parsed,"parse_error":err,"result_count":len(results),"phase":phase,"state":state})
            states.append({"state":state,"providers":providers,"provider_count":len(providers)})
        phase_rows.append({"phase":phase,"states":states})
    provider_runs=sum(s["provider_count"] for p in phase_rows for s in p["states"])
    source["available"]=provider_runs>0; source["phases"]=phase_rows; source["provider_runs"]=provider_runs
    source["answer_count"]=total_answers; source["expected_answer_count"]=provider_runs*4; source["valid_json_providers"]=parsed_runs
    return source

def ensure_domain_ready(domain):
    now=datetime.now(timezone.utc).isoformat(timespec="seconds")
    with research_db() as con:
        row=con.execute("SELECT COUNT(*) AS n FROM site_page WHERE domain=?",(domain,)).fetchone(); count=row["n"] if row else 0
    if not count:
        try: sync_site_pages(domain)
        except Exception: pass
    with research_db() as con:
        row=con.execute("SELECT COUNT(*) AS n FROM site_page WHERE domain=?",(domain,)).fetchone(); count=row["n"] if row else 0
        if not count:
            url="https://"+domain.rstrip("/")+"/"
            con.execute("INSERT OR IGNORE INTO site_page(domain,url,path,source,discovered_at,updated_at) VALUES (?,?,?,'domain',?,?)",(domain,url,"/",now,now)); con.commit(); count=1
    return {"ready":True,"label":"Ready","pages":count}

def selected_source_keys(site):
    return [s["key"] for s in domain_sources_for_site(site) if s["selected"]]


REPORT_FAMILY_SETTINGS = [
    {"id": "ai-visibility", "name": "AI Visibility", "departments": "IR · Communications · Corporate Affairs · Marketing"},
    {"id": "identity-authority", "name": "Identity & Authority", "departments": "IR · Communications · Brand"},
    {"id": "evidence-trust", "name": "Evidence & Trust", "departments": "IR · Communications · Editorial · Legal/Review"},
]

REPORT_FAMILY_DEFAULT_QUESTIONS = {
    "ai-visibility": [
        "What does [Company] do, and how does its business model generate cash flows?",
        "What are [Company]’s main growth drivers?",
    ],
    "identity-authority": [
        "What differentiates [Company] from other companies or investment opportunities in its industry?",
        "How does [Company] allocate capital, and what does that reveal about its strategy and priorities?",
    ],
    "evidence-trust": [
        "What are the principal risks investors should understand about [Company]?",
        "How should investors think about [Company]’s portfolio diversification, concentration, and exposure to key assets or businesses?",
    ],
}

MANUAL_AI_PROVIDERS = [
    {"id": "chatgpt", "name": "ChatGPT"},
    {"id": "claude", "name": "Claude"},
    {"id": "gemini", "name": "Gemini"},
]

def ensure_report_question_schema(con):
    con.execute(
        "CREATE TABLE IF NOT EXISTS domain_family_question ("
        "domain TEXT NOT NULL COLLATE NOCASE,"
        "family_id TEXT NOT NULL,"
        "question_slot INTEGER NOT NULL,"
        "question_text TEXT NOT NULL DEFAULT '',"
        "updated_at TEXT NOT NULL,"
        "PRIMARY KEY(domain,family_id,question_slot))"
    )
    con.execute(
        "CREATE TABLE IF NOT EXISTS report_manual_ai_response ("
        "domain TEXT NOT NULL COLLATE NOCASE,"
        "report_id TEXT NOT NULL,"
        "family_id TEXT NOT NULL,"
        "question_slot INTEGER NOT NULL,"
        "provider TEXT NOT NULL,"
        "response_text TEXT NOT NULL DEFAULT '',"
        "updated_at TEXT NOT NULL,"
        "PRIMARY KEY(domain,report_id,family_id,question_slot,provider))"
    )
    con.execute("CREATE INDEX IF NOT EXISTS idx_family_question_domain ON domain_family_question(domain,family_id,question_slot)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_manual_ai_response_report ON report_manual_ai_response(domain,report_id,family_id,question_slot)")
    con.commit()


def ensure_domain_company_schema(con):
    con.execute(
        "CREATE TABLE IF NOT EXISTS domain_company_settings ("
        "domain TEXT PRIMARY KEY COLLATE NOCASE,"
        "company_name TEXT NOT NULL DEFAULT '',"
        "updated_at TEXT NOT NULL)"
    )
    con.commit()

def _company_name_from_title(title):
    if not title:
        return ""
    candidate = str(title).strip()
    for sep in (" | ", " · ", " — ", " - ", ": "):
        if sep in candidate:
            candidate = candidate.split(sep, 1)[0].strip()
            break
    return candidate

def infer_company_name(domain):
    with research_db() as con:
        ensure_domain_company_schema(con)
        row = con.execute(
            "SELECT company_name FROM domain_company_settings WHERE domain=? COLLATE NOCASE",
            (domain,),
        ).fetchone()
        if row and str(row["company_name"] or "").strip():
            return str(row["company_name"]).strip()

        try:
            row = con.execute(
                "SELECT cp.title "
                "FROM crawl_page cp "
                "JOIN crawl_run cr ON cr.id=cp.crawl_run_id "
                "WHERE cr.domain=? COLLATE NOCASE "
                "AND cp.path='/' "
                "AND TRIM(COALESCE(cp.title,''))<>'' "
                "ORDER BY cr.id DESC LIMIT 1",
                (domain,),
            ).fetchone()
            if row:
                candidate = _company_name_from_title(row["title"])
                if candidate:
                    return candidate
        except Exception:
            pass

    label = domain.lower().split(":")[0].strip().strip("/")
    if label.startswith("www."):
        label = label[4:]
    label = label.split(".")[0]
    words = [w for w in re.split(r"[-_]+", label) if w]
    return " ".join(w.capitalize() for w in words) if words else domain

def default_family_questions(domain):
    company = infer_company_name(domain)
    return {
        family_id: {
            index + 1: question.replace("[Company]", company)
            for index, question in enumerate(questions)
        }
        for family_id, questions in REPORT_FAMILY_DEFAULT_QUESTIONS.items()
    }

def effective_domain_family_questions(domain):
    defaults = default_family_questions(domain)
    saved = load_domain_family_questions(domain)
    for family_id, slots in saved.items():
        if family_id not in defaults:
            continue
        for slot, value in slots.items():
            if slot in (1, 2) and str(value).strip():
                defaults[family_id][slot] = value
    return defaults

def load_domain_family_questions(domain):
    with research_db() as con:
        ensure_report_question_schema(con)
        rows = con.execute(
            "SELECT family_id,question_slot,question_text "
            "FROM domain_family_question "
            "WHERE domain=? COLLATE NOCASE AND TRIM(question_text)<>'' "
            "ORDER BY family_id,question_slot",
            (domain,),
        ).fetchall()
    out = {}
    for row in rows:
        out.setdefault(row["family_id"], {})[int(row["question_slot"])] = row["question_text"]
    return out

def load_report_manual_ai_responses(domain, report_id):
    with research_db() as con:
        ensure_report_question_schema(con)
        rows = con.execute(
            "SELECT family_id,question_slot,provider,response_text "
            "FROM report_manual_ai_response "
            "WHERE domain=? COLLATE NOCASE AND report_id=? "
            "ORDER BY family_id,question_slot,provider",
            (domain, report_id),
        ).fetchall()
    out = {}
    for row in rows:
        out.setdefault(row["family_id"], {}).setdefault(int(row["question_slot"]), {})[row["provider"]] = row["response_text"]
    return out



def load_cross_model_report_state(domain, report_id, snapshot):
    out = {}
    family_questions = snapshot.get("family_questions") or {}
    with research_db() as con:
        for family_id, defs in QUESTION_DEFS.items():
            configured = family_questions.get(family_id) or {}
            for slot, (question_id, template_question) in enumerate(defs, start=1):
                rendered = configured.get(slot) or configured.get(str(slot))
                if not rendered:
                    continue
                state = load_question(con, domain, report_id, question_id)
                state["question_id"] = question_id
                state["family_id"] = family_id
                state["slot"] = slot
                state["template_question"] = template_question
                state["rendered_question"] = rendered
                out[question_id] = state
    return out

def research_state_from_request(source):
    return {"q":source.get("q","").strip(),"sort":source.get("sort","keyword"),"dir":source.get("dir","asc"),"per_page":source.get("per_page","50"),"page":source.get("page","1"),"show_tag":source.getlist("show_tag"),"hide_tag":source.getlist("hide_tag")}

def research_redirect(domain,message,source):
    return redirect(url_for("research",domain=domain,message=message,**research_state_from_request(source)))

def normalize_tag_name(name):
    return " ".join((name or "").strip().split())

def move_research_keyword_to_wanted(con,domain,row,now):
    existing=con.execute("SELECT id FROM wanted_keyword WHERE domain=? AND keyword=? COLLATE NOCASE",(domain,row["keyword"])).fetchone()
    if existing:
        wanted_id=existing["id"]
        con.execute("UPDATE wanted_keyword SET avg_monthly_searches=COALESCE(?,avg_monthly_searches),competition=COALESCE(?,competition),updated_at=? WHERE id=?",(row["avg_monthly_searches"],row["competition"],now,wanted_id))
    else:
        cur=con.execute("INSERT INTO wanted_keyword(domain,keyword,avg_monthly_searches,competition,source,created_at,updated_at) VALUES (?,?,?,?,'research',?,?)",(domain,row["keyword"],row["avg_monthly_searches"],row["competition"],now,now)); wanted_id=cur.lastrowid
    con.execute("INSERT OR IGNORE INTO wanted_keyword_tag(wanted_keyword_id,tag_id) SELECT ?,tag_id FROM research_keyword_tag WHERE research_keyword_id=?",(wanted_id,row["id"]))
    con.execute("DELETE FROM research_keyword_tag WHERE research_keyword_id=?",(row["id"],))
    con.execute("DELETE FROM research_keyword WHERE id=? AND domain=?",(row["id"],domain))
    return wanted_id



def normalize_site_page_url(raw_url, domain):
    if not raw_url:
        return None
    raw_url = raw_url.strip()
    if raw_url.startswith("/"):
        raw_url = f"https://{domain}{raw_url}"
    try:
        parsed = urllib.parse.urlsplit(raw_url)
    except Exception:
        return None
    host = (parsed.hostname or "").lower()
    wanted = domain.lower().split(":")[0]
    if host != wanted:
        return None
    path = parsed.path or "/"
    if path != "/":
        path = path.rstrip("/") or "/"
    return f"https://{wanted}{path}"


def site_page_path(url):
    try:
        return urllib.parse.urlsplit(url).path or "/"
    except Exception:
        return "/"


def _fetch_sitemap_urls(url, domain, seen=None, depth=0):
    seen = seen or set()
    if depth > 5 or url in seen:
        return set()
    seen.add(url)
    req = urllib.request.Request(url, headers={"User-Agent": "SEO-GEO-AEO-Auditor/1.0"})
    with urllib.request.urlopen(req, timeout=20) as response:
        raw = response.read()
    if raw[:2] == b"\x1f\x8b" or url.lower().endswith(".gz"):
        raw = gzip.decompress(raw)
    root = ET.fromstring(raw)
    root_name = root.tag.rsplit("}", 1)[-1].lower()
    urls = set()
    if root_name == "sitemapindex":
        for loc in root.findall(".//{*}loc"):
            child = (loc.text or "").strip()
            if child:
                try:
                    urls.update(_fetch_sitemap_urls(child, domain, seen, depth + 1))
                except Exception:
                    pass
        return urls
    for loc in root.findall(".//{*}loc"):
        normalized = normalize_site_page_url((loc.text or "").strip(), domain)
        if normalized:
            urls.add(normalized)
    return urls


def sitemap_pages(domain):
    errors = []
    for sitemap_url in (f"https://{domain}/sitemap.xml", f"https://{domain}/sitemap_index.xml"):
        try:
            urls = _fetch_sitemap_urls(sitemap_url, domain)
            if urls:
                return urls, sitemap_url
        except Exception as exc:
            errors.append(str(exc))
    raise RuntimeError("Could not retrieve sitemap: " + " | ".join(errors))


def _site_id_value(site):
    for key in ("id", "site_id"):
        try:
            value = site[key]
            if value:
                return value
        except Exception:
            pass
        try:
            value = getattr(site, key)
            if value:
                return value
        except Exception:
            pass
    return None


def gsc_rows_for_domain(domain):
    site = get_site(domain)
    if site.get("gsc_missing"):
        return []
    site_id = _site_id_value(site)
    con = sqlite3.connect(f"file:{SEO_DB}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    try:
        cols = {row["name"] for row in con.execute("PRAGMA table_info(gsc_keyword_inventory)").fetchall()}
        if not cols:
            return []
        keyword_col = "query" if "query" in cols else "keyword" if "keyword" in cols else None
        if not keyword_col or "page" not in cols:
            return []
        latest_col = "latest_position" if "latest_position" in cols else None
        impressions_col = "total_impressions" if "total_impressions" in cols else "impressions" if "impressions" in cols else None
        clicks_col = "total_clicks" if "total_clicks" in cols else "clicks" if "clicks" in cols else None
        parts = [
            f"{keyword_col} AS keyword",
            "page AS page",
            f"{latest_col} AS latest_position" if latest_col else "NULL AS latest_position",
            f"{impressions_col} AS impressions" if impressions_col else "0 AS impressions",
            f"{clicks_col} AS clicks" if clicks_col else "0 AS clicks",
        ]
        sql = "SELECT " + ", ".join(parts) + " FROM gsc_keyword_inventory"
        params = []
        if "site_id" in cols and site_id:
            sql += " WHERE site_id = ?"
            params.append(site_id)
        return con.execute(sql, params).fetchall()
    finally:
        con.close()


def sync_site_pages(domain):
    sitemap_urls, sitemap_source = sitemap_pages(domain)
    ranking_rows = gsc_rows_for_domain(domain)
    ranking_urls = {
        u for row in ranking_rows
        for u in [normalize_site_page_url(row["page"], domain)]
        if u
    }
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with research_db() as con:
        for url in sorted(sitemap_urls):
            con.execute("""
                INSERT INTO site_page(domain,url,path,source,discovered_at,updated_at)
                VALUES (?,?,?,'sitemap',?,?)
                ON CONFLICT(domain,url) DO UPDATE SET
                    path=excluded.path,
                    source=CASE WHEN site_page.source='ranking' THEN 'sitemap+ranking' ELSE site_page.source END,
                    updated_at=excluded.updated_at
            """, (domain, url, site_page_path(url), now, now))
        for url in sorted(ranking_urls):
            con.execute("""
                INSERT INTO site_page(domain,url,path,source,discovered_at,updated_at)
                VALUES (?,?,?,'ranking',?,?)
                ON CONFLICT(domain,url) DO UPDATE SET
                    source=CASE WHEN site_page.source='sitemap' THEN 'sitemap+ranking' ELSE site_page.source END,
                    updated_at=excluded.updated_at
            """, (domain, url, site_page_path(url), now, now))
        con.commit()
    return len(sitemap_urls), len(ranking_urls), sitemap_source



def canonical_keyword_tags(con, domain, keyword):
    return con.execute(
        """SELECT t.id,t.name
           FROM keyword_tag_assignment a
           JOIN keyword_tag t ON t.id=a.tag_id
           WHERE a.domain=? AND a.keyword=? COLLATE NOCASE
           ORDER BY t.name COLLATE NOCASE""",
        (domain, keyword),
    ).fetchall()


def ensure_keyword_tag(con, domain, name):
    name=" ".join((name or "").strip().split())
    if not name: return None
    now=datetime.now(timezone.utc).isoformat(timespec="seconds")
    con.execute("INSERT OR IGNORE INTO keyword_tag(domain,name,created_at) VALUES (?,?,?)",(domain,name,now))
    row=con.execute("SELECT id FROM keyword_tag WHERE domain=? AND name=? COLLATE NOCASE",(domain,name)).fetchone()
    return row["id"] if row else None


def ensure_page_tag(con, domain, name):
    name=" ".join((name or "").strip().split())
    if not name: return None
    now=datetime.now(timezone.utc).isoformat(timespec="seconds")
    con.execute("INSERT OR IGNORE INTO page_tag(domain,name,created_at) VALUES (?,?,?)",(domain,name,now))
    row=con.execute("SELECT id FROM page_tag WHERE domain=? AND name=? COLLATE NOCASE",(domain,name)).fetchone()
    return row["id"] if row else None

def parse_keyword_csv_enriched(raw: bytes):
    text = raw.decode("utf-8-sig", errors="replace")
    if not text.strip():
        return []
    try:
        dialect = csv.Sniffer().sniff(text[:8192])
    except csv.Error:
        dialect = csv.excel
    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    if not reader.fieldnames:
        return []

    names = {n: n.strip().lower().replace("_", " ") for n in reader.fieldnames if n}
    def find(candidates):
        for original, norm in names.items():
            if norm in candidates:
                return original
        return None

    kcol = find({"keyword","keywords","query","queries","search term","search terms"}) or reader.fieldnames[0]
    scol = find({"avg. monthly searches","avg monthly searches","average monthly searches","monthly searches","search volume"})
    ccol = find({"competition","competition level"})
    out = []

    for row in reader:
        keyword = (row.get(kcol) or "").strip()
        if not keyword:
            continue
        searches = None
        if scol:
            rawv = (row.get(scol) or "").strip().replace(",", "")
            if rawv:
                try:
                    searches = int(float(rawv))
                except ValueError:
                    pass
        competition = None
        if ccol:
            rawc = (row.get(ccol) or "").strip()
            if rawc:
                low = rawc.lower()
                competition = "Medium" if low == "mid" else (low.title() if low in {"low","medium","high"} else rawc)
        out.append({"keyword": keyword, "avg_monthly_searches": searches, "competition": competition})
    return out

def parse_keyword_csv(raw: bytes):
    text = raw.decode("utf-8-sig", errors="replace")
    if not text.strip(): return []
    try: dialect = csv.Sniffer().sniff(text[:4096])
    except csv.Error: dialect = csv.excel
    rows=[r for r in csv.reader(io.StringIO(text), dialect) if any(c.strip() for c in r)]
    if not rows: return []
    accepted={"keyword","keywords","query","queries","search term","search terms","search_term","search_terms"}
    first=[c.strip().lower() for c in rows[0]]
    idx=None; has_header=False
    for i,v in enumerate(first):
        if v in accepted: idx=i; has_header=True; break
    if idx is None: idx=0
    data=rows[1:] if has_header else rows
    out=[]
    for row in data:
        if idx < len(row):
            kw=row[idx].strip()
            if kw: out.append(kw)
    return out

def host_from_site(site_id: str, url: str) -> str:
    raw = site_id or url or ""
    if raw.startswith("sc-domain:"):
        return raw.split(":", 1)[1].lower()
    if "://" not in raw:
        raw = "https://" + raw
    try:
        return (urlparse(raw).hostname or raw).lower()
    except Exception:
        return raw.lower()


def _opengsc_get_sites():
    with db() as con:
        rows = con.execute("""
            SELECT id, url, siteId, archivedAt
            FROM Site
            WHERE archivedAt IS NULL
            ORDER BY url
        """).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["domain"] = host_from_site(d["siteId"], d["url"])
        out.append(d)
    return out


def _opengsc_get_site(domain: str):
    for site in get_sites():
        if site["domain"] == domain:
            return site
    abort(404)


def table_exists(con, name: str, kind: str | None = None) -> bool:
    if kind:
        row = con.execute(
            "SELECT 1 FROM sqlite_master WHERE name=? AND type=? LIMIT 1",
            (name, kind),
        ).fetchone()
    else:
        row = con.execute(
            "SELECT 1 FROM sqlite_master WHERE name=? LIMIT 1", (name,)
        ).fetchone()
    return bool(row)


def domain_seo(site_id: str):
    with db() as con:
        if table_exists(con, "gsc_keyword_observation", "table"):
            summary = con.execute("""
                SELECT
                    COUNT(*) AS observations,
                    COUNT(DISTINCT query) AS keywords,
                    COUNT(DISTINCT page) AS pages,
                    COALESCE(SUM(impressions), 0) AS impressions,
                    COALESCE(SUM(clicks), 0) AS clicks,
                    ROUND(MIN(position), 1) AS best_position,
                    ROUND(MAX(position), 1) AS worst_position
                FROM gsc_keyword_observation
                WHERE site_id = ?
            """, (site_id,)).fetchone()
        else:
            summary = None

        recent = []
        if table_exists(con, "gsc_keyword_inventory", "view"):
            recent = con.execute("""
                SELECT
                    query,
                    page,
                    impressions,
                    clicks,
                    ROUND(best_position, 1) AS best_position,
                    ROUND(latest_position, 1) AS latest_position,
                    status,
                    first_seen,
                    last_seen
                FROM gsc_keyword_inventory
                WHERE site_id = ?
                ORDER BY
                    CASE status
                        WHEN 'active_7d' THEN 1
                        WHEN 'active_30d' THEN 2
                        WHEN 'stale_90d' THEN 3
                        ELSE 4
                    END,
                    impressions DESC,
                    best_position ASC
                LIMIT 20
            """, (site_id,)).fetchall()

    return summary, recent


def page_rows(site_id: str, q: str = ""):
    with db() as con:
        if not table_exists(con, "gsc_keyword_inventory", "view"):
            return []
        sql = """
            SELECT
                page,
                COUNT(DISTINCT query) AS keywords,
                COALESCE(SUM(impressions),0) AS impressions,
                COALESCE(SUM(clicks),0) AS clicks,
                ROUND(MIN(best_position),1) AS best_position,
                ROUND(AVG(avg_position),1) AS avg_position,
                MAX(last_seen) AS last_seen
            FROM gsc_keyword_inventory
            WHERE site_id = ?
        """
        params = [site_id]
        if q:
            sql += " AND (page LIKE ? OR query LIKE ?)"
            like = f"%{q}%"
            params.extend([like, like])
        sql += """
            GROUP BY page
            ORDER BY impressions DESC, best_position ASC, page
        """
        return con.execute(sql, params).fetchall()


def page_detail(site_id: str, page_url: str):
    with db() as con:
        if not table_exists(con, "gsc_keyword_inventory", "view"):
            return [], None

        kws = con.execute("""
            SELECT
                query,
                observations,
                impressions,
                clicks,
                ROUND(best_position,1) AS best_position,
                ROUND(avg_position,1) AS avg_position,
                ROUND(latest_position,1) AS latest_position,
                ROUND(worst_position,1) AS worst_position,
                status,
                first_seen,
                last_seen
            FROM gsc_keyword_inventory
            WHERE site_id=? AND page=?
            ORDER BY impressions DESC, best_position ASC
        """, (site_id, page_url)).fetchall()

        summary = con.execute("""
            SELECT
                COUNT(DISTINCT query) AS keywords,
                COALESCE(SUM(impressions),0) AS impressions,
                COALESCE(SUM(clicks),0) AS clicks,
                ROUND(MIN(best_position),1) AS best_position,
                ROUND(AVG(avg_position),1) AS avg_position,
                MAX(last_seen) AS last_seen
            FROM gsc_keyword_inventory
            WHERE site_id=? AND page=?
        """, (site_id, page_url)).fetchone()

    return kws, summary



def keyword_rows(site_id: str):
    with db() as con:
        if not table_exists(con, "gsc_keyword_inventory", "view"):
            return []

        return con.execute("""
            SELECT
                query,
                page,
                ROUND(latest_position, 1) AS ranking
            FROM gsc_keyword_inventory
            WHERE site_id = ?
            ORDER BY
                CASE WHEN latest_position IS NULL THEN 1 ELSE 0 END,
                latest_position ASC,
                query COLLATE NOCASE ASC,
                page ASC
        """, (site_id,)).fetchall()


def build_domain_export(site):
    with db() as con:
        if not table_exists(con, "gsc_keyword_inventory", "view"):
            raise RuntimeError("gsc_keyword_inventory view is not available")

        keywords = con.execute("""
            SELECT
                query AS keyword,
                ROUND(MIN(best_position), 1) AS best_ranking,
                ROUND(MIN(latest_position), 1) AS latest_ranking,
                SUM(impressions) AS impressions,
                SUM(clicks) AS clicks,
                MIN(first_seen) AS first_seen,
                MAX(last_seen) AS last_seen,
                COUNT(DISTINCT page) AS landing_pages
            FROM gsc_keyword_inventory
            WHERE site_id = ?
            GROUP BY query
            ORDER BY
                CASE WHEN MIN(latest_position) IS NULL THEN 1 ELSE 0 END,
                MIN(latest_position) ASC,
                query COLLATE NOCASE ASC
        """, (site["id"],)).fetchall()

        landing_pages = con.execute("""
            SELECT
                page AS landing_page,
                COUNT(DISTINCT query) AS keywords,
                SUM(impressions) AS impressions,
                SUM(clicks) AS clicks,
                ROUND(MIN(best_position), 1) AS best_ranking,
                ROUND(AVG(avg_position), 1) AS avg_ranking,
                MIN(first_seen) AS first_seen,
                MAX(last_seen) AS last_seen
            FROM gsc_keyword_inventory
            WHERE site_id = ?
            GROUP BY page
            ORDER BY impressions DESC, best_ranking ASC, landing_page ASC
        """, (site["id"],)).fetchall()

        page_keywords = con.execute("""
            SELECT
                page AS landing_page,
                query AS keyword,
                ROUND(best_position, 1) AS best_ranking,
                ROUND(avg_position, 1) AS avg_ranking,
                ROUND(latest_position, 1) AS latest_ranking,
                ROUND(worst_position, 1) AS worst_ranking,
                impressions,
                clicks,
                status,
                first_seen,
                last_seen
            FROM gsc_keyword_inventory
            WHERE site_id = ?
            ORDER BY landing_page ASC, latest_ranking ASC, keyword COLLATE NOCASE ASC
        """, (site["id"],)).fetchall()

    def csv_bytes(rows):
        buf = io.StringIO()
        if rows:
            writer = csv.DictWriter(buf, fieldnames=rows[0].keys())
            writer.writeheader()
            for row in rows:
                writer.writerow(dict(row))
        return buf.getvalue().encode("utf-8-sig")

    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("keywords.csv", csv_bytes(keywords))
        zf.writestr("landing-pages.csv", csv_bytes(landing_pages))
        zf.writestr("landing-page-keywords.csv", csv_bytes(page_keywords))

    archive.seek(0)
    return archive

def geo_engine_audit(url, page_type="auto"):
    return run_geo_aeo_audit(url, page_type)


def latest_audit_page(con,page_id):
    return con.execute(
        """SELECT ap.*,ar.id AS run_id,ar.completed_at,ar.status AS run_status
           FROM audit_page ap JOIN audit_run ar ON ar.id=ap.audit_run_id
           WHERE ap.page_id=? AND ar.status IN ('completed','partial')
           ORDER BY ar.id DESC LIMIT 1""",(page_id,)
    ).fetchone()


def recompute_domain_summary(con,run_id,domain):
    pages=con.execute("SELECT geo_score,aeo_score,combined_score FROM audit_page WHERE audit_run_id=?",(run_id,)).fetchall()
    def avg(name):
        vals=[r[name] for r in pages if r[name] is not None]
        return round(sum(vals)/len(vals)) if vals else None
    c=con.execute(
        """SELECT
        SUM(CASE WHEN s.observed_status='FAIL' THEN 1 ELSE 0 END) fail_count,
        SUM(CASE WHEN s.observed_status='PARTIAL' THEN 1 ELSE 0 END) partial_count,
        SUM(CASE WHEN s.observed_status='PASS' THEN 1 ELSE 0 END) pass_count,
        SUM(CASE WHEN s.observed_status='UNKNOWN' THEN 1 ELSE 0 END) unknown_count,
        SUM(CASE WHEN s.observed_status='MANUAL_REVIEW' THEN 1 ELSE 0 END) manual_count
        FROM audit_signal s JOIN audit_page p ON p.id=s.audit_page_id WHERE p.audit_run_id=?""",(run_id,)
    ).fetchone()
    now=datetime.now(timezone.utc).isoformat(timespec="seconds")
    con.execute(
        """INSERT INTO audit_domain_summary(
        audit_run_id,domain,pages_audited,geo_score,aeo_score,combined_score,
        fail_count,partial_count,pass_count,unknown_count,manual_count,created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(audit_run_id) DO UPDATE SET
        pages_audited=excluded.pages_audited,geo_score=excluded.geo_score,aeo_score=excluded.aeo_score,
        combined_score=excluded.combined_score,fail_count=excluded.fail_count,partial_count=excluded.partial_count,
        pass_count=excluded.pass_count,unknown_count=excluded.unknown_count,manual_count=excluded.manual_count""",
        (run_id,domain,len(pages),avg("geo_score"),avg("aeo_score"),avg("combined_score"),
         c["fail_count"] or 0,c["partial_count"] or 0,c["pass_count"] or 0,c["unknown_count"] or 0,c["manual_count"] or 0,now)
    )


def store_structured_audit(domain,run_id,page_id,url,report):
    now=datetime.now(timezone.utc).isoformat(timespec="seconds")
    capture=report.get("capture",{}); geo=report.get("geo",{}); aeo=report.get("aeo",{}); combined=report.get("combined",{})
    with research_db() as con:
        con.execute(
            """INSERT OR REPLACE INTO audit_page(
            audit_run_id,page_id,url,page_type,geo_score,aeo_score,combined_score,
            geo_json,aeo_json,combined_json,capture_json,created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (run_id,page_id,url,capture.get("page_type"),geo.get("score"),aeo.get("score"),combined.get("score"),
             json.dumps(geo),json.dumps(aeo),json.dumps(combined),json.dumps(capture),now)
        )
        ap=con.execute("SELECT id FROM audit_page WHERE audit_run_id=? AND page_id=?",(run_id,page_id)).fetchone()
        audit_page_id=ap["id"]
        con.execute("DELETE FROM audit_signal WHERE audit_page_id=?",(audit_page_id,))
        for item in report.get("findings",[]):
            con.execute(
                """INSERT INTO audit_signal(
                audit_page_id,family,signal_key,category,title,observed_status,severity,
                weight,evidence,recommendation,source_title,source_url)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (audit_page_id,item.get("family",""),item.get("id",""),item.get("category",""),item.get("title",""),
                 item.get("status",""),item.get("severity",""),item.get("weight",0) or 0,item.get("evidence",""),
                 item.get("recommendation",""),item.get("source_title",""),item.get("source_url",""))
            )
        recompute_domain_summary(con,run_id,domain)
        con.commit()


def audit_worker(domain,run_id,pages):
    errors=[]
    for page in pages:
        try:
            store_structured_audit(domain,run_id,page["id"],page["url"],geo_engine_audit(page["url"]))
        except Exception as exc:
            errors.append(f'{page["url"]}: {exc}')
    status="completed" if not errors else ("partial" if len(errors)<len(pages) else "failed")
    now=datetime.now(timezone.utc).isoformat(timespec="seconds")
    with research_db() as con:
        con.execute("UPDATE audit_run SET status=?,completed_at=?,error=? WHERE id=?",(status,now,"\n".join(errors),run_id))
        recompute_domain_summary(con,run_id,domain)
        con.commit()


def start_audit_run(domain,pages,scope):
    # PB_AUDIT_ZERO_PAGE_FALLBACK
    if not pages:
        try:
            sync_site_pages(domain)
            with research_db() as _con:
                pages = _con.execute("SELECT id,url,path FROM site_page WHERE domain=? ORDER BY path COLLATE NOCASE", (domain,)).fetchall()
        except Exception:
            pages = pages or []
    if not pages:
        pages = [{"id": None, "url": "https://" + domain.rstrip("/") + "/", "path": "/"}]
    now=datetime.now(timezone.utc).isoformat(timespec="seconds")
    with research_db() as con:
        cur=con.execute("INSERT INTO audit_run(domain,scope,status,started_at) VALUES (?,?,?,?)",(domain,scope,"running",now))
        run_id=cur.lastrowid
        con.commit()
    threading.Thread(target=audit_worker,args=(domain,run_id,[dict(x) for x in pages]),daemon=True).start()
    return run_id

def report_files(domain: str | None = None):
    if not REPORTS_DIR.exists():
        return []
    out = []
    for p in REPORTS_DIR.iterdir():
        if not p.is_file():
            continue
        if p.suffix.lower() not in {".pdf", ".md", ".json", ".html", ".txt"}:
            continue
        if domain and domain.lower() not in p.name.lower():
            # Keep generic GEO/AEO reports visible too; domain matching gets priority.
            score = 1
        else:
            score = 0
        out.append((score, p.stat().st_mtime, p.name))
    out.sort(key=lambda x: (x[0], -x[1], x[2].lower()))
    return [x[2] for x in out]



def normalize_dashboard_domain(value):
    value=(value or "").strip()
    if not value:
        return None,None
    if value.lower().startswith("sc-domain:"):
        value=value.split(":",1)[1].strip()
    if "://" not in value:
        value="https://"+value
    try:
        parsed=urllib.parse.urlsplit(value)
    except Exception:
        return None,None
    host=(parsed.hostname or "").strip().lower()
    if not host or "." not in host:
        return None,None
    return host,"https://"+host


def _site_value(site,key,default=None):
    try:
        return site[key]
    except Exception:
        pass
    try:
        return getattr(site,key)
    except Exception:
        return default


def _opengsc_site_domain(site):
    for key in ("domain","url","siteUrl","site_url","property"):
        value=_site_value(site,key)
        if not value:
            continue
        domain,_=normalize_dashboard_domain(str(value))
        if domain:
            return domain
    return None


def sync_dashboard_domains_from_opengsc():
    with research_db() as _suppression_con:
        _suppression_con.execute("""
            CREATE TABLE IF NOT EXISTS domain_suppression (
                domain TEXT PRIMARY KEY COLLATE NOCASE,
                suppressed_at TEXT NOT NULL
            )
        """)
        _suppressed_domains = {
            r["domain"].lower()
            for r in _suppression_con.execute("SELECT domain FROM domain_suppression").fetchall()
        }
        _suppression_con.commit()
    now=datetime.now(timezone.utc).isoformat(timespec="seconds")
    try:
        gsc_sites=_opengsc_get_sites()
    except Exception:
        gsc_sites=[]
    with research_db() as con:
        for gsc in gsc_sites:
            domain=_opengsc_site_domain(gsc)
            gsc_id=_site_value(gsc,"id")
            if not domain or not gsc_id:
                continue
            if domain.lower() in _suppressed_domains:
                continue
            con.execute(
                """INSERT INTO dashboard_domain(domain,base_url,gsc_site_id,created_at,updated_at)
                   VALUES (?,?,?,?,?)
                   ON CONFLICT(domain) DO UPDATE SET
                     gsc_site_id=excluded.gsc_site_id,
                     base_url=excluded.base_url,
                     updated_at=excluded.updated_at""",
                (domain,"https://"+domain,str(gsc_id),now,now)
            )
        con.commit()


def get_sites():
    sync_dashboard_domains_from_opengsc()
    with research_db() as con:
        rows=con.execute(
            "SELECT id,domain,base_url,gsc_site_id FROM dashboard_domain ORDER BY domain COLLATE NOCASE"
        ).fetchall()
    return [{
        "id":r["gsc_site_id"] or f"__GSC_MISSING__:{r['domain']}",
        "dashboard_domain_id":r["id"],
        "domain":r["domain"],
        "base_url":r["base_url"],
        "gsc_site_id":r["gsc_site_id"],
        "gsc_missing":not bool(r["gsc_site_id"]),
    } for r in rows]


def get_site(domain):
    wanted,_=normalize_dashboard_domain(domain)
    if not wanted:
        abort(404)
    sync_dashboard_domains_from_opengsc()
    with research_db() as con:
        r=con.execute(
            "SELECT id,domain,base_url,gsc_site_id FROM dashboard_domain WHERE domain=? COLLATE NOCASE",
            (wanted,)
        ).fetchone()
    if not r:
        abort(404)
    return {
        "id":r["gsc_site_id"] or f"__GSC_MISSING__:{r['domain']}",
        "dashboard_domain_id":r["id"],
        "domain":r["domain"],
        "base_url":r["base_url"],
        "gsc_site_id":r["gsc_site_id"],
        "gsc_missing":not bool(r["gsc_site_id"]),
    }


def create_dashboard_domain(value):
    domain,base_url=normalize_dashboard_domain(value)
    if not domain:
        raise ValueError("Enter a valid domain, for example example.com.")
    now=datetime.now(timezone.utc).isoformat(timespec="seconds")
    sync_dashboard_domains_from_opengsc()
    with research_db() as con:
        existing=con.execute(
            "SELECT id FROM dashboard_domain WHERE domain=? COLLATE NOCASE",(domain,)
        ).fetchone()
        if existing:
            return domain,False
        con.execute(
            "INSERT INTO dashboard_domain(domain,base_url,gsc_site_id,created_at,updated_at) VALUES (?,?,NULL,?,?)",
            (domain,base_url,now,now)
        )
        con.commit()
    sync_dashboard_domains_from_opengsc()
    return domain,True


@app.route("/")
def index():
    sites = get_sites()
    if not sites:
        return render_template("empty.html")
    return redirect(url_for("overview", domain=sites[0]["domain"]))



@app.route("/domains/new",methods=["GET","POST"])
def domain_new():
    message=request.args.get("message","").strip()

    if request.method=="POST":
        raw=request.form.get("domain","").strip()
        try:
            domain,created=create_dashboard_domain(raw)
        except ValueError as exc:
            return render_template("domain_new.html",sites=get_sites(),site=None,message=str(exc))

        sitemap_message=""
        if created:
            try:
                sitemap_count,ranking_count,source=sync_site_pages(domain)
                sitemap_message=f" Added {sitemap_count} sitemap page(s)."
            except Exception as exc:
                sitemap_message=f" Domain added; sitemap discovery failed: {exc}"

        site=get_site(domain)
        gsc_message=" GSC linked." if not site["gsc_missing"] else " GSC missing; SEO ranking fields will remain empty."

        ensure_domain_ready(domain)
        return redirect(url_for("domain_sources",domain=domain,message=("Domain added." if created else "Domain already exists.")+" Select any additional data sources, then continue to Reports."))

    return render_template("domain_new.html",sites=get_sites(),site=None,message=message)


@app.route("/d/<domain>/sources",methods=["GET","POST"])
def domain_sources(domain):
    site=get_site(domain); readiness=ensure_domain_ready(domain); message=request.args.get("message","").strip()
    if request.method=="POST":
        selected=set(request.form.getlist("selected")); custom_name=request.form.get("custom_name","").strip(); custom_detail=request.form.get("custom_detail","").strip(); now=datetime.now(timezone.utc).isoformat(timespec="seconds"); detected=detected_source_state(site)
        with research_db() as con:
            ensure_domain_source_schema(con)
            for key,name,_ in SOURCE_CATALOG:
                connected=bool(detected.get(key,{}).get("connected"))
                con.execute("INSERT INTO domain_source(domain,source_key,source_name,selected,connection_status,detail,updated_at) VALUES (?,?,?,?,?,?,?) ON CONFLICT(domain,source_key) DO UPDATE SET source_name=excluded.source_name,selected=excluded.selected,connection_status=excluded.connection_status,detail=CASE WHEN excluded.detail<>'' THEN excluded.detail ELSE domain_source.detail END,updated_at=excluded.updated_at",(domain,key,name,int(key in selected or connected),"connected" if connected else "not_connected",detected.get(key,{}).get("detail",""),now))
            if custom_name:
                custom_key="custom_"+re.sub(r"[^a-z0-9]+","_",custom_name.lower()).strip("_")
                if custom_key=="custom_": custom_key="custom_source"
                con.execute("INSERT INTO domain_source(domain,source_key,source_name,selected,connection_status,detail,updated_at) VALUES (?,?,?,1,'not_connected',?,?) ON CONFLICT(domain,source_key) DO UPDATE SET source_name=excluded.source_name,selected=1,detail=excluded.detail,updated_at=excluded.updated_at",(domain,custom_key,custom_name,custom_detail,now))
            con.commit()
        return redirect(url_for("domain_sources",domain=domain,message="Sources saved. Domain is ready to run reports."))
    return render_template("sources.html",sites=get_sites(),site=site,sources=domain_sources_for_site(site),readiness=readiness,message=message)

@app.route("/d/<domain>/sources/manual-ai", methods=["GET", "POST"])
def manual_ai_source(domain):
    site=get_site(domain); message=request.args.get("message","").strip()
    if request.method=="POST":
        current=load_manual_ai_source(domain); prompts={}; responses={}
        for phase in ("phase1","phase2"):
            for state in ("state1","state2"):
                prefix=f"{phase}_{state}"; prompts[prefix]=request.form.get(f"{prefix}_prompt_text","")
                for provider in ("chatgpt","claude","gemini"):
                    key=f"{prefix}_{provider}"; uploaded=_manual_ai_upload_text(f"{key}_upload"); pasted=request.form.get(f"{key}_response","")
                    responses[key]=uploaded if uploaded is not None else pasted
        old_prompts=tuple(str(current.get(f"{p}_{s}_prompt_text") or "") for p in ("phase1","phase2") for s in ("state1","state2"))
        new_prompts=tuple(prompts[f"{p}_{s}"] for p in ("phase1","phase2") for s in ("state1","state2"))
        version=int(current.get("question_set_version") or 1)+(1 if old_prompts!=new_prompts else 0)
        now=datetime.now(timezone.utc).isoformat(timespec="seconds")
        with research_db() as con:
            ensure_manual_ai_source_schema(con)
            con.execute("INSERT INTO manual_ai_source(domain,question_set_version,analysis_model,analysis_system_prompt,analysis_text,analysis_status,analysis_error,analysis_updated_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?) ON CONFLICT(domain) DO UPDATE SET question_set_version=excluded.question_set_version,updated_at=excluded.updated_at",(domain,version,current.get("analysis_model") or "",current.get("analysis_system_prompt") or DEFAULT_ANALYSIS_SYSTEM_PROMPT,current.get("analysis_text") or "",current.get("analysis_status") or "not_run",current.get("analysis_error") or "",current.get("analysis_updated_at") or "",now))
            for phase in ("phase1","phase2"):
                for state in ("state1","state2"):
                    prefix=f"{phase}_{state}"
                    con.execute("INSERT INTO manual_ai_state_source(domain,phase,state,prompt_text,chatgpt_response,claude_response,gemini_response,updated_at) VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(domain,phase,state) DO UPDATE SET prompt_text=excluded.prompt_text,chatgpt_response=excluded.chatgpt_response,claude_response=excluded.claude_response,gemini_response=excluded.gemini_response,updated_at=excluded.updated_at",(domain,phase,state,prompts[prefix],responses[f"{prefix}_chatgpt"],responses[f"{prefix}_claude"],responses[f"{prefix}_gemini"],now))
            ensure_domain_source_schema(con)
            con.execute("INSERT INTO domain_source(domain,source_key,source_name,selected,connection_status,detail,updated_at) VALUES (?,?,?,1,'not_connected',?,?) ON CONFLICT(domain,source_key) DO UPDATE SET source_name=excluded.source_name,selected=1,detail=excluded.detail,updated_at=excluded.updated_at",(domain,"manual_ai","Manual AI Responses",f"Four-state Manual AI source · question-set v{version}",now))
            con.commit()
        return redirect(url_for("manual_ai_source",domain=domain,message=f"Saved question-set v{version}: 2 phases × 2 states."))
    return render_template("manual_ai_responses.html",sites=get_sites(),site=site,state=load_manual_ai_source(domain),message=message)


@app.post("/d/<domain>/sources/manual-ai/analyze")
def manual_ai_source_analyze(domain):
    get_site(domain); source=load_manual_ai_source(domain); model=request.form.get("analysis_model","").strip(); system_prompt=request.form.get("analysis_system_prompt","").strip(); now=datetime.now(timezone.utc).isoformat(timespec="seconds")
    try: analysis=run_manual_ai_analysis(source,model,system_prompt); status="success"; error=""
    except Exception as exc: analysis=source.get("analysis_text") or ""; status="error"; error=str(exc)
    with research_db() as con:
        ensure_manual_ai_source_schema(con); con.execute("UPDATE manual_ai_source SET analysis_model=?,analysis_system_prompt=?,analysis_text=?,analysis_status=?,analysis_error=?,analysis_updated_at=?,updated_at=? WHERE domain=? COLLATE NOCASE",(model,system_prompt,analysis,status,error,now,now,domain)); con.commit()
    msg="AI response analysis completed." if status=="success" else f"Analysis failed: {error}"
    return redirect(url_for("manual_ai_source",domain=domain,message=msg))


@app.route("/d/<domain>/tools")
def tools(domain):
    site=get_site(domain)
    return render_template("tools.html",sites=get_sites(),site=site)



@app.post("/d/<domain>/settings/company-controlled-domains")
def save_company_controlled_domains(domain):
    get_site(domain)
    raw = request.form.get("company_controlled_domains", "")
    values = [line.strip() for line in raw.splitlines() if line.strip()]
    with research_db() as con:
        save_controlled_domains(con, domain, values)
    return redirect(url_for("domain_settings", domain=domain, message="Company-controlled domains saved."))

@app.route("/d/<domain>/settings", methods=["GET", "POST"])
def domain_settings(domain):
    site = get_site(domain)
    message = request.args.get("message", "").strip()

    if request.method == "POST":
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        company_name = request.form.get("company_name", "").strip() or infer_company_name(domain)
        valid_family_ids = {f["id"] for f in REPORT_FAMILY_SETTINGS}

        with research_db() as con:
            ensure_report_question_schema(con)
            ensure_domain_company_schema(con)

            con.execute(
                "INSERT INTO domain_company_settings(domain,company_name,updated_at) "
                "VALUES (?,?,?) "
                "ON CONFLICT(domain) DO UPDATE SET "
                "company_name=excluded.company_name,updated_at=excluded.updated_at",
                (domain, company_name, now),
            )

            placeholders = ",".join("?" for _ in valid_family_ids)
            con.execute(
                f"DELETE FROM domain_family_question WHERE domain=? COLLATE NOCASE "
                f"AND (family_id NOT IN ({placeholders}) OR question_slot NOT IN (1,2))",
                (domain, *sorted(valid_family_ids)),
            )

            defaults = {
                family_id: {
                    index + 1: q.replace("[Company]", company_name)
                    for index, q in enumerate(REPORT_FAMILY_DEFAULT_QUESTIONS[family_id])
                }
                for family_id in valid_family_ids
            }

            for family_id in valid_family_ids:
                for slot in (1, 2):
                    value = request.form.get(f"q_{family_id}_{slot}", "").strip()
                    if not value:
                        value = defaults[family_id][slot]
                    con.execute(
                        "INSERT INTO domain_family_question(domain,family_id,question_slot,question_text,updated_at) "
                        "VALUES (?,?,?,?,?) "
                        "ON CONFLICT(domain,family_id,question_slot) DO UPDATE SET "
                        "question_text=excluded.question_text,updated_at=excluded.updated_at",
                        (domain, family_id, slot, value, now),
                    )
            con.commit()

        return redirect(url_for("domain_settings", domain=domain, message="Domain questions saved."))

    return render_template(
        "domain_settings.html",
        sites=get_sites(),
        site=site,
        families=REPORT_FAMILY_SETTINGS,
        questions=effective_domain_family_questions(domain),
        company_name=infer_company_name(domain),
        message=message,
        company_controlled_domains='\n'.join(controlled_domains(research_db(), domain)[1:]),
    )

@app.route("/d/<domain>/")
def overview(domain):
    site = get_site(domain)
    summary, recent = domain_seo(site["id"])
    return render_template("overview.html",sites=get_sites(),site=site,summary=summary,recent=recent,reports=report_files(domain)[:5],readiness=ensure_domain_ready(domain),sources=domain_sources_for_site(site))


@app.route("/d/<domain>/pages")
def pages(domain):
    site = get_site(domain)
    q = request.args.get("q", "").strip()
    message = request.args.get("message", "").strip()

    with research_db() as con:
        count = con.execute("SELECT COUNT(*) AS n FROM site_page WHERE domain=?", (domain,)).fetchone()["n"]
    if count == 0:
        try:
            sync_site_pages(domain)
        except Exception as exc:
            if not message:
                message = f"Initial sitemap sync failed: {exc}"

    ranking_counts = {}
    for row in gsc_rows_for_domain(domain):
        normalized = normalize_site_page_url(row["page"], domain)
        if normalized:
            ranking_counts[normalized] = ranking_counts.get(normalized, 0) + 1

    with research_db() as con:
        wanted_counts = {row["page_id"]: row["n"] for row in con.execute(
            "SELECT page_id,COUNT(*) AS n FROM wanted_keyword WHERE page_id IS NOT NULL GROUP BY page_id"
        ).fetchall()}
        note_ids = {row["page_id"] for row in con.execute(
            "SELECT page_id FROM page_note WHERE TRIM(content)<>''"
        ).fetchall()}
        where = "WHERE domain=?"
        params = [domain]
        if q:
            where += " AND (path REGEXP ? OR url REGEXP ?)"
            params += [f"%{q}%", f"%{q}%"]
        page_rows = con.execute(f"SELECT id,url,path,source FROM site_page {where} ORDER BY path COLLATE NOCASE", params).fetchall()
        total = con.execute("SELECT COUNT(*) AS n FROM site_page WHERE domain=?", (domain,)).fetchone()["n"]

    rows = [{
        "id": r["id"], "url": r["url"], "path": r["path"], "source": r["source"],
        "ranking_count": ranking_counts.get(r["url"], 0),
        "wanted_count": wanted_counts.get(r["id"], 0),
        "has_note": r["id"] in note_ids,
    } for r in page_rows]

    return render_template("pages.html", sites=get_sites(), site=site, rows=rows, total=total, q=q, message=message)



@app.route("/d/<domain>/page")
def page(domain):
    site = get_site(domain)
    page_url = request.args.get("url", "").strip()
    if not page_url:
        abort(400)
    keywords, summary = page_detail(site["id"], page_url)
    return render_template(
        "page.html",
        sites=get_sites(),
        site=site,
        page_url=page_url,
        keywords=keywords,
        summary=summary,
    )



@app.route("/d/<domain>/keywords-dashboard")
def keywords_dashboard(domain):
    site = get_site(domain)
    return render_template("keywords_dashboard.html", sites=get_sites(), site=site)



@app.route("/d/<domain>/keywords")
def keywords(domain):
    site = get_site(domain)
    return render_template(
        "keywords.html",
        sites=get_sites(),
        site=site,
        rows=keyword_rows(site["id"]),
    )


@app.route("/d/<domain>/export")
def export_domain(domain):
    site = get_site(domain)

    try:
        archive = build_domain_export(site)
    except RuntimeError as exc:
        return str(exc), 409

    return send_file(
        archive,
        mimetype="application/zip",
        as_attachment=True,
        download_name=f"{domain}-seo-export.zip",
    )




@app.route("/d/<domain>/wanted")
def wanted(domain):
    site = get_site(domain)
    q = request.args.get("q", "").strip()
    sort = request.args.get("sort", "keyword")
    direction = request.args.get("dir", "asc").lower()
    show_tags = request.args.getlist("show_tag")
    hide_tags = request.args.getlist("hide_tag")

    try:
        per_page = int(request.args.get("per_page", "50"))
    except ValueError:
        per_page = 50
    if per_page not in {25, 50, 100, 250, 1000}:
        per_page = 50

    try:
        page = max(1, int(request.args.get("page", "1")))
    except ValueError:
        page = 1

    if sort not in {"keyword", "searches", "competition"}:
        sort = "keyword"
    if direction not in {"asc", "desc"}:
        direction = "asc"

    order_map = {
        "keyword": "w.keyword COLLATE NOCASE",
        "searches": "w.avg_monthly_searches",
        "competition": "CASE LOWER(COALESCE(w.competition,'')) WHEN 'low' THEN 1 WHEN 'medium' THEN 2 WHEN 'mid' THEN 2 WHEN 'high' THEN 3 ELSE 4 END",
    }

    conditions = ["w.domain = ?"]
    params = [domain]

    if q:
        conditions.append("w.keyword REGEXP ?")
        params.append(q)

    show_real = [x for x in show_tags if x != "__untagged__" and x.isdigit()]
    hide_real = [x for x in hide_tags if x != "__untagged__" and x.isdigit()]
    show_untagged = "__untagged__" in show_tags
    hide_untagged = "__untagged__" in hide_tags

    if show_real or show_untagged:
        parts = []
        if show_real:
            ph = ",".join("?" for _ in show_real)
            parts.append(
                f"EXISTS (SELECT 1 FROM wanted_keyword_tag wt WHERE wt.wanted_keyword_id=w.id AND wt.tag_id IN ({ph}))"
            )
            params.extend(int(x) for x in show_real)
        if show_untagged:
            parts.append(
                "NOT EXISTS (SELECT 1 FROM wanted_keyword_tag wt WHERE wt.wanted_keyword_id=w.id)"
            )
        conditions.append("(" + " OR ".join(parts) + ")")

    if hide_real:
        ph = ",".join("?" for _ in hide_real)
        conditions.append(
            f"NOT EXISTS (SELECT 1 FROM wanted_keyword_tag wt WHERE wt.wanted_keyword_id=w.id AND wt.tag_id IN ({ph}))"
        )
        params.extend(int(x) for x in hide_real)

    if hide_untagged:
        conditions.append(
            "EXISTS (SELECT 1 FROM wanted_keyword_tag wt WHERE wt.wanted_keyword_id=w.id)"
        )

    where = "WHERE " + " AND ".join(conditions)
    order = order_map[sort]
    direction_sql = "ASC" if direction == "asc" else "DESC"

    tags_expr = "(SELECT GROUP_CONCAT(tag_name,'||') FROM (SELECT t.name AS tag_name FROM wanted_keyword_tag wt JOIN keyword_tag t ON t.id=wt.tag_id WHERE wt.wanted_keyword_id=w.id ORDER BY t.name COLLATE NOCASE))"

    with research_db() as con:
        tags = con.execute(
            "SELECT id,name FROM keyword_tag WHERE domain=? ORDER BY name COLLATE NOCASE",
            (domain,),
        ).fetchall()

        page_options = con.execute(
            "SELECT id,path,url FROM site_page WHERE domain=? ORDER BY path COLLATE NOCASE",
            (domain,),
        ).fetchall()

        total = con.execute(
            "SELECT COUNT(*) AS n FROM wanted_keyword WHERE domain=?",
            (domain,),
        ).fetchone()["n"]

        filtered = con.execute(
            f"SELECT COUNT(*) AS n FROM wanted_keyword w {where}",
            params,
        ).fetchone()["n"]

        pages = max(1, (filtered + per_page - 1) // per_page)
        page = min(page, pages)
        offset = (page - 1) * per_page

        rows = con.execute(
            f"SELECT w.id,w.keyword,w.avg_monthly_searches,w.competition,w.source,w.page_id,w.created_at,w.updated_at,{tags_expr} AS tags FROM wanted_keyword w {where} ORDER BY {order} {direction_sql},w.keyword COLLATE NOCASE ASC LIMIT ? OFFSET ?",
            [*params, per_page, offset],
        ).fetchall()

    return render_template(
        "wanted.html",
        sites=get_sites(),
        site=site,
        rows=rows,
        page_options=page_options,
        tags=tags,
        show_tags=show_tags,
        hide_tags=hide_tags,
        total=total,
        filtered_total=filtered,
        q=q,
        sort=sort,
        direction=direction,
        page=page,
        pages=pages,
        per_page=per_page,
        start_index=(offset + 1 if filtered else 0),
        message=request.args.get("message", "").strip(),
    )



@app.post("/d/<domain>/wanted/add")
def wanted_add(domain):
    get_site(domain); keyword=request.form.get("keyword","").strip()
    if not keyword: return redirect(url_for("wanted",domain=domain,message="Keyword cannot be empty."))
    now=datetime.now(timezone.utc).isoformat(timespec="seconds")
    with research_db() as con:
        try:
            con.execute("INSERT INTO wanted_keyword(domain,keyword,source,created_at,updated_at) VALUES (?,?,'manual',?,?)",(domain,keyword,now,now)); con.commit(); msg="Wanted keyword added."
        except sqlite3.IntegrityError: msg="That keyword is already in Wanted."
    return redirect(url_for("wanted",domain=domain,message=msg))

@app.post("/d/<domain>/wanted/<int:keyword_id>/delete")
def wanted_delete(domain, keyword_id):
    get_site(domain)
    with research_db() as con:
        con.execute("DELETE FROM wanted_keyword WHERE id=? AND domain=?",(keyword_id,domain)); con.commit()
    return redirect(url_for("wanted",domain=domain,message="Wanted keyword deleted."))

@app.post("/d/<domain>/research/<int:keyword_id>/save")
def research_save(domain,keyword_id):
    get_site(domain); now=datetime.now(timezone.utc).isoformat(timespec="seconds")
    with research_db() as con:
        row=con.execute("SELECT id,keyword,avg_monthly_searches,competition FROM research_keyword WHERE id=? AND domain=?",(keyword_id,domain)).fetchone()
        if not row: return research_redirect(domain,"Research keyword not found.",request.form)
        move_research_keyword_to_wanted(con,domain,row,now); con.commit()
    return research_redirect(domain,f'Moved "{row["keyword"]}" to Wanted. Tags preserved.',request.form)


@app.route("/d/<domain>/research")
def research(domain):
    site=get_site(domain); q=request.args.get("q","").strip(); sort=request.args.get("sort","keyword"); direction=request.args.get("dir","asc").lower(); show_tags=request.args.getlist("show_tag"); hide_tags=request.args.getlist("hide_tag")
    try: per_page=int(request.args.get("per_page","50"))
    except ValueError: per_page=50
    if per_page not in {25,50,100,250,1000}: per_page=50
    try: page=max(1,int(request.args.get("page","1")))
    except ValueError: page=1
    if sort not in {"keyword","searches","competition","tag"}: sort="keyword"
    if direction not in {"asc","desc"}: direction="asc"
    conditions=["k.domain=?"]; params=[domain]
    if q: conditions.append("k.keyword REGEXP ?"); params.append(q)
    show_real=[x for x in show_tags if x!="__untagged__" and x.isdigit()]; hide_real=[x for x in hide_tags if x!="__untagged__" and x.isdigit()]
    if show_real or "__untagged__" in show_tags:
        parts=[]
        if show_real:
            ph=','.join('?' for _ in show_real); parts.append(f"EXISTS (SELECT 1 FROM research_keyword_tag rt WHERE rt.research_keyword_id=k.id AND rt.tag_id IN ({ph}))"); params.extend(int(x) for x in show_real)
        if "__untagged__" in show_tags: parts.append("NOT EXISTS (SELECT 1 FROM research_keyword_tag rt WHERE rt.research_keyword_id=k.id)")
        conditions.append('('+ ' OR '.join(parts) +')')
    if hide_real:
        ph=','.join('?' for _ in hide_real); conditions.append(f"NOT EXISTS (SELECT 1 FROM research_keyword_tag rt WHERE rt.research_keyword_id=k.id AND rt.tag_id IN ({ph}))"); params.extend(int(x) for x in hide_real)
    if "__untagged__" in hide_tags: conditions.append("EXISTS (SELECT 1 FROM research_keyword_tag rt WHERE rt.research_keyword_id=k.id)")
    where='WHERE '+' AND '.join(conditions)
    competition="CASE LOWER(COALESCE(k.competition,'')) WHEN 'low' THEN 1 WHEN 'medium' THEN 2 WHEN 'mid' THEN 2 WHEN 'high' THEN 3 ELSE 4 END"
    first_tag="COALESCE((SELECT MIN(t.name) FROM research_keyword_tag rt JOIN keyword_tag t ON t.id=rt.tag_id WHERE rt.research_keyword_id=k.id),'')"
    order={"keyword":"k.keyword COLLATE NOCASE","searches":"k.avg_monthly_searches","competition":competition,"tag":first_tag+" COLLATE NOCASE"}[sort]; direction_sql='ASC' if direction=='asc' else 'DESC'
    tags_expr="(SELECT GROUP_CONCAT(tag_name,'||') FROM (SELECT t.name AS tag_name FROM research_keyword_tag rt JOIN keyword_tag t ON t.id=rt.tag_id WHERE rt.research_keyword_id=k.id ORDER BY t.name COLLATE NOCASE))"
    with research_db() as con:
        tags=con.execute("SELECT id,name FROM keyword_tag WHERE domain=? ORDER BY name COLLATE NOCASE",(domain,)).fetchall(); total=con.execute("SELECT COUNT(*) n FROM research_keyword WHERE domain=?",(domain,)).fetchone()["n"]; filtered=con.execute(f"SELECT COUNT(*) n FROM research_keyword k {where}",params).fetchone()["n"]
        pages=max(1,(filtered+per_page-1)//per_page); page=min(page,pages); offset=(page-1)*per_page
        rows=con.execute(f"SELECT k.id,k.keyword,k.avg_monthly_searches,k.competition,k.created_at,k.updated_at,{tags_expr} AS tags FROM research_keyword k {where} ORDER BY {order} {direction_sql},k.keyword COLLATE NOCASE ASC,k.id ASC LIMIT ? OFFSET ?",[*params,per_page,offset]).fetchall()
    return render_template("research.html",sites=get_sites(),site=site,rows=rows,tags=tags,total=total,filtered_total=filtered,q=q,sort=sort,direction=direction,show_tags=show_tags,hide_tags=hide_tags,page=page,pages=pages,per_page=per_page,start_index=(offset+1 if filtered else 0),end_index=min(offset+len(rows),filtered),message=request.args.get("message","").strip(),next_keyword_dir=("desc" if sort=="keyword" and direction=="asc" else "asc"),next_searches_dir=("desc" if sort=="searches" and direction=="asc" else "asc"),next_competition_dir=("desc" if sort=="competition" and direction=="asc" else "asc"),next_tag_dir=("desc" if sort=="tag" and direction=="asc" else "asc"))


@app.post("/d/<domain>/research/bulk-save")
def research_bulk_save(domain):
    get_site(domain); scope=request.form.get("scope","selected")
    with research_db() as con:
        if scope=="all": rows=con.execute("SELECT id,keyword,avg_monthly_searches,competition FROM research_keyword WHERE domain=? ORDER BY id",(domain,)).fetchall()
        else:
            ids=[]
            for value in request.form.getlist("keyword_ids"):
                try: ids.append(int(value))
                except (TypeError,ValueError): pass
            if not ids: return research_redirect(domain,"No keywords were selected.",request.form)
            ph=','.join('?' for _ in ids); rows=con.execute(f"SELECT id,keyword,avg_monthly_searches,competition FROM research_keyword WHERE domain=? AND id IN ({ph}) ORDER BY id",[domain,*ids]).fetchall()
        now=datetime.now(timezone.utc).isoformat(timespec="seconds")
        for row in rows: move_research_keyword_to_wanted(con,domain,row,now)
        con.commit()
    return research_redirect(domain,f"Moved {len(rows)} keyword(s) to Wanted. Tags preserved.",request.form)


@app.post("/d/<domain>/research/bulk-tag")
def research_bulk_tag(domain):
    get_site(domain); scope=request.form.get("scope","selected"); action=request.form.get("tag_action","add"); tag_id_raw=request.form.get("tag_id","").strip(); new_tag=normalize_tag_name(request.form.get("new_tag",""))
    with research_db() as con:
        if scope=="all": ids=[r["id"] for r in con.execute("SELECT id FROM research_keyword WHERE domain=?",(domain,)).fetchall()]
        else:
            ids=[]
            for value in request.form.getlist("keyword_ids"):
                try: ids.append(int(value))
                except (TypeError,ValueError): pass
        if not ids: return research_redirect(domain,"No keywords were selected.",request.form)
        tag_id=None
        if action=="add" and new_tag:
            now=datetime.now(timezone.utc).isoformat(timespec="seconds"); con.execute("INSERT OR IGNORE INTO keyword_tag(domain,name,created_at) VALUES (?,?,?)",(domain,new_tag,now)); tag_id=con.execute("SELECT id FROM keyword_tag WHERE domain=? AND name=? COLLATE NOCASE",(domain,new_tag)).fetchone()["id"]
        elif tag_id_raw.isdigit():
            row=con.execute("SELECT id FROM keyword_tag WHERE id=? AND domain=?",(int(tag_id_raw),domain)).fetchone(); tag_id=row["id"] if row else None
        if tag_id is None: return research_redirect(domain,"Choose an existing tag or enter a new tag.",request.form)
        if action=="add": con.executemany("INSERT OR IGNORE INTO research_keyword_tag(research_keyword_id,tag_id) VALUES (?,?)",[(i,tag_id) for i in ids]); verb='Added'
        else: con.executemany("DELETE FROM research_keyword_tag WHERE research_keyword_id=? AND tag_id=?",[(i,tag_id) for i in ids]); verb='Removed'
        name=con.execute("SELECT name FROM keyword_tag WHERE id=?",(tag_id,)).fetchone()["name"]; con.commit()
    return research_redirect(domain,f'{verb} tag "{name}" for {len(ids)} keyword(s).',request.form)

@app.post("/d/<domain>/research/bulk-delete")
def research_bulk_delete(domain):
    get_site(domain); scope=request.form.get("scope","selected")
    with research_db() as con:
        if scope=="all": ids=[r["id"] for r in con.execute("SELECT id FROM research_keyword WHERE domain=?",(domain,)).fetchall()]
        else:
            ids=[]
            for value in request.form.getlist("keyword_ids"):
                try: ids.append(int(value))
                except (TypeError,ValueError): pass
        if not ids: return research_redirect(domain,"No keywords were selected.",request.form)
        ph=','.join('?' for _ in ids); con.execute(f"DELETE FROM research_keyword_tag WHERE research_keyword_id IN ({ph})",ids); con.execute(f"DELETE FROM research_keyword WHERE domain=? AND id IN ({ph})",[domain,*ids]); con.commit()
    return research_redirect(domain,f"Deleted {len(ids)} research keyword(s).",request.form)


@app.post("/d/<domain>/research/upload")
def research_upload(domain):
    get_site(domain)
    upload = request.files.get("file")
    if not upload or not upload.filename:
        return redirect(url_for("research", domain=domain, message="Choose a CSV file first."))

    records = parse_keyword_csv_enriched(upload.read())
    if not records:
        return redirect(url_for("research", domain=domain, message="No keywords were found in that CSV."))

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    added = updated = 0
    with research_db() as con:
        for record in records:
            existing = con.execute(
                "SELECT id FROM research_keyword WHERE domain=? AND keyword=? COLLATE NOCASE",
                (domain, record["keyword"]),
            ).fetchone()
            if existing:
                con.execute(
                    """UPDATE research_keyword
                       SET avg_monthly_searches=COALESCE(?,avg_monthly_searches),
                           competition=COALESCE(?,competition),
                           updated_at=?
                       WHERE id=?""",
                    (record["avg_monthly_searches"], record["competition"], now, existing["id"]),
                )
                updated += 1
            else:
                con.execute(
                    """INSERT INTO research_keyword
                       (domain,keyword,avg_monthly_searches,competition,created_at,updated_at)
                       VALUES (?,?,?,?,?,?)""",
                    (domain, record["keyword"], record["avg_monthly_searches"], record["competition"], now, now),
                )
                added += 1
        con.commit()

    return redirect(url_for("research", domain=domain, message=f"Imported {added} new keyword(s). Updated {updated} existing keyword(s)."))


@app.post("/d/<domain>/research/<int:keyword_id>/edit")
def research_edit(domain,keyword_id):
    get_site(domain); keyword=request.form.get("keyword","").strip()
    if not keyword: return redirect(url_for("research",domain=domain,message="Keyword cannot be empty."))
    now=datetime.now(timezone.utc).isoformat(timespec="seconds")
    with research_db() as con:
        try:
            cur=con.execute("UPDATE research_keyword SET keyword = ?, updated_at = ? WHERE id = ? AND domain = ?",(keyword,now,keyword_id,domain)); con.commit(); msg="Keyword updated." if cur.rowcount else "Keyword not found."
        except sqlite3.IntegrityError: msg="That keyword already exists."
    return redirect(url_for("research",domain=domain,message=msg))

@app.post("/d/<domain>/research/<int:keyword_id>/delete")
def research_delete(domain,keyword_id):
    get_site(domain)
    with research_db() as con:
        con.execute("DELETE FROM research_keyword_tag WHERE research_keyword_id=?",(keyword_id,)); con.execute("DELETE FROM research_keyword WHERE id=? AND domain=?",(keyword_id,domain)); con.commit()
    return research_redirect(domain,"Research keyword deleted.",request.form)


@app.post("/d/<domain>/pages/sync")
def pages_sync(domain):
    get_site(domain)
    try:
        sitemap_count, ranking_count, source = sync_site_pages(domain)
        message = f"Pages refreshed: {sitemap_count} sitemap page(s), {ranking_count} ranking landing page(s). Source: {source}"
    except Exception as exc:
        message = f"Page refresh failed: {exc}"
    return redirect(url_for("pages", domain=domain, message=message))


@app.route("/d/<domain>/pages/<int:page_id>")
def page_workspace(domain, page_id):
    site = get_site(domain)
    with research_db() as con:
        page = con.execute("SELECT id,domain,url,path FROM site_page WHERE id=? AND domain=?", (page_id, domain)).fetchone()
        if not page:
            abort(404)
        wanted_rows = con.execute("""
            SELECT w.id,w.keyword,w.avg_monthly_searches,w.competition,
              (SELECT GROUP_CONCAT(tag_name,'||') FROM (
                 SELECT t.name AS tag_name
                 FROM wanted_keyword_tag wt JOIN keyword_tag t ON t.id=wt.tag_id
                 WHERE wt.wanted_keyword_id=w.id ORDER BY t.name COLLATE NOCASE
              )) AS tags
            FROM wanted_keyword w
            WHERE w.domain=? AND w.page_id=?
            ORDER BY w.keyword COLLATE NOCASE
        """, (domain, page_id)).fetchall()
        note_row = con.execute("SELECT content FROM page_note WHERE page_id=?", (page_id,)).fetchone()

    ranking_rows = []
    for row in gsc_rows_for_domain(domain):
        if normalize_site_page_url(row["page"], domain) == page["url"]:
            ranking_rows.append({
                "keyword": row["keyword"],
                "latest_position": row["latest_position"],
                "impressions": row["impressions"] or 0,
                "clicks": row["clicks"] or 0,
            })
    ranking_rows.sort(key=lambda r: (r["latest_position"] is None, r["latest_position"] if r["latest_position"] is not None else 999999, r["keyword"].lower()))
    return render_template("page_workspace.html", sites=get_sites(), site=site, page=page, ranking_rows=ranking_rows, wanted_rows=wanted_rows, note=note_row["content"] if note_row else "", message=request.args.get("message", "").strip())


@app.post("/d/<domain>/pages/<int:page_id>/wanted/add")
def page_wanted_add(domain, page_id):
    get_site(domain)
    keyword = request.form.get("keyword", "").strip()

    if not keyword:
        return redirect(url_for(
            "page_workspace",
            domain=domain,
            page_id=page_id,
            message="Keyword cannot be empty.",
        ))

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    with research_db() as con:
        page_row = con.execute(
            "SELECT id FROM site_page WHERE id=? AND domain=?",
            (page_id, domain),
        ).fetchone()

        if not page_row:
            abort(404)

        existing = con.execute(
            "SELECT id FROM wanted_keyword WHERE domain=? AND keyword=? COLLATE NOCASE",
            (domain, keyword),
        ).fetchone()

        if existing:
            con.execute(
                "UPDATE wanted_keyword SET page_id=?,updated_at=? WHERE id=?",
                (page_id, now, existing["id"]),
            )
            message = "Existing Wanted keyword assigned to this page."
        else:
            con.execute(
                "INSERT INTO wanted_keyword(domain,keyword,page_id,source,created_at,updated_at) VALUES (?,?,?,'manual-page',?,?)",
                (domain, keyword, page_id, now, now),
            )
            message = "Wanted keyword added to this page."

        con.commit()

    return redirect(url_for(
        "page_workspace",
        domain=domain,
        page_id=page_id,
        message=message,
    ))


@app.post("/d/<domain>/pages/<int:page_id>/note")
def page_note_save(domain, page_id):
    get_site(domain)
    content = request.form.get("content", "")
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with research_db() as con:
        if not con.execute("SELECT id FROM site_page WHERE id=? AND domain=?", (page_id, domain)).fetchone():
            abort(404)
        con.execute("""
            INSERT INTO page_note(page_id,content,updated_at) VALUES (?,?,?)
            ON CONFLICT(page_id) DO UPDATE SET content=excluded.content,updated_at=excluded.updated_at
        """, (page_id, content, now))
        con.commit()
    return redirect(url_for("page_workspace", domain=domain, page_id=page_id, message="Note saved."))


@app.post("/d/<domain>/wanted/<int:keyword_id>/page")
def wanted_assign_page(domain, keyword_id):
    get_site(domain)
    raw = request.form.get("page_id", "").strip()
    page_id = int(raw) if raw.isdigit() else None
    with research_db() as con:
        if page_id is not None and not con.execute("SELECT id FROM site_page WHERE id=? AND domain=?", (page_id, domain)).fetchone():
            page_id = None
        con.execute("UPDATE wanted_keyword SET page_id=?,updated_at=? WHERE id=? AND domain=?", (page_id, datetime.now(timezone.utc).isoformat(timespec="seconds"), keyword_id, domain))
        con.commit()
    return redirect(url_for("wanted", domain=domain, q=request.form.get("q", ""), sort=request.form.get("sort", "keyword"), dir=request.form.get("dir", "asc"), per_page=request.form.get("per_page", "50"), page=request.form.get("page", "1"), message="Page assignment updated."))


@app.get("/d/<domain>/keyword-note")
def keyword_note_get(domain):
    get_site(domain)
    keyword = request.args.get("keyword", "").strip()
    if not keyword:
        return {"content": ""}

    with research_db() as con:
        row = con.execute(
            "SELECT content FROM keyword_note WHERE domain=? AND keyword=? COLLATE NOCASE",
            (domain, keyword),
        ).fetchone()

    return {"content": row["content"] if row else ""}


@app.post("/d/<domain>/keyword-note")
def keyword_note_save(domain):
    get_site(domain)
    keyword = request.form.get("keyword", "").strip()
    content = request.form.get("content", "")
    if not keyword:
        abort(400)

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    with research_db() as con:
        con.execute(
            """
            INSERT INTO keyword_note(domain,keyword,content,updated_at)
            VALUES (?,?,?,?)
            ON CONFLICT(domain,keyword) DO UPDATE SET
              content=excluded.content,
              updated_at=excluded.updated_at
            """,
            (domain, keyword, content, now),
        )
        con.commit()

    return {"ok": True}



@app.post("/d/<domain>/taxonomy/lookup")
def taxonomy_lookup(domain):
    get_site(domain)
    kind=request.form.get("kind","keyword")
    values=[v for v in request.form.getlist("values") if v]
    out={}
    with research_db() as con:
        if kind=="page":
            tags=con.execute("SELECT id,name FROM page_tag WHERE domain=? ORDER BY name COLLATE NOCASE",(domain,)).fetchall()
            for v in values:
                if not v.isdigit(): continue
                rows=con.execute("""SELECT t.id,t.name FROM site_page_tag pt JOIN page_tag t ON t.id=pt.tag_id JOIN site_page p ON p.id=pt.page_id WHERE pt.page_id=? AND p.domain=? ORDER BY t.name COLLATE NOCASE""",(int(v),domain)).fetchall()
                out[v]=[dict(r) for r in rows]
        else:
            tags=con.execute("SELECT id,name FROM keyword_tag WHERE domain=? ORDER BY name COLLATE NOCASE",(domain,)).fetchall()
            for kw in values:
                out[kw]=[dict(r) for r in canonical_keyword_tags(con,domain,kw)]
    return {"tags":[dict(t) for t in tags],"assignments":out}


@app.post("/d/<domain>/taxonomy/apply")
def taxonomy_apply(domain):
    get_site(domain)
    kind=request.form.get("kind","keyword")
    action=request.form.get("action","add")
    values=[v for v in request.form.getlist("values") if v]
    tag_id_raw=request.form.get("tag_id","").strip()
    new_tag=request.form.get("new_tag","").strip()
    if action not in {"add","remove"} or not values: abort(400)

    with research_db() as con:
        if kind=="page":
            tag_id=ensure_page_tag(con,domain,new_tag) if new_tag and action=="add" else None
            if tag_id is None and tag_id_raw.isdigit():
                row=con.execute("SELECT id FROM page_tag WHERE id=? AND domain=?",(int(tag_id_raw),domain)).fetchone()
                tag_id=row["id"] if row else None
            if tag_id is None: abort(400)
            ids=[int(v) for v in values if v.isdigit()]
            if action=="add":
                con.executemany("INSERT OR IGNORE INTO site_page_tag(page_id,tag_id) VALUES (?,?)",[(i,tag_id) for i in ids])
            else:
                con.executemany("DELETE FROM site_page_tag WHERE page_id=? AND tag_id=?",[(i,tag_id) for i in ids])
        else:
            tag_id=ensure_keyword_tag(con,domain,new_tag) if new_tag and action=="add" else None
            if tag_id is None and tag_id_raw.isdigit():
                row=con.execute("SELECT id FROM keyword_tag WHERE id=? AND domain=?",(int(tag_id_raw),domain)).fetchone()
                tag_id=row["id"] if row else None
            if tag_id is None: abort(400)
            if action=="add":
                con.executemany("INSERT OR IGNORE INTO keyword_tag_assignment(domain,keyword,tag_id) VALUES (?,?,?)",[(domain,v,tag_id) for v in values])
            else:
                con.executemany("DELETE FROM keyword_tag_assignment WHERE domain=? AND keyword=? COLLATE NOCASE AND tag_id=?",[(domain,v,tag_id) for v in values])
        con.commit()
    return {"ok":True}


@app.route("/d/<domain>/keyword")
def keyword_workspace(domain):
    site=get_site(domain)
    keyword=request.args.get("keyword","").strip()
    if not keyword: abort(400)
    raw=[r for r in gsc_rows_for_domain(domain) if (r["keyword"] or "").casefold()==keyword.casefold()]
    with research_db() as con:
        pages=con.execute("SELECT id,path,url FROM site_page WHERE domain=? ORDER BY path COLLATE NOCASE",(domain,)).fetchall()
        by_url={p["url"]:p for p in pages}
        rankings=[]
        for r in raw:
            n=normalize_site_page_url(r["page"],domain)
            p=by_url.get(n)
            rankings.append({"page":r["page"],"page_id":p["id"] if p else None,"path":p["path"] if p else r["page"],"latest_position":r["latest_position"],"impressions":r["impressions"] or 0,"clicks":r["clicks"] or 0})
        wanted=con.execute("""SELECT w.id,w.page_id,p.path AS page_path FROM wanted_keyword w LEFT JOIN site_page p ON p.id=w.page_id WHERE w.domain=? AND w.keyword=? COLLATE NOCASE""",(domain,keyword)).fetchone()
        tags=canonical_keyword_tags(con,domain,keyword)
        all_keyword_tags=con.execute("SELECT id,name FROM keyword_tag WHERE domain=? ORDER BY name COLLATE NOCASE",(domain,)).fetchall()
        note_row=con.execute("SELECT content FROM keyword_note WHERE domain=? AND keyword=? COLLATE NOCASE",(domain,keyword)).fetchone()
    rankings.sort(key=lambda r:(r["latest_position"] is None,r["latest_position"] if r["latest_position"] is not None else 999999))
    return render_template("keyword_workspace.html",sites=get_sites(),site=site,keyword=keyword,rankings=rankings,pages=pages,wanted=wanted,tags=tags,all_keyword_tags=all_keyword_tags,note=note_row["content"] if note_row else "",message=request.args.get("message","").strip())


@app.post("/d/<domain>/keyword/wanted")
def keyword_wanted_set(domain):
    get_site(domain)
    keyword=request.form.get("keyword","").strip()
    raw=request.form.get("page_id","").strip()
    page_id=int(raw) if raw.isdigit() else None
    if not keyword: abort(400)
    now=datetime.now(timezone.utc).isoformat(timespec="seconds")
    with research_db() as con:
        existing=con.execute("SELECT id FROM wanted_keyword WHERE domain=? AND keyword=? COLLATE NOCASE",(domain,keyword)).fetchone()
        if existing:
            con.execute("UPDATE wanted_keyword SET page_id=?,updated_at=? WHERE id=?",(page_id,now,existing["id"]))
        else:
            con.execute("INSERT INTO wanted_keyword(domain,keyword,page_id,source,created_at,updated_at) VALUES (?,?,?,'keyword-workspace',?,?)",(domain,keyword,page_id,now,now))
        con.commit()
    return redirect(url_for("keyword_workspace",domain=domain,keyword=keyword,message="Wanted target updated."))


@app.post("/d/<domain>/keyword/tag")
def keyword_tag_change(domain):
    get_site(domain)
    keyword=request.form.get("keyword","").strip()
    action=request.form.get("action","add")
    tag_id_raw=request.form.get("tag_id","").strip()
    new_tag=request.form.get("new_tag","").strip()
    with research_db() as con:
        tag_id=ensure_keyword_tag(con,domain,new_tag) if new_tag and action=="add" else None
        if tag_id is None and tag_id_raw.isdigit():
            row=con.execute("SELECT id FROM keyword_tag WHERE id=? AND domain=?",(int(tag_id_raw),domain)).fetchone()
            tag_id=row["id"] if row else None
        if tag_id is None:
            return redirect(url_for("keyword_workspace",domain=domain,keyword=keyword,message="Choose a tag."))
        if action=="add":
            con.execute("INSERT OR IGNORE INTO keyword_tag_assignment(domain,keyword,tag_id) VALUES (?,?,?)",(domain,keyword,tag_id))
        else:
            con.execute("DELETE FROM keyword_tag_assignment WHERE domain=? AND keyword=? COLLATE NOCASE AND tag_id=?",(domain,keyword,tag_id))
        con.commit()
    return redirect(url_for("keyword_workspace",domain=domain,keyword=keyword,message="Keyword tags updated."))


@app.post("/d/<domain>/keyword/note")
def keyword_note_page_save(domain):
    get_site(domain)
    keyword=request.form.get("keyword","").strip()
    content=request.form.get("content","")
    now=datetime.now(timezone.utc).isoformat(timespec="seconds")
    with research_db() as con:
        con.execute("""INSERT INTO keyword_note(domain,keyword,content,updated_at) VALUES (?,?,?,?) ON CONFLICT(domain,keyword) DO UPDATE SET content=excluded.content,updated_at=excluded.updated_at""",(domain,keyword,content,now))
        con.commit()
    return redirect(url_for("keyword_workspace",domain=domain,keyword=keyword,message="Note saved."))

@app.route("/d/<domain>/geo-aeo")
def geo_aeo_integrated(domain):
    site=get_site(domain)
    with research_db() as con:
        latest_run=con.execute("SELECT * FROM audit_run WHERE domain=? ORDER BY id DESC LIMIT 1",(domain,)).fetchone()
        summary={}; page_rows=[]; priority_signals=[]
        if latest_run:
            summary=con.execute("SELECT * FROM audit_domain_summary WHERE audit_run_id=?",(latest_run["id"],)).fetchone() or {}
            page_rows=con.execute(
                """SELECT ap.page_id,p.path,ap.geo_score,ap.aeo_score,ap.combined_score,
                SUM(CASE WHEN s.observed_status='FAIL' THEN 1 ELSE 0 END) fail_count,
                SUM(CASE WHEN s.observed_status='PARTIAL' THEN 1 ELSE 0 END) partial_count
                FROM audit_page ap JOIN site_page p ON p.id=ap.page_id
                LEFT JOIN audit_signal s ON s.audit_page_id=ap.id
                WHERE ap.audit_run_id=? GROUP BY ap.id ORDER BY p.path COLLATE NOCASE""",(latest_run["id"],)
            ).fetchall()
            priority_signals=con.execute(
                """SELECT p.path,s.family,s.signal_key,s.category,s.title,s.observed_status,s.severity,
                COALESCE(st.workflow_status,'open') workflow_status,COALESCE(st.priority,'') priority,
                COALESCE(st.user_note,'') user_note
                FROM audit_signal s JOIN audit_page ap ON ap.id=s.audit_page_id JOIN site_page p ON p.id=ap.page_id
                LEFT JOIN audit_signal_state st ON st.domain=? AND st.page_id=ap.page_id AND st.family=s.family AND st.signal_key=s.signal_key
                WHERE ap.audit_run_id=? AND s.observed_status IN ('FAIL','PARTIAL','UNKNOWN','MANUAL_REVIEW')
                ORDER BY CASE s.severity WHEN 'CRITICAL' THEN 1 WHEN 'HIGH' THEN 2 WHEN 'MEDIUM' THEN 3 ELSE 4 END,p.path LIMIT 100""",
                (domain,latest_run["id"])
            ).fetchall()
    return render_template("geo_aeo_integrated.html",sites=get_sites(),site=site,latest_run=latest_run,summary=summary,
                           page_rows=page_rows,priority_signals=priority_signals,message=request.args.get("message","").strip())


@app.post("/d/<domain>/geo-aeo/run")
def geo_aeo_run_domain(domain):
    get_site(domain)
    with research_db() as con:
        pages=con.execute("SELECT id,url,path FROM site_page WHERE domain=? ORDER BY path COLLATE NOCASE",(domain,)).fetchall()
    if not pages:
        return redirect(url_for("geo_aeo_integrated",domain=domain,message="No site pages are available to audit."))
    run_id=start_audit_run(domain,pages,"whole_site")
    return redirect(url_for("geo_aeo_integrated",domain=domain,message=f"Audit run #{run_id} started."))


@app.post("/d/<domain>/pages/<int:page_id>/geo-aeo/run")
def geo_aeo_run_page(domain,page_id):
    get_site(domain)
    with research_db() as con:
        page=con.execute("SELECT id,url,path FROM site_page WHERE id=? AND domain=?",(page_id,domain)).fetchone()
    if not page: abort(404)
    return {"ok":True,"run_id":start_audit_run(domain,[page],"single_page")}


@app.get("/d/<domain>/pages/<int:page_id>/geo-aeo.json")
def geo_aeo_page_json(domain,page_id):
    get_site(domain)
    with research_db() as con:
        audit=latest_audit_page(con,page_id)
        if not audit: return {"audit":None,"signals":[]}
        rows=con.execute(
            """SELECT s.family,s.signal_key,s.category,s.title,s.observed_status,s.severity,s.evidence,s.recommendation,
            s.source_title,s.source_url,COALESCE(st.workflow_status,'open') workflow_status,
            COALESCE(st.priority,'') priority,COALESCE(st.user_note,'') user_note,COALESCE(st.override_status,'') override_status
            FROM audit_signal s LEFT JOIN audit_signal_state st
            ON st.domain=? AND st.page_id=? AND st.family=s.family AND st.signal_key=s.signal_key
            WHERE s.audit_page_id=? ORDER BY s.family,s.category,s.signal_key""",(domain,page_id,audit["id"])
        ).fetchall()
    return {"audit":{"run_id":audit["run_id"],"geo_score":audit["geo_score"],"aeo_score":audit["aeo_score"],
                     "combined_score":audit["combined_score"],"page_type":audit["page_type"],"completed_at":audit["completed_at"]},
            "signals":[dict(x) for x in rows]}


@app.post("/d/<domain>/pages/<int:page_id>/geo-aeo/state")
def geo_aeo_signal_state(domain,page_id):
    get_site(domain)
    family=request.form.get("family","").strip(); signal_key=request.form.get("signal_key","").strip()
    workflow_status=request.form.get("workflow_status","open").strip(); priority=request.form.get("priority","").strip()
    user_note=request.form.get("user_note",""); override_status=request.form.get("override_status","").strip()
    if workflow_status not in {"open","accepted","fixed","ignore"}: workflow_status="open"
    if priority not in {"","low","medium","high","critical"}: priority=""
    now=datetime.now(timezone.utc).isoformat(timespec="seconds")
    with research_db() as con:
        con.execute(
            """INSERT INTO audit_signal_state(domain,page_id,family,signal_key,workflow_status,priority,user_note,override_status,updated_at)
            VALUES (?,?,?,?,?,?,?,?,?) ON CONFLICT(domain,page_id,family,signal_key) DO UPDATE SET
            workflow_status=excluded.workflow_status,priority=excluded.priority,user_note=excluded.user_note,
            override_status=excluded.override_status,updated_at=excluded.updated_at""",
            (domain,page_id,family,signal_key,workflow_status,priority,user_note,override_status,now)
        )
        con.commit()
    return {"ok":True}


@app.route("/d/<domain>/geo-aeo/report/<int:run_id>")
def geo_aeo_report(domain,run_id):
    site=get_site(domain)
    with research_db() as con:
        run=con.execute("SELECT * FROM audit_run WHERE id=? AND domain=?",(run_id,domain)).fetchone()
        if not run: abort(404)
        summary=con.execute("SELECT * FROM audit_domain_summary WHERE audit_run_id=?",(run_id,)).fetchone() or {}
        page_rows=con.execute("SELECT ap.*,p.path FROM audit_page ap JOIN site_page p ON p.id=ap.page_id WHERE ap.audit_run_id=? ORDER BY p.path COLLATE NOCASE",(run_id,)).fetchall()
        pages=[]
        for p in page_rows:
            sig=con.execute(
                """SELECT s.*,COALESCE(st.workflow_status,'open') workflow_status,COALESCE(st.priority,'') priority,
                COALESCE(st.user_note,'') user_note FROM audit_signal s LEFT JOIN audit_signal_state st
                ON st.domain=? AND st.page_id=? AND st.family=s.family AND st.signal_key=s.signal_key
                WHERE s.audit_page_id=? ORDER BY s.family,s.category,s.signal_key""",(domain,p["page_id"],p["id"])
            ).fetchall()
            item=dict(p); item["signals"]=[dict(x) for x in sig]; pages.append(item)
    return render_template("geo_aeo_report.html",site=site,run=run,summary=summary,pages=pages)

@app.route("/d/<domain>/reports")
def reports(domain):
    site = get_site(domain)
    return render_template(
        "reports.html",
        sites=get_sites(),
        site=site,
        reports=report_files(domain),
        report_sessions=list_report_sessions(RESEARCH_DB, domain),
    )


@app.post("/d/<domain>/reports/full")
def generate_full_web_report(domain):
    site=get_site(domain); ensure_domain_ready(domain)
    with research_db() as con:
        pages=con.execute("SELECT id,url,path FROM site_page WHERE domain=? ORDER BY path COLLATE NOCASE",(domain,)).fetchall()
    try:
        from crawlers.seo import crawl_worker,ensure_schema as ensure_crawl_schema
        urls=[p["url"] for p in pages if p["url"]]
        if urls:
            with research_db() as con:
                ensure_crawl_schema(con); cur=con.execute("INSERT INTO crawl_run(domain,base_url,status,page_cap,delay_ms,obey_robots,report_scope,selected_urls_json) VALUES (?,?,?,?,?,?,?,?)",(domain,"https://"+domain,"queued",len(urls),0,1,"report",json.dumps(urls))); crawl_run_id=cur.lastrowid; con.commit()
            crawl_worker(crawl_run_id,domain,"https://"+domain,len(urls),0,True,research_db,urls,False)
    except Exception:
        pass
    try:
        now=datetime.now(timezone.utc).isoformat(timespec="seconds")
        with research_db() as con:
            cur=con.execute("INSERT INTO audit_run(domain,scope,status,started_at) VALUES (?,?,?,?)",(domain,"report","running",now)); audit_run_id=cur.lastrowid; con.commit()
        audit_worker(domain,audit_run_id,[dict(p) for p in pages])
    except Exception:
        pass
    report_data=collect_report_data(domain=domain,site_id=_site_id_value(site),seo_db=SEO_DB,research_db=RESEARCH_DB)
    report_data["selected_sources"]=selected_source_keys(site); report_data["source_inventory"]=domain_sources_for_site(site)
    report_id=report_data["family_questions"] = effective_domain_family_questions(domain)
    report_data["manual_ai_source"] = manual_ai_source_for_report(domain)
    report_data["manual_ai_source"]=manual_ai_source_for_report(domain)
    report_id=create_report_session(RESEARCH_DB,domain,report_data)
    return redirect(url_for("report_session_view",domain=domain,report_id=report_id))


@app.get("/d/<domain>/reports/<report_id>")
def report_session_view(domain, report_id):
    site = get_site(domain)
    session = load_report_session(RESEARCH_DB, domain, report_id)
    if not session:
        abort(404)
    report = prepare_report_view(session["snapshot"])
    report["cross_model"] = load_cross_model_report_state(domain, report_id, session["snapshot"])
    with research_db() as con:
        report["cross_model_rollups"] = report_rollups(con, domain, report_id)
        report["company_controlled_domains"] = controlled_domains(con, domain)
    report["manual_ai_responses"] = load_report_manual_ai_responses(domain, report_id)
    return render_template(
        "full_report.html",
        sites=get_sites(),
        site=site,
        report_session=session,
        report=report,
        manual_ai_providers=MANUAL_AI_PROVIDERS,
        cross_model_question_defs=QUESTION_DEFS,
    )



@app.post("/d/<domain>/reports/<report_id>/family/<family_id>/manual-ai-responses")
def save_report_manual_ai_responses(domain, report_id, family_id):
    get_site(domain)
    session = load_report_session(RESEARCH_DB, domain, report_id)
    if not session:
        abort(404)

    valid_family_ids = {f["id"] for f in REPORT_FAMILY_SETTINGS}
    if family_id not in valid_family_ids:
        abort(404)

    snapshot_questions = session["snapshot"].get("family_questions") or {}
    family_questions = snapshot_questions.get(family_id) or {}
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    with research_db() as con:
        ensure_report_question_schema(con)
        for slot_key, question_text in family_questions.items():
            try:
                slot = int(slot_key)
            except (TypeError, ValueError):
                continue
            if slot not in (1, 2, 3) or not str(question_text).strip():
                continue

            for provider in MANUAL_AI_PROVIDERS:
                provider_id = provider["id"]
                value = request.form.get(f"response_{slot}_{provider_id}", "").strip()
                if value:
                    con.execute(
                        "INSERT INTO report_manual_ai_response("
                        "domain,report_id,family_id,question_slot,provider,response_text,updated_at"
                        ") VALUES (?,?,?,?,?,?,?) "
                        "ON CONFLICT(domain,report_id,family_id,question_slot,provider) DO UPDATE SET "
                        "response_text=excluded.response_text,updated_at=excluded.updated_at",
                        (domain, report_id, family_id, slot, provider_id, value, now),
                    )
                else:
                    con.execute(
                        "DELETE FROM report_manual_ai_response "
                        "WHERE domain=? COLLATE NOCASE AND report_id=? AND family_id=? "
                        "AND question_slot=? AND provider=?",
                        (domain, report_id, family_id, slot, provider_id),
                    )
        con.commit()

    return redirect(url_for("report_session_view", domain=domain, report_id=report_id) + f"#{family_id}")



@app.post("/d/<domain>/reports/<report_id>/cross-model/<question_id>")
def save_cross_model_question(domain, report_id, question_id):
    get_site(domain)
    session = load_report_session(RESEARCH_DB, domain, report_id)
    if not session:
        abort(404)
    if question_id not in QUESTION_TO_FAMILY:
        abort(404)

    family_id = QUESTION_TO_FAMILY[question_id]
    defs = QUESTION_DEFS[family_id]
    slot = next((i for i, (qid, _q) in enumerate(defs, start=1) if qid == question_id), None)
    configured = (session["snapshot"].get("family_questions") or {}).get(family_id) or {}
    rendered = configured.get(slot) or configured.get(str(slot))
    if not rendered:
        abort(400)

    provider_ids = [p.strip() for p in request.form.get("providers", "chatgpt,claude,gemini").split(",") if p.strip()]
    with research_db() as con:
        for provider in provider_ids:
            status = request.form.get(f"status_{provider}", "success").strip()
            if status not in PROVIDER_STATUSES:
                status = "provider_error"
            upsert_response(con, {
                "domain": domain,
                "report_id": report_id,
                "question_id": question_id,
                "family_id": family_id,
                "template_question": QUESTION_TEMPLATES[question_id],
                "rendered_question": rendered,
                "provider": provider,
                "model": request.form.get(f"model_{provider}", "").strip(),
                "raw_answer": request.form.get(f"answer_{provider}", ""),
                "citations": request.form.get(f"citations_{provider}", ""),
                "country": request.form.get(f"country_{provider}", "").strip(),
                "city": request.form.get(f"city_{provider}", "").strip(),
                "answer_language": request.form.get(f"language_{provider}", "").strip(),
                "live_search_status": request.form.get(f"live_search_{provider}", "").strip(),
                "provider_status": status,
            })
        run_comparison(con, domain, report_id, question_id)
    return redirect(url_for("report_session_view", domain=domain, report_id=report_id) + f"#{family_id}-{question_id}")

@app.post("/d/<domain>/reports/<report_id>/cross-model/<question_id>/rerun")
def rerun_cross_model_question(domain, report_id, question_id):
    get_site(domain)
    session = load_report_session(RESEARCH_DB, domain, report_id)
    if not session or question_id not in QUESTION_TO_FAMILY:
        abort(404)
    with research_db() as con:
        run_comparison(con, domain, report_id, question_id)
    family_id = QUESTION_TO_FAMILY[question_id]
    return redirect(url_for("report_session_view", domain=domain, report_id=report_id) + f"#{family_id}-{question_id}")

@app.get("/d/<domain>/reports/<report_id>/pdf")
def report_session_pdf(domain, report_id):
    get_site(domain)
    session = load_report_session(RESEARCH_DB, domain, report_id)
    if not session:
        abort(404)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    safe_domain = re.sub(r"[^A-Za-z0-9._-]+", "-", domain).strip("-") or "domain"
    filename = f"{safe_domain}-audit-{report_id}.pdf"
    output_path = REPORTS_DIR / filename
    build_full_report_pdf(session["snapshot"], output_path)
    return send_file(
        output_path,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename,
    )


@app.post("/d/<domain>/audit")
def run_audit(domain):
    return geo_aeo_run_domain(domain)



@app.route("/reports/<path:filename>")
def download_report(filename):
    if ".." in filename or filename.startswith("/"):
        abort(400)
    return send_from_directory(REPORTS_DIR, filename, as_attachment=False)


@app.context_processor
def helpers():
    def pct(clicks, impressions):
        try:
            return round((float(clicks) / float(impressions)) * 100, 2) if impressions else 0
        except Exception:
            return 0
    return {"pct": pct}



# PB SEO crawler
from crawlers.seo import register_crawler
app.config["PB_GET_SITES"] = get_sites
register_crawler(app, research_db, get_site)


# PB delete-domain feature
from services.domains import register_delete_domain
register_delete_domain(app, research_db, get_site, get_sites)


# PB extension: DataForSEO
from integrations.dataforseo.extension import register_dataforseo_extension
register_dataforseo_extension(app, research_db, get_site, get_sites)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "4018")), debug=False)
