from __future__ import annotations

import base64
from flask import Flask, jsonify
from services.security_boundary import configure_security


def _basic(username: str, password: str) -> str:
    raw = base64.b64encode(f"{username}:{password}".encode()).decode()
    return f"Basic {raw}"


def _configure_env(monkeypatch, mode="application"):
    monkeypatch.setenv("PULSE_SECURITY_MODE", mode)
    monkeypatch.setenv("PULSE_SECRET_KEY", "test-secret-key")
    monkeypatch.setenv("PULSE_ADMIN_USERNAME", "admin")
    monkeypatch.setenv("PULSE_ADMIN_PASSWORD", "correct-password")
    monkeypatch.setenv("PULSE_PUBLIC_REPORTS_ENABLED", "1")
    monkeypatch.delenv("PULSE_REVOKED_REPORT_IDS", raising=False)
    monkeypatch.setenv("PULSE_PROXY_AUTH_HEADER", "X-Pulse-Authenticated")
    monkeypatch.setenv("PULSE_PROXY_AUTH_VALUE", "proxy-ok")


def _make_app(monkeypatch, mode="application"):
    _configure_env(monkeypatch, mode)
    app = Flask(__name__)
    app.config.update(TESTING=True)
    configure_security(app)

    @app.get("/manage")
    def manage():
        return "ok"

    @app.post("/mutate")
    def mutate():
        return jsonify(ok=True)

    @app.get("/reports/<report_id>")
    def public_report(report_id):
        return f"report:{report_id}"

    @app.post("/reports/<report_id>/reply")
    def public_report_note_reply(report_id):
        return jsonify(ok=True)

    @app.get("/reports/_static/<path:filename>")
    def public_report_static(filename):
        return filename

    return app


def _csrf(client, path, headers=None):
    response = client.get(path, headers=headers or {})
    assert response.status_code == 200
    with client.session_transaction() as sess:
        return sess["_pulse_csrf_token"]


def test_application_mode_rejects_anonymous_management(monkeypatch):
    app = _make_app(monkeypatch)
    assert app.test_client().get("/manage").status_code == 401


def test_application_mode_accepts_valid_basic_auth(monkeypatch):
    app = _make_app(monkeypatch)
    response = app.test_client().get(
        "/manage", headers={"Authorization": _basic("admin", "correct-password")}
    )
    assert response.status_code == 200


def test_application_mode_fails_closed_without_credentials(monkeypatch):
    monkeypatch.setenv("PULSE_SECURITY_MODE", "application")
    monkeypatch.setenv("PULSE_SECRET_KEY", "test-secret-key")
    monkeypatch.delenv("PULSE_ADMIN_USERNAME", raising=False)
    monkeypatch.delenv("PULSE_ADMIN_PASSWORD", raising=False)
    app = Flask(__name__)
    app.config.update(TESTING=True)
    configure_security(app)

    @app.get("/manage")
    def manage():
        return "ok"

    assert app.test_client().get("/manage").status_code == 503


def test_reverse_proxy_mode_requires_assertion(monkeypatch):
    app = _make_app(monkeypatch, "reverse_proxy")
    client = app.test_client()
    assert client.get("/manage").status_code == 401
    assert client.get("/manage", headers={"X-Pulse-Authenticated": "proxy-ok"}).status_code == 200


def test_internal_mode_allows_management_without_auth(monkeypatch):
    app = _make_app(monkeypatch, "internal")
    assert app.test_client().get("/manage").status_code == 200


def test_public_report_bypasses_management_auth(monkeypatch):
    app = _make_app(monkeypatch)
    assert app.test_client().get("/reports/capability123").status_code == 200


def test_public_reports_can_be_disabled(monkeypatch):
    _configure_env(monkeypatch)
    monkeypatch.setenv("PULSE_PUBLIC_REPORTS_ENABLED", "0")
    app = Flask(__name__)
    app.config.update(TESTING=True)
    configure_security(app)

    @app.get("/reports/<report_id>")
    def public_report(report_id):
        return report_id

    assert app.test_client().get("/reports/abc").status_code == 404


def test_specific_public_report_can_be_revoked(monkeypatch):
    _configure_env(monkeypatch)
    monkeypatch.setenv("PULSE_REVOKED_REPORT_IDS", "revoked123,other")
    app = Flask(__name__)
    app.config.update(TESTING=True)
    configure_security(app)

    @app.get("/reports/<report_id>")
    def public_report(report_id):
        return report_id

    client = app.test_client()
    assert client.get("/reports/revoked123").status_code == 404
    assert client.get("/reports/allowed123").status_code == 200


def test_management_mutation_requires_csrf(monkeypatch):
    app = _make_app(monkeypatch)
    client = app.test_client()
    auth = {"Authorization": _basic("admin", "correct-password")}
    assert client.post("/mutate", headers=auth).status_code == 403
    token = _csrf(client, "/manage", headers=auth)
    assert client.post("/mutate", headers={**auth, "X-CSRF-Token": token}).status_code == 200


def test_public_reply_requires_csrf(monkeypatch):
    app = _make_app(monkeypatch)
    client = app.test_client()
    assert client.post("/reports/abc/reply").status_code == 403
    token = _csrf(client, "/reports/abc")
    assert client.post("/reports/abc/reply", headers={"X-CSRF-Token": token}).status_code == 200
