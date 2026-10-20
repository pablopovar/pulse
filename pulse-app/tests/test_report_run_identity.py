"""Report assembly must use the run IDs returned by its own refresh job."""

import sqlite3

import pytest

from services import report_data


class EmptyAdapter:
    def __init__(self, path):
        pass

    def report_core(self, site_id):
        return {}

    def enrich_report(self, data, site_id, domain):
        return data


def _evidence_db(tmp_path, monkeypatch):
    path = tmp_path / "research.db"
    with sqlite3.connect(path) as con:
        con.executescript("""
            CREATE TABLE audit_run (
                id INTEGER PRIMARY KEY, domain TEXT, execution_run_id TEXT, status TEXT
            );
            CREATE TABLE crawl_run (
                id INTEGER PRIMARY KEY, domain TEXT, execution_run_id TEXT, status TEXT
            );
            INSERT INTO audit_run VALUES (1, 'example.com', 'A', 'completed');
            INSERT INTO crawl_run VALUES (11, 'example.com', 'A', 'completed');
            INSERT INTO audit_run VALUES (2, 'example.com', 'B', 'completed');
            INSERT INTO crawl_run VALUES (22, 'example.com', 'B', 'completed');
        """)
    monkeypatch.setattr(report_data, "OpenGSCAdapter", EmptyAdapter)
    # Keep this fixture focused on run selection; ancillary source tables are
    # exercised in their own integration tests.
    monkeypatch.setattr(report_data, "_rows", lambda *args, **kwargs: [])
    return path


def _collect(path, **overrides):
    args = dict(
        domain="example.com", site_id=None, seo_db=path, research_db=path,
        execution_run_id="A", audit_run_id=1, crawl_run_id=11,
    )
    args.update(overrides)
    return report_data.collect_report_data(**args)


def test_overlapping_refresh_uses_its_own_evidence(tmp_path, monkeypatch):
    path = _evidence_db(tmp_path, monkeypatch)
    result = _collect(path)
    assert (result["audit"]["id"], result["crawl"]["id"]) == (1, 11)
    assert result["observation_provenance"]["execution_run_id"] == "A"
    assert result["observation_provenance"]["inputs_linked"] is True


@pytest.mark.parametrize("overrides", [
    {"audit_run_id": 2},
    {"crawl_run_id": 22},
    {"audit_run_id": 999},
    {"crawl_run_id": 999},
    {"domain": "other.com"},
    {"execution_run_id": "other-job"},
])
def test_mismatched_or_missing_evidence_refuses_assembly(tmp_path, monkeypatch, overrides):
    path = _evidence_db(tmp_path, monkeypatch)
    with pytest.raises(RuntimeError, match="Report evidence missing or inconsistent"):
        _collect(path, **overrides)


def test_incomplete_audit_refuses_assembly(tmp_path, monkeypatch):
    path = _evidence_db(tmp_path, monkeypatch)
    with sqlite3.connect(path) as con:
        con.execute("UPDATE audit_run SET status='partial' WHERE id=1")
    with pytest.raises(RuntimeError, match="Report evidence missing or inconsistent"):
        _collect(path)


def test_missing_research_db_refuses_assembly(tmp_path, monkeypatch):
    monkeypatch.setattr(report_data, "OpenGSCAdapter", EmptyAdapter)
    with pytest.raises(RuntimeError, match="Report evidence missing or inconsistent"):
        _collect(tmp_path / "absent.db")
