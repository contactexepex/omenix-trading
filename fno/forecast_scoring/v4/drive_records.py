"""Write-once v4 records as G8 reads them (story G10 completion, criteria 6 and 8): every file of one Drive folder whose
receipt is in the checkout, brought through O9's verified cache before it is used. No receipt yet: no files (nothing
to fetch, so no Drive needed). A receipt whose bytes Drive does not return or returns changed stops the report or look
with the file named, never a report built from fewer records."""

from __future__ import annotations

from collections.abc import Callable

from ...storage.drive_cache import DriveCache
from ...storage.receipts import ReceiptFolder
from .days import DayFileError

NOT_VERIFIED = "the v4 records in {folder} could not be read from Drive: {problems}"


class DriveRecords:
    def __init__(self, receipts: ReceiptFolder, cache: Callable[[], DriveCache], area: str, folder: str):
        """`cache()`: the Drive cache, built only when a file has to be fetched; `folder`: inside the area."""
        self.receipts, self.cache, self.prefix = receipts, cache, f"{area}/{folder}"

    def paths(self) -> list[str]:
        """Each receipted file's Drive path, read from the receipts alone (no Drive access)."""
        return [r.path for r in self.receipts.under(self.prefix)]

    def files(self) -> dict[str, bytes]:
        """Each receipted file's Drive path and verified bytes."""
        receipts = self.receipts.under(self.prefix)
        if not receipts:
            return {}
        cache = self.cache()
        report = cache.sync(self.prefix)
        if report.problems:
            raise DayFileError(NOT_VERIFIED.format(folder=self.prefix, problems="; ".join(report.problems)))
        return {r.path: cache.local(r.path).read_bytes() for r in receipts}
