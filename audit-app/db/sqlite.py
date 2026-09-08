from __future__ import annotations

import sqlite3
from pathlib import Path

DEFAULT_BUSY_TIMEOUT_MS = 30_000


def connect_sqlite(
    path: str | Path,
    *,
    readonly: bool = False,
    busy_timeout_ms: int = DEFAULT_BUSY_TIMEOUT_MS,
) -> sqlite3.Connection:
    db_path = Path(path)
    if not readonly:
        db_path.parent.mkdir(parents=True, exist_ok=True)

    timeout_seconds = max(float(busy_timeout_ms) / 1000.0, 0.001)

    if readonly:
        con = sqlite3.connect(
            f"file:{db_path}?mode=ro",
            uri=True,
            timeout=timeout_seconds,
        )
    else:
        con = sqlite3.connect(
            db_path,
            timeout=timeout_seconds,
        )

    con.row_factory = sqlite3.Row
    con.execute(f"PRAGMA busy_timeout={int(busy_timeout_ms)}")
    con.execute("PRAGMA foreign_keys=ON")

    if readonly:
        con.execute("PRAGMA query_only=ON")
    else:
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA synchronous=NORMAL")

    return con
