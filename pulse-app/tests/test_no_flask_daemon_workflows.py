import ast
from pathlib import Path

APP = Path(__file__).resolve().parents[1]


def test_no_flask_daemon_workflows():
    offenders = {}
    for rel in ("app.py", "crawlers/seo.py"):
        hits = [
            i
            for i, line in enumerate((APP / rel).read_text().splitlines(), 1)
            if "threading.Thread(" in line or "daemon=True" in line
        ]
        if hits:
            offenders[rel] = hits
    assert offenders == {}


def test_worker_workflows_do_not_import_flask_app_module():
    path = APP / "jobs" / "workflows.py"
    tree = ast.parse(path.read_text())
    offenders = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(alias.name == "app" for alias in node.names):
                offenders.append(node.lineno)
        elif isinstance(node, ast.ImportFrom) and node.module == "app":
            offenders.append(node.lineno)
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "importlib"
            and node.func.attr == "import_module"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and node.args[0].value == "app"
        ):
            offenders.append(node.lineno)
    assert offenders == []
