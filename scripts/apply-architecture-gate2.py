#!/usr/bin/env python3
from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "pulse-app" / "app.py"
FULL_PDF = ROOT / "pulse-app" / "reports" / "full_pdf.py"
WORKFLOWS = ROOT / "pulse-app" / "jobs" / "workflows.py"
CRAWLER = ROOT / "pulse-app" / "crawlers" / "seo.py"
PATCHED_PATHS = [
    "pulse-app/app.py",
    "pulse-app/reports/full_pdf.py",
    "pulse-app/jobs/workflows.py",
    "pulse-app/crawlers/seo.py",
]


def run(*args: str) -> None:
    print("+", " ".join(args), flush=True)
    subprocess.run(args, cwd=ROOT, check=True)


def restore_patched_files() -> None:
    subprocess.run(["git", "restore", "--", *PATCHED_PATHS], cwd=ROOT, check=False)


def replace_between(text: str, start: str, end: str, replacement: str) -> str:
    """Replace from start up to, but not including, end."""
    i = text.find(start)
    if i < 0:
        raise RuntimeError(f"start marker not found: {start!r}")
    j = text.find(end, i)
    if j < 0:
        raise RuntimeError(f"end marker not found after {start!r}: {end!r}")
    prefix = text[:i]
    suffix = text[j:]
    body = replacement.rstrip()
    return prefix + (body + "\n\n" if body else "") + suffix


def replace_once(text: str, old: str, new: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"expected one occurrence, found {count}: {old[:100]!r}")
    return text.replace(old, new, 1)


def patch_app() -> None:
    text = APP.read_text()

    text = replace_once(
        text,
        "from reports.full_pdf import collect_report_data, build_full_report_pdf",
        "from reports.full_pdf import build_full_report_pdf\nfrom services.report_data import collect_report_data",
    )
    anchor = "from jobs.store import cancel_queued_job, get_job, list_jobs\n"
    imports = '''from integrations.opengsc_adapter import OpenGSCAdapter
from services.page_discovery import (
    discover_domain_sitemap,
    discover_sitemap_urls,
    get_discovery_state,
    set_discovery_state,
    sync_site_pages as canonical_sync_site_pages,
)
from services.source_inventory import (
    detected_source_state as service_detected_source_state,
    domain_sources_for_site as service_domain_sources_for_site,
    selected_source_keys as service_selected_source_keys,
    site_id_value as service_site_id_value,
)
'''
    if imports not in text:
        text = replace_once(text, anchor, anchor + imports)

    text = replace_between(
        text,
        "def detected_source_state(site):",
        "def ensure_manual_ai_source_schema(con):",
        '''def detected_source_state(site):
    return service_detected_source_state(site, SEO_DB)


def domain_sources_for_site(site):
    return service_domain_sources_for_site(
        site,
        research_db=RESEARCH_DB,
        opengsc_db=SEO_DB,
    )''',
    )

    text = replace_between(
        text,
        "def ensure_domain_ready(domain):",
        "REPORT_FAMILY_DEFAULT_QUESTIONS = {",
        '''def ensure_domain_ready(domain):
    with research_db() as con:
        row = con.execute(
            "SELECT COUNT(*) AS n FROM site_page WHERE domain=?", (domain,)
        ).fetchone()
        count = int(row["n"] if row else 0)
    discovery = get_discovery_state(RESEARCH_DB, domain)
    ready = count > 0
    label = "Ready" if ready else discovery.get("status", "not_started").replace("_", " ").title()
    return {
        "ready": ready,
        "label": label,
        "pages": count,
        "discovery": discovery,
    }


def selected_source_keys(site):
    return service_selected_source_keys(
        site,
        research_db=RESEARCH_DB,
        opengsc_db=SEO_DB,
    )''',
    )

    text = replace_between(
        text,
        "def _fetch_sitemap_urls(url, domain, seen=None, depth=0):",
        "def canonical_keyword_tags(con, domain, keyword):",
        '''def _fetch_sitemap_urls(url, domain, seen=None, depth=0):
    urls, _errors = discover_sitemap_urls(
        url,
        domain,
        max_depth=max(0, 5 - int(depth or 0)),
    )
    return urls


def sitemap_pages(domain):
    urls, source, _errors = discover_domain_sitemap(domain)
    return urls, source


def _site_id_value(site):
    return service_site_id_value(site)


def gsc_rows_for_domain(domain):
    site = get_site(domain)
    if site.get("gsc_missing"):
        return []
    return OpenGSCAdapter(SEO_DB).gsc_keyword_rows(_site_id_value(site))


def sync_site_pages(domain):
    site = get_site(domain)
    outcome = canonical_sync_site_pages(
        domain,
        research_db=RESEARCH_DB,
        opengsc_db=SEO_DB,
        site_id=_site_id_value(site),
    )
    return outcome["sitemap_count"], outcome["ranking_count"], outcome["sitemap_source"]''',
    )

    text = replace_between(
        text,
        "def _opengsc_get_sites():",
        "def _opengsc_get_site(domain: str):",
        '''def _opengsc_get_sites():
    out = []
    for row in OpenGSCAdapter(SEO_DB).list_sites():
        item = dict(row)
        item["domain"] = host_from_site(item.get("siteId", ""), item.get("url", ""))
        out.append(item)
    return out''',
    )

    text = replace_between(
        text,
        "def table_exists(con, name: str, kind: str | None = None) -> bool:",
        "def geo_engine_audit(url, page_type=\"auto\"):",
        '''def domain_seo(site_id: str):
    return OpenGSCAdapter(SEO_DB).domain_seo(site_id)


def page_rows(site_id: str, q: str = ""):
    return OpenGSCAdapter(SEO_DB).landing_page_rows(site_id, q)


def page_detail(site_id: str, page_url: str):
    return OpenGSCAdapter(SEO_DB).page_detail(site_id, page_url)


def keyword_rows(site_id: str):
    return OpenGSCAdapter(SEO_DB).keyword_rows(site_id)


def build_domain_export(site):
    adapter = OpenGSCAdapter(SEO_DB)
    if not adapter.available():
        raise RuntimeError("OpenGSC database is not available")
    payload = adapter.domain_export(site["id"])

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
        zf.writestr("keywords.csv", csv_bytes(payload["keywords"]))
        zf.writestr("landing-pages.csv", csv_bytes(payload["landing_pages"]))
        zf.writestr("landing-page-keywords.csv", csv_bytes(payload["page_keywords"]))
    archive.seek(0)
    return archive''',
    )

    text = replace_between(
        text,
        '@app.route("/domains/new",methods=["GET","POST"])',
        '@app.route("/d/<domain>/sources",methods=["GET","POST"])',
        '''@app.route("/domains/new",methods=["GET","POST"])
def domain_new():
    message=request.args.get("message","").strip()

    if request.method=="POST":
        raw=request.form.get("domain","").strip()
        try:
            domain,created=create_dashboard_domain(raw)
        except ValueError as exc:
            return render_template("domain_new.html",sites=get_sites(),site=None,message=str(exc))

        if created:
            job=enqueue_job(
                RESEARCH_DB,
                "page_discovery",
                domain=domain,
                payload={"domain":domain},
                max_attempts=3,
            )
            set_discovery_state(RESEARCH_DB,domain,"queued",job_id=job["id"],error="")
            message=f"Domain added. Page discovery queued · job {job['id']}."
        else:
            message="Domain already exists."

        return redirect(url_for("domain_sources",domain=domain,message=message))

    return render_template("domain_new.html",sites=get_sites(),site=None,message=message)''',
    )

    old_initial_discovery = '''    with research_db() as con:
        count = con.execute("SELECT COUNT(*) AS n FROM site_page WHERE domain=?", (domain,)).fetchone()["n"]
    if count == 0:
        try:
            sync_site_pages(domain)
        except Exception as exc:
            if not message:
                message = f"Initial sitemap sync failed: {exc}"

'''
    text = replace_once(
        text,
        old_initial_discovery,
        '    discovery = get_discovery_state(RESEARCH_DB, domain)\n\n',
    )
    text = replace_once(
        text,
        '    return render_template("pages.html", sites=get_sites(), site=site, rows=rows, total=total, q=q, message=message)',
        '    return render_template("pages.html", sites=get_sites(), site=site, rows=rows, total=total, q=q, message=message, discovery=discovery)',
    )

    text = replace_between(
        text,
        '@app.post("/d/<domain>/pages/sync")',
        '@app.route("/d/<domain>/pages/<int:page_id>")',
        '''@app.post("/d/<domain>/pages/sync")
def pages_sync(domain):
    get_site(domain)
    job=enqueue_job(
        RESEARCH_DB,
        "page_discovery",
        domain=domain,
        payload={"domain":domain},
        max_attempts=3,
    )
    set_discovery_state(RESEARCH_DB,domain,"queued",job_id=job["id"],error="")
    return redirect(url_for("pages",domain=domain,message=f"Page discovery queued · job {job['id']}"))''',
    )

    forbidden = [
        "gsc_keyword_inventory", "gsc_keyword_observation", "ClaritySnapshot",
        "AeoCheck", "TrackedQuestion", "TrackedKeyword", "RefDomainRow",
        "BacklinkSnapshot", "DomainMetricCache", "CompetitorKeyword", "SiteAuditPage",
        "SitemapUrl", "SiteHealth", 'FROM Site', 'FROM "Site"',
    ]
    leftovers = [token for token in forbidden if token in text]
    if leftovers:
        raise RuntimeError(f"OpenGSC schema references remain in app.py: {leftovers}")

    APP.write_text(text)


def patch_full_pdf() -> None:
    text = FULL_PDF.read_text()
    text = replace_once(
        text,
        "from reports.extended_sources import enrich_report_data",
        "from services.report_data import collect_report_data",
    )
    text = replace_between(
        text,
        "def collect_report_data(domain: str, site_id: str | None, seo_db: Path, research_db: Path):",
        "def _styles():",
        "",
    )
    forbidden = [
        "gsc_keyword_inventory", "gsc_keyword_observation", "ClaritySnapshot",
        "AeoCheck", "TrackedQuestion",
    ]
    leftovers = [token for token in forbidden if token in text]
    if leftovers:
        raise RuntimeError(f"OpenGSC schema references remain in full_pdf.py: {leftovers}")
    FULL_PDF.write_text(text)


def patch_workflows() -> None:
    text = WORKFLOWS.read_text()
    text = replace_once(
        text,
        "from reports.full_pdf import collect_report_data",
        "from services.report_data import collect_report_data",
    )
    WORKFLOWS.write_text(text)


def patch_crawler() -> None:
    text = CRAWLER.read_text()
    anchor = "from services.safe_fetcher import SafeFetchError, safe_fetcher\n"
    import_line = "from services.page_discovery import discover_domain_sitemap, discover_sitemap_urls\n"
    if import_line not in text:
        text = replace_once(text, anchor, anchor + import_line)

    text = replace_between(
        text,
        "def parse_sitemap(url: str, domain: str, seen=None, depth=0):",
        "UTILITY_SEGMENTS = {",
        '''def parse_sitemap(url: str, domain: str, seen=None, depth=0):
    # Compatibility wrapper. Sitemap traversal lives in services.page_discovery.
    urls, _errors = discover_sitemap_urls(
        url,
        domain,
        max_depth=max(0, 5 - int(depth or 0)),
    )
    return sorted(urls)''',
    )

    text = replace_between(
        text,
        "def discover_seed_urls(base_url: str, domain: str):",
        "def build_robot_parser(base_url: str):",
        '''def discover_seed_urls(base_url: str, domain: str):
    try:
        urls, _source, _warnings = discover_domain_sitemap(domain)
        out = [normalize_url(url) for url in sorted(urls)]
    except Exception:
        out = [normalize_url(base_url.rstrip("/") + "/")]
    seen = set()
    unique = []
    for url in out:
        if url not in seen:
            seen.add(url)
            unique.append(url)
    return unique''',
    )

    # XML parsing for sitemap traversal now belongs only to page_discovery.py.
    text = text.replace("import xml.etree.ElementTree as ET\n", "")
    CRAWLER.write_text(text)


def test_in_isolated_runtime() -> None:
    run("python3", "-m", "compileall", "-q", "pulse-app")
    run("docker", "compose", "build", "pulse-app")
    run(
        "docker", "compose", "run", "--rm", "--no-deps",
        "-e", "RESEARCH_DB=/tmp/pulse-gate2-targeted.db",
        "pulse-app", "sh", "-lc",
        "rm -f /tmp/pulse-gate2-targeted.db* && python -m db.migrate up && python -m pytest -q "
        "tests/test_no_flask_daemon_workflows.py "
        "tests/test_request_paths_no_discovery_io.py "
        "tests/test_page_discovery.py "
        "tests/test_single_sitemap_implementation.py "
        "tests/test_opengsc_adapter.py "
        "tests/test_opengsc_schema_isolation.py "
        "tests/test_worker_workflows_idempotency.py "
        "tests/test_migrations_and_sqlite.py",
    )
    run(
        "docker", "compose", "run", "--rm", "--no-deps",
        "-e", "RESEARCH_DB=/tmp/pulse-gate2-full.db",
        "pulse-app", "sh", "-lc",
        "rm -f /tmp/pulse-gate2-full.db* && python -m db.migrate up && python -m pytest -q",
    )


def deploy_verified_gate() -> None:
    # Migration 0006 is additive: it introduces discovery state without rewriting
    # or deleting existing Pulse observations.
    run("docker", "compose", "run", "--rm", "--no-deps", "pulse-app", "python", "-m", "db.migrate", "up")
    run("docker", "compose", "run", "--rm", "--no-deps", "pulse-app", "python", "-m", "db.migrate", "status")
    run("docker", "compose", "up", "-d", "--force-recreate", "pulse-app", "pulse-worker")
    run("docker", "compose", "ps")


def main() -> int:
    run("git", "diff", "--quiet")
    run("git", "diff", "--cached", "--quiet")
    branch = subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT, text=True).strip()
    if branch != "architecture-hardening":
        raise SystemExit(f"Refusing to run on branch {branch!r}; expected 'architecture-hardening'.")

    try:
        patch_app()
        patch_full_pdf()
        patch_workflows()
        patch_crawler()
        test_in_isolated_runtime()
    except BaseException:
        print("Gate 2 verification failed; restoring locally transformed files.", flush=True)
        restore_patched_files()
        raise

    run("git", "add", *PATCHED_PATHS)
    run("git", "commit", "-m", "Complete application service and discovery boundaries")

    deploy_verified_gate()
    run("git", "push", "origin", "architecture-hardening")
    print("Gate 2 applied, tested, committed, migrated, restarted, and pushed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
