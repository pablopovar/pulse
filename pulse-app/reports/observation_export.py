from __future__ import annotations

import csv
import io
import json
import xml.etree.ElementTree as ET
import tempfile
from dataclasses import dataclass
from collections.abc import Callable
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "pulse-observation-v1"


@dataclass(frozen=True)
class ObservationRenderer:
    """One projection of the canonical observation dataset.

    Renderers never query SQLite and never assemble their own report data.
    They receive the same normalized observation and only decide how that
    observation is represented.
    """

    name: str
    extension: str
    mimetype: str
    render: Callable[[dict[str, Any]], bytes]


_RENDERERS: dict[str, ObservationRenderer] = {}


def register_renderer(renderer: ObservationRenderer, *aliases: str) -> None:
    for name in (renderer.name, *aliases):
        _RENDERERS[name.lower()] = renderer


def renderer_for(name: str) -> ObservationRenderer | None:
    return _RENDERERS.get(str(name or "").lower())


def render_observation(dataset: dict[str, Any], name: str) -> tuple[bytes, ObservationRenderer]:
    renderer = renderer_for(name)
    if renderer is None:
        raise KeyError(name)
    return renderer.render(dataset), renderer


def _jsonable(value: Any):
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return value


def _executive_projection(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Build the client-facing interpretation from the immutable observation.

    This is deliberately part of normalization rather than a renderer. JSON,
    CSV, XML, Markdown, PDF, and HTML therefore share one interpretation of
    the same stored evidence.
    """
    from reports.web_report import prepare_report_view

    report = prepare_report_view(snapshot)
    return _jsonable({
        "current_verdict": (report.get("executive_summary") or {}).get("finding") or (report.get("high_signal_findings") or [{}])[0],
        "executive_summary": report.get("executive_summary") or {},
        "high_signal_findings": report.get("high_signal_findings") or [],
        "top_actions": report.get("top_actions") or [],
        "pulse_summary": report.get("pulse_summary") or {},
        "monitoring_coverage": report.get("monitoring_coverage") or {},
        "report_quality": report.get("report_quality") or {},
        "methodology": report.get("methodology") or "",
        "methodology_version": report.get("methodology_version") or "",
        "scoring_version": report.get("scoring_version") or "",
    })


def canonical_dataset(snapshot: dict[str, Any], *, domain: str, observation_id: str) -> dict[str, Any]:
    normalized_snapshot = _jsonable(snapshot)
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
        "report_view": _executive_projection(snapshot),
        "resource_schema": "services.resource_outcome.ResourceOutcome",
        # The canonical observation is lossless.  Named top-level projections
        # make common converters simple; the immutable normalized snapshot
        # preserves every report field for renderers that need the full view.
        "report_snapshot": normalized_snapshot,
    })


def json_bytes(dataset: dict[str, Any]) -> bytes:
    return json.dumps(dataset, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")


def csv_bytes(dataset: dict[str, Any]) -> bytes:
    rows = dataset.get("resource_outcomes") or dataset.get("url_decisions") or dataset.get("crawl_pages") or []
    shared = {key: dataset.get(key) for key in ("schema_version", "domain", "observation_id", "observed_at", "crawl_run", "source_observations", "sitemap", "sitemap_reconciliation", "llm_sources", "report_view")}
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
    view = dataset.get("report_view") or {}
    verdict = view.get("current_verdict") or {}
    if verdict:
        lines += ["## Current verdict", "", f"**{verdict.get('title') or 'Observation available'}**", "", str(verdict.get("message") or ""), ""]
    findings = view.get("high_signal_findings") or []
    if findings:
        lines += ["## High-signal findings", ""]
        for finding in findings:
            lines += [f"### {finding.get('title') or 'Finding'}", "", str(finding.get("message") or ""), ""]
    actions = view.get("top_actions") or []
    if actions:
        lines += ["## Top actions", ""]
        for action in actions[:10]:
            recommendation = action.get("recommendation_object") or {}
            lines += [f"### {action.get('title') or 'Action'}", "", str(recommendation.get("recommended_action") or action.get("recommendation") or ""), ""]
    rows = dataset.get("resource_outcomes") or dataset.get("url_decisions") or dataset.get("crawl_pages") or []
    lines += ["## URL decisions", "", "| URL | Status | Decision | Type |", "| --- | --- | --- | --- |"]
    for row in rows:
        lines.append("| {url} | {status} | {decision} | {resource_type} |".format(
            url=row.get("requested_url", row.get("url", "")),
            status=row.get("http_status", row.get("status_code", row.get("outcome", ""))),
            decision=row.get("audit_state", row.get("crawl_state", row.get("decision_reason", row.get("eligibility", "")))),
            resource_type=row.get("resource_type", row.get("content_type", "")),
        ))
    for source in dataset.get("llm_sources") or []:
        lines += ["", f"## {source.get('name') or source.get('source_key') or 'LLM guidance'}", "", f"- Availability: `{source.get('status') or source.get('availability') or 'unavailable'}`", f"- Observed: `{source.get('observed_at') or 'unavailable'}`"]
        if source.get("content") or source.get("raw_content"):
            lines += ["", "```text", str(source.get("content") or source.get("raw_content")), "```"]
        elif source.get("error") or source.get("reason"):
            lines += ["", f"Reason: {source.get('error') or source.get('reason')}"]
    return ("\n".join(lines) + "\n").encode("utf-8")


def pdf_bytes(dataset: dict[str, Any]) -> bytes:
    from reports.full_pdf import build_full_report_pdf
    from reports.web_report import prepare_report_view

    snapshot = prepare_report_view(dict(dataset.get("report_snapshot") or {}))
    snapshot.setdefault("domain", dataset.get("domain") or "")
    with tempfile.TemporaryDirectory(prefix="pulse-pdf-") as directory:
        path = Path(directory) / "observation.pdf"
        build_full_report_pdf(snapshot, path, locale=str(dataset.get("presentation_locale") or "en"))
        return path.read_bytes()


register_renderer(ObservationRenderer("json", "json", "application/json", json_bytes))
register_renderer(ObservationRenderer("csv", "csv", "text/csv", csv_bytes))
register_renderer(ObservationRenderer("xml", "xml", "application/xml", xml_bytes))
register_renderer(ObservationRenderer("markdown", "md", "text/markdown", markdown_text), "md")
register_renderer(ObservationRenderer("pdf", "pdf", "application/pdf", pdf_bytes))
