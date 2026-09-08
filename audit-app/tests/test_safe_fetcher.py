import socket
import pytest
import requests
from services.safe_fetcher import SafeFetcher, UnsafeDestination, ResponseTooLarge, FetchTimeout, DisallowedContentType


class FakeResponse:
    def __init__(self, status=200, headers=None, chunks=None):
        self.status_code = status
        self.headers = headers or {"Content-Type": "text/html"}
        self._chunks = list(chunks or [b"ok"])
    def iter_content(self, chunk_size=65536):
        yield from self._chunks
    def close(self):
        pass


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []
        self.trust_env = True
    def request(self, method, url, **kwargs):
        self.requests.append((method, url, kwargs))
        response = self.responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        return response


def _public_dns(monkeypatch, ip="93.184.216.34"):
    def fake_getaddrinfo(host, port, type=0):
        family = socket.AF_INET6 if ":" in ip else socket.AF_INET
        sockaddr = (ip, port, 0, 0) if family == socket.AF_INET6 else (ip, port)
        return [(family, socket.SOCK_STREAM, 6, "", sockaddr)]
    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)


@pytest.mark.parametrize("url", [
    "http://127.0.0.1/", "http://10.0.0.1/", "http://172.16.0.1/",
    "http://192.168.1.1/", "http://169.254.169.254/latest/meta-data/",
    "http://100.100.100.200/latest/meta-data/",
])
def test_blocks_private_and_metadata_ipv4(url):
    with pytest.raises(UnsafeDestination):
        SafeFetcher(session=FakeSession([])).resolve_and_validate(url)


@pytest.mark.parametrize("url", ["http://[::1]/", "http://[fc00::1]/", "http://[fe80::1]/", "http://[fd00:ec2::254]/"])
def test_blocks_non_public_ipv6(url):
    with pytest.raises(UnsafeDestination):
        SafeFetcher(session=FakeSession([])).resolve_and_validate(url)


def test_dns_private_ipv4_blocked(monkeypatch):
    _public_dns(monkeypatch, "192.168.10.8")
    with pytest.raises(UnsafeDestination):
        SafeFetcher(session=FakeSession([])).get("https://example.com/")


def test_dns_private_ipv6_blocked(monkeypatch):
    _public_dns(monkeypatch, "fd00::1234")
    with pytest.raises(UnsafeDestination):
        SafeFetcher(session=FakeSession([])).get("https://example.com/")


def test_redirect_to_private_blocked_before_second_request(monkeypatch):
    _public_dns(monkeypatch)
    session = FakeSession([FakeResponse(302, {"Location": "http://127.0.0.1/admin"}, [])])
    with pytest.raises(UnsafeDestination):
        SafeFetcher(session=session).get("https://example.com/start")
    assert len(session.requests) == 1


def test_redirect_revalidated(monkeypatch):
    calls = []
    def fake_getaddrinfo(host, port, type=0):
        calls.append(host)
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port))]
    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)
    session = FakeSession([
        FakeResponse(302, {"Location": "https://www.example.com/final"}, []),
        FakeResponse(200, {"Content-Type": "text/html"}, [b"done"]),
    ])
    response = SafeFetcher(session=session).get("https://example.com/start")
    assert response.content == b"done"
    assert "example.com" in calls and "www.example.com" in calls
    assert len(session.requests) == 2


def test_oversized_content_length(monkeypatch):
    _public_dns(monkeypatch)
    session = FakeSession([FakeResponse(200, {"Content-Type": "text/html", "Content-Length": "9999"}, [b"x"])])
    with pytest.raises(ResponseTooLarge):
        SafeFetcher(max_response_bytes=100, session=session).get("https://example.com/")


def test_streamed_response_over_limit(monkeypatch):
    _public_dns(monkeypatch)
    session = FakeSession([FakeResponse(200, {"Content-Type": "text/html"}, [b"a" * 60, b"b" * 60])])
    with pytest.raises(ResponseTooLarge):
        SafeFetcher(max_response_bytes=100, session=session).get("https://example.com/")


def test_timeout(monkeypatch):
    _public_dns(monkeypatch)
    with pytest.raises(FetchTimeout):
        SafeFetcher(session=FakeSession([requests.Timeout("timeout")])).get("https://example.com/")


def test_disallowed_content_type(monkeypatch):
    _public_dns(monkeypatch)
    session = FakeSession([FakeResponse(200, {"Content-Type": "image/png"}, [b"png"])])
    with pytest.raises(DisallowedContentType):
        SafeFetcher(session=session).get("https://example.com/image.png")


def test_non_http_scheme_blocked():
    with pytest.raises(UnsafeDestination):
        SafeFetcher(session=FakeSession([])).resolve_and_validate("file:///etc/passwd")


def test_environment_proxies_disabled():
    session = FakeSession([])
    SafeFetcher(session=session)
    assert session.trust_env is False
