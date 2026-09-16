from services.manual_ai_payload import parse_manual_ai_payload


def test_valid_json_object():
    parsed = parse_manual_ai_payload('{"results": []}')
    assert parsed.kind == "json"
    assert parsed.value == {"results": []}
    assert parsed.error == ""


def test_fenced_json_object():
    fence = chr(96) * 3
    parsed = parse_manual_ai_payload(
        fence + 'json\n{"provider": "chatgpt"}\n' + fence
    )
    assert parsed.kind == "fenced_json"
    assert parsed.value == {"provider": "chatgpt"}


def test_json_embedded_in_surrounding_prose():
    parsed = parse_manual_ai_payload('Here is the result:\n{"results": [1]}\nDone.')
    assert parsed.kind == "embedded_json"
    assert parsed.value == {"results": [1]}


def test_plain_text_is_preserved_as_non_json():
    parsed = parse_manual_ai_payload("The provider returned an ordinary prose answer.")
    assert parsed.kind == "plain_text"
    assert parsed.value is None
    assert parsed.error


def test_malformed_json_is_classified_without_raising():
    parsed = parse_manual_ai_payload('{"results": [}')
    assert parsed.kind == "malformed_json"
    assert parsed.value is None
    assert parsed.error


def test_valid_non_object_json_is_rejected():
    parsed = parse_manual_ai_payload('["not", "an", "object"]')
    assert parsed.kind == "non_object_json"
    assert parsed.value is None
