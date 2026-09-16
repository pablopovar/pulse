from __future__ import annotations

from pathlib import Path

APP = Path(__file__).resolve().parents[1]
ADAPTER = APP / "integrations" / "opengsc_adapter.py"

OPEN_GSC_SCHEMA_NAMES = {
    "gsc_keyword_inventory",
    "gsc_keyword_observation",
    "ClaritySnapshot",
    "AeoCheck",
    "TrackedQuestion",
    "TrackedKeyword",
    "RefDomainRow",
    "BacklinkSnapshot",
    "DomainMetricCache",
    "CompetitorKeyword",
    "SiteAuditPage",
    "SitemapUrl",
    "SiteHealth",
}


def test_opengsc_schema_names_are_confined_to_adapter():
    offenders = {}
    for path in APP.rglob("*.py"):
        if path == ADAPTER or "tests" in path.parts:
            continue
        text = path.read_text()
        hits = sorted(name for name in OPEN_GSC_SCHEMA_NAMES if name in text)
        if hits:
            offenders[str(path.relative_to(APP))] = hits
    assert offenders == {}
