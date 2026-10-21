import sqlite3
from urllib.parse import parse_qs, urlsplit

from db.migrate import migrate_up
from db.sqlite import connect_sqlite
from integrations.dataforseo import connector
from integrations.dataforseo.extension import register_dataforseo_extension
from services.source_inventory import domain_sources_for_site


def source_map(research_db, opengsc_db, site=None):
    site = site or {"domain": "example.com", "id": "__GSC_MISSING__:example.com", "gsc_missing": True}
    return {
        row["key"]: row
        for row in domain_sources_for_site(
            site,
            research_db=research_db,
            opengsc_db=opengsc_db,
        )
    }


def test_source_inventory_separates_selection_from_connection(tmp_path, monkeypatch):
    research_db = tmp_path / "research.db"
    opengsc_db = tmp_path / "missing-opengsc.db"
    migrate_up(research_db)
    monkeypatch.setenv("DATAFORSEO_KILL_SWITCH", "1")
    monkeypatch.delenv("DATAFORSEO_LOGIN", raising=False)
    monkeypatch.delenv("DATAFORSEO_PASSWORD", raising=False)

    sources = source_map(research_db, opengsc_db)

    assert sources["gsc"]["connector_status"] == "Not connected in OpenGSC"
    assert sources["dataforseo"]["connector_status"] == "Blocked by environment kill switch"
    assert sources["ga4"]["connection_kind"] == "unavailable"
    assert sources["ga4"]["connector_status"] == "Connector not implemented in Pulse"
    assert sources["ga4"]["selected"] is False


def test_dataforseo_only_appears_enabled_after_project_and_credentials_are_ready(tmp_path, monkeypatch):
    research_db = tmp_path / "research.db"
    opengsc_db = tmp_path / "missing-opengsc.db"
    migrate_up(research_db)
    monkeypatch.setenv("DATAFORSEO_LOGIN", "test-login")
    monkeypatch.setenv("DATAFORSEO_PASSWORD", "test-password")
    monkeypatch.setenv("DATAFORSEO_KILL_SWITCH", "0")

    with connect_sqlite(research_db) as con:
        connector.save_project_settings(
            con,
            "example.com",
            enabled=True,
            max_items_per_run=10,
            max_calls_per_run=2,
        )

    source = source_map(research_db, opengsc_db)["dataforseo"]
    assert source["connector_status"].startswith("Enabled for this domain")
    assert source["selected"] is True


def test_gsc_property_is_not_reported_connected_when_opengsc_has_no_matching_site(tmp_path):
    research_db = tmp_path / "research.db"
    opengsc_db = tmp_path / "opengsc.db"
    migrate_up(research_db)
    with sqlite3.connect(opengsc_db) as con:
        con.execute('CREATE TABLE "Site" (id TEXT, url TEXT, siteId TEXT, archivedAt TEXT)')
        con.execute('INSERT INTO "Site" VALUES (?, ?, ?, NULL)', ("different-site", "https://elsewhere.test", "sc-domain:elsewhere.test"))

    source = source_map(
        research_db,
        opengsc_db,
        {"domain": "example.com", "id": "example-site", "gsc_missing": False},
    )["gsc"]
    assert source["connector_status"] == "Not connected in OpenGSC"


def test_dataforseo_enable_request_explains_environment_kill_switch(tmp_path, monkeypatch):
    from flask import Flask

    research_db = tmp_path / "research.db"
    migrate_up(research_db)
    monkeypatch.setenv("DATAFORSEO_KILL_SWITCH", "1")
    site = {"domain": "example.com"}

    def db_factory():
        return connect_sqlite(research_db)

    app = Flask(__name__)
    register_dataforseo_extension(app, db_factory, lambda _domain: site, lambda: [site])

    response = app.test_client().post(
        "/d/example.com/extensions/dataforseo/settings",
        data={"enabled": "1", "max_calls_per_run": "2", "max_items_per_run": "10"},
    )

    assert response.status_code == 302
    message = parse_qs(urlsplit(response.headers["Location"]).query)["message"][0]
    assert "DataForSEO was not enabled" in message
    with connect_sqlite(research_db) as con:
        row = con.execute(
            "SELECT enabled FROM extension_project WHERE domain='example.com' AND extension_key='dataforseo'"
        ).fetchone()
    assert row["enabled"] == 0
