"""Writing one calibration report (story section 2): write-once to Drive with its receipt, and nothing at all while
no expiry is settled or when Drive already holds a report for the same last settled expiry."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ..price_distribution.store import DistributionStore
from .folders import CALIBRATION, calibration_path

NONE_SETTLED = "{underlying}: no settled expiry yet: nothing written"
ALREADY = "{underlying}: a report for the last settled expiry {expiry} is already in Drive: nothing written"
WRITTEN = "{underlying}: report written: {path}"


def encode(report: dict) -> bytes:
    return (json.dumps(report, sort_keys=True, indent=1, allow_nan=False) + "\n").encode()


def publish(report: dict, data_root: Path, store: DistributionStore) -> str:
    """`data_root`: the synced Drive cache's `data` folder, where earlier reports are looked for."""
    underlying, last = report["underlying"], report["last_settled_expiry"]
    if last is None:
        return NONE_SETTLED.format(underlying=underlying)
    if any((data_root / CALIBRATION).glob(f"{underlying.lower()}_{last}_*.json")):
        return ALREADY.format(underlying=underlying, expiry=last)
    data = encode(report)
    path = calibration_path(underlying, last, hashlib.sha256(data).hexdigest())
    store.put(path, data)
    return WRITTEN.format(underlying=underlying, path=path)
