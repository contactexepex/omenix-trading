"""Groww's and NSE's 3 pm snapshots side by side (story O6, owner's choice (a)): nothing switches to NSE until the
owner has seen how far the two disagree. Per day, from each source's canonical snapshot: when it was captured (and
NSE's page time), how many contracts each has and which strikes only one has, and over the contracts both quote
validly, the median gap between their mids and each source's median spread (ask minus bid)."""

from __future__ import annotations

import csv
import json
from datetime import date, datetime
from pathlib import Path
from statistics import median

from ..storage.raw_store import RawFileStore
from .recorder import DATASET, NONE_MARKER, NSE_DATASET, QuoteSnapshotRecorder

DAY_LINE = (
    "{day}: captured groww {g_at}, nse {n_at} (NSE page time {page}); contracts groww {g_n}, nse {n_n}; "
    "only groww {only_g}, only nse {only_n}; both valid {both}: median |mid gap| {gap}, "
    "median spread groww {g_spread}, nse {n_spread}"
)
ONE_SIDE_LINE = "{day}: groww {groww}; nse {nse} (no comparison)"
NO_DAYS = "no day has a snapshot from either source yet"


def _canonical_days(folder: Path) -> list[date]:
    days = set()
    for dataset in (DATASET, NSE_DATASET):
        for marker in (folder / dataset).glob("*/*/nifty_*.canonical"):
            days.add(datetime.strptime(marker.stem, "nifty_%Y%m%d").date())
    return sorted(days)


def _snapshot(store: RawFileStore, dataset: str, day: date) -> tuple[dict, dict] | None:
    """(meta, rows keyed by expiry, strike and type) of the day's canonical snapshot, or None."""
    marker = store.get(QuoteSnapshotRecorder.path(day, f"nifty_{day:%Y%m%d}.canonical", dataset))
    snapshot_id = marker.decode().strip() if marker else NONE_MARKER
    if snapshot_id == NONE_MARKER:
        return None
    meta = json.loads(store.get(QuoteSnapshotRecorder.path(day, f"{snapshot_id}.meta.json", dataset)))
    rows = csv.DictReader(
        store.get(QuoteSnapshotRecorder.path(day, f"{snapshot_id}.csv", dataset)).decode().splitlines()
    )
    return meta, {(r["expiry"], r["strike"], r["type"]): r for r in rows}


def _two_sided(row: dict) -> tuple[float, float] | None:
    """(mid, spread) of a valid row."""
    if row["valid"] != "true":
        return None
    bid, ask = float(row["bid"]), float(row["ask"])
    return (bid + ask) / 2, ask - bid


def _median(values: list[float]) -> str:
    return f"{median(values):.2f}" if values else "-"


def day_line(day: date, groww: tuple[dict, dict], nse: tuple[dict, dict]) -> str:
    (g_meta, g_rows), (n_meta, n_rows) = groww, nse
    both = [(_two_sided(g_rows[k]), _two_sided(n_rows[k])) for k in g_rows.keys() & n_rows.keys()]
    both = [(g, n) for g, n in both if g and n]
    page = next((r["quote_time"][11:19] for r in n_rows.values() if r["quote_time"]), "-")
    return DAY_LINE.format(
        day=day, g_at=g_meta["started_at"][11:19], n_at=n_meta["started_at"][11:19], page=page,
        g_n=len(g_rows), n_n=len(n_rows), only_g=len(g_rows.keys() - n_rows.keys()),
        only_n=len(n_rows.keys() - g_rows.keys()), both=len(both),
        gap=_median([abs(g[0] - n[0]) for g, n in both]),
        g_spread=_median([g[1] for g, _ in both]), n_spread=_median([n[1] for _, n in both]),
    )  # fmt: skip


def compare_lines(folder: Path, store: RawFileStore) -> list[str]:
    """`folder` is the repository's quote folder (the days come from its canonical markers); the snapshots are read
    through `store`, which holds Groww's quote files in Drive (A4b)."""
    lines = []
    for day in _canonical_days(folder):
        groww, nse = _snapshot(store, DATASET, day), _snapshot(store, NSE_DATASET, day)
        if groww and nse:
            lines.append(day_line(day, groww, nse))
        else:
            state = {True: "recorded", False: "none"}
            lines.append(ONE_SIDE_LINE.format(day=day, groww=state[bool(groww)], nse=state[bool(nse)]))
    return lines or [NO_DAYS]
