from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ManualAIPayload:
    """Tolerant interpretation of one stored provider response.

    Storage is deliberately untouched: callers retain the original raw response.
    This object only exposes a best-effort JSON object projection plus a stable
    classification for UI/report diagnostics.
    """

    value: dict[str, Any] | None
    kind: str
    error: str = ""


_FENCE_RE = re.compile(r"^\`\`\`(?:json)?\s*([\s\S]*?)\s*\`\`\`$", re.I)


def parse_manual_ai_payload(raw: Any) -> ManualAIPayload:
    """Parse valid, fenced, or prose-embedded JSON without changing raw storage.

    Kinds:
    - empty: no response
    - json: a top-level JSON object
    - fenced_json: a JSON object inside one Markdown fence
    - embedded_json: the first decodable JSON object in surrounding prose
    - plain_text: non-JSON text
    - malformed_json: JSON-looking text that cannot be decoded
    - non_object_json: valid JSON whose top-level value is not an object
    """

    text = str(raw or "").strip()
    if not text:
        return ManualAIPayload(None, "empty")

    fenced = _FENCE_RE.match(text)
    candidates: list[tuple[str, str]] = []
    if fenced:
        candidates.append(("fenced_json", fenced.group(1).strip()))
    else:
        candidates.append(("json", text))

    last_error = ""
    for kind, candidate in candidates:
        try:
            value = json.loads(candidate)
        except json.JSONDecodeError as exc:
            last_error = str(exc)
        else:
            if isinstance(value, dict):
                return ManualAIPayload(value, kind)
            return ManualAIPayload(
                None,
                "non_object_json",
                "Top-level JSON value must be an object.",
            )

    decoder = json.JSONDecoder()
    saw_object_start = False
    for index, character in enumerate(text):
        if character != "{":
            continue
        saw_object_start = True
        try:
            value, _end = decoder.raw_decode(text[index:])
        except json.JSONDecodeError as exc:
            last_error = str(exc)
            continue
        if isinstance(value, dict):
            return ManualAIPayload(value, "embedded_json")
        last_error = "Top-level JSON value must be an object."

    if fenced or saw_object_start:
        return ManualAIPayload(None, "malformed_json", last_error or "Malformed JSON object.")
    return ManualAIPayload(None, "plain_text", "Response does not contain a JSON object.")
