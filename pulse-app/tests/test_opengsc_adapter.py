from __future__ import annotations

import sqlite3

from integrations.opengsc_adapter import OpenGSCAdapter


def test_missing_db_returns_empty_results(tmp_path):
    adapter = OpenGSCAdapter(tmp_path / "missing.db")
    assert adapter.list_sites() == []
    assert adapter.gsc_keyword_rows("site-1") == []
    assert adapter.detected_source_state("site-1") == {}
    assert adapter.report_core("site-1") == {"seo": None, "keywords": []}


def test_site_and_keyword_mapping(tmp_path):
    db = tmp_path / "opengsc.db"
    con = sqlite3.connect(db)
    try:
        con.execute('CREATE TABLE "Site" (id TEXT,url TEXT,siteId TEXT,archivedAt TEXT)')
        con.execute('INSERT INTO "Site" VALUES (?,?,?,NULL)', ("site-1", "https://example.com", "sc-domain:example.com"))
        con.execute(
            "CREATE TABLE gsc_keyword_inventory (site_id TEXT,query TEXT,page TEXT,latest_position REAL,total_impressions INTEGER,total_clicks INTEGER)"
        )
        con.execute(
            "INSERT INTO gsc_keyword_inventory VALUES (?,?,?,?,?,?)",
            ("site-1", "example", "https://example.com/a", 2.5, 100, 5),
        )
        con.commit()
    finally:
        con.close()

    adapter = OpenGSCAdapter(db)
    assert adapter.list_sites()[0]["id"] == "site-1"
    rows = adapter.gsc_keyword_rows("site-1")
    assert rows == [{
        "keyword": "example",
        "page": "https://example.com/a",
        "latest_position": 2.5,
        "impressions": 100,
        "clicks": 5,
    }]


def test_source_state_mapping(tmp_path):
    db = tmp_path / "opengsc.db"
    con = sqlite3.connect(db)
    try:
        con.execute('CREATE TABLE "ClaritySnapshot" (siteId TEXT)')
        con.execute('INSERT INTO "ClaritySnapshot" VALUES (?)', ("site-1",))
        con.execute('CREATE TABLE "TrackedQuestion" (id TEXT,siteId TEXT)')
        con.execute('CREATE TABLE "AeoCheck" (questionId TEXT,engine TEXT)')
        con.execute('INSERT INTO "TrackedQuestion" VALUES (?,?)', ("q1", "site-1"))
        con.executemany('INSERT INTO "AeoCheck" VALUES (?,?)', [("q1", "chatgpt"), ("q1", "gemini")])
        con.commit()
    finally:
        con.close()

    state = OpenGSCAdapter(db).detected_source_state("site-1")
    assert state["ga4"]["connected"] is True
    assert state["chatgpt"]["connected"] is True
    assert state["gemini"]["connected"] is True
    assert "claude" not in state


def test_report_core_maps_gsc_observations(tmp_path):
    db = tmp_path / "opengsc.db"
    con = sqlite3.connect(db)
    try:
        con.execute(
            "CREATE TABLE gsc_keyword_observation (site_id TEXT,query TEXT,page TEXT,impressions INTEGER,clicks INTEGER,position REAL,date TEXT)"
        )
        con.execute(
            "CREATE TABLE gsc_keyword_inventory (site_id TEXT,query TEXT,page TEXT,impressions INTEGER,clicks INTEGER,best_position REAL,latest_position REAL,status TEXT,first_seen TEXT,last_seen TEXT)"
        )
        con.execute(
            "INSERT INTO gsc_keyword_observation VALUES (?,?,?,?,?,?,?)",
            ("site-1", "q", "/", 20, 2, 3.0, "2026-09-01"),
        )
        con.execute(
            "INSERT INTO gsc_keyword_inventory VALUES (?,?,?,?,?,?,?,?,?,?)",
            ("site-1", "q", "/", 20, 2, 3.0, 4.0, "active", "2026-09-01", "2026-09-02"),
        )
        con.commit()
    finally:
        con.close()

    data = OpenGSCAdapter(db).report_core("site-1")
    assert data["seo"]["keywords"] == 1
    assert data["seo"]["impressions"] == 20
    assert data["keywords"][0]["query"] == "q"
