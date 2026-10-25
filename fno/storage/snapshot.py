"""State that changes over time, kept write-once (story O9, rule 2): each change is a new file
`<name>/<run_id>.json` (run_id starts with the UTC time, so names sort by time) and the reader takes the newest.
Replaces the in-place overwrite of Drive's `index/` and `paper/` files."""

from __future__ import annotations

import json
from pathlib import Path

from .data_store import DataStore
from .raw_store import path_parts
from .receipts import Receipt

SNAPSHOT_SUFFIX = ".json"


def snapshot_path(name: str, run_id: str) -> str:
    return f"{name}/{run_id}{SNAPSHOT_SUFFIX}"


def write_snapshot(store: DataStore, name: str, state: dict) -> Receipt:
    path_parts(name)
    data = json.dumps(state, sort_keys=True, indent=1).encode("utf-8")
    return store.put(snapshot_path(name, store.run_id), data)


def latest_snapshot(folder: Path) -> dict | None:
    """The newest state in a snapshot folder on disk (the Drive cache), or None when there is none yet."""
    files = sorted(f for f in Path(folder).glob(f"*{SNAPSHOT_SUFFIX}") if not f.name.startswith("."))
    return json.loads(files[-1].read_text(encoding="utf-8")) if files else None
