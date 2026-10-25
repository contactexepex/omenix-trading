"""Spread report from recorded 3 pm quote snapshots (story A4): how far ask and bid sit from the middle, by distance
from the money. Uses each day's canonical snapshot only and valid two-sided quotes only. Quotes are not fills."""

from __future__ import annotations

import csv
import io
import statistics as st
from pathlib import Path

from ..storage.raw_store import RawFileStore
from .recorder import DATASET, NONE_MARKER

BANDS = ((0.00, 0.01, "0-1%"), (0.01, 0.02, "1-2%"), (0.02, 0.03, "2-3%"), (0.03, 0.0501, "3-5%"))


def canonical_snapshots(folder: Path, store: RawFileStore, dataset: str = DATASET) -> list[str]:
    """CSV texts of every day's canonical snapshot of a dataset (days marked "none" are skipped). The days come from
    the canonical markers in the repository's quote `folder`; the quote files are read through `store`, which holds
    Groww's in Drive (A4b)."""
    texts = []
    for marker in sorted((folder / dataset).rglob("nifty_*.canonical")):
        name = marker.read_text().strip()
        if name and name != NONE_MARKER:
            path = marker.with_name(f"{name}.csv").relative_to(folder).as_posix()
            texts.append(store.get(path).decode())
    return texts


def spread_report(snapshots: list[str]) -> dict:
    """Per distance band: median and 90th percentile half-spread (Rs) of valid quotes, share invalid, counts."""
    bands = {label: {"half_spreads": [], "invalid": 0, "total": 0} for *_, label in BANDS}
    for text in snapshots:
        for row in csv.DictReader(io.StringIO(text)):
            distance = abs(float(row["strike"]) / float(row["spot"]) - 1)
            label = next((name for low, high, name in BANDS if low <= distance < high), None)
            if label is None:
                continue
            band = bands[label]
            band["total"] += 1
            if row["valid"] == "true":
                band["half_spreads"].append((float(row["ask"]) - float(row["bid"])) / 2)
            else:
                band["invalid"] += 1
    out = {"days": len(snapshots), "bands": {}}
    for label, band in bands.items():
        values = sorted(band["half_spreads"])
        out["bands"][label] = {
            "valid_quotes": len(values),
            "median_half_spread": round(st.median(values), 2) if values else None,
            "p90_half_spread": round(values[int(0.9 * (len(values) - 1))], 2) if values else None,
            "invalid_share": round(band["invalid"] / band["total"], 3) if band["total"] else None,
        }
    return out
