from __future__ import annotations

import ipaddress
import socket
from dataclasses import dataclass, field
from typing import Iterable
from urllib.parse import urljoin, urlsplit

import requests


class SafeFetchError(RuntimeError):
    pass


class UnsafeDestination(SafeFetchError):
    pass


class TooManyRedirects(SafeFetchError):
    pass


class ResponseTooLarge(SafeFetchError):
    pass


class DisallowedContentType(SafeFetchError):
    pass


class FetchTimeout(SafeFetchError):
    pass


DEFAULT_ALLOWED_CONTENT_TYPES = frozenset({
    "text/html", "application/xhtml+xml", "application/xml", "text/xml",
    "text/plain", "application/json", "application/ld+json",
    "application/rss+xml", "application/atom+xml", "application/gzip",
    "application/x-gzip", "application/octet-stream",
})

BLOCKED_HOSTNAMES = frozenset({
    "localhost", "localhost.localdomain", "metadata", "metadata.google.internal", "instance-data",
})
BLOCKED_IPS = frozenset({
    "169.254.169.254", "169.254.170.2", "100.100.100.200", "fd00:ec2::254",
})


@dataclass(frozen=True)
class RedirectHop:
    source_url: str
    status_code: int
    target_url: str


@dataclass
class SafeResponse:
    status_code: int
    url: str
    headers: dict[str, str]
    content: bytes
    history: list[RedirectHop] = field(default_factory=list)

    @property
    def text(self) -> str:
        ctype = self.headers.get("content-type", "")
        charset = "utf-8"
        for part in ctype.split(";")[1:]:
            key, sep, value = part.strip().partition("=")
            if sep and key.lower() == "charset" and value.strip():
                charset = value.strip().strip("\"'")
                break
        try:
            return self.content.decode(charset, errors="replace")
        except LookupError:
            return self.content.decode("utf-8", errors="replace")


class SafeFetcher:
    def __init__(
        self,
        *,
        connect_timeout: float = 5.0,
        read_timeout: float = 20.0,
        max_redirects: int = 5,
        max_response_bytes: int = 5 * 1024 * 1024,
        allowed_content_types: Iterable[str] | None = None,
        session: requests.Session | None = None,
    ):
        self.connect_timeout = float(connect_timeout)
        self.read_timeout = float(read_timeout)
        self.max_redirects = int(max_redirects)
        self.max_response_bytes = int(max_response_bytes)
        self.allowed_content_types = frozenset(
            x.lower() for x in (allowed_content_types or DEFAULT_ALLOWED_CONTENT_TYPES)
        )
        self.session = session or requests.Session()
        self.session.trust_env = False

    @classmethod
    def _validate_ip(cls, raw_ip: str):
        try:
            ip = ipaddress.ip_address(raw_ip.split("%", 1)[0])
        except ValueError as exc:
            raise UnsafeDestination(f"Invalid resolved address: {raw_ip}") from exc
        if str(ip) in BLOCKED_IPS:
            raise UnsafeDestination(f"Blocked cloud-metadata destination: {ip}")
        if (
            ip.is_loopback or ip.is_private or ip.is_link_local or ip.is_reserved
            or ip.is_multicast or ip.is_unspecified
        ):
            raise UnsafeDestination(f"Non-public destination is not allowed: {ip}")
        return ip

    def resolve_and_validate(self, url: str):
        parsed = urlsplit(url)
        scheme = parsed.scheme.lower()
        if scheme not in {"http", "https"}:
            raise UnsafeDestination("Only http and https URLs are allowed.")
        if parsed.username or parsed.password:
            raise UnsafeDestination("URLs containing credentials are not allowed.")
        if not parsed.hostname:
            raise UnsafeDestination("URL must contain a hostname.")

        host = parsed.hostname.rstrip(".").lower()
        if host in BLOCKED_HOSTNAMES or host.endswith(".localhost"):
            raise UnsafeDestination(f"Blocked hostname: {host}")

        try:
            literal = ipaddress.ip_address(host.split("%", 1)[0])
        except ValueError:
            literal = None
        if literal is not None:
            validated = self._validate_ip(str(literal))
            return host, (str(validated),)

        port = parsed.port or (443 if scheme == "https" else 80)
        try:
            records = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
        except socket.gaierror as exc:
            raise SafeFetchError(f"DNS resolution failed for {host}: {exc}") from exc

        ips = []
        for record in records:
            sockaddr = record[4]
            if not sockaddr:
                continue
            value = str(self._validate_ip(sockaddr[0]))
            if value not in ips:
                ips.append(value)
        if not ips:
            raise SafeFetchError(f"DNS returned no usable addresses for {host}.")
        return host, tuple(ips)

    @staticmethod
    def _media_type(headers: dict[str, str]) -> str:
        return headers.get("content-type", "").split(";", 1)[0].strip().lower()

    def _validate_content_type(self, headers, allowed_content_types, method):
        if method == "HEAD":
            return
        allowed = frozenset(x.lower() for x in (allowed_content_types or self.allowed_content_types))
        media_type = self._media_type(headers)
        if media_type and media_type not in allowed:
            raise DisallowedContentType(f"Content-Type is not allowed: {media_type}")

    def _read_limited(self, response, max_bytes: int) -> bytes:
        headers = {str(k).lower(): str(v) for k, v in response.headers.items()}
        content_length = headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > max_bytes:
                    raise ResponseTooLarge(f"Response Content-Length exceeds {max_bytes} bytes.")
            except ValueError:
                pass
        chunks = []
        total = 0
        for chunk in response.iter_content(chunk_size=64 * 1024):
            if not chunk:
                continue
            total += len(chunk)
            if total > max_bytes:
                raise ResponseTooLarge(f"Response exceeded {max_bytes} bytes.")
            chunks.append(chunk)
        return b"".join(chunks)

    def fetch(self, url: str, *, method="GET", headers=None, max_response_bytes=None, allowed_content_types=None):
        method = method.upper()
        if method not in {"GET", "HEAD"}:
            raise SafeFetchError(f"Method is not allowed for SafeFetcher: {method}")

        current_url = url
        history = []
        max_bytes = self.max_response_bytes if max_response_bytes is None else int(max_response_bytes)

        for redirect_index in range(self.max_redirects + 1):
            self.resolve_and_validate(current_url)
            try:
                response = self.session.request(
                    method, current_url, headers=headers or {},
                    timeout=(self.connect_timeout, self.read_timeout),
                    allow_redirects=False, stream=True,
                )
            except requests.Timeout as exc:
                raise FetchTimeout(f"Timed out fetching {current_url}") from exc
            except requests.RequestException as exc:
                raise SafeFetchError(f"HTTP request failed for {current_url}: {exc}") from exc

            normalized_headers = {str(k).lower(): str(v) for k, v in response.headers.items()}
            if response.status_code in {301, 302, 303, 307, 308}:
                location = normalized_headers.get("location", "").strip()
                response.close()
                if not location:
                    raise SafeFetchError(f"Redirect response from {current_url} had no Location header.")
                if redirect_index >= self.max_redirects:
                    raise TooManyRedirects(f"Redirect limit exceeded ({self.max_redirects}).")
                target_url = urljoin(current_url, location)
                self.resolve_and_validate(target_url)
                history.append(RedirectHop(current_url, response.status_code, target_url))
                current_url = target_url
                continue

            try:
                self._validate_content_type(normalized_headers, allowed_content_types, method)
                content = b"" if method == "HEAD" else self._read_limited(response, max_bytes)
            finally:
                response.close()

            return SafeResponse(response.status_code, current_url, normalized_headers, content, history)

        raise TooManyRedirects(f"Redirect limit exceeded ({self.max_redirects}).")

    def get(self, url: str, **kwargs):
        return self.fetch(url, method="GET", **kwargs)

    def head(self, url: str, **kwargs):
        return self.fetch(url, method="HEAD", **kwargs)


safe_fetcher = SafeFetcher()
