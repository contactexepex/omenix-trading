"""The scores report (story "Outcome and scores"): per underlying the session-first summary, the verdict at the fixed
looks, descriptive buckets by |delta| and by days to expiry (never decided on), unscored rows by reason, and the late
issues (scored, marked). An issue whose next session is still ahead is pending, not unscored."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date

from .constants import DAYS_BUCKETS, DELTA_BUCKETS, RULE, SCORE_SCHEMA
from .scores import Scored, score_record
from .sessions import looks, session_of, summary


@dataclass(frozen=True)
class Issued:
    record: dict
    next_record: dict | None  # G13's record of d+, None when there is none
    late: bool


def _name(low, high, unit: str) -> str:
    return f"{low}+{unit}" if high is None else f"{low}-{high}{unit}"


def _buckets(days: Sequence[tuple[str, list[Scored]]]) -> dict:
    out = {}
    for field, buckets, unit in (("delta_bucket", DELTA_BUCKETS, " |delta|"), ("days_bucket", DAYS_BUCKETS, " days")):
        for i, (low, high) in enumerate(buckets):
            found = [session_of(day, [r for r in rows if getattr(r, field) == i]) for day, rows in days]
            out[_name(low, high, unit)] = summary([s for s in found if s is not None])
    return out


def underlying_report(entries: Iterable[Issued], today: date) -> dict:
    days, unscored, late, pending = [], Counter(), 0, []
    for entry in sorted(entries, key=lambda e: e.record["day"]):
        if date.fromisoformat(entry.record["next_session"]) > today:
            pending.append(entry.record["day"])
            continue
        scored, missing = score_record(entry.record, entry.next_record)
        unscored.update(missing)
        late += entry.late
        days.append((entry.record["day"], scored))
    sessions = [s for s in (session_of(day, rows) for day, rows in days) if s is not None]
    return {"rule": RULE, "issued_days": len(days) + len(pending), "pending_days": pending,
            "late_issues": late, "unscored": dict(sorted(unscored.items())), **summary(sessions),
            "looks": looks(sessions), "buckets": _buckets(days)}  # fmt: skip


def score_report(by_underlying: dict[str, list[Issued]], today: date, method_sha256: str) -> dict:
    return {
        "schema": SCORE_SCHEMA,
        "as_of": today.isoformat(),
        "method_sha256": method_sha256,
        "underlyings": {u: underlying_report(entries, today) for u, entries in sorted(by_underlying.items())},
    }


def summary_lines(report: dict) -> list[str]:
    lines = []
    for underlying, r in report["underlyings"].items():
        rule = r["methods"].get(RULE, {})
        lines.append(f"{underlying}: {r['sessions']} scored sessions ({r['rows']} rows), {len(r['pending_days'])} "
                     f"pending, {r['late_issues']} late; rule inside 90% {rule.get('inside_90')}, inside 50% "
                     f"{rule.get('inside_50')}; rule minus decay_only {r['minus_decay_only']['mean']}; "
                     f"{r['looks']['status']}")  # fmt: skip
    return lines
