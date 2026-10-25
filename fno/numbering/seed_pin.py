"""The seed pin (story O12): the seeded history of each registry, fixed by its SHA-256 in a code file.

Seeded rows (session `existing`) may repeat a number, so adding one later could hide a new clash. Their SHA-256 per
category lives in `fno/numbering/seed_pins.json`; changing it is a code change (lane 1, judged), never a claim.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from fno.numbering.registry import Row

PINS = "fno/numbering/seed_pins.json"


def seeded_digest(rows: list[Row]) -> str:
    return hashlib.sha256("".join(row.as_line() for row in rows if row.seeded).encode()).hexdigest()


def read_pins(root: Path) -> dict[str, str]:
    path = root / PINS
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def write_pins(root: Path, pins: dict[str, str]) -> None:
    (root / PINS).parent.mkdir(parents=True, exist_ok=True)
    (root / PINS).write_text(json.dumps(pins, indent=2, sort_keys=True) + "\n", encoding="utf-8")
