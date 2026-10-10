import json
import xml.etree.ElementTree as ET

from reports.observation_export import canonical_dataset, csv_bytes, json_bytes, markdown_text, xml_bytes


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


def test_markdown_uses_resource_outcome_field_names():
    value = canonical_dataset({
        "resource_outcomes": [{"requested_url": "https://example.com/a.json", "http_status": 200, "audit_state": "collected_not_audited", "resource_type": "json"}],
    }, domain="example.com", observation_id="obs-fields")
    rendered = markdown_text(value).decode("utf-8")
    assert "https://example.com/a.json" in rendered
    assert "200" in rendered
    assert "collected_not_audited" in rendered
