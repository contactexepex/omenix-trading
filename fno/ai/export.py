"""The input a book's routine reads (story F1's allowlisted export): the day's committed v2 pack, the official closes
of the last sessions before the day, a few facts derived from them and, for Hybrid only, the rules' numbers and its
envelope. Built from named files only, so nothing else in the repository (another book's records or submissions, the
history back-fill) can enter it; `export_sha256` (canonical JSON) ties every answer to exactly this input."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
from datetime import date
from pathlib import Path

from .envelope import Envelope
from .paths import CLOSES_FILE, pack_path
from .pointer import BookPointer
from .versions import BookVersion

CLOSES_SESSIONS = 260  # about a year: enough for 20-day base rates, and no 2019-2023 (holdout) row
RV_RETURNS, ANNUAL_SESSIONS = 20, 252


class ExportRefused(ValueError):
    """The committed files do not match the pointer (wrong pack) or an item outside the book's allowlist was asked."""


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def build_export(root: Path, pointer: BookPointer, version: BookVersion) -> dict:
    """The book's input; refuses when the committed pack is not the one the pointer names."""
    pack = _pack(Path(root), pointer)
    closes = recent_closes(Path(root) / CLOSES_FILE, pointer.day)
    export = {
        "book": pointer.book,
        "day": pointer.day.isoformat(),
        "version": version.label,
        "pack_sha256": pointer.pack_sha256,
        "pack": pack,
        "closes_before_day": [{"date": d, "nifty": n, "vix": v} for d, n, v in closes],
        "derived": derived_facts(pack, closes),
    }
    if (pointer.rules is None) != (version.envelope_width is None):
        raise ExportRefused(f"{pointer.book}: rules belong to Hybrid's input only")
    if pointer.rules is not None:
        envelope = Envelope.from_rules(pointer.rules, version.envelope_width)
        export["rules"] = {"by_question": pointer.rules, "envelope": envelope.as_json()}
    return export


def export_sha256(export: dict) -> str:
    return hashlib.sha256(canonical(export)).hexdigest()


def _pack(root: Path, pointer: BookPointer) -> dict:
    path = root / pack_path(pointer.day)
    if not path.is_file():
        raise ExportRefused(f"no committed pack for {pointer.day}: pull main and try again")
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != pointer.pack_sha256:
        raise ExportRefused(f"the committed pack for {pointer.day} is not the one fired")
    return json.loads(data)


def recent_closes(path: Path, day: date) -> list[tuple[str, float, float]]:
    """The last sessions strictly before `day` with both official closes (date, NIFTY 50, India VIX)."""
    if not path.is_file():
        return []
    rows = csv.DictReader(io.StringIO(path.read_text(encoding="utf-8")))
    closes = [(r["date"], float(r["underlying"]), float(r["vix"])) for r in rows
              if r["underlying"] and r["vix"] and r["date"] < day.isoformat()]  # fmt: skip
    return sorted(closes)[-CLOSES_SESSIONS:]


def derived_facts(pack: dict, closes: list[tuple[str, float, float]]) -> dict:
    """Facts computed from the input itself, so neither book spends its minutes on arithmetic: trailing RV20 with the
    15:00 spot standing for today's close (as the live baselines do), and the 15:00 change against yesterday."""
    fields = {f["name"]: f["value"] for f in pack.get("fields", [])}
    spot, vix = fields.get("nifty_spot"), fields.get("india_vix")
    last = closes[-1] if closes else None
    path = [c[1] for c in closes[-RV_RETURNS:]] + ([spot] if spot else [])
    return {
        "trailing_rv20_points_with_1500_spot": realised_vol_points(path),
        "nifty_1500_change_pct_vs_previous_close": (spot / last[1] - 1) * 100 if spot and last else None,
        "vix_1500_change_vs_previous_close": vix - last[2] if vix is not None and last else None,
    }


def realised_vol_points(path: list[float]) -> float | None:
    """B1's RV: root mean square of the daily log returns, not demeaned, times sqrt(252), in points; 20 returns only."""
    returns = [math.log(b / a) for a, b in zip(path, path[1:])]
    if len(returns) != RV_RETURNS:
        return None
    return math.sqrt(ANNUAL_SESSIONS * sum(r * r for r in returns) / RV_RETURNS) * 100
