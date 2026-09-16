from __future__ import annotations

import app as app_module

from db.migrate import migrate_up
from db.sqlite import connect_sqlite
from services.page_discovery import get_domain_readiness, set_discovery_state


def test_domain_readiness_is_read_only_and_reflects_discovery_state(tmp_path):
    db = tmp_path / "pulse.db"
    migrate_up(db)

    initial = get_domain_readiness(db, "example.com")
    assert initial == {
        "ready": False,
        "label": "Discovery not started",
        "pages": 0,
        "status": "not_started",
        "error": "",
    }

    set_discovery_state(db, "example.com", "queued", job_id="job-1")
    queued = get_domain_readiness(db, "example.com")
    assert queued["ready"] is False
    assert queued["label"] == "Discovery queued"
    assert queued["pages"] == 0

    with connect_sqlite(db) as con:
        con.execute(
            "INSERT INTO site_page("
            "domain,url,path,source,discovered_at,updated_at"
            ") VALUES (?,?,?,?,?,?)",
            (
                "example.com",
                "https://example.com/",
                "/",
                "sitemap",
                "2026-09-16T00:00:00+00:00",
                "2026-09-16T00:00:00+00:00",
            ),
        )
        con.commit()

    ready = get_domain_readiness(db, "example.com")
    assert ready["ready"] is True
    assert ready["label"] == "Ready"
    assert ready["pages"] == 1


def test_sources_and_overview_get_routes_render_with_readiness(monkeypatch, tmp_path):
    db = tmp_path / "pulse.db"
    migrate_up(db)
    site = {
        "id": 1,
        "domain": "example.com",
        "url": "https://example.com",
        "gsc_missing": True,
    }

    monkeypatch.setattr(app_module, "RESEARCH_DB", db)
    monkeypatch.setattr(app_module, "get_site", lambda domain: site)
    monkeypatch.setattr(app_module, "get_sites", lambda: [site])
    monkeypatch.setattr(app_module, "domain_sources_for_site", lambda current: [])
    monkeypatch.setattr(app_module, "infer_company_name", lambda domain: "Example")
    monkeypatch.setattr(app_module, "domain_seo", lambda site_id: ({}, []))
    monkeypatch.setattr(app_module, "report_files", lambda domain: [])

    with app_module.app.test_request_context("/d/example.com/sources"):
        rendered = app_module.domain_sources("example.com")
        assert "Sources &amp; Settings" in rendered
        assert "Discovery not started" in rendered

    with app_module.app.test_request_context("/d/example.com/"):
        rendered = app_module.overview("example.com")
        assert "example.com" in rendered
        assert "Discovery not started" in rendered


def test_removed_compatibility_helper_is_not_referenced():
    source = (app_module.APP_DIR / "app.py").read_text()
    assert "ensure_domain_ready" not in source
