import pytest

from services.url_policy import (
    URLPolicyError,
    audit_target_url,
    crawl_url_identity,
    domain_hostname,
    external_source_url,
    normalize_hostname,
    safe_url_join,
    same_hostname,
    same_origin,
    site_page_identity,
)


def test_hostname_normalization_is_case_trailing_dot_and_idn_aware():
    assert normalize_hostname("Example.COM.") == "example.com"
    assert normalize_hostname("BÜCHER.example") == "xn--bcher-kva.example"
    assert domain_hostname("sc-domain:BÜCHER.example") == "xn--bcher-kva.example"


def test_crawl_identity_preserves_scheme_query_and_trailing_slash():
    assert crawl_url_identity("HTTP://Example.COM:80/a//b/?x=1#part") == (
        "http://example.com/a/b/?x=1"
    )
    assert crawl_url_identity("https://example.com/a") == "https://example.com/a"
    assert crawl_url_identity("https://example.com/a/") == "https://example.com/a/"
    assert crawl_url_identity("example.com/a") == "https://example.com/a"


def test_crawl_identity_removes_default_ports_but_preserves_custom_ports():
    assert crawl_url_identity("https://example.com:443/") == "https://example.com/"
    assert crawl_url_identity("https://example.com:8443/") == "https://example.com:8443/"


def test_site_page_policy_intentionally_merges_http_and_https():
    expected = "https://example.com/about"
    assert site_page_identity("http://EXAMPLE.com:8080/about/?x=1#team", "example.com") == expected
    assert site_page_identity("https://example.com/about", "example.com") == expected
    assert site_page_identity("/about/", "example.com") == expected
    assert site_page_identity("https://other.example/about", "example.com") is None


def test_audit_target_policy_defaults_bare_input_and_rejects_other_schemes():
    assert audit_target_url("Example.com/a?x=1#part") == "https://example.com/a?x=1"
    assert audit_target_url("http://example.com/") == "http://example.com/"
    with pytest.raises(URLPolicyError):
        audit_target_url("ftp://example.com/file")


def test_external_source_policy_requires_explicit_scheme_and_preserves_fragment():
    assert external_source_url("https://Example.com/source?q=1#evidence") == (
        "https://example.com/source?q=1#evidence"
    )
    with pytest.raises(URLPolicyError):
        external_source_url("example.com/source")


def test_same_origin_understands_default_and_custom_ports():
    assert same_origin("https://EXAMPLE.com/a", "https://example.com:443/b")
    assert not same_origin("http://example.com/", "https://example.com/")
    assert not same_origin("https://example.com:8443/", "https://example.com/")
    assert same_hostname("https://BÜCHER.example/a", "xn--bcher-kva.example")


def test_safe_join_validates_result_scheme():
    assert safe_url_join("https://example.com/a/", "../b") == "https://example.com/b"
    with pytest.raises(URLPolicyError):
        safe_url_join("https://example.com/", "javascript:alert(1)")


@pytest.mark.parametrize("value", ["", "http://", "https://exa mple.com", "http://example.com:bad/"])
def test_malformed_urls_are_rejected(value):
    with pytest.raises(URLPolicyError):
        crawl_url_identity(value)
