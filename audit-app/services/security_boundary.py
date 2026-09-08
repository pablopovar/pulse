from __future__ import annotations

import base64
import hmac
import os
import secrets
from dataclasses import dataclass

from flask import abort, request, session


SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})
PUBLIC_ENDPOINTS = frozenset(
    {
        "public_report",
        "public_report_static",
        "public_report_note_reply",
    }
)
VALID_SECURITY_MODES = frozenset({"application", "reverse_proxy", "internal"})


@dataclass(frozen=True)
class SecurityConfig:
    mode: str
    admin_username: str
    admin_password: str
    proxy_header: str
    proxy_value: str
    public_reports_enabled: bool
    revoked_report_ids: frozenset[str]


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def load_security_config() -> SecurityConfig:
    mode = os.environ.get("PULSE_SECURITY_MODE", "application").strip().lower()
    if mode not in VALID_SECURITY_MODES:
        raise RuntimeError(
            "PULSE_SECURITY_MODE must be one of: application, reverse_proxy, internal"
        )

    revoked = frozenset(
        item.strip()
        for item in os.environ.get("PULSE_REVOKED_REPORT_IDS", "").split(",")
        if item.strip()
    )

    return SecurityConfig(
        mode=mode,
        admin_username=os.environ.get("PULSE_ADMIN_USERNAME", "").strip(),
        admin_password=os.environ.get("PULSE_ADMIN_PASSWORD", ""),
        proxy_header=os.environ.get(
            "PULSE_PROXY_AUTH_HEADER", "X-Pulse-Authenticated"
        ).strip(),
        proxy_value=os.environ.get("PULSE_PROXY_AUTH_VALUE", "1"),
        public_reports_enabled=_env_bool("PULSE_PUBLIC_REPORTS_ENABLED", True),
        revoked_report_ids=revoked,
    )


def _constant_equal(left: str, right: str) -> bool:
    return hmac.compare_digest(
        left.encode("utf-8", errors="surrogatepass"),
        right.encode("utf-8", errors="surrogatepass"),
    )


def _basic_credentials() -> tuple[str, str] | None:
    header = request.headers.get("Authorization", "")
    if not header.startswith("Basic "):
        return None
    try:
        decoded = base64.b64decode(header[6:].strip(), validate=True).decode("utf-8")
        username, password = decoded.split(":", 1)
    except Exception:
        return None
    return username, password


def _require_application_auth(config: SecurityConfig):
    if not config.admin_username or not config.admin_password:
        return (
            "Pulse application authentication is enabled but "
            "PULSE_ADMIN_USERNAME/PULSE_ADMIN_PASSWORD are not configured.",
            503,
        )

    credentials = _basic_credentials()
    if credentials:
        username, password = credentials
        if _constant_equal(username, config.admin_username) and _constant_equal(
            password, config.admin_password
        ):
            return None

    return (
        "Authentication required.",
        401,
        {"WWW-Authenticate": 'Basic realm="Pulse management", charset="UTF-8"'},
    )


def _require_proxy_auth(config: SecurityConfig):
    if not config.proxy_header:
        return (
            "Pulse reverse-proxy mode requires PULSE_PROXY_AUTH_HEADER.",
            503,
        )

    supplied = request.headers.get(config.proxy_header, "")
    if _constant_equal(supplied, config.proxy_value):
        return None

    return ("Reverse-proxy authentication boundary not satisfied.", 401)


def _csrf_token() -> str:
    token = session.get("_pulse_csrf_token")
    if not isinstance(token, str) or len(token) < 32:
        token = secrets.token_urlsafe(32)
        session["_pulse_csrf_token"] = token
    return token


def _validate_csrf():
    expected = session.get("_pulse_csrf_token")
    supplied = (
        request.headers.get("X-CSRF-Token")
        or request.form.get("_csrf_token")
        or ""
    )

    if (
        not isinstance(expected, str)
        or not supplied
        or not hmac.compare_digest(expected, supplied)
    ):
        abort(403, description="CSRF validation failed.")


def _public_report_id() -> str | None:
    if request.endpoint not in {"public_report", "public_report_note_reply"}:
        return None
    value = request.view_args.get("report_id") if request.view_args else None
    return str(value) if value else None


def _enforce_public_report_capability(config: SecurityConfig):
    report_id = _public_report_id()
    if report_id is None:
        return

    if not config.public_reports_enabled or report_id in config.revoked_report_ids:
        abort(404)


def configure_security(app):
    config = load_security_config()
    app.config["PULSE_SECURITY"] = config

    app.secret_key = os.environ.get("PULSE_SECRET_KEY") or secrets.token_hex(32)
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Strict",
        SESSION_COOKIE_SECURE=_env_bool("PULSE_SECURE_COOKIES", False),
    )

    @app.context_processor
    def pulse_security_context():
        return {"csrf_token": _csrf_token}

    @app.before_request
    def pulse_security_boundary():
        # Materialize a CSRF token for every session, including GET
        # requests that do not render a Jinja template.
        _csrf_token()

        endpoint = request.endpoint or ""

        if endpoint in PUBLIC_ENDPOINTS:
            _enforce_public_report_capability(config)
            if request.method not in SAFE_METHODS:
                _validate_csrf()
            return None

        if endpoint == "static":
            return None

        if config.mode == "application":
            auth_response = _require_application_auth(config)
            if auth_response is not None:
                return auth_response
        elif config.mode == "reverse_proxy":
            auth_response = _require_proxy_auth(config)
            if auth_response is not None:
                return auth_response

        if request.method not in SAFE_METHODS:
            _validate_csrf()

        return None

    return config
