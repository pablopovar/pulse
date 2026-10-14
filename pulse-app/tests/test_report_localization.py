import ast
from pathlib import Path

from reports.localization import localize_report_html, resolve_report_locale, translate_text


def test_locale_prefers_explicit_query_then_persistent_cookie():
    assert resolve_report_locale("es", "en", "en-US") == "es"
    assert resolve_report_locale(None, "es", "en-US") == "es"
    assert resolve_report_locale(None, None, "es-AR,es;q=0.9") == "es"
    assert resolve_report_locale(None, None, "en-US") == "en"


def test_server_localization_preserves_raw_evidence():
    html = """<!doctype html><html lang='en'><body>
      <h1>Your visibility and website report</h1>
      <label aria-label='Language'>Language</label>
      <pre>Recommendation: open</pre>
      <div class='llm-verbatim'>Current verdict</div>
    </body></html>"""
    localized = localize_report_html(html, "es")
    assert 'lang="es"' in localized
    assert "Tu informe de visibilidad y sitio web" in localized
    assert 'aria-label="Idioma"' in localized
    assert "<pre>Recommendation: open</pre>" in localized
    assert '<div class="llm-verbatim">Current verdict</div>' in localized


def test_dynamic_executive_and_coverage_copy_is_localized():
    assert translate_text("example.com's Living Pulse", "es") == "Pulso del dominio example.com"
    assert translate_text("11/11 affected", "es") == "11/11 afectadas"
    assert translate_text("3 review", "es") == "3 para revisar"
    assert "solamente al conjunto auditado" in translate_text(
        "11 pages were successfully audited against an initial target of 25. "
        "The report remains usable, but conclusions apply only to the audited cohort.",
        "es",
    )


def test_every_declared_detector_title_recommendation_and_fixed_explanation_has_spanish():
    engine = Path(__file__).parents[1] / "audits" / "geo_aeo" / "engine.py"
    tree = ast.parse(engine.read_text(encoding="utf-8"))
    missing = []
    detector_count = 0
    for node in ast.walk(tree):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "add"
            and len(node.args) >= 7
        ):
            continue
        detector_count += 1
        for label, index in (("title", 3), ("explanation", 5), ("recommendation", 6)):
            argument = node.args[index]
            if not isinstance(argument, ast.Constant) or not isinstance(argument.value, str):
                continue
            source = argument.value
            if translate_text(source, "es") == source:
                missing.append(f"{label}: {source}")
    assert detector_count == 116
    assert missing == []


def test_every_declared_crawler_issue_title_has_spanish():
    crawler = Path(__file__).parents[1] / "crawlers" / "seo.py"
    tree = ast.parse(crawler.read_text(encoding="utf-8"))
    titles = []
    for node in ast.walk(tree):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "add_issue"
            and len(node.args) >= 6
        ):
            continue
        title = node.args[5]
        if isinstance(title, ast.Constant) and isinstance(title.value, str):
            titles.append(title.value)
    assert len(titles) == 16
    assert [title for title in titles if translate_text(title, "es") == title] == []
