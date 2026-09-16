from __future__ import annotations

import ipaddress
import re
from urllib.parse import SplitResult, urljoin, urlsplit, urlunsplit


class URLPolicyError(ValueError):
    pass


def normalize_hostname(value: str | None) -> str:
    """Return one lowercase ASCII hostname identity (IDNA-aware, no trailing dot)."""

    host = str(value or "").strip().strip("[]").rstrip(".")
    if not host:
        raise URLPolicyError("URL must contain a hostname.")
    try:
        return ipaddress.ip_address(host).compressed.lower()
    except ValueError:
        pass
    try:
        normalized = host.encode("idna").decode("ascii").lower()
    except UnicodeError as exc:
        raise URLPolicyError(f"Invalid hostname: {host}") from exc
    labels = normalized.split(".")
    if (
        not normalized
        or any(
            not label
            or len(label) > 63
            or label.startswith("-")
            or label.endswith("-")
            or re.fullmatch(r"[a-z0-9-]+", label) is None
            for label in labels
        )
    ):
        raise URLPolicyError(f"Invalid hostname: {host}")
    return normalized


def domain_hostname(value: str | None) -> str:
    """Normalize a bare domain, sc-domain property, or absolute URL to a hostname."""

    raw = str(value or "").strip()
    if raw.lower().startswith("sc-domain:"):
        raw = raw.split(":", 1)[1].strip()
    if not raw:
        raise URLPolicyError("Domain is required.")
    parsed = urlsplit(raw if "://" in raw else "//" + raw)
    return normalize_hostname(parsed.hostname)


def _http_parts(value: str, *, default_scheme: str | None = None) -> tuple[SplitResult, str, str, int | None]:
    raw = str(value or "").strip()
    if not raw:
        raise URLPolicyError("URL is required.")
    if default_scheme and "://" not in raw:
        raw = default_scheme + ":" + raw if raw.startswith("//") else default_scheme + "://" + raw
    try:
        parsed = urlsplit(raw)
        scheme = parsed.scheme.lower()
        if scheme not in {"http", "https"}:
            raise URLPolicyError("URL scheme must be HTTP or HTTPS.")
        host = normalize_hostname(parsed.hostname)
        port = parsed.port
    except (TypeError, ValueError) as exc:
        if isinstance(exc, URLPolicyError):
            raise
        raise URLPolicyError(f"Malformed URL: {value}") from exc
    if parsed.username is not None or parsed.password is not None:
        raise URLPolicyError("Credentials are not allowed in URLs.")
    return parsed, scheme, host, port


def _netloc(host: str, scheme: str, port: int | None) -> str:
    rendered_host = f"[{host}]" if ":" in host else host
    default_port = 80 if scheme == "http" else 443
    return rendered_host if port in {None, default_port} else f"{rendered_host}:{port}"


def normalized_origin(url: str) -> tuple[str, str, int]:
    _parsed, scheme, host, port = _http_parts(url)
    return scheme, host, port or (80 if scheme == "http" else 443)


def origin_url(url: str) -> str:
    parsed, scheme, host, port = _http_parts(url)
    return urlunsplit((scheme, _netloc(host, scheme, port), "", "", ""))


def same_origin(left: str, right: str) -> bool:
    try:
        return normalized_origin(left) == normalized_origin(right)
    except URLPolicyError:
        return False


def same_hostname(url: str, domain: str) -> bool:
    try:
        _parsed, _scheme, host, _port = _http_parts(url)
        return host == domain_hostname(domain)
    except URLPolicyError:
        return False


def safe_url_join(base: str, reference: str) -> str:
    """Join a reference and reject any resulting non-HTTP(S) target."""

    joined = urljoin(base, str(reference or "").strip())
    _http_parts(joined)
    return joined


def url_path(url: str) -> str:
    try:
        return urlsplit(url).path or "/"
    except Exception:
        return "/"


def path_with_query(url: str) -> str:
    parsed = urlsplit(url)
    path = parsed.path or "/"
    return path + (("?" + parsed.query) if parsed.query else "")


def crawl_url_identity(value: str) -> str:
    """Crawler identity: preserve scheme, query, path and trailing slash; drop fragment.

    A missing scheme is explicitly interpreted as HTTPS for legacy crawl form input.
    Host casing/IDNs and default ports are normalized. Custom ports remain distinct.
    """

    parsed, scheme, host, port = _http_parts(value, default_scheme="https")
    path = re.sub(r"/{2,}", "/", parsed.path or "/")
    return urlunsplit((scheme, _netloc(host, scheme, port), path, parsed.query, ""))


def site_page_identity(value: str | None, domain: str) -> str | None:
    """Site-page identity: same hostname, HTTPS, no port/query/fragment/trailing slash.

    This intentionally merges HTTP and HTTPS observations into the established
    Pulse page inventory identity. A leading-slash value is relative to domain.
    """

    if value is None or not str(value).strip():
        return None
    try:
        wanted = domain_hostname(domain)
        raw = str(value).strip()
        if raw.startswith("/"):
            raw = f"https://{wanted}{raw}"
        parsed, _scheme, host, _port = _http_parts(raw)
    except URLPolicyError:
        return None
    if host != wanted:
        return None
    path = parsed.path or "/"
    if path != "/":
        path = path.rstrip("/") or "/"
    return urlunsplit(("https", wanted, path, "", ""))


def audit_target_url(value: str) -> str:
    """Audit target: absolute HTTP(S), HTTPS default for bare input, fragment removed."""

    parsed, scheme, host, port = _http_parts(value, default_scheme="https")
    return urlunsplit((scheme, _netloc(host, scheme, port), parsed.path or "/", parsed.query, ""))


def external_source_url(value: str) -> str:
    """External evidence URL: require explicit HTTP(S) and preserve query/fragment."""

    parsed, scheme, host, port = _http_parts(value)
    return urlunsplit(
        (scheme, _netloc(host, scheme, port), parsed.path or "/", parsed.query, parsed.fragment)
    )
