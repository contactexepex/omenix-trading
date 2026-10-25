"""The session's public counts (story 3.4, privacy), written and committed by the fleet's single runner (MS-P1c's
assumption: one writer per session): c's outcome counts per road and driver, and the three counts (MS-P1f) per road,
driver and session, codes and whole numbers only. Both files are write-once: the same text again is a no-op."""

import csv
import io
from collections.abc import Callable, Iterable, Sequence
from datetime import date
from pathlib import Path, PurePosixPath
from typing import Protocol

from ..constants import SLOT_1500
from ..contracts.dashcam import ReplayConflict
from ..contracts.records import DecisionRecord
from ..contracts.tickets import OpportunityCounts
from ..dashcam.counts import PublicCountsFile
from ..dashcam.names import counts_path

OPPORTUNITY_HEADER = ("session", "road", "driver", "eligible", "fillable", "executed")
OPPORTUNITY_SUFFIX = ".opportunity.csv"
MARKS_SUFFIX = ".marks.txt"  # the run's marks on the session's record, one per line (MS-P1j)
COMMIT_WHAT = "school counts {session}"
NOT_PUSHED = "counts NOT pushed {session}: {outcome}; the next run of the session pushes them"


class CountsCommitter(Protocol):
    def commit(self, what: str, paths: Sequence[str]) -> str | None:
        """Adds, commits and pushes exactly `paths` (repository-relative), nothing else; None when they are on
        `main`, else the refusal's one line."""


def opportunity_path(session: date, slot: str) -> Path:
    plain = Path(counts_path(session, slot))
    return plain.with_name(plain.stem + OPPORTUNITY_SUFFIX)


def marks_path(session: date, slot: str) -> Path:
    plain = Path(counts_path(session, slot))
    return plain.with_name(plain.stem + MARKS_SUFFIX)


def opportunity_text(counts: Iterable[OpportunityCounts]) -> str:
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(OPPORTUNITY_HEADER)
    rows = sorted(
        (c.session.isoformat(), c.road.value, c.driver_id, c.eligible, c.fillable, c.executed) for c in counts
    )
    writer.writerows(rows)
    return out.getvalue()


class SessionCounts:
    def __init__(self, root: Path, committer: CountsCommitter | None,
                 extra: Callable[[date], tuple[str, ...]] = lambda session: (),
                 alert: Callable[[str], object] = lambda line: None):  # fmt: skip
        """`committer` None writes only (tests, replays); the daily run commits and pushes. `extra(session)`: the
        files the run's session step wrote that the same commit takes (the instructor's counts file and receipts).
        `alert`: #fno-desk for the record, which hears of every refused commit by name."""
        self.root, self.committer, self.extra, self.alert = Path(root), committer, extra, alert
        self.outcomes = PublicCountsFile(self.root)

    def write(self, session: date, slot: str, records: tuple[DecisionRecord, ...],
              counts: tuple[OpportunityCounts, ...]) -> tuple[str, ...]:  # fmt: skip
        """Writes the session's counts and commits them: the refusal's line, if any (see `commit`)."""
        self.outcomes.write(session, slot, records)
        file, text = self.root / opportunity_path(session, slot), opportunity_text(counts)
        if file.is_file() and file.read_text() != text:
            raise ReplayConflict(f"rule broken: {opportunity_path(session, slot)} holds other counts")
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(text)
        return self.commit(session)

    def mark(self, session: date, slot: str, line: str) -> None:
        """Adds `line` to the session's marks once; committed with the counts (MS-P1j)."""
        file = self.root / marks_path(session, slot)
        held = file.read_text().splitlines() if file.is_file() else []
        if line not in held:
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text("".join(f"{m}\n" for m in (*held, line)))

    def marks(self, session: date, slot: str) -> tuple[str, ...]:
        file = self.root / marks_path(session, slot)
        return tuple(file.read_text().splitlines()) if file.is_file() else ()

    def written(self, session: date, slot: str) -> bool:
        return all(
            (self.root / path).is_file() for path in (counts_path(session, slot), opportunity_path(session, slot))
        )

    def commit(self, session: date) -> tuple[str, ...]:
        """Commits and pushes the session's own files not yet on `main`; never the folder. A refusal is alerted by
        name and returned as the run's line (it exits 1); nothing is reported as done, and the next run pushes."""
        if self.committer is None:
            return ()
        refused = self.committer.commit(COMMIT_WHAT.format(session=session), self.files(session))
        if refused is None:
            return ()
        line = NOT_PUSHED.format(session=session, outcome=refused)
        self.alert(line)
        return (line,)

    def files(self, session: date, slot: str = SLOT_1500) -> tuple[str, ...]:
        paths = (counts_path(session, slot), opportunity_path(session, slot), marks_path(session, slot))
        return tuple(str(PurePosixPath(p)) for p in paths) + tuple(self.extra(session))
