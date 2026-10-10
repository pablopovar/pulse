"""Small, file-backed CSS skins for Pulse domains."""

from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path


MAX_CSS_BYTES = 100_000
DOMAIN_PATTERN = re.compile(r"[a-z0-9][a-z0-9.-]*[a-z0-9]\Z")


def skin_directory(research_db: Path) -> Path:
    return Path(os.environ.get("PULSE_SKINS_DIR") or research_db.parent / "skins")


def _domain_name(domain: str) -> str:
    name = domain.lower()
    if not DOMAIN_PATTERN.fullmatch(name) or ".." in name:
        raise ValueError("Invalid domain for skin file.")
    return name


def skin_paths(research_db: Path, domain: str) -> tuple[Path, Path]:
    name = _domain_name(domain)
    folder = skin_directory(research_db)
    return folder / f"{name}.css", folder / f"{name}.json"


def load_skin(research_db: Path, domain: str) -> dict[str, str]:
    css_path, settings_path = skin_paths(research_db, domain)
    mode = "basic"
    try:
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
        if settings.get("mode") == "custom":
            mode = "custom"
    except (OSError, ValueError, AttributeError):
        pass
    try:
        css = css_path.read_text(encoding="utf-8")
    except OSError:
        css = ""
    return {"mode": mode, "css": css}


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(content)
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def save_skin(research_db: Path, domain: str, mode: str, css: str) -> None:
    if mode not in {"basic", "custom"}:
        raise ValueError("Choose Basic or Custom CSS.")
    if len(css.encode("utf-8")) > MAX_CSS_BYTES:
        raise ValueError("CSS must be smaller than 100 KB.")
    if mode == "custom" and not css.strip():
        raise ValueError("Enter CSS before selecting Custom CSS.")
    css_path, settings_path = skin_paths(research_db, domain)
    _atomic_write(css_path, css)
    _atomic_write(settings_path, json.dumps({"mode": mode}) + "\n")


def rendered_css(research_db: Path, domain: str, default_css: str) -> str:
    skin = load_skin(research_db, domain)
    return default_css + ("\n\n" + skin["css"] if skin["mode"] == "custom" else "")


def delete_skin(research_db: Path, domain: str) -> None:
    for path in skin_paths(research_db, domain):
        path.unlink(missing_ok=True)
