from __future__ import annotations

from pathlib import Path

APP = Path(__file__).resolve().parents[1]
ADAPTER = APP / "integrations" / "opengsc_adapter.py"

# OpenGSC-owned tables/views referenced by the adapter. If application code
# starts naming any of these directly, the integration boundary has leaked.
OPEN_GSC_SCHEMA_NAMES = {
    "Site",
    "gsc_keyword_inventory",
    "gsc_keyword_observation",
    "ClaritySnapshot",
    "AeoCheck",
    "TrackedQuestion",
    "TrackedKeyword",
    "Backlink",
    "RefDomainRow",
    "BacklinkSnapshot",
    "DomainMetricCache",
    "CompetitorKeyword",
    "SiteAudit",
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
