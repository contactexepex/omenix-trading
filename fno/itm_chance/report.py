"""One underlying's calibration report (story section 2): the settled expiries and their outcome source, the
cross-check problems, and the calibration table for all sources together, each source apart and, at an expiry-day
change, each regime apart. No `made_at`: a rerun on the same inputs is byte-identical, so the write-once store makes
it a no-op."""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Callable, Iterable
from datetime import date

from .calibration import table
from .chances import ExpiryChances, expiry_chances
from .constants import EXPLORATORY, MEASURE, SCHEMA, SOURCE_3PM, SOURCE_ALL, SOURCE_EOD, TAIL_NOTE, UNIT_NOTE
from .rows import Row, of_source, rows_for
from .settlement import Settled

TUESDAY, THURSDAY = 1, 3
NUMBERS = re.compile(r"\d[\d.,]*")


def chances_of(records: Iterable[dict], underlying: str) -> list[ExpiryChances]:
    return [e for record in records if record["underlying"] == underlying for e in expiry_chances(record)]


def regime_start(expiries: Iterable[date]) -> date | None:
    """The first Tuesday expiry after which no expiry falls on a Thursday (NIFTY's move from Thursday to Tuesday),
    read from the records' own expiries; None when there is no such change."""
    ordered = sorted(set(expiries))
    for i, e in enumerate(ordered):
        before, after = ordered[:i], ordered[i:]
        if (
            e.weekday() == TUESDAY
            and any(x.weekday() == THURSDAY for x in before)
            and all(x.weekday() != THURSDAY for x in after)
        ):
            return e
    return None


def _settlement_dict(s: Settled, issue_days: int) -> dict:
    """`issue_days`: the record days with a distribution for this expiry (what leaving it out costs)."""
    return {"expiry": s.expiry.isoformat(), "price": s.price, "source": s.source, "official_close": s.close,
            "problem": s.problem, "issue_days": issue_days}  # fmt: skip


def reason_kind(reason: str) -> str:
    """A reason with its numbers replaced, so reasons of one kind are counted together."""
    return NUMBERS.sub("n", reason)


def _slices(rows: list[Row], start: date | None) -> dict:
    slices = {source: table(of_source(rows, source)) for source in (SOURCE_ALL, SOURCE_3PM, SOURCE_EOD)}
    if start is not None:
        together = of_source(rows, SOURCE_ALL)
        slices[f"expiries before {start}"] = table([r for r in together if r.expiry < start])
        slices[f"expiries from {start}"] = table([r for r in together if r.expiry >= start])
    return slices


def calibration_report(underlying: str, records: Iterable[dict], settle: Callable[[str, date], Settled],
                       as_of: date, methods: dict[str, str]) -> dict:  # fmt: skip
    """`settle(underlying, expiry)`: the outcome of one expiry; only expiries on or before `as_of` are asked."""
    expiries = chances_of(records, underlying)
    asked = sorted({e.expiry for e in expiries if e.expiry <= as_of})
    settled = {expiry: settle(underlying, expiry) for expiry in asked}
    usable = sorted(e for e, s in settled.items() if s.usable)
    rows = rows_for(expiries, settled)
    start = regime_start(e.expiry for e in expiries)
    no_chance = Counter(reason_kind(e.reason) for e in expiries if e.distribution is None)
    days = Counter(e.expiry for e in expiries if e.distribution is not None)
    entries = {expiry: _settlement_dict(s, days[expiry]) for expiry, s in settled.items()}
    return {
        "schema": SCHEMA, "underlying": underlying, "as_of": as_of.isoformat(), "methods": methods,
        "measure": MEASURE, "notes": [EXPLORATORY, TAIL_NOTE, UNIT_NOTE],
        "settled_expiries": [e.isoformat() for e in usable],
        "last_settled_expiry": usable[-1].isoformat() if usable else None,
        "outcome_sources": dict(sorted(Counter(settled[e].source for e in usable).items())),
        "outcome_counts": dict(sorted(Counter(s.outcome for s in settled.values()).items())),
        "settlements": list(entries.values()),
        "left_out": [entries[e] for e, s in settled.items() if not s.usable],
        "expiry_day_change": start.isoformat() if start else None,
        "expiries_without_distribution": dict(sorted(no_chance.items())),
        "slices": _slices(rows, start),
    }  # fmt: skip


def summary_lines(report: dict) -> list[str]:
    together = report["slices"][SOURCE_ALL]
    lines = [f"{report['underlying']}: {len(report['settled_expiries'])} settled expiries "
             f"({report['outcome_counts']}), {len(report['left_out'])} left out; "
             f"{together['rows']} rows over {together['expiries']} expiries; {MEASURE}"]  # fmt: skip
    lines += [f"  left out {s['expiry']}: {s['problem']} ({s['issue_days']} issue days)" for s in report["left_out"]]
    for b in together["buckets"]:
        lines.append(f"  {b['bucket']}: Brier {b['brier']} {b['brier_interval_95']}, reliability {b['reliability']}, "
                     f"n expiries {b['expiries']}")  # fmt: skip
    return lines
