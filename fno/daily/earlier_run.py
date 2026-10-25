"""Story O1, gap F1 (judge 412 add. 2-3, judge 417): a 3 pm part that an earlier run started. Its output and exit code
went with that run, so it ends when its lock frees and its outcome is read from its canonical markers: `ok` "recorded
earlier (commit <sha>)" when every marker names an attempt, `failed` when one is missing or is `none` (the window
ended without a complete attempt: no ok without data, O10). The run cannot stop it, as it did not start it."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import date

from ..quotes.recorder import NONE_MARKER, QuoteSnapshotRecorder
from .processes import Process

QUOTES = "research/data/quotes/"  # the quote store's folder in the checkout (`fno/storage/wiring.py` QUOTES_FOLDER)
NOT_YET_COMMITTED = "not yet committed"
RECORDED_EARLIER = "recorded earlier (commit {commit})"
NO_RECORD = "an earlier run's recorder ended without every canonical marker: {missing}"
ENDED_NONE = "the day ended none, no complete attempt (recorded earlier, commit {commit}): {markers}"


class PartMarkers:
    """A part's canonical markers in the checkout, and the commit that holds them."""

    def __init__(self, root, git):
        self.root, self.git = root, git

    def paths(self, day: date, canonicals: Sequence[tuple[str, str]]) -> list[str]:
        return [QUOTES + QuoteSnapshotRecorder.path(day, f"{stem}_{day:%Y%m%d}.canonical", dataset)
                for dataset, stem in canonicals]  # fmt: skip

    def missing(self, day: date, canonicals: Sequence[tuple[str, str]]) -> list[str]:
        return [path for path in self.paths(day, canonicals) if not (self.root / path).is_file()]

    def ended_none(self, day: date, canonicals: Sequence[tuple[str, str]]) -> list[str]:
        """The markers that say the window ended without a complete attempt."""
        present = (path for path in self.paths(day, canonicals) if (self.root / path).is_file())
        return [path for path in present if (self.root / path).read_text(encoding="utf-8").strip() == NONE_MARKER]

    def recorded(self, day: date, canonicals: Sequence[tuple[str, str]]) -> str | None:
        """The commit holding every marker, `NOT_YET_COMMITTED` when one is still to commit; None if one is missing."""
        if self.missing(day, canonicals):
            return None
        paths = self.paths(day, canonicals)
        if self.git.changed(paths):
            return NOT_YET_COMMITTED
        return self.git("log", "-1", "--format=%h", "--", *paths).stdout.strip() or NOT_YET_COMMITTED


class EarlierRun(Process):
    def __init__(
        self, held: Callable[[], bool], markers: PartMarkers, day: date, canonicals: Sequence[tuple[str, str]]
    ):
        self.held, self.markers, self.day, self.canonicals = held, markers, day, canonicals
        self.code: int | None = None
        self.line = ""

    def poll(self) -> int | None:
        if self.code is None and not self.held():
            self.code, self.line = self._outcome()
        return self.code

    def _outcome(self) -> tuple[int, str]:
        """The exit code and line its recorder would have left, read from the markers."""
        commit = self.markers.recorded(self.day, self.canonicals)
        if not commit:
            return 1, NO_RECORD.format(missing=", ".join(self.markers.missing(self.day, self.canonicals)))
        ended_none = self.markers.ended_none(self.day, self.canonicals)
        if ended_none:
            return 1, ENDED_NONE.format(commit=commit, markers=", ".join(ended_none))
        return 0, RECORDED_EARLIER.format(commit=commit)

    def lines(self) -> list[str]:
        return [self.line] if self.line else []

    def alerted(self) -> bool:
        """Never known: the earlier run may have died before its alert, so a failure is alerted again here (a
        duplicate is better than a silent day; owner, 16 Oct: every failure alerts)."""
        return False

    def stop(self) -> None:
        """Never stopped here: the alert gives the hand fix (stop it, then rerun)."""
