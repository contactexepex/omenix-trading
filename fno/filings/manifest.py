"""The filings manifest (story A12): one CSV per filing type in the repository, one row per archived XBRL file, with
its SHA-256 (and Drive's MD5, so coverage can check Drive's copies from a listing), when the exchange made it public
(`filed_at`) and when we first saw it (`first_seen`).

Rows are only appended (thousands of files: never a whole rewrite per file) and never changed; a second row for the
same link with a different SHA-256 is refused. A revised filing has its own link, so it is a row of its own.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from ..storage.raw_store import RawFileConflict
from .filing import Filing

FIELDS = (
    "symbol", "period_end", "consolidation", "filed_at", "first_seen", "url", "sha256", "md5", "size_bytes",
    "balance_sheet", "cash_flow",
)  # fmt: skip
YES, NO, NOT_APPLICABLE = "yes", "no", ""


@dataclass(frozen=True)
class ArchivedFiling:
    filing: Filing
    first_seen: datetime
    sha256: str
    md5: str
    size_bytes: int
    balance_sheet: bool | None = None  # results only: the file holds a balance sheet
    cash_flow: bool | None = None  # results only: the file holds a cash-flow statement


def _flag(value: bool | None) -> str:
    return NOT_APPLICABLE if value is None else (YES if value else NO)


def _unflag(text: str) -> bool | None:
    return None if text == NOT_APPLICABLE else text == YES


class FilingManifest:
    def __init__(self, folder: Path):
        self.folder = Path(folder)
        self._rows: dict[str, dict[str, ArchivedFiling]] = {}  # kind -> url -> row (read once per kind)

    def path_for(self, kind: str) -> Path:
        return self.folder / f"{kind}.csv"

    def rows(self, kind: str) -> dict[str, ArchivedFiling]:
        """Link -> archived filing, for one filing type."""
        if kind not in self._rows:
            path = self.path_for(kind)
            lines = path.read_text(encoding="utf-8").splitlines() if path.is_file() else []
            self._rows[kind] = {r["url"]: self._parse(kind, r) for r in csv.DictReader(lines)}
        return self._rows[kind]

    def record(self, row: ArchivedFiling) -> None:
        """Appends a row; the same file again changes nothing, a different SHA-256 for its link is refused."""
        kind, known = row.filing.kind, self.rows(row.filing.kind)
        existing = known.get(row.filing.url)
        if existing is not None:
            if existing.sha256 != row.sha256:
                raise RawFileConflict(f"{row.filing.filename}: the manifest already has a different SHA-256")
            return
        path = self.path_for(kind)
        path.parent.mkdir(parents=True, exist_ok=True)
        new_file = not path.is_file()
        with path.open("a", encoding="utf-8", newline="") as out:
            writer = csv.writer(out, lineterminator="\n")
            if new_file:
                writer.writerow(FIELDS)
            writer.writerow(self._cells(row))
        known[row.filing.url] = row

    @staticmethod
    def _cells(row: ArchivedFiling) -> tuple:
        f = row.filing
        return (
            f.symbol, f.period_end.isoformat(), f.consolidation, f.filed_at.isoformat(),
            row.first_seen.isoformat(timespec="seconds"), f.url, row.sha256, row.md5, row.size_bytes,
            _flag(row.balance_sheet), _flag(row.cash_flow),
        )  # fmt: skip

    @staticmethod
    def _parse(kind: str, r: dict) -> ArchivedFiling:
        filing = Filing(
            kind,
            r["symbol"],
            date.fromisoformat(r["period_end"]),
            datetime.fromisoformat(r["filed_at"]),
            r["url"],
            r["consolidation"],
        )
        return ArchivedFiling(
            filing,
            datetime.fromisoformat(r["first_seen"]),
            r["sha256"],
            r["md5"],
            int(r["size_bytes"]),
            _unflag(r["balance_sheet"]),
            _unflag(r["cash_flow"]),
        )
