"""The day's packs as one step (stories E2 and E3): the common market pack and each packed book's private pack, built
and written once. `desk pack` and the daily run both use it. The common pack is refused (PackError) while the day's
canonical A4 snapshot is not committed, so the daily run pulls first and retries until the recorder's window ends.
A book's private pack holds its account folder's text, so it is kept privately (`keep`: Drive, story E2c) and only its
`.sha256` file is committed beside the common pack. A book with a sheet (story E2e) gets its evaluation in its private
pack; a sheet that fails refuses that book's pack only, with one alert, and the other books' packs are still written.
An `isolated` book (story F1t: each live AI book) is refused alone the same way when its private pack cannot be built
at all (a file its builder refuses), so an AI book's folder can never stop Book 1's pack."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from datetime import date, time
from pathlib import Path

from ..alerts.sender import AlertSender
from .book_sheet import BookSheet
from .common_pack import CommonPack, CommonPackBuilder
from .daily_ports import Packs
from .pack_store import PackStore
from .private_pack import PrivatePackBuilder

SHEET_REFUSED = ("F&O paper desk {day} {book}: private pack NOT built: its sheet failed ({error}); its decision has no "
                 "private pack today")  # fmt: skip
BUILD_REFUSED = ("F&O paper desk {day} {book}: private pack NOT built ({error}); its decision has no private pack "
                 "today")  # fmt: skip


class WrittenPacks(Packs):
    def __init__(self, common: CommonPackBuilder, private: PrivatePackBuilder, store: PackStore, cutoff: time,
                 books: Sequence[str], refresh: Callable[[], None] = lambda: None,
                 keep: Callable[[list[Path]], None] = lambda paths: None,
                 sheets: Mapping[str, BookSheet] | None = None, alerts: AlertSender | None = None,
                 isolated: Sequence[str] = ()):  # fmt: skip
        self.common, self.private, self.store, self.cutoff = common, private, store, cutoff
        self.books, self.refresh = tuple(books), refresh  # refresh: pull, so another container's snapshot is seen
        self.keep = keep  # keep(paths): the private packs, kept out of the public record
        self.sheets, self.alerts = dict(sheets or {}), alerts  # story E2e: each book's own evaluation, if it has one
        self.isolated = frozenset(isolated)  # story F1t: books whose pack failure refuses that book alone

    def build(self, day: date) -> CommonPack:
        self.refresh()
        pack = self.common.build(day, self.cutoff)
        self.store.write_common(pack)
        for book in self.books:
            self._write_private(book, day, pack)
        self.keep([self.store.private_path(book, day) for book in self.books])  # a refused book's is absent: skipped
        return pack

    def _write_private(self, book: str, day: date, common: CommonPack) -> None:
        sheet = self.sheets.get(book)
        try:
            evaluation = sheet.sheet(book, day, common) if sheet else None
        except Exception as failure:  # noqa: BLE001 - one book's sheet must never stop another book's pack
            self._refused(SHEET_REFUSED.format(day=day, book=book, error=f"{type(failure).__name__}: {failure}"))
            return
        if book not in self.isolated:
            self.store.write_private(self.private.build(book, day, evaluation))
            return
        try:
            self.store.write_private(self.private.build(book, day, evaluation))
        except Exception as failure:  # noqa: BLE001 - an AI book's folder never stops Book 1's pack (story F1t)
            self._refused(BUILD_REFUSED.format(day=day, book=book, error=type(failure).__name__))

    def _refused(self, text: str) -> None:
        print(self.alerts.send(text) if self.alerts else text)

    def written(self, day: date) -> list[tuple[Path, str]]:
        """Each written pack file of the day with its SHA-256 (from its `.sha256` file)."""
        paths = [self.store.common_path(day), *(self.store.private_path(book, day) for book in self.books)]
        return [(p, p.with_suffix(".sha256").read_text(encoding="utf-8").split()[0]) for p in paths if p.is_file()]

    def stored(self, day: date) -> CommonPack | None:
        path = self.store.common_path(day)
        return CommonPack.read(day, path) if path.is_file() else None

    def files(self, day: date) -> tuple[Path, ...]:
        """What the pack step commits: the common pack, and every pack's `.sha256` (a private pack's text is kept)."""
        common = self.store.common_path(day)
        sums = tuple(written.with_suffix(".sha256") for written, _ in self.written(day))
        return ((common,) if common.is_file() else ()) + sums
