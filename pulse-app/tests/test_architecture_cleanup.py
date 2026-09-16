from __future__ import annotations

import ast
from pathlib import Path

APP = Path(__file__).resolve().parents[1]


def _route_keys(path: Path):
    tree = ast.parse(path.read_text())
    keys = []
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call) or not isinstance(decorator.func, ast.Attribute):
                continue
            method = decorator.func.attr
            if method not in {"route", "get", "post", "put", "patch", "delete"}:
                continue
            if not decorator.args or not isinstance(decorator.args[0], ast.Constant):
                continue
            route = decorator.args[0].value
            if method == "route":
                methods = {"GET"}
                for keyword in decorator.keywords:
                    if keyword.arg == "methods" and isinstance(keyword.value, (ast.List, ast.Tuple)):
                        methods = {
                            str(item.value).upper()
                            for item in keyword.value.elts
                            if isinstance(item, ast.Constant)
                        }
            else:
                methods = {method.upper()}
            keys.extend((route, item, node.name) for item in methods)
    return keys


def test_flask_route_method_pairs_are_unique():
    seen = {}
    duplicates = []
    for route, method, function in _route_keys(APP / "app.py"):
        key = (route, method)
        if key in seen:
            duplicates.append((route, method, seen[key], function))
        else:
            seen[key] = function
    assert duplicates == []


def test_runtime_schema_compatibility_stubs_are_gone():
    offenders = []
    for path in APP.rglob("*.py"):
        if "tests" in path.parts:
            continue
        if "Compatibility hook only. Schema is owned by versioned migrations." in path.read_text():
            offenders.append(str(path.relative_to(APP)))
    assert offenders == []


def test_manual_ai_payload_parser_has_one_owner():
    targets = [
        APP / "app.py",
        APP / "services" / "manual_ai_report.py",
        APP / "services" / "manual_ai_payload.py",
    ]
    owners = []
    legacy = []
    for path in targets:
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if node.name == "parse_manual_ai_payload":
                owners.append(str(path.relative_to(APP)))
            if node.name in {"_parse_payload", "_parse_manual_provider_payload", "parse_payload"}:
                legacy.append((str(path.relative_to(APP)), node.name))
    assert owners == ["services/manual_ai_payload.py"]
    assert legacy == []
