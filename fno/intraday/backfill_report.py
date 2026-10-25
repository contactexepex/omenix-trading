"""What a back-fill run prints (story A16b): the windows, every session whose later answer differs from the copy kept,
every deferred session with how many runs have deferred it, the void share and void sessions by reason, and the
pre-open check, as counts. Never a level."""

from __future__ import annotations

from collections import Counter

from .backfill import BackfillReport
from .minute_check import beyond
from .session_rv import VOID, VOID_SHARE_FLAG, VOID_SHARE_LIMIT


def report_lines(report: BackfillReport, rows: list[dict], deferral_counts: Counter) -> list[str]:
    """`rows`: every written row of the requested sessions (this run's and earlier ones)."""
    lines = list(report.windows) + [f"CHANGED {change}" for change in report.changed]
    for day, reason in sorted(report.deferred.items()):
        lines.append(
            f"DEFERRED {day}: {reason} (deferred by {deferral_counts.get(day.isoformat(), 1)} run(s), never written)"
        )
    void = [r for r in rows if r["status"] == VOID]
    reasons = Counter(reason.split(":")[0] for r in void for reason in r["void_reason"].split("; ") if reason)
    share = len(void) / len(rows) if rows else 0.0
    flag = VOID_SHARE_FLAG if share > VOID_SHARE_LIMIT else ""
    checked = [r for r in rows if r["nse_open_gap"]]
    pre_open = [r["session"] for r in checked if beyond(float(r["nse_open_gap"]))]
    provenance = Counter(r["provenance"] for r in rows)
    lines += [
        f"sessions {len(report.sessions)}: {len(report.written)} written now, {report.held} held before, "
        f"{len(report.deferred)} deferred",
        f"void {len(void)} of {len(rows)} ({share:.1%}){flag}; by reason: {dict(sorted(reasons.items())) or 'none'}",
        f"provenance: {dict(sorted(provenance.items())) or 'none'}",
        f"pre-open gap above 0.05 on {len(pre_open)} of {len(checked)} sessions with a 1-minute answer"
        + (f": {', '.join(pre_open)}" if pre_open else ""),
    ]
    lines += _void_sessions(void)
    return lines + ([f"STOPPED: {report.stopped}"] if report.stopped else [])


def _void_sessions(void: list[dict]) -> list[str]:
    """Every void session by date under each of its reasons (a short or halted session is listed, never excluded)."""
    by_reason: dict[str, list[str]] = {}
    for row in void:
        for reason in filter(None, row["void_reason"].split("; ")):
            by_reason.setdefault(reason.split(":")[0], []).append(row["session"])
    return [f"void {reason}: {', '.join(sorted(days))}" for reason, days in sorted(by_reason.items())]
