from pathlib import Path

import pytest

from services.domain_skin import delete_skin, load_skin, rendered_css, save_skin


def test_domain_css_is_isolated_and_basic_selection_preserves_draft(tmp_path: Path):
    database = tmp_path / "research.db"
    custom = ":root { --skin-brand: #123456; }"

    save_skin(database, "example.com", "custom", custom)
    assert rendered_css(database, "example.com", "basic") == "basic\n\n" + custom
    assert rendered_css(database, "other.com", "basic") == "basic"

    save_skin(database, "example.com", "basic", custom)
    assert rendered_css(database, "example.com", "basic") == "basic"
    assert load_skin(database, "example.com")["css"] == custom
    delete_skin(database, "example.com")
    assert load_skin(database, "example.com") == {"mode": "basic", "css": ""}


def test_invalid_domain_and_oversized_css_are_rejected(tmp_path: Path):
    database = tmp_path / "research.db"
    with pytest.raises(ValueError):
        save_skin(database, "../other.com", "custom", "body {}")
    with pytest.raises(ValueError):
        save_skin(database, "example.com", "custom", "x" * 100_001)
    with pytest.raises(ValueError):
        save_skin(database, "example.com", "custom", "")
