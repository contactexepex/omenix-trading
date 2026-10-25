"""Which routine sessions must be audited (owner's condition 1, 14 Oct 2026): every session of the first 10 session days
on which the AI books were fired, then 2 sessions a week drawn at random from that week's fired sessions. The draw's
seed is the week and its last session's official NIFTY 50 close, confirmed against the Drive archive (`draw_seed.py`),
so it exists only after the week is over and nobody can know or steer it in advance. Callers pass the verified seeds
(built in `wiring.py`); a week without one is not drawn. Each draw is recorded once with its seed inputs
(`research/forecasts/ai_v1/draws/<YYYY>-W<ww>.json`), so anyone can redraw it. Each protocol's runs are drawn apart,
from their own fire logs into their own `draws/` (`RunTerms`, v2 the default; G11 round 2c): v4's first 10 days are
audited in full, like v2's were."""

from __future__ import annotations

import json
import random
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path

from .draw_seed import Week, WeekSeed
from .run_terms import V2_TERMS, RunTerms
from .transcript_audit import TranscriptAudits

FIRST_DAYS_ALL_AUDITED = 10
WEEKLY_SAMPLE = 2
FIRED_SUFFIX = "_fired.json"


@dataclass(frozen=True, order=True)
class FiredSession:
    day: date
    book: str
    entry: dict  # the fire log's entry: version, session link, time


def fired_sessions(root: Path, terms: RunTerms = V2_TERMS) -> list[FiredSession]:
    """Every book-day of `terms`' protocol that was actually fired, oldest first."""
    found = []
    for path in sorted((Path(root) / terms.folder).glob(f"*/*{FIRED_SUFFIX}")):
        day = date.fromisoformat(path.name.removesuffix(FIRED_SUFFIX))
        for book, entry in sorted(terms.fired_books(json.loads(path.read_text(encoding="utf-8"))).items()):
            if entry.get("fired"):
                found.append(FiredSession(day, book, entry))
    return found


def first_days(sessions: list[FiredSession]) -> set[date]:
    return set(sorted({s.day for s in sessions})[:FIRST_DAYS_ALL_AUDITED])


def weeks_to_draw(sessions: list[FiredSession]) -> set[Week]:
    """The weeks with fired sessions after the first 10 days: the only ones whose seed is needed."""
    first = first_days(sessions)
    return {s.day.isocalendar()[:2] for s in sessions if s.day not in first}


def weekly_draws(sessions: list[FiredSession], seeds: dict[Week, WeekSeed]) -> dict[Week, list[FiredSession]]:
    """The 2 sessions drawn from each week after the first 10 days, for weeks whose seed exists."""
    first, weeks = first_days(sessions), {}
    for s in sessions:
        if s.day not in first:
            weeks.setdefault(s.day.isocalendar()[:2], []).append(s)
    return {week: sorted(random.Random(seeds[week].value).sample(sorted(members), min(WEEKLY_SAMPLE, len(members))))
            for week, members in sorted(weeks.items()) if week in seeds}  # fmt: skip


def sessions_to_audit(sessions: list[FiredSession], seeds: dict[Week, WeekSeed]) -> list[FiredSession]:
    """The sessions the rule selects, audited or not."""
    first = first_days(sessions)
    drawn = [s for chosen in weekly_draws(sessions, seeds).values() for s in chosen]
    return sorted([s for s in sessions if s.day in first] + drawn)


def record_draws(root: Path, seeds: dict[Week, WeekSeed], terms: RunTerms = V2_TERMS) -> list[str]:
    """Writes each new week's draw with its seed inputs (written once); returns the files written."""
    written = []
    for week, chosen in weekly_draws(fired_sessions(root, terms), seeds).items():
        path = Path(root) / terms.draws_folder / f"{seeds[week].week}.json"
        if path.is_file():
            continue
        record = {"seed": asdict(seeds[week]), "drawn": [[s.day.isoformat(), s.book] for s in chosen]}
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(record, sort_keys=True, indent=1) + "\n", encoding="utf-8")
        written.append(str(path.relative_to(root)))
    return written


def audits_due(root: Path, seeds: dict[Week, WeekSeed], terms: RunTerms = V2_TERMS) -> list[FiredSession]:
    """Selected sessions without an audit record yet."""
    audits = TranscriptAudits(root, terms)
    return [s for s in sessions_to_audit(fired_sessions(root, terms), seeds) if audits.get(s.day, s.book) is None]
