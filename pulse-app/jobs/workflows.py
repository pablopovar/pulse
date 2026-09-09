from __future__ import annotations
import importlib, json, os
from datetime import datetime, timezone
from pathlib import Path

from db.sqlite import connect_sqlite
from jobs.store import set_job_stage, set_job_publication_status

RESEARCH_DB = Path(os.environ.get("RESEARCH_DB", "/data/audit/research.db"))

def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def appmod():
    return importlib.import_module("app")

def result(status, **refs):
    return {"status": status, "result_ref": refs}

def ensure_crawl(job):
    p=job["payload"]; rid=job["id"]
    with connect_sqlite(RESEARCH_DB) as con:
        row=con.execute("SELECT id,status FROM crawl_run WHERE execution_run_id=?",(rid,)).fetchone()
        if row: return int(row["id"]), str(row["status"])
        urls=p.get("selected_urls") or []
        cur=con.execute(
            """INSERT INTO crawl_run(domain,base_url,status,page_cap,delay_ms,obey_robots,report_scope,selected_urls_json,execution_run_id)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (p["domain"],p.get("base_url") or "https://"+p["domain"],"queued",
             int(p.get("page_cap") or len(urls) or 100),int(p.get("delay_ms") or 0),
             int(bool(p.get("obey_robots",True))),p.get("report_scope") or "",
             json.dumps(urls),rid))
        con.commit(); return int(cur.lastrowid),"queued"

def reset_crawl(run_id):
    with connect_sqlite(RESEARCH_DB) as con:
        con.execute("DELETE FROM crawl_issue WHERE crawl_run_id=?",(run_id,))
        con.execute("DELETE FROM crawl_link WHERE crawl_run_id=?",(run_id,))
        con.execute("DELETE FROM crawl_page WHERE crawl_run_id=?",(run_id,))
        con.execute("""UPDATE crawl_run SET status='queued',started_at=NULL,completed_at=NULL,error=NULL,
                       pages_discovered=0,pages_crawled=0,pages_failed=0 WHERE id=?""",(run_id,))
        con.commit()

def run_crawl(job, worker_id):
    from crawlers.seo import crawl_worker
    p=job["payload"]; run_id,status=ensure_crawl(job)
    if status in {"completed","partial"}: return result(status,crawl_run_id=run_id)
    reset_crawl(run_id)
    set_job_stage(RESEARCH_DB,job["id"],worker_id=worker_id,stage="crawl")
    urls=p.get("selected_urls") or None
    app=appmod()
    crawl_worker(run_id,p["domain"],p.get("base_url") or "https://"+p["domain"],
                 int(p.get("page_cap") or len(urls or []) or 100),int(p.get("delay_ms") or 0),
                 bool(p.get("obey_robots",True)),app.research_db,urls,
                 bool(p.get("follow_links",not bool(urls))))
    with connect_sqlite(RESEARCH_DB,readonly=True) as con:
        row=con.execute("SELECT status,error FROM crawl_run WHERE id=?",(run_id,)).fetchone()
    status=str(row["status"] or "failed")
    if status=="failed": raise RuntimeError(row["error"] or "crawl failed")
    return result(status,crawl_run_id=run_id)

def ensure_audit(job, scope):
    with connect_sqlite(RESEARCH_DB) as con:
        row=con.execute("SELECT id,status FROM audit_run WHERE execution_run_id=?",(job["id"],)).fetchone()
        if row: return int(row["id"]),str(row["status"])
        cur=con.execute("INSERT INTO audit_run(domain,scope,status,started_at,execution_run_id) VALUES (?,?, 'running', ?, ?)",
                        (job["payload"]["domain"],scope,now(),job["id"]))
        con.commit(); return int(cur.lastrowid),"running"

def reset_audit(run_id):
    with connect_sqlite(RESEARCH_DB) as con:
        ids=[int(r["id"]) for r in con.execute("SELECT id FROM audit_page WHERE audit_run_id=?",(run_id,))]
        for i in ids: con.execute("DELETE FROM audit_signal WHERE audit_page_id=?",(i,))
        con.execute("DELETE FROM audit_page WHERE audit_run_id=?",(run_id,))
        con.execute("DELETE FROM audit_domain_summary WHERE audit_run_id=?",(run_id,))
        con.execute("UPDATE audit_run SET status='running',completed_at=NULL,error='' WHERE id=?",(run_id,))
        con.commit()

def audit_pages(domain,page_ids):
    app=appmod()
    with connect_sqlite(RESEARCH_DB,readonly=True) as con:
        if page_ids:
            q=",".join("?" for _ in page_ids)
            rows=con.execute(f"SELECT id,url,path FROM site_page WHERE domain=? AND id IN ({q}) ORDER BY path COLLATE NOCASE",[domain,*page_ids]).fetchall()
        else:
            rows=con.execute("SELECT id,url,path FROM site_page WHERE domain=? ORDER BY path COLLATE NOCASE",(domain,)).fetchall()
    if not rows and not page_ids:
        app.sync_site_pages(domain)
        with connect_sqlite(RESEARCH_DB,readonly=True) as con:
            rows=con.execute("SELECT id,url,path FROM site_page WHERE domain=? ORDER BY path COLLATE NOCASE",(domain,)).fetchall()
    return [dict(r) for r in rows]

def run_audit(job, worker_id):
    p=job["payload"]; run_id,status=ensure_audit(job,p.get("scope") or "whole_site")
    if status in {"completed","partial"}: return result(status,audit_run_id=run_id)
    reset_audit(run_id)
    set_job_stage(RESEARCH_DB,job["id"],worker_id=worker_id,stage="audit")
    pages=audit_pages(p["domain"],p.get("page_ids") or [])
    if not pages: raise RuntimeError("No site pages are available to audit.")
    appmod().audit_worker(p["domain"],run_id,pages)
    with connect_sqlite(RESEARCH_DB,readonly=True) as con:
        row=con.execute("SELECT status,error FROM audit_run WHERE id=?",(run_id,)).fetchone()
    status=str(row["status"] or "failed")
    if status=="failed": raise RuntimeError(row["error"] or "audit failed")
    return result(status,audit_run_id=run_id)

def run_ai(job, worker_id):
    p=job["payload"]; rid=job["id"]; src=p["source_snapshot"]; prm=p["parameters"]; ts=now()
    with connect_sqlite(RESEARCH_DB) as con:
        row=con.execute("SELECT status FROM manual_ai_analysis_run WHERE run_id=?",(rid,)).fetchone()
        if row and row["status"]=="completed": return result("completed",manual_ai_analysis_run_id=rid)
        con.execute("""INSERT INTO manual_ai_analysis_run(run_id,domain,status,provider,model,parameters_json,source_snapshot_json,started_at,created_at,updated_at)
                       VALUES (?,?, 'running', ?, ?, ?, ?, ?, ?, ?)
                       ON CONFLICT(run_id) DO UPDATE SET status='running',error_json='{}',started_at=excluded.started_at,completed_at=NULL,updated_at=excluded.updated_at""",
                    (rid,p["domain"],prm.get("provider") or "",prm.get("model") or "",json.dumps(prm),json.dumps(src),ts,ts,ts))
        con.commit()
    set_job_stage(RESEARCH_DB,rid,worker_id=worker_id,stage="ai_analysis")
    app=appmod()
    try:
        analysis=app.run_manual_ai_analysis(src,prm.get("model") or "",prm.get("system_prompt") or "",
            provider=prm.get("provider") or "ollama",reasoning_effort=prm.get("reasoning_effort") or "high",
            temperature=float(prm.get("temperature",.1)),top_p=float(prm.get("top_p",.9)),
            max_output_tokens=int(prm.get("max_output_tokens",8000)))
    except Exception as exc:
        err={"kind":exc.__class__.__name__,"message":str(exc),"stage":"provider_execution","at":now()}
        with connect_sqlite(RESEARCH_DB) as con:
            con.execute("UPDATE manual_ai_analysis_run SET status='failed',error_json=?,completed_at=?,updated_at=? WHERE run_id=?",
                        (json.dumps(err),now(),now(),rid)); con.commit()
        raise
    ts=now()
    with connect_sqlite(RESEARCH_DB) as con:
        con.execute("BEGIN IMMEDIATE")
        con.execute("UPDATE manual_ai_analysis_run SET status='completed',analysis_text=?,error_json='{}',completed_at=?,updated_at=? WHERE run_id=?",
                    (analysis,ts,ts,rid))
        con.execute("""UPDATE manual_ai_source SET analysis_provider=?,analysis_model=?,analysis_reasoning_effort=?,
                       analysis_temperature=?,analysis_top_p=?,analysis_max_output_tokens=?,analysis_system_prompt_version=?,
                       analysis_parameters_json=?,analysis_system_prompt=?,analysis_text=?,analysis_status='success',
                       analysis_error='',analysis_updated_at=?,updated_at=? WHERE domain=? COLLATE NOCASE""",
                    (prm.get("provider") or "ollama",prm.get("model") or "",prm.get("reasoning_effort") or "high",
                     float(prm.get("temperature",.1)),float(prm.get("top_p",.9)),int(prm.get("max_output_tokens",8000)),
                     int(prm.get("system_prompt_version",1)),json.dumps(prm),prm.get("system_prompt") or "",analysis,ts,ts,p["domain"]))
        con.commit()
    return result("completed",manual_ai_analysis_run_id=rid)

def run_report_refresh(job, worker_id):
    p=job["payload"]; domain=p["domain"]; rid=job["id"]; app=appmod()
    set_job_publication_status(RESEARCH_DB,rid,worker_id=worker_id,publication_status="pending")
    crawl=run_crawl({**job,"payload":{"domain":domain,"base_url":"https://"+domain,"page_cap":int(p.get("page_cap") or 5000),
              "delay_ms":int(p.get("delay_ms") or 0),"obey_robots":True,"report_scope":"report","selected_urls":[],"follow_links":True}},worker_id)
    if crawl["status"]!="completed":
        set_job_publication_status(RESEARCH_DB,rid,worker_id=worker_id,publication_status="withheld")
        return {"status":"partial","result_ref":{**crawl["result_ref"],"publication":"withheld"},"error":{"kind":"prerequisite_partial","message":"crawl incomplete"}}
    audit=run_audit({**job,"payload":{"domain":domain,"scope":"report","page_ids":[]}},worker_id)
    if audit["status"]!="completed":
        set_job_publication_status(RESEARCH_DB,rid,worker_id=worker_id,publication_status="withheld")
        return {"status":"partial","result_ref":{**crawl["result_ref"],**audit["result_ref"],"publication":"withheld"},"error":{"kind":"prerequisite_partial","message":"audit incomplete"}}
    set_job_stage(RESEARCH_DB,rid,worker_id=worker_id,stage="assemble_report")
    site=app.get_site(domain)
    data=app.collect_report_data(domain=domain,site_id=app._site_id_value(site),seo_db=app.SEO_DB,research_db=app.RESEARCH_DB)
    data["selected_sources"]=app.selected_source_keys(site); data["source_inventory"]=app.domain_sources_for_site(site)
    data["manual_ai_source"]=app.manual_ai_source_for_report(domain)
    set_job_stage(RESEARCH_DB,rid,worker_id=worker_id,stage="publish",publication_status="publishing")
    report_id=app.create_report_session(RESEARCH_DB,domain,data,execution_run_id=rid,publish=True)
    set_job_publication_status(RESEARCH_DB,rid,worker_id=worker_id,publication_status="published")
    return result("completed",crawl_run_id=crawl["result_ref"]["crawl_run_id"],audit_run_id=audit["result_ref"]["audit_run_id"],report_id=report_id,publication="published")
