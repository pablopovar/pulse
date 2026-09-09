from jobs.workflows import run_crawl, run_audit, run_ai, run_report_refresh

def _healthcheck(job, worker_id=None):
    return {"status":"completed","result_ref":{"kind":"worker_healthcheck","echo":job.get("payload") or {}}}

HANDLERS={
    "worker.healthcheck":_healthcheck,
    "crawl":run_crawl,
    "geo_aeo_audit":run_audit,
    "manual_ai_analysis":run_ai,
    "report_refresh":run_report_refresh,
}
def handler_for(job_type):
    return HANDLERS.get(job_type)
