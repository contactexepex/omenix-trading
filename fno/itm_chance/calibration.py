"""The calibration table of one row set (story section 2): per horizon bucket and chance bin the rows, the distinct
expiries, the mean chance and the observed frequency; per bucket the Brier score and its reliability part. Every 95%
interval comes from one cluster bootstrap that resamples whole expiries (2,000 draws, fixed seed): rows of one expiry
share one settlement, so they are never treated as independent."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from .constants import BIN_EDGES, DRAWS, HORIZON_BUCKETS, INTERVAL, SEED
from .rows import Row, bin_name, bin_of, bucket_name, bucket_of

N, SP, SY, SP2, SPY = range(5)  # the sums kept per expiry, bucket and bin


def sums(rows: Sequence[Row]) -> tuple[list, np.ndarray]:
    """The expiries in date order and their sums, shape (expiries, buckets, bins, 5)."""
    expiries = sorted({r.expiry for r in rows})
    where = {e: i for i, e in enumerate(expiries)}
    out = np.zeros((len(expiries), len(HORIZON_BUCKETS), len(BIN_EDGES) - 1, 5))
    for r in rows:
        out[where[r.expiry], bucket_of(r.days), bin_of(r.p)] += (1.0, r.p, r.y, r.p * r.p, r.p * r.y)
    return expiries, out


def statistics(total: np.ndarray) -> dict[str, np.ndarray]:
    """From summed rows (..., buckets, bins, 5): per bin mean chance and frequency, per bucket Brier and reliability
    (NaN where there are no rows)."""
    n = total[..., N]
    with np.errstate(invalid="ignore", divide="ignore"):
        mean_p, freq = total[..., SP] / n, total[..., SY] / n
        rows = n.sum(axis=-1)
        brier = (total[..., SP2] - 2 * total[..., SPY] + total[..., SY]).sum(axis=-1) / rows
        gap = np.where(n > 0, n * (mean_p - freq) ** 2, 0.0)
        reliability = gap.sum(axis=-1) / rows
    return {"mean_p": mean_p, "frequency": freq, "brier": brier, "reliability": reliability}


def bootstrap(per_expiry: np.ndarray, draws: int = DRAWS, seed: int = SEED) -> dict[str, np.ndarray]:
    """The statistics of `draws` resamples of whole expiries (with replacement)."""
    count = per_expiry.shape[0]
    rng = np.random.default_rng(seed)
    picks = rng.integers(0, count, size=(draws, count))
    weights = np.stack([np.bincount(p, minlength=count) for p in picks]).astype(float)
    return statistics(np.einsum("de,ebkm->dbkm", weights, per_expiry))


def _interval(values: np.ndarray) -> list[float] | None:
    kept = values[~np.isnan(values)]
    return None if kept.size == 0 else [round(float(v), 6) for v in np.percentile(kept, INTERVAL)]


def _number(value: float) -> float | None:
    return None if np.isnan(value) else round(float(value), 6)


def table(rows: Sequence[Row]) -> dict:
    """The calibration table as plain data (no row-level outcome is shown)."""
    expiries, per_expiry = sums(rows)
    if not expiries:
        return {"rows": 0, "expiries": 0, "buckets": []}
    point, drawn = statistics(per_expiry.sum(axis=0)), bootstrap(per_expiry)
    present = per_expiry[..., N] > 0
    buckets = []
    for b in range(len(HORIZON_BUCKETS)):
        bins = [{"bin": bin_name(k), "rows": int(per_expiry[:, b, k, N].sum()), "expiries": int(present[:, b, k].sum()),
                 "mean_chance": _number(point["mean_p"][b, k]), "frequency": _number(point["frequency"][b, k]),
                 "frequency_interval_95": _interval(drawn["frequency"][:, b, k])}
                for k in range(len(BIN_EDGES) - 1) if present[:, b, k].any()]  # fmt: skip
        buckets.append({"bucket": bucket_name(b), "rows": int(per_expiry[:, b, :, N].sum()),
                        "expiries": int(present[:, b, :].any(axis=1).sum()), "brier": _number(point["brier"][b]),
                        "brier_interval_95": _interval(drawn["brier"][:, b]),
                        "reliability": _number(point["reliability"][b]),
                        "reliability_interval_95": _interval(drawn["reliability"][:, b]), "bins": bins})  # fmt: skip
    return {"rows": len(rows), "expiries": len(expiries), "first_expiry": expiries[0].isoformat(),
            "last_expiry": expiries[-1].isoformat(), "buckets": buckets}  # fmt: skip
