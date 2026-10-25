"""Claiming a number (story O12): append a registry row on a fresh copy of `main` and push it; git decides the race.

A push to `main` is refused when someone else pushed first, so exactly one claimant wins each number. The loser
re-reads the new `main`, takes the next number and tries again (bounded, with a random pause). A number belongs to
the claimant only once its push is accepted.
"""

from __future__ import annotations

import random
import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from fno.shared.models import now_utc
from fno.shared.numbering.blocks import LEDGER_TRIAL, BlockSeries, parse_block
from fno.shared.numbering.categories import ADDENDUM_OF, CATEGORIES, SLUG, WHOLE, Category
from fno.shared.numbering.git_main import GitMain, MainCopy
from fno.shared.numbering.registry import SEEDED, Row, append_row, next_number, utc_stamp

TRIES = 8
PAUSE_SECONDS = (0.5, 3.0)
CLAIMABLE: dict[str, Category | BlockSeries] = {**CATEGORIES, LEDGER_TRIAL.name: LEDGER_TRIAL}  # story O12e: blocks
MESSAGE = "Number claim: {category} {number} {name}\n\nClaimed by {session} (story O12; lane 3, a status row).\n"


class ClaimRefused(ValueError):
    """The request itself is wrong (bad slug, taken number, unknown report); retrying cannot help."""


class ClaimNotPushed(RuntimeError):
    """Every try lost the race (or the push kept failing); no number was claimed."""


@dataclass(frozen=True)
class Claim:
    category: str
    number: str
    name: str


@dataclass(frozen=True)
class ClaimRequest:
    category: Category | BlockSeries
    slug: str
    session: str
    report: str | None = None  # the report an addendum extends
    exact: str | None = None  # a specific number asked for, instead of the next one (a block `<a>-<b>` for trials)
    count: int | None = None  # ledger trials only: how many ids the block holds (1 when not given)


class NumberClaimer:
    def __init__(
        self,
        git: GitMain,
        clock: Callable[[], datetime] = lambda: now_utc(),
        pause: Callable[[float], None] = time.sleep,
        tries: int = TRIES,
    ):
        self._git, self._clock, self._pause, self._tries = git, clock, pause, tries

    def claim(self, request: ClaimRequest) -> Claim:
        _refuse_bad_request(request)
        with self._git.main_copy() as copy:
            for attempt in range(1, self._tries + 1):
                registry = copy.path / request.category.registry
                number = _number(request, copy)
                name = request.category.claimed_name(number, request.slug)
                append_row(registry, Row(number, name, request.session, utc_stamp(self._clock())))
                message = MESSAGE.format(
                    category=request.category.name, number=number, name=name, session=request.session
                )
                if copy.commit_and_push(request.category.registry, message):
                    return Claim(request.category.name, number, name)
                if attempt < self._tries:
                    self._pause(random.uniform(*PAUSE_SECONDS))  # pause first, so the retry reads the newest main
                    copy.reset_to_main()
        raise ClaimNotPushed(f"no {request.category.name} number claimed: {self._tries} pushes to main were refused")


def _refuse_bad_request(request: ClaimRequest) -> None:
    if not SLUG.fullmatch(request.slug):
        raise ClaimRefused(f"slug {request.slug!r}: use lower-case letters and digits joined by '-' or '_'")
    if not request.session.strip() or request.session == SEEDED:
        raise ClaimRefused(f"name the claiming session (--session); {SEEDED!r} is reserved for the seeded history")
    is_addendum = request.category.name in ADDENDUM_OF
    if is_addendum != (request.report is not None):
        raise ClaimRefused(f"{request.category.name}: --report is {'required' if is_addendum else 'not allowed'}")
    if isinstance(request.category, BlockSeries):
        _refuse_bad_block(request)
    elif request.count is not None:
        raise ClaimRefused(f"{request.category.name}: --count is for ledger-trial blocks only")
    elif request.exact is not None and not re.fullmatch(WHOLE, request.exact):
        raise ClaimRefused(f"--number {request.exact!r}: a whole number from 1")


def _refuse_bad_block(request: ClaimRequest) -> None:
    if request.count is not None and request.count < 1:
        raise ClaimRefused(f"--count {request.count}: at least 1")
    if request.exact is not None and (request.count is not None or parse_block(request.exact) is None):
        raise ClaimRefused(f"--number {request.exact!r}: a block <a>-<b> with a <= b (or one id), without --count")


def _number(request: ClaimRequest, copy: MainCopy) -> str:
    """The next free number, or the exact one asked for; a number is taken by a registry row or by a file (or
    heading) already on `main`, so a file written without a claim is never handed out again."""
    category = request.category
    if isinstance(category, BlockSeries):
        return _block(category, request, copy)
    if request.report is not None and request.report not in copy.taken(ADDENDUM_OF[category.name]):
        raise ClaimRefused(f"{category.name}: report {request.report} is not on main")
    taken = copy.taken(category)
    if request.exact is None:
        return next_number(category, taken, request.report)
    number = f"{request.report}.{request.exact}" if request.report is not None else request.exact
    if number in taken:
        raise ClaimRefused(f"{category.name} {number} is already taken")
    return number


def _block(series: BlockSeries, request: ClaimRequest, copy: MainCopy) -> str:
    """Story O12e: the next free block of `count` ids on `main`, or the exact block asked for when nothing on `main`
    (a block or a ledger id) overlaps it."""
    if request.exact is None:
        return series.next_block(copy.path, request.count or 1)
    taken = series.overlapping(copy.path, parse_block(request.exact))
    if taken:
        raise ClaimRefused(f"{series.name} {request.exact} overlaps {', '.join(b.text for b in taken)} on main")
    return request.exact
