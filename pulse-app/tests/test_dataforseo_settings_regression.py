from db.migrate import migrate_up
from db.sqlite import connect_sqlite
from integrations.dataforseo import connector


def test_dataforseo_settings_use_migrated_schema_without_request_time_ddl(tmp_path):
    db = tmp_path / "pulse.db"
    migrate_up(db)
    assert not hasattr(connector, "ensure_schema")

    with connect_sqlite(db) as con:
        connector.save_project_settings(
            con,
            "example.com",
            enabled=True,
            max_items_per_run=25,
            max_calls_per_run=3,
        )
        row = con.execute(
            "SELECT * FROM extension_project WHERE domain=? AND extension_key='dataforseo'",
            ("example.com",),
        ).fetchone()
    assert row["enabled"] == 1
    assert row["max_items_per_run"] == 25
    assert row["max_calls_per_run"] == 3


def test_dataforseo_kill_switch_upserts_atomically(tmp_path):
    db = tmp_path / "pulse.db"
    migrate_up(db)
    with connect_sqlite(db) as con:
        connector.set_kill_switch(con, True)
        assert con.execute(
            "SELECT kill_switch FROM extension_global WHERE extension_key='dataforseo'"
        ).fetchone()["kill_switch"] == 1
        connector.set_kill_switch(con, False)
        assert con.execute(
            "SELECT kill_switch FROM extension_global WHERE extension_key='dataforseo'"
        ).fetchone()["kill_switch"] == 0
