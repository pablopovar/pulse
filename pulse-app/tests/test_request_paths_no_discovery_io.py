from __future__ import annotations

import ast
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "app.py"
FORBIDDEN_CALLS = {"sync_site_pages", "sitemap_pages", "_fetch_sitemap_urls"}


def _route_methods(fn: ast.FunctionDef) -> set[str]:
    methods: set[str] = set()
    routed = False
    for decorator in fn.decorator_list:
        if not isinstance(decorator, ast.Call) or not isinstance(decorator.func, ast.Attribute):
            continue
        name = decorator.func.attr
        if name in {"get", "post", "put", "patch", "delete", "route"}:
            routed = True
        if name == "route":
            explicit = None
            for kw in decorator.keywords:
                if kw.arg == "methods" and isinstance(kw.value, (ast.List, ast.Tuple)):
                    explicit = {
                        str(item.value).upper()
                        for item in kw.value.elts
                        if isinstance(item, ast.Constant)
                    }
            methods |= explicit or {"GET"}
        elif name in {"get", "post", "put", "patch", "delete"}:
            methods.add(name.upper())
    return methods if routed else set()


def test_get_routes_do_not_trigger_page_discovery_network_work():
    tree = ast.parse(APP.read_text())
    offenders = {}
    for fn in [node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]:
        methods = _route_methods(fn)
        if "GET" not in methods:
            continue
        hits = []
        for node in ast.walk(fn):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_CALLS:
                hits.append((node.lineno, node.func.id))
        if hits:
            offenders[fn.name] = hits
    assert offenders == {}


def test_page_refresh_route_enqueues_instead_of_discovering_inline():
    tree = ast.parse(APP.read_text())
    target = next(
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "pages_sync"
    )
    called = {
        node.func.id
        for node in ast.walk(target)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert "enqueue_job" in called
    assert not (called & FORBIDDEN_CALLS)
