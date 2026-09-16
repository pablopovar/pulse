from __future__ import annotations

from pathlib import Path

APP = Path(__file__).resolve().parents[1]
ADAPTER = APP / "integrations" / "opengsc_adapter.py"

# Distinctive OpenGSC-owned schema identifiers can be checked as literals.
# Generic Prisma model names use quoted SQL tokens so ordinary prose such as
# "site" or "backlink" does not create false positives.
OPEN_GSC_SCHEMA_TOKENS = {
    '"Site"',
    "gsc_keyword_inventory",
    "gsc_keyword_observation",
    "ClaritySnapshot",
    "AeoCheck",
    "TrackedQuestion",
    "TrackedKeyword",
    '"Backlink"',
    "RefDomainRow",
    "BacklinkSnapshot",
    "DomainMetricCache",
    "CompetitorKeyword",
    '"SiteAudit"',
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
        hits = sorted(token for token in OPEN_GSC_SCHEMA_TOKENS if token in text)
        if hits:
            offenders[str(path.relative_to(APP))] = hits
    assert offenders == {}
