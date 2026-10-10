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
    """Return the pre-existing light/legacy CSS and settings paths.

    The unsuffixed CSS file predates paired themes.  It remains the legacy
    light-theme file so existing custom skins keep working without migration.
    """
    name = _domain_name(domain)
    folder = skin_directory(research_db)
    return folder / f"{name}.css", folder / f"{name}.json"


def themed_css_path(research_db: Path, domain: str, variant: str) -> Path:
    if variant not in {"light", "dark"}:
        raise ValueError("Theme variant must be light or dark.")
    name = _domain_name(domain)
    return skin_directory(research_db) / f"{name}.{variant}.css"


def load_skin(research_db: Path, domain: str) -> dict[str, str]:
    legacy_css_path, settings_path = skin_paths(research_db, domain)
    mode = "basic"
    try:
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
        if settings.get("mode") == "custom":
            mode = "custom"
    except (OSError, ValueError, AttributeError):
        pass
    try:
        legacy_css = legacy_css_path.read_text(encoding="utf-8")
    except OSError:
        legacy_css = ""
    try:
        light_css = themed_css_path(research_db, domain, "light").read_text(encoding="utf-8")
    except OSError:
        light_css = legacy_css
    try:
        dark_css = themed_css_path(research_db, domain, "dark").read_text(encoding="utf-8")
    except OSError:
        dark_css = ""
    # css is retained for callers from the one-file skin implementation.
    return {"mode": mode, "css": light_css, "light_css": light_css, "dark_css": dark_css}


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


def save_skin(research_db: Path, domain: str, mode: str, light_css: str, dark_css: str = "") -> None:
    if mode not in {"basic", "custom"}:
        raise ValueError("Choose Basic or Custom CSS.")
    if len(light_css.encode("utf-8")) > MAX_CSS_BYTES or len(dark_css.encode("utf-8")) > MAX_CSS_BYTES:
        raise ValueError("Each CSS file must be smaller than 100 KB.")
    if mode == "custom" and not (light_css.strip() or dark_css.strip()):
        raise ValueError("Enter light or dark CSS before selecting Custom themes.")
    legacy_css_path, settings_path = skin_paths(research_db, domain)
    # Keep the original file in sync as a safe fallback for installations that
    # were created before separate light and dark files existed.
    _atomic_write(legacy_css_path, light_css)
    _atomic_write(themed_css_path(research_db, domain, "light"), light_css)
    _atomic_write(themed_css_path(research_db, domain, "dark"), dark_css)
    _atomic_write(settings_path, json.dumps({"mode": mode}) + "\n")


def rendered_css(research_db: Path, domain: str, default_css: str, variant: str | None = None) -> str:
    skin = load_skin(research_db, domain)
    if variant is not None:
        if variant not in {"light", "dark"}:
            raise ValueError("Theme variant must be light or dark.")
        return skin[f"{variant}_css"] if skin["mode"] == "custom" else ""
    return default_css + ("\n\n" + skin["css"] if skin["mode"] == "custom" else "")


def delete_skin(research_db: Path, domain: str) -> None:
    legacy_css_path, settings_path = skin_paths(research_db, domain)
    for path in (legacy_css_path, settings_path, themed_css_path(research_db, domain, "light"), themed_css_path(research_db, domain, "dark")):
        path.unlink(missing_ok=True)
