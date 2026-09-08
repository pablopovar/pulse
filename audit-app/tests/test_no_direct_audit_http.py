import ast
from pathlib import Path

APPDIR = Path(__file__).resolve().parents[1]


def _forbidden_calls(path: Path):
    tree = ast.parse(path.read_text())
    hits = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        base = node.func.value
        if isinstance(base, ast.Name) and base.id == "requests":
            hits.append((node.lineno, f"requests.{node.func.attr}"))
        if (
            node.func.attr == "urlopen"
            and isinstance(base, ast.Attribute)
            and isinstance(base.value, ast.Name)
            and base.value.id == "urllib"
            and base.attr == "request"
        ):
            hits.append((node.lineno, "urllib.request.urlopen"))
    return hits


def test_crawler_and_audit_modules_do_not_bypass_safe_fetcher():
    offenders = {}
    for root in [APPDIR / "crawlers", APPDIR / "audits"]:
        for path in root.rglob("*.py"):
            hits = _forbidden_calls(path)
            if hits:
                offenders[str(path.relative_to(APPDIR))] = hits
    assert offenders == {}


def test_app_sitemap_fetch_no_longer_uses_urlopen():
    source = (APPDIR / "app.py").read_text()
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in {"_sitemap_urls", "sitemap_pages"}:
            segment = ast.get_source_segment(source, node) or ""
            assert "urllib.request.urlopen" not in segment
