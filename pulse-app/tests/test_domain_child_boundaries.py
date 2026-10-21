from __future__ import annotations

import app as app_module
import pytest
from werkzeug.exceptions import HTTPException

from db.migrate import migrate_up
from db.sqlite import connect_sqlite


def test_foreign_child_ids_do_not_change_or_expose_other_domain(tmp_path, monkeypatch):
    db = tmp_path / "pulse.db"
    migrate_up(db)
    monkeypatch.setattr(app_module, "RESEARCH_DB", db)
    monkeypatch.setattr(app_module, "get_site", lambda domain: {"domain": domain})
    with connect_sqlite(db) as con:
        keyword_id = con.execute(
            "INSERT INTO research_keyword(domain,keyword,created_at,updated_at) VALUES ('b.com','foreign','now','now')"
        ).lastrowid
        tag_id = con.execute(
            "INSERT INTO keyword_tag(domain,name,created_at) VALUES ('b.com','tag','now')"
        ).lastrowid
        con.execute("INSERT INTO research_keyword_tag(research_keyword_id,tag_id) VALUES (?,?)", (keyword_id, tag_id))
        own_keyword_tag = con.execute(
            "INSERT INTO keyword_tag(domain,name,created_at) VALUES ('a.com','own','now')"
        ).lastrowid
        page_id = con.execute(
            "INSERT INTO site_page(domain,url,path,source,discovered_at,updated_at) "
            "VALUES ('b.com','https://b.com/','/','sitemap','now','now')"
        ).lastrowid
        own_tag = con.execute(
            "INSERT INTO page_tag(domain,name,created_at) VALUES ('a.com','own','now')"
        ).lastrowid
        con.commit()

    app = app_module.app
    with app.test_request_context(f"/d/a.com/research/{keyword_id}/delete", method="POST"):
        app_module.research_delete("a.com", keyword_id)
    with app.test_request_context(
        "/d/a.com/research/bulk-tag", method="POST",
        data={"keyword_ids": str(keyword_id), "tag_id": str(own_keyword_tag)},
    ):
        app_module.research_bulk_tag("a.com")
    with app.test_request_context(
        "/d/a.com/taxonomy/apply", method="POST",
        data={"kind": "page", "action": "add", "values": str(page_id), "tag_id": str(own_tag)},
    ):
        app_module.taxonomy_apply("a.com")
    with app.test_request_context(
        "/d/a.com/research/bulk-delete", method="POST",
        data={"keyword_ids": str(keyword_id)},
    ):
        app_module.research_bulk_delete("a.com")
    with app.test_request_context(
        "/d/a.com/keyword/wanted", method="POST",
        data={"keyword": "target", "page_id": str(page_id)},
    ):
        with pytest.raises(HTTPException) as error:
            app_module.keyword_wanted_set("a.com")
        assert error.value.code == 400
    with app.test_request_context(f"/d/a.com/pages/{page_id}/geo-aeo.json"):
        with pytest.raises(HTTPException) as error:
            app_module.geo_aeo_page_json("a.com", page_id)
        assert error.value.code == 404
    with app.test_request_context(f"/d/a.com/pages/{page_id}/geo-aeo/state", method="POST"):
        with pytest.raises(HTTPException) as error:
            app_module.geo_aeo_signal_state("a.com", page_id)
        assert error.value.code == 404

    with connect_sqlite(db, readonly=True) as con:
        assert con.execute("SELECT COUNT(*) FROM research_keyword_tag WHERE research_keyword_id=?", (keyword_id,)).fetchone()[0] == 1
        assert con.execute("SELECT COUNT(*) FROM research_keyword WHERE id=?", (keyword_id,)).fetchone()[0] == 1
        assert con.execute("SELECT COUNT(*) FROM site_page_tag WHERE page_id=?", (page_id,)).fetchone()[0] == 0
