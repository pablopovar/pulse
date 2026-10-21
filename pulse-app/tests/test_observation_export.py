import json
import xml.etree.ElementTree as ET

from reports.observation_export import (
    ObservationRenderer, canonical_dataset, csv_bytes, json_bytes, markdown_text,
    register_renderer, render_observation, xml_bytes,
)
from reports.web_report import prepare_report_view


def dataset():
    return canonical_dataset({
        "generated_at": "2026-10-05T12:00:00+00:00",
        "crawl_pages": [{"url": "https://example.com/feed.xml", "content_type": "application/xml", "resource_type": "xml", "audit_status": "collected_not_audited"}],
        "monitoring_inventory": {"urls": [{"url": "https://example.com/feed.xml", "eligibility": "excluded", "decision_reason": "feed_or_machine_document"}]},
        "audit_signals": [],
    }, domain="example.com", observation_id="obs-1")


def test_all_formats_preserve_observation_identity_and_non_html_record():
    value = dataset()
    assert json.loads(json_bytes(value))["observation_id"] == "obs-1"
    assert "feed.xml" in csv_bytes(value).decode("utf-8")
    root = ET.fromstring(xml_bytes(value))
    assert root.attrib["schema_version"] == "pulse-observation-v1"
    assert "feed.xml" in markdown_text(value).decode("utf-8")
    assert value["report_snapshot"]["crawl_pages"][0]["url"].endswith("feed.xml")
    assert "report_view" in value
    assert "high_signal_findings" in value["report_view"]


def test_converter_plugins_receive_the_canonical_observation():
    seen = []
    register_renderer(ObservationRenderer(
        "test-format", "test", "application/x-pulse-test",
        lambda observation: seen.append(observation) or observation["observation_id"].encode(),
    ))
    body, renderer = render_observation(dataset(), "test-format")
    assert body == b"obs-1"
    assert renderer.extension == "test"
    assert seen[0]["schema_version"] == "pulse-observation-v1"
    assert seen[0]["resource_outcomes"] == []


def test_markdown_uses_resource_outcome_field_names():
    value = canonical_dataset({
        "resource_outcomes": [{"requested_url": "https://example.com/a.json", "http_status": 200, "audit_state": "collected_not_audited", "resource_type": "json"}],
    }, domain="example.com", observation_id="obs-fields")
    rendered = markdown_text(value).decode("utf-8")
    assert "https://example.com/a.json" in rendered
    assert "200" in rendered
    assert "collected_not_audited" in rendered


def test_markdown_projects_the_same_executive_view_as_json():
    value = canonical_dataset({
        "seo": {
            "impressions": 150,
            "clicks": 0,
            "period_start": "2026-09-01",
            "period_end": "2026-09-30",
        },
        "audit_signals": [],
    }, domain="example.com", observation_id="obs-executive")
    title = value["report_view"]["current_verdict"]["title"]
    assert title == "Search visibility is not turning into search clicks"
    assert title in markdown_text(value).decode("utf-8")


def test_unconnected_gsc_is_explicit_and_has_no_inferred_metrics():
    snapshot = {
        "seo": None,
        "keywords": [{"query": "example", "page": "https://example.com/", "impressions": 100000}],
        "audit_signals": [],
    }
    report = prepare_report_view(snapshot)
    seo_family = next(f for f in report["families"] if f["kind"] == "seo")
    assert seo_family["gsc_available"] is False
    assert seo_family["gsc_unavailable_label"] == "Google Search Console not connected"
    assert seo_family["keywords"] == []
    assert all(seo_family["seo"].get(key) is None for key in ("keywords", "pages", "impressions", "clicks", "ctr"))

    exported = canonical_dataset(snapshot, domain="example.com", observation_id="obs-no-gsc")
    coverage = exported["report_view"]["gsc_reporting"]
    assert coverage["status"] == "not_connected"
    assert coverage["label"] == "Google Search Console not connected"
    assert all(value is None for value in coverage["metrics"].values())
    assert coverage["ctr"] is None
    assert not any(f.get("source") == "Google Search Console" for f in report["high_signal_findings"])


def test_connected_gsc_zeroes_remain_measured_zeroes():
    report = prepare_report_view({
        "seo": {
            "keywords": 0,
            "pages": 0,
            "impressions": 0,
            "clicks": 0,
            "period_start": "2026-09-01",
            "period_end": "2026-09-28",
        },
        "keywords": [],
        "audit_signals": [],
    })
    seo_family = next(f for f in report["families"] if f["kind"] == "seo")
    assert seo_family["gsc_available"] is True
    assert [seo_family["seo"].get(key) for key in ("keywords", "pages", "impressions", "clicks", "ctr")] == [0, 0, 0, 0, 0]
