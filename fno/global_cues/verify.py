"""Recomputes every cue table row from the archived copy it names (story A17): the copy is found by its SHA-256 in
the snapshot log, read from the raw archive, its SHA-256 checked, and its value for the row's date compared. Read-only.
"""

from __future__ import annotations

import hashlib
from collections import Counter
from collections.abc import Callable
from datetime import date, datetime

from ..storage.raw_store import RawFileStore
from .collection import UNREADABLE
from .snapshot_log import SnapshotLog
from .source import GlobalCueSource
from .table import provenance

PRIVATE_DIFFERS = "values differ (private cue: values never printed)"


class CueTableVerifier:
    def __init__(self, store: RawFileStore, log: SnapshotLog, next_session: Callable[[date], date]):
        """`next_session`: the first NSE session after a date, to recompute each row's `provenance`."""
        self.store, self.log, self.next_session = store, log, next_session

    def problems(self, source: GlobalCueSource, rows: list[dict[str, str]]) -> list[str]:
        if not rows:
            return []  # the command names an empty table itself
        days = [row["value_date"] for row in rows]
        twice = sorted(d for d, n in Counter(days).items() if n > 1)
        problems = [f"{source.cue} {d}: the table holds this date twice" for d in twice]
        problems += [] if days == sorted(days) else [f"{source.cue}: the table's dates are not in order"]
        paths, parsed, fetched = self.log.paths_by_sha256(source.cue), {}, self.log.fetched_by_sha256(source.cue)
        for row in rows:
            sha256 = row["source_sha256"]
            if sha256 not in parsed:
                parsed[sha256] = self._values(source, paths.get(sha256), sha256)
            values = parsed[sha256]
            if isinstance(values, str):
                problems.append(f"{source.cue} {row['value_date']}: {values}")
            elif values.get(row["value_date"]) != float(row["value"]):
                copy = values.get(row["value_date"])
                shown = PRIVATE_DIFFERS if source.private else f"table {row['value']}, archived copy {copy}"
                problems.append(f"{source.cue} {row['value_date']}: {shown}")
            problems += self._timing(source.cue, row, fetched.get(sha256))
        return problems

    def _values(self, source: GlobalCueSource, path: str | None, sha256: str) -> dict[str, float] | str:
        if path is None:
            return f"no logged copy with SHA-256 {sha256[:12]}"
        data = self.store.get(path)
        if data is None or hashlib.sha256(data).hexdigest() != sha256:
            return f"{path} missing from the archive or not the logged bytes"
        try:
            return {v.value_date.isoformat(): v.value for v in source.parse(data)}
        except UNREADABLE as exc:
            return f"{path} fails the publisher's check: {exc}"

    def _timing(self, cue: str, row: dict[str, str], fetched_at: datetime | None) -> list[str]:
        """`first_seen_at` never before the copy was fetched, and `provenance` recomputed from it."""
        seen = datetime.fromisoformat(row["first_seen_at"])
        problems = []
        if fetched_at is not None and _to_copy_second(seen) < _to_copy_second(fetched_at):
            problems.append(f"{cue} {row['value_date']}: first seen {seen} before its copy was fetched {fetched_at}")
        label = provenance(date.fromisoformat(row["value_date"]), seen, self.next_session)
        if row["provenance"] != label:
            problems.append(f"{cue} {row['value_date']}: labelled {row['provenance']}, should be {label}")
        return problems


def _to_copy_second(moment: datetime) -> datetime:
    """A moment at a copy path's precision (`archived_copies.COPY_TIME`, whole seconds). An adopted row is first seen
    at its path's second, while the log may keep the same copy's fetch to the microsecond (A17d adopted FBIL copies
    already logged by the fill: DRY1 row c4), so the two are compared at the coarser of the two precisions."""
    return moment.replace(microsecond=0)
