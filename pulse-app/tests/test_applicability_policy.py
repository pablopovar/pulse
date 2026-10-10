from __future__ import annotations

from db.migrate import migrate_up
from reports.web_report import _audit_family
from services.applicability_policy import (
    apply_policy,
    load_page_type_overrides,
    load_policy,
    save_page_type_override,
    save_policy,
)


def _signal(title: str, *, url: str = "https://example.test/page/", status: str = "FAIL") -> dict:
    return {
        "title": title,
        "url": url,
        "path": "/" + url.rstrip("/").split("/")[-1] + "/",
        "category": "Question & Intent Alignment",
        "observed_status": status,
        "severity": "LOW",
        "signal_key": title.lower().replace(" ", "-"),
    }


def test_policy_persists_enabled_groups_and_page_type_override(tmp_path):
    db = tmp_path / "research.db"
    migrate_up(db)

    saved = save_policy(db, "example.test", ["faq", "not-a-policy-key"])
    save_page_type_override(db, "example.test", "https://example.test/private/", "privacy_legal")

    assert saved["enabled_checks"] == ["faq"]
    assert load_policy(db, "example.test")["enabled_checks"] == ["faq"]
    assert load_page_type_overrides(db, "example.test") == {
        "https://example.test/private/": "privacy_legal"
    }


def test_optional_checks_are_not_applicable_until_enabled():
    result = apply_policy([_signal("Comparison intent supported")], policy={"enabled_checks": []}, overrides={})
    assert result[0]["observed_status"] == "NOT_APPLICABLE"
    assert "disabled" in result[0]["applicability_reason"]

    enabled = apply_policy([_signal("Comparison intent supported")], policy={"enabled_checks": ["comparison"]}, overrides={})
    assert enabled[0]["observed_status"] == "FAIL"

    structured = apply_policy([_signal("Comparisons are structured")], policy={"enabled_checks": []}, overrides={})
    assert structured[0]["observed_status"] == "NOT_APPLICABLE"


def test_special_page_override_makes_optional_check_not_applicable():
    url = "https://example.test/thank-you/"
    result = apply_policy(
        [_signal("External supporting sources", url=url)],
        policy={"enabled_checks": ["external_evidence"]},
        overrides={url: "thank_you"},
    )
    assert result[0]["page_type"] == "thank_you"
    assert result[0]["page_type_confidence"] == "operator"
    assert result[0]["observed_status"] == "NOT_APPLICABLE"


def test_domain_wide_check_is_aggregated_once():
    signals = [
        {**_signal("HSTS on HTTPS", url="https://example.test/one/"), "category": "Technical Delivery & Consistency", "scope": "domain"},
        {**_signal("HSTS on HTTPS", url="https://example.test/two/"), "category": "Technical Delivery & Consistency", "scope": "domain"},
    ]
    family = _audit_family(
        {"name": "Onsite", "categories": ["Technical Delivery & Consistency"]}, signals
    )
    check = family["categories_data"][0]["checks"][0]
    assert check["scope"] == "domain"
    assert check["pages_affected"] == 1
