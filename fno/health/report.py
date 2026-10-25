"""The health run as text (story O8): one message for #fno-desk, at most one line per check with its bad sessions, plus
a full per-session table for the job's log."""

from __future__ import annotations

from datetime import date

from ..constants import HEALTH_NOT_DUE, HEALTH_PROBLEMS
from .checker import Finding, HealthRun

HEADER = "health {day}: {verdict} ({checks} checks, sessions {first} to {last})"
FAILED = "health check FAILED: {error}"
NO_SESSION = "no session in the window"


def _day(day: date) -> str:
    return f"{day.day} {day:%b}"


def _sessions(findings: list[Finding]) -> str:
    """Sessions with the same status and reason share one part: "missed (none) 14 Oct, 15 Oct"."""
    groups: dict[tuple[str, str], list[date]] = {}
    for f in findings:
        groups.setdefault((f.result.status, f.result.detail), []).append(f.session)
    return "; ".join(f"{status} ({detail}) {', '.join(_day(d) for d in days)}"
                     for (status, detail), days in groups.items())  # fmt: skip


def problem_lines(run: HealthRun) -> list[str]:
    bad = {name: [f for f in run.findings if f.check == name and f.result.status in HEALTH_PROBLEMS]
           for name in run.checks}  # fmt: skip
    lines = [f"- {name}: {_sessions(found)}" for name, found in bad.items() if found]
    if run.missed_runs:
        lines.append(f"- health check did not run on {', '.join(_day(d) for d in run.missed_runs)}")
    return lines + [f"- {warning}" for warning in run.warnings]


def verdict(run: HealthRun) -> str:
    if not run.sessions:
        return NO_SESSION
    count = len(problem_lines(run))
    return f"{count} problem{'s' * (count != 1)}" if count else "all on time"


def message(run: HealthRun) -> str:
    if not run.sessions:
        return f"health {_day(run.run_day)}: {NO_SESSION}"
    header = HEADER.format(day=_day(run.run_day), verdict=verdict(run), checks=len(run.checks),
                           first=_day(run.sessions[0]), last=_day(run.sessions[-1]))  # fmt: skip
    pending = [f"{f.check} {_day(f.session)}" for f in run.findings if f.result.status == HEALTH_NOT_DUE]
    return "\n".join([header, *problem_lines(run), *([f"not due yet: {', '.join(pending)}"] if pending else [])])


def table(run: HealthRun) -> list[str]:
    return [f"{f.check} | {f.session} | {f.result.status} | {f.result.detail}" for f in run.findings]
