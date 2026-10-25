"""One pass over the circular feeds (story A20b). Every circular not seen before is listed in the run that first sees
it, with its first-seen time and its file status (`saved`, `failed`, `not_kept` when not F&O-relevant). A failed file
is retried by later runs for 3 days: a retry writes a new row for the same link, carrying the first row's first-seen
time, with `saved` or, after 3 days, `abandoned`. The run's new rows form one part of `circulars/list` (O9)."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, date, datetime, timedelta

from ..models import now_utc
from ..storage.data_store import DataStore
from ..storage.part_table import PartTable
from .feeds import CircularFeed
from .model import ABANDONED, COLUMNS, FAILED, NOT_KEPT, SAVED, Circular, FeedFailed, Problem

LIST_TABLE, FILES_FOLDER = "circulars/list", "circulars/files"
WINDOW = timedelta(days=14)  # every NSE run asks 14 days back: a gap of dropped runs up to 14 days loses nothing
RETRY_FOR = timedelta(days=3)
FEED_LINE = "{source}: {listed} listed, {new} new, {files} file(s) saved"
RETRY_LINE = "retried files: {saved} saved, {abandoned} abandoned, {failing} still failing"
FEED_FAILED = "{source}: list NOT read: {error}"
FILE_FAILED = "{source} {number}: file NOT saved (listed as failed; retried for 3 days): {error}"
FILE_ABANDONED = "{source} {number}: file still failing after 3 days, abandoned: {link}"
LIST_NOT_SAVED = "the run's new circulars NOT saved to Drive (the next run lists them again): {error}"
MAY_HAVE_SKIPPED = (
    "{source}: none of the {listed} circulars on its latest page was seen before: some may have been missed "
    "between runs (check the publisher's full list)"
)
Freshness = Callable[[str, Sequence[Circular], date], Problem | None]


def file_path(circular: Circular) -> str:
    return f"{FILES_FOLDER}/{circular.source}/{circular.issued_on:%Y/%m}/{circular.filename}"


def latest_rows(rows: Sequence[dict]) -> dict[str, tuple[str, dict]]:
    """Link -> (earliest first_seen_at, latest row): the rows come in path order, by day then by run."""
    known: dict[str, tuple[str, dict]] = {}
    for row in rows:
        first = known[row["link"]][0] if row["link"] in known else row["first_seen_at"]
        known[row["link"]] = (first, row)
    return known


class CircularCapture:
    def __init__(self, feeds: Mapping[str, CircularFeed], freshness: Mapping[str, Freshness],
                 relevant: Callable[[Circular], bool], store: DataStore,
                 clock: Callable[[], datetime] = lambda: now_utc(), out=print):  # fmt: skip
        self.feeds, self.freshness, self.relevant, self.store = feeds, freshness, relevant, store
        self.clock, self.out = clock, out
        self.table = PartTable(store, LIST_TABLE, COLUMNS)

    def run(self, today: date, rows: Sequence[dict]) -> list[Problem]:
        """Captures every feed and retries failed files; returns the run's problems. `rows`: every row listed so far."""
        known, problems, new_rows = latest_rows(rows), [], []
        for source, feed in self.feeds.items():
            new_rows += self._capture(source, feed, today, known, {r["source"] for r in rows}, problems)
        new_rows += self._retry(known, problems)
        if new_rows:
            try:
                self.table.write(today, new_rows)
            except (OSError, RuntimeError, ValueError) as exc:  # Drive: the run's other problems are kept too
                problems.append(Problem("list-part", LIST_NOT_SAVED.format(error=exc)))
        return problems

    def _capture(self, source: str, feed: CircularFeed, today: date, known: Mapping, seen_sources: set[str],
                 problems: list[Problem]) -> list[dict]:  # fmt: skip
        try:
            listed = feed.fetch(today - WINDOW, today)  # one circular per link (the feed merges NSE's repeats)
        except (FeedFailed, ValueError) as exc:  # unreadable, or a date the feed's layout cannot hold
            problems.append(Problem(f"{source}:list", FEED_FAILED.format(source=source, error=exc)))
            return []
        if stale := self.freshness[source](source, listed, today):
            problems.append(stale)
        if feed.LATEST_PAGE_ONLY and source in seen_sources and not any(c.link in known for c in listed):
            problems.append(Problem(f"{source}:gap", MAY_HAVE_SKIPPED.format(source=source, listed=len(listed))))
        first_seen_at = self.clock().astimezone(UTC).isoformat()
        rows = [self._first_row(feed, c, first_seen_at, problems) for c in listed if c.link not in known]
        files = sum(row["file"] == SAVED for row in rows)
        self.out(FEED_LINE.format(source=source, listed=len(listed), new=len(rows), files=files))
        return rows

    def _first_row(self, feed: CircularFeed, circular: Circular, first_seen_at: str, problems: list[Problem]) -> dict:
        relevant = self.relevant(circular)
        status = self._save(feed, circular, problems) if relevant else NOT_KEPT
        return circular.row(relevant, first_seen_at, status)

    def _save(self, feed: CircularFeed, circular: Circular, problems: list[Problem]) -> str:
        if self.store.receipts.read(f"{self.store.area}/{file_path(circular)}") is not None:
            return SAVED  # saved by a run whose list part failed: the receipted copy stands (write-once)
        try:
            self.store.put(file_path(circular), feed.download(circular))
            return SAVED
        except (
            OSError,
            RuntimeError,
            ValueError,
        ) as exc:  # refused, Drive (requests errors are OSError), a changed file
            text = FILE_FAILED.format(source=circular.source, number=circular.number, error=exc)
            problems.append(Problem(f"file:{circular.source}:{circular.number}", text))
            return FAILED

    def _retry(self, known: Mapping[str, tuple[str, dict]], problems: list[Problem]) -> list[dict]:
        rows, now, counts = [], self.clock().astimezone(UTC), {SAVED: 0, ABANDONED: 0, FAILED: 0}
        for first_seen_at, row in known.values():
            if row["file"] != FAILED or row["source"] not in self.feeds:
                continue
            circular, tried = Circular.from_row(row), []
            status = self._save(self.feeds[row["source"]], circular, tried)
            if status == FAILED and now - datetime.fromisoformat(first_seen_at) > RETRY_FOR:
                status = ABANDONED
                text = FILE_ABANDONED.format(source=circular.source, number=circular.number, link=circular.link)
                tried = [Problem(f"file:{circular.source}:{circular.number}:abandoned", text, episode=False)]
            problems += tried
            counts[status] += 1
            if status != FAILED:  # a row only when the status changes
                rows.append(circular.row(True, first_seen_at, status))
        if any(counts.values()):
            self.out(RETRY_LINE.format(saved=counts[SAVED], abandoned=counts[ABANDONED], failing=counts[FAILED]))
        return rows
