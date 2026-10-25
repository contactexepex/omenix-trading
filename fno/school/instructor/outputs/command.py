"""`python -m fno.school.instructor` (story MS-INS, part e): one session's run (`--session`) or the descriptive review
(`--review FIRST LAST`), a dry run unless `--write`. Off with the school's switch. Registered under MS-P1j's
`fno school` group when j lands (orchestrator, 22 Oct 2026). Nothing is posted anywhere: lines are printed."""

import argparse
from collections.abc import Callable
from datetime import date

from ...constants import SCHOOL_OFF_LINE
from ...settings import school_settings
from ..ports import InstructorKind
from .comparison import sealed_decisions
from .review import ReviewSources, build_review
from .review_text import review_lines
from .why_line import why_line

SESSION_LINE = (
    "instructor {session}: {closed} closed and classified, {attributed} attributed, {rechecked} rechecked{dry}"
)
DRY = " (dry run: nothing written)"
UNREADABLE = "ALERT: outcomes files not readable: {days}"
ORPHANS = "ALERT: corrections naming no outcome on file: {count}"


def parser() -> argparse.ArgumentParser:
    parse = argparse.ArgumentParser(prog="python -m fno.school.instructor")
    group = parse.add_mutually_exclusive_group(required=True)
    group.add_argument("--session", type=date.fromisoformat)
    group.add_argument("--review", nargs=2, type=date.fromisoformat, metavar=("FIRST", "LAST"))
    parse.add_argument("--write", action="store_true", help="write the instructor's own files (default: dry run)")
    return parse


def run(argv, config: dict, wiring, review_sources: Callable[[dict], ReviewSources] | None = None) -> list[str]:
    """`wiring` is the instructor's composition root (a module, or a fake in tests); `review_sources` builds what the
    review reads from MS-P1j's record (`review_wiring.build_review_sources`); without it the review says the three
    counts were not supplied and treats no entry as unfilled."""
    args = parser().parse_args(argv)
    if not school_settings(config).enabled:
        return [SCHOOL_OFF_LINE]
    if args.session:
        return _session(args.session, args.write, config, wiring)
    return _review(*args.review, args.write, wiring, review_sources(config) if review_sources else None)


def _session(session: date, write: bool, config: dict, wiring) -> list[str]:
    result = wiring.build_instructor_run(config).for_session(session, write)
    if write:
        wiring.build_counts_file().write(session, result.classifications)
    rechecked = sum(bool(r.corrects) for r in result.classifications)
    counts = dict(
        closed=len(result.classifications) - rechecked, attributed=len(result.attributions), rechecked=rechecked
    )
    lines = [SESSION_LINE.format(session=session, dry="" if write else DRY, **counts)]
    lines += [UNREADABLE.format(days=", ".join(map(str, result.unreadable)))] if result.unreadable else []
    lines += [ORPHANS.format(count=len(result.orphans))] if result.orphans else []
    return lines + [why_line(r) for r in result.classifications]


def _review(first: date, last: date, write: bool, wiring, sources: ReviewSources | None) -> list[str]:
    reader, store = wiring.build_path_reader(), wiring.build_instructor_store()
    sessions = reader.sessions(first, last)
    read = reader.closed_between(first, last)
    decisions = sealed_decisions(reader.dashcam, sessions)
    unfilled = sources.unfilled(first, last) if sources else frozenset()
    paired = wiring.build_comparison().rows(decisions, read.paths, unfilled)
    review = build_review(first, last, sessions, read, decisions, store, paired, len(reader.orphan_corrections()),
                          sources.counts if sources else None)  # fmt: skip
    if write:
        store.write(last, InstructorKind.PAIRED, paired)
    return review_lines(review) + ([] if write else [DRY.strip()])
