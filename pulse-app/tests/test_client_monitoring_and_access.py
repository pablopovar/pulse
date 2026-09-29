from __future__ import annotations

from db.migrate import migrate_up
from db.sqlite import connect_sqlite
from reports.web_report import create_report_session, load_report_session, prepare_report_view
from services.public_report_access import access_state, disable_access_password, password_valid, set_access_password


def _snapshot():
    return {
        "domain": "example.com",
        "crawl": {"id": 1, "page_cap": 15},
        "audit_summary": {"pages_audited": 4},
        "audit_signals": [],
    }


def test_report_captures_inventory_and_marks_partial_coverage(tmp_path):
    db = tmp_path / "pulse.db"
    migrate_up(db)
    with connect_sqlite(db) as con:
        con.execute(
            "INSERT INTO crawl_run(id,domain,base_url,status,page_cap,delay_ms,obey_robots,report_scope) "
            "VALUES (1,'example.com','https://example.com','completed',15,0,1,'report')"
        )
        con.execute(
            """INSERT INTO crawl_url_inventory(domain,url,source,classification,eligibility,decision_reason,
                priority_score,discovered_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?)""",
            ("example.com", "https://example.com/", "sitemap", "core_page", "eligible", "useful_content_candidate", 1, "now", "now"),
        )
        con.commit()

    report_id = create_report_session(db, "example.com", _snapshot())
    session = load_report_session(db, "example.com", report_id)
    view = prepare_report_view(session["snapshot"])

    assert view["monitoring_inventory"]["summary"]["known_urls"] == 1
    assert view["monitoring_inventory"]["coverage"]["coverage_state"] == "partial"


def test_client_report_password_is_hashed_and_can_be_disabled(tmp_path):
    db = tmp_path / "pulse.db"
    migrate_up(db)

    state = set_access_password(db, "example.com", "a strong client password")
    assert state["enabled"] is True
    assert password_valid(db, "example.com", "a strong client password") is True
    assert password_valid(db, "example.com", "wrong password") is False

    assert disable_access_password(db, "example.com")["enabled"] is False
    assert access_state(db, "example.com")["configured"] is True
    assert password_valid(db, "example.com", "a strong client password") is False
