from __future__ import annotations

from pathlib import Path
from typing import Any

from integrations.opengsc_adapter import OpenGSCAdapter


def enrich_report_data(data: dict[str, Any], seo_db: Path, site_id: str | None, domain: str):
    """Populate OpenGSC-backed report sections through the integration adapter."""
    return OpenGSCAdapter(seo_db).enrich_report(data, site_id, domain)
