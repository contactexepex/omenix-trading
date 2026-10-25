"""Fills the India VIX month files missing from the raw archive (story A15), in the A9 librarian's way.

For each month: a file already in the store is read back and checked (content, and SHA-256 against its manifest row),
and kept as it is even when it fails (that is reported, never replaced). A missing month is fetched, checked and only
then saved; the store writes its manifest row in the same operation (FingerprintingStore). A month the source has no
answer for, or answers with a file that fails the check, writes nothing and is named. Run it again after a stop: only
missing months are fetched. Knows only the interfaces.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import date

from ..storage.raw_source import RawFileSource
from ..storage.raw_store import RawFileConflict, RawFileStore, StoredCopyDamaged
from .month_file import VixMonthReader

PROGRESS_EVERY = 24  # months between progress lines


@dataclass
class VixFillReport:
    months: list[date] = field(default_factory=list)
    present: list[date] = field(default_factory=list)  # in the store and passing the check
    uploaded: list[date] = field(default_factory=list)
    damaged: list[tuple[date, str]] = field(default_factory=list)  # in the store but failing the check; left alone
    rejected: list[tuple[date, str]] = field(default_factory=list)  # the source's answer failed the check; not saved
    not_published: list[date] = field(default_factory=list)  # the source had no answer (404)

    @property
    def complete(self) -> bool:
        return not (self.damaged or self.rejected or self.not_published)

    def lines(self) -> list[str]:
        lines = [
            f"India VIX months: {len(self.months)} asked, {len(self.present)} already archived and checked, "
            f"{len(self.uploaded)} uploaded"
        ]
        lines += [f"damaged in store (left as is) {m:%Y-%m}: {why}" for m, why in self.damaged]
        lines += [f"rejected from source (not saved) {m:%Y-%m}: {why}" for m, why in self.rejected]
        lines += [f"not published by the source {m:%Y-%m}" for m in self.not_published]
        return lines


class VixHistoryLibrarian:
    def __init__(
        self,
        store: RawFileStore,
        source: RawFileSource,
        path_for: Callable[[date], str],
        reader: VixMonthReader,
        fingerprints: Mapping[date, str],
        log: Callable[[str], None] = print,
    ):
        """`fingerprints`: month -> SHA-256 from the dataset's manifest; `store` writes a row for each file it saves."""
        self.store, self.source, self.path_for, self.reader = store, source, path_for, reader
        self.fingerprints, self.log = fingerprints, log

    def fill(self, months: list[date]) -> VixFillReport:
        report = VixFillReport(list(months))
        for done, month in enumerate(months, start=1):
            self._fill_month(month, report)
            if done % PROGRESS_EVERY == 0:
                self.log(f"India VIX history: {done}/{len(months)} months")
        return report

    def _fill_month(self, month: date, report: VixFillReport) -> None:
        path = self.path_for(month)
        stored = self.store.get(path)
        if stored is not None:
            self._keep(path, month, stored, report)
            return
        data = self.source.fetch(path)
        if data is None:
            report.not_published.append(month)
            return
        problem = self._problem(data, month)
        if problem:
            report.rejected.append((month, problem))
            return
        try:
            self.store.put(path, data)
        except (StoredCopyDamaged, RawFileConflict) as exc:  # a conflict may come after Drive took the bytes
            report.damaged.append((month, str(exc)))
            return
        report.uploaded.append(month)

    def _keep(self, path: str, month: date, stored: bytes, report: VixFillReport) -> None:
        want = self.fingerprints.get(month)
        problem = self._problem(stored, month)
        if want is not None and hashlib.sha256(stored).hexdigest() != want:
            problem = "SHA-256 differs from the manifest"
        if problem:
            report.damaged.append((month, problem))
            return
        if want is None:  # saved by a run stopped before its manifest row: the same bytes again write only the row
            self.store.put(path, stored)
        report.present.append(month)

    def _problem(self, data: bytes, month: date) -> str | None:
        try:
            self.reader.read(data, month)
        except ValueError as exc:
            return str(exc)
        return None
