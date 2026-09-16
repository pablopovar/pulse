from __future__ import annotations

import ast
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
CANONICAL = APP / "services" / "page_discovery.py"


def _calls_et_fromstring(path: Path) -> bool:
    tree = ast.parse(path.read_text())
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr != "fromstring":
            continue
        value = node.func.value
        if isinstance(value, ast.Name) and value.id == "ET":
            return True
    return False


def test_only_canonical_discovery_module_parses_sitemap_xml():
    offenders = []
    for path in APP.rglob("*.py"):
        if path == CANONICAL or "tests" in path.parts:
            continue
        if _calls_et_fromstring(path):
            offenders.append(str(path.relative_to(APP)))
    assert offenders == []
    assert _calls_et_fromstring(CANONICAL)


def test_crawler_delegates_sitemap_traversal_to_discovery_service():
    crawler = (APP / "crawlers" / "seo.py").read_text()
    assert "from services.page_discovery import discover_domain_sitemap, discover_sitemap_urls" in crawler
    assert "discover_sitemap_urls(" in crawler
    assert "discover_domain_sitemap(" in crawler
