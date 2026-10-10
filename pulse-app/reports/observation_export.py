from __future__ import annotations

import csv
import io
import json
import xml.etree.ElementTree as ET
from typing import Any


SCHEMA_VERSION = "pulse-observation-v1"


def _jsonable(value: Any):
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return value


def canonical_dataset(snapshot: dict[str, Any], *, domain: str, observation_id: str) -> dict[str, Any]:
    monitoring = snapshot.get("monitoring_inventory") or {}
    urls = list(monitoring.get("urls") or [])
    crawl_pages = list(snapshot.get("crawl_pages") or [])
    if not urls and crawl_pages:
        urls = crawl_pages
    return _jsonable({
        "schema_version": SCHEMA_VERSION,
        "domain": domain,
        "observation_id": observation_id,
        "observed_at": (snapshot.get("report_metadata") or {}).get("audit_date") or snapshot.get("generated_at"),
        "observation_provenance": snapshot.get("observation_provenance") or {},
        "source_observations": (snapshot.get("report_metadata") or {}).get("source_observations") or [],
        "crawl_run": snapshot.get("crawl_run") or (monitoring.get("crawl_run") or {}),
        "resource_outcomes": snapshot.get("resource_outcomes") or [],
        "url_decisions": urls,
        "crawl_pages": crawl_pages,
        "crawl_issues": snapshot.get("crawl_issues") or [],
        "audit_summary": snapshot.get("audit_summary") or {},
        "audit_pages": snapshot.get("audit_pages") or [],
        "audit_signals": snapshot.get("audit_signals") or [],
        "sitemap": snapshot.get("sitemap") or snapshot.get("sitemap_inventory") or [],
        "sitemap_reconciliation": snapshot.get("sitemap_reconciliation") or [],
        "llm_sources": snapshot.get("llm_sources") or snapshot.get("agent_readiness_sources") or [],
        "resource_schema": "services.resource_outcome.ResourceOutcome",
    })


def json_bytes(dataset: dict[str, Any]) -> bytes:
    return json.dumps(dataset, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")


def csv_bytes(dataset: dict[str, Any]) -> bytes:
    rows = dataset.get("resource_outcomes") or dataset.get("url_decisions") or dataset.get("crawl_pages") or []
    shared = {key: dataset.get(key) for key in ("schema_version", "domain", "observation_id", "observed_at", "crawl_run", "source_observations", "sitemap", "sitemap_reconciliation", "llm_sources")}
    fields = sorted(set(shared) | {key for row in rows if isinstance(row, dict) for key in row})
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=fields or ["url"], extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        combined = shared | (row if isinstance(row, dict) else {"url": row})
        writer.writerow({key: json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else value for key, value in combined.items()})
    return out.getvalue().encode("utf-8-sig")


def xml_bytes(dataset: dict[str, Any]) -> bytes:
    root = ET.Element("pulse-observation", {"schema_version": SCHEMA_VERSION, "domain": str(dataset.get("domain") or ""), "observation_id": str(dataset.get("observation_id") or "")})
    for section_name, value in dataset.items():
        if section_name in {"schema_version", "domain", "observation_id"}:
            continue
        section = ET.SubElement(root, section_name)
        for index, row in enumerate(value if isinstance(value, list) else [value]):
            item = ET.SubElement(section, "item", {"index": str(index)})
            for key, value in (row.items() if isinstance(row, dict) else [("value", row)]):
                child = ET.SubElement(item, str(key).replace(" ", "_"))
                child.text = json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else "" if value is None else str(value)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def markdown_text(dataset: dict[str, Any]) -> bytes:
    lines = [f"# Pulse observation: {dataset.get('domain')}", "", f"- Observation: `{dataset.get('observation_id')}`", f"- Schema: `{dataset.get('schema_version')}`", f"- Observed at: `{dataset.get('observed_at') or 'unavailable'}`", ""]
    rows = dataset.get("resource_outcomes") or dataset.get("url_decisions") or dataset.get("crawl_pages") or []
    lines += ["## URL decisions", "", "| URL | Status | Decision | Type |", "| --- | --- | --- | --- |"]
    for row in rows:
        lines.append("| {url} | {status} | {decision} | {resource_type} |".format(url=row.get("url", ""), status=row.get("status_code", row.get("outcome", "")), decision=row.get("decision_reason", row.get("eligibility", "")), resource_type=row.get("resource_type", row.get("content_type", ""))))
    for source in dataset.get("llm_sources") or []:
        lines += ["", f"## {source.get('name') or source.get('source_key') or 'LLM guidance'}", "", f"- Availability: `{source.get('status') or source.get('availability') or 'unavailable'}`", f"- Observed: `{source.get('observed_at') or 'unavailable'}`"]
        if source.get("content") or source.get("raw_content"):
            lines += ["", "```text", str(source.get("content") or source.get("raw_content")), "```"]
        elif source.get("error") or source.get("reason"):
            lines += ["", f"Reason: {source.get('error') or source.get('reason')}"]
    return ("\n".join(lines) + "\n").encode("utf-8")
