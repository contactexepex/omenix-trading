"""The seed of the weekly transcript-audit draw (owner's condition 1; judge 62 addenda 1 and 2). The week's label
alone is predictable, so the seed also takes NSE's official NIFTY 50 close of the week's last session: nobody controls
it and nobody knows it until the week is over. The repository's closes file only says which day and which archived
file (its SHA-256); the close itself is read from that file in the Drive archive, which the routines cannot reach. A
close the archive does not confirm, or a disagreement between the file and the archive, refuses the week's draw
(fails closed). A week is a candidate only once a later week's close is in, so its last close is final."""

from __future__ import annotations

import csv
import hashlib
import io
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from .close_archive import CloseArchive, SeedRefused

Week = tuple[int, int]  # ISO year and week number
REFUSED = "Omenix F&O AI audit draw for {week} refused: {reason}"


@dataclass(frozen=True)
class WeekSeed:
    week: str  # e.g. 2026-W43
    close_date: str  # the week's last session
    nifty_close: str  # NIFTY 50's official close that day, as read from the Drive archive
    index_sha256: str  # the archived index-close file it was read from

    @property
    def value(self) -> int:
        return int(hashlib.sha256(f"{self.week}|{self.close_date}|{self.nifty_close}".encode()).hexdigest(), 16)


@dataclass(frozen=True)
class LastClose:
    day: str
    underlying: str  # the closes file's NIFTY 50 close (checked against the archive, never used as the seed)
    index_sha256: str


def week_label(week: Week) -> str:
    return f"{week[0]}-W{week[1]:02d}"


def final_last_closes(closes_file: Path) -> dict[Week, LastClose]:
    """Each week's last session in the closes file, for weeks a later week's close follows."""
    if not closes_file.is_file():
        return {}
    last: dict[Week, LastClose] = {}
    for row in csv.DictReader(io.StringIO(closes_file.read_text(encoding="utf-8"))):
        week = date.fromisoformat(row["date"]).isocalendar()[:2]  # a blank close still counts: it is refused later
        if week not in last or row["date"] > last[week].day:
            last[week] = LastClose(row["date"], row["underlying"], row["index_sha256"])
    newest = max(last, default=None)
    return {w: c for w, c in last.items() if w != newest}


def verified_seeds(
    closes_file: Path, archive: CloseArchive, weeks: set[Week]
) -> tuple[dict[Week, WeekSeed], list[str]]:
    """Seeds of the `weeks` (those with sessions to draw from) whose last close the archive confirms, and one line per
    week it refused."""
    seeds, refused = {}, []
    for week, close in sorted(final_last_closes(closes_file).items()):
        if week not in weeks:
            continue
        try:
            _require_last_session(archive, date.fromisoformat(close.day))
            archived = archive.nifty_close(date.fromisoformat(close.day), close.index_sha256)
            if float(close.underlying) != archived:
                raise SeedRefused(f"{close.day}: the closes file says {close.underlying}, the archive {archived!r}")
            seeds[week] = WeekSeed(week_label(week), close.day, repr(archived), close.index_sha256)
        except (SeedRefused, ValueError) as reason:
            refused.append(REFUSED.format(week=week_label(week), reason=reason))
    return seeds, refused


def _require_last_session(archive: CloseArchive, day: date) -> None:
    """The closes file's last day of the week must be the week's last archived session: a deleted row must not move
    the seed to an earlier close."""
    for later in (day + timedelta(days=n) for n in range(1, 7 - day.weekday())):
        if archive.has_file(later):
            raise SeedRefused(f"{later}: archived in Drive but missing from the closes file")
