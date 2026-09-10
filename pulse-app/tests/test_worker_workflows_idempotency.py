from db.migrate import migrate_up
from db.sqlite import connect_sqlite
from reports.web_report import create_report_session


def snap(label):
    return {"domain":"example.com","audit_signals":[],"manual_ai_snapshot":{"available":True,"analysis_status":"success","analysis_text":label}}


def test_duplicate_publication_is_idempotent(tmp_path):
    db=tmp_path/'pulse.db'; migrate_up(db)
    first=create_report_session(db,'example.com',snap('A'),execution_run_id='same',publish=True)
    second=create_report_session(db,'example.com',snap('B'),execution_run_id='same',publish=True)
    assert first==second
    with connect_sqlite(db,readonly=True) as con:
        assert con.execute("SELECT COUNT(*) FROM report_session WHERE execution_run_id='same'").fetchone()[0]==1


def test_partial_artifact_does_not_replace_current(tmp_path):
    db=tmp_path/'pulse.db'; migrate_up(db)
    good=create_report_session(db,'example.com',snap('GOOD'),execution_run_id='good',publish=True)
    create_report_session(db,'example.com',snap('PARTIAL'),execution_run_id='partial',publish=False)
    with connect_sqlite(db,readonly=True) as con:
        assert con.execute("SELECT current_report_id FROM domain_report WHERE domain='example.com'").fetchone()[0]==good
