from __future__ import annotations

from dataclasses import asdict, dataclass
import base64
from datetime import datetime, timezone
import hashlib
from typing import Any

RESOURCE_TYPES = {"html", "xml", "json", "text", "pdf", "image", "feed", "binary", "unsupported"}
LIFECYCLE_STATES = {"discovered", "eligible", "excluded", "fetched", "audited", "collected_not_audited", "duplicate", "unsupported_content_type", "fetch_failed"}
TEXTUAL_RESOURCE_TYPES = {"html", "xml", "json", "text", "feed"}
MAX_RETAINED_BODY_BYTES = 1024 * 1024

@dataclass(frozen=True)
class ResourceOutcome:
    requested_url: str
    final_url: str = ""
    http_status: int | None = None
    content_type: str = ""
    resource_type: str = "unsupported"
    response_size: int = 0
    response_hash: str = ""
    etag: str = ""
    last_modified: str = ""
    redirect_chain: tuple[str, ...] = ()
    discovered_at: str = ""
    observed_at: str = ""
    crawl_state: str = ""
    audit_state: str = ""
    failure_kind: str = ""
    reason: str = ""
    duplicate_or_canonical_target: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self) | {"redirect_chain": list(self.redirect_chain)}

def normalize_resource_type(content_type: str, *, url: str = "") -> str:
    ctype = (content_type or "").split(";", 1)[0].lower().strip()
    path = url.lower().split("?", 1)[0]
    if "html" in ctype: return "html"
    if "rss" in ctype or "atom" in ctype or path.endswith((".rss", ".atom")): return "feed"
    if "xml" in ctype: return "xml"
    if "json" in ctype: return "json"
    if ctype.startswith("text/"): return "text"
    if "pdf" in ctype or path.endswith(".pdf"): return "pdf"
    if ctype.startswith("image/"): return "image"
    if not ctype or ctype in {"application/octet-stream", "application/binary"}: return "binary"
    return "unsupported"


def response_evidence(*, requested_url: str, final_url: str = "", status: int | None = None,
                      headers: dict[str, str] | None = None, body: bytes | None = None,
                      discovered_at: str = "", observed_at: str = "") -> dict[str, Any]:
    """Build the single persisted response contract used by crawler/report/export code.

    Bodies are deliberately retained only for bounded textual resources.  The
    caller can persist this dict directly without needing content-type-specific
    special cases.
    """
    hdrs = {str(k).lower(): str(v) for k, v in (headers or {}).items()}
    raw = body or b""
    resource_type = normalize_resource_type(hdrs.get("content-type", ""), url=final_url or requested_url)
    retain = resource_type in TEXTUAL_RESOURCE_TYPES and len(raw) <= MAX_RETAINED_BODY_BYTES
    observed = observed_at or datetime.now(timezone.utc).isoformat(timespec="seconds")
    if retain:
        hdrs["x-pulse-retained-body-encoding"] = "base64"
    return ResourceOutcome(
        requested_url=requested_url,
        final_url=final_url or requested_url,
        http_status=status,
        content_type=hdrs.get("content-type", ""),
        resource_type=resource_type,
        response_size=len(raw),
        response_hash=hashlib.sha256(raw).hexdigest() if raw else "",
        etag=hdrs.get("etag", ""),
        last_modified=hdrs.get("last-modified", ""),
        discovered_at=discovered_at,
        observed_at=observed,
        crawl_state="fetched",
        audit_state="audited" if resource_type == "html" else "collected_not_audited",
        reason="" if retain or resource_type == "html" else ("body_not_retained" if resource_type not in TEXTUAL_RESOURCE_TYPES else "body_over_size_limit"),
    ).as_dict() | {"response_headers": hdrs, "raw_body": base64.b64encode(raw).decode("ascii") if retain else "", "body_retained": retain}


def persist_resource_outcome(con, *, crawl_run_id: int | None, domain: str, outcome: dict[str, Any]) -> None:
    """Idempotently persist one URL lifecycle outcome in the migration-backed store."""
    observed = str(outcome.get("observed_at") or datetime.now(timezone.utc).isoformat(timespec="seconds"))
    con.execute(
        """
        INSERT INTO resource_outcome(
          crawl_run_id,domain,requested_url,final_url,http_status,content_type,
          resource_type,response_size,response_sha256,response_headers_json,response_body,
          body_retained,etag,last_modified,redirect_chain_json,discovered_at,observed_at,
          crawl_state,audit_state,failure_kind,reason,duplicate_or_canonical_target,created_at
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(crawl_run_id,requested_url) DO UPDATE SET
          final_url=excluded.final_url,http_status=excluded.http_status,content_type=excluded.content_type,
          resource_type=excluded.resource_type,response_size=excluded.response_size,
          response_sha256=excluded.response_sha256,response_headers_json=excluded.response_headers_json,
          response_body=excluded.response_body,body_retained=excluded.body_retained,etag=excluded.etag,
          last_modified=excluded.last_modified,redirect_chain_json=excluded.redirect_chain_json,
          observed_at=excluded.observed_at,crawl_state=excluded.crawl_state,audit_state=excluded.audit_state,
          failure_kind=excluded.failure_kind,reason=excluded.reason,
          duplicate_or_canonical_target=excluded.duplicate_or_canonical_target
        """,
        (crawl_run_id, domain, outcome.get("requested_url", ""), outcome.get("final_url", ""), outcome.get("http_status"),
         outcome.get("content_type", ""), outcome.get("resource_type", "unsupported"), int(outcome.get("response_size") or 0),
         outcome.get("response_hash", ""), json_dumps(outcome.get("response_headers") or {}), outcome.get("raw_body", ""),
         int(bool(outcome.get("body_retained"))), outcome.get("etag", ""), outcome.get("last_modified", ""),
         json_dumps(outcome.get("redirect_chain") or []), outcome.get("discovered_at", ""), observed,
         outcome.get("crawl_state", "discovered"), outcome.get("audit_state", ""), outcome.get("failure_kind", ""),
         outcome.get("reason", ""), outcome.get("duplicate_or_canonical_target", ""), observed),
    )


def json_dumps(value: Any) -> str:
    import json
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
