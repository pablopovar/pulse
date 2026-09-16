from datetime import datetime, timedelta, timezone

import pytest

from db.migrate import migrate_up
from db.sqlite import connect_sqlite
from jobs.publication import publish_report_if_owned
from jobs.store import claim_next_job, enqueue_job, get_job, recover_abandoned_jobs
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


def _prepared_owned_report(db, run_id='run-1', worker_id='worker-a'):
    baseline=create_report_session(db,'example.com',snap('BASELINE'),publish=True)
    enqueue_job(db,'report_refresh',domain='example.com',job_id=run_id)
    claimed=claim_next_job(db,worker_id=worker_id,lease_seconds=60)
    assert claimed and claimed['id']==run_id
    report_id=create_report_session(db,'example.com',snap('NEW'),execution_run_id=run_id,publish=False)
    return baseline, report_id


def test_owned_publication_advances_current_atomically(tmp_path):
    db=tmp_path/'pulse.db'; migrate_up(db)
    baseline, report_id=_prepared_owned_report(db)
    assert report_id != baseline
    assert publish_report_if_owned(
        db,job_id='run-1',worker_id='worker-a',domain='example.com',report_id=report_id
    )
    with connect_sqlite(db,readonly=True) as con:
        current=con.execute("SELECT current_report_id FROM domain_report WHERE domain='example.com'").fetchone()[0]
    assert current==report_id
    assert get_job(db,'run-1')['publication_status']=='published'


def test_duplicate_owned_publication_does_not_create_another_session(tmp_path):
    db=tmp_path/'pulse.db'; migrate_up(db)
    _, report_id=_prepared_owned_report(db)
    assert publish_report_if_owned(db,job_id='run-1',worker_id='worker-a',domain='example.com',report_id=report_id)
    assert publish_report_if_owned(db,job_id='run-1',worker_id='worker-a',domain='example.com',report_id=report_id)
    with connect_sqlite(db,readonly=True) as con:
        assert con.execute("SELECT COUNT(*) FROM report_session WHERE execution_run_id='run-1'").fetchone()[0]==1
        assert con.execute("SELECT current_report_id FROM domain_report WHERE domain='example.com'").fetchone()[0]==report_id


def test_stale_worker_cannot_publish_after_recovery(tmp_path):
    db=tmp_path/'pulse.db'; migrate_up(db)
    baseline=create_report_session(db,'example.com',snap('BASELINE'),publish=True)
    enqueue_job(db,'report_refresh',domain='example.com',job_id='run-stale')
    past=datetime.now(timezone.utc)-timedelta(seconds=5)
    claim_next_job(db,worker_id='worker-a',lease_seconds=1,at=past)
    report_id=create_report_session(db,'example.com',snap('STALE'),execution_run_id='run-stale',publish=False)
    assert recover_abandoned_jobs(db)=={'requeued':1,'failed':0}
    replacement=claim_next_job(db,worker_id='worker-b',lease_seconds=60)
    assert replacement and replacement['id']=='run-stale'

    assert not publish_report_if_owned(
        db,job_id='run-stale',worker_id='worker-a',domain='example.com',report_id=report_id
    )
    with connect_sqlite(db,readonly=True) as con:
        assert con.execute("SELECT current_report_id FROM domain_report WHERE domain='example.com'").fetchone()[0]==baseline


def test_publication_exception_preserves_last_valid_current_and_retry_succeeds(tmp_path):
    db=tmp_path/'pulse.db'; migrate_up(db)
    baseline, report_id=_prepared_owned_report(db)
    with connect_sqlite(db) as con:
        con.execute("""
            CREATE TRIGGER block_report_publish
            BEFORE UPDATE ON domain_report
            BEGIN
              SELECT RAISE(ABORT,'publication blocked');
            END
        """)
        con.commit()

    with pytest.raises(Exception, match='publication blocked'):
        publish_report_if_owned(
            db,job_id='run-1',worker_id='worker-a',domain='example.com',report_id=report_id
        )

    with connect_sqlite(db,readonly=True) as con:
        assert con.execute("SELECT current_report_id FROM domain_report WHERE domain='example.com'").fetchone()[0]==baseline
    assert get_job(db,'run-1')['publication_status']!='published'

    with connect_sqlite(db) as con:
        con.execute("DROP TRIGGER block_report_publish")
        con.commit()

    assert publish_report_if_owned(
        db,job_id='run-1',worker_id='worker-a',domain='example.com',report_id=report_id
    )
    with connect_sqlite(db,readonly=True) as con:
        assert con.execute("SELECT current_report_id FROM domain_report WHERE domain='example.com'").fetchone()[0]==report_id
