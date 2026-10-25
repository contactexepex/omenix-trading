"""The checks of the cue tables, rewritten on every run (story A17; reports, not records).

Public cues' gaps and the RBI/FBIL comparison (dates and kinds only, never a rate: story A17d) go to
`research/data/global-cues/checks/`. A private cue's gaps (dates,
never values, but still kept out of this public repository by the owner's rule) go to its own Drive log; only their
counts are printed. Each run writes a full new snapshot there; the newest is current. When both US index tables are
read (the Drive settings present), the dates-only list of US trading days is rewritten too (story A17b); from it the
S&P 500's weekday gaps can be derived (an open owner item, data README). Each index with an official and a Yahoo cue
is compared (story A17e, `pair_checks.py`): the dates go to Drive, the counts are printed, and the indexes with Yahoo
only are named as unverified.
"""

from __future__ import annotations

import csv
import io
from collections import Counter
from pathlib import Path

from ..storage.row_log import DriveSnapshots
from .checks import GAP_FIELDS, OVERLAP_FIELDS, gap_rows, overlap_rows
from .cue_calendars import CueCalendar
from .index_reader import IndexPair
from .pair_checks import PAIR_FIELDS, compared_dates, pair_rows, pair_summary
from .table import CueTable
from .trading_dates import FIELDS as TRADING_DATE_FIELDS
from .trading_dates import NASDAQ100_CUE, SP500_CUE, us_trading_dates

GAPS_FILE, OVERLAP_FILE = "gaps.csv", "overlap_usdinr.csv"
RBI_CUE, FBIL_CUE = "usdinr_rbi", "usdinr_fbil"


class CueChecks:
    def __init__(
        self,
        tables: dict[str, CueTable],
        folder: Path,
        private_gaps: dict[str, DriveSnapshots] | None = None,
        trading_dates: Path | None = None,
        pairs: dict[str, IndexPair] | None = None,
        pair_snapshots: dict[str, DriveSnapshots] | None = None,
        pair_sessions: dict[str, CueCalendar] | None = None,
    ):
        """`private_gaps`: cue -> where its gaps go in Drive (those cues never reach the repository's files).
        `trading_dates`: where the dates-only US trading days go, when both US index tables are given."""
        self.tables, self.checks_folder, self.private_gaps = tables, Path(folder), private_gaps or {}
        self.trading_dates = trading_dates
        self.pairs, self.pair_snapshots, self.pair_sessions = pairs or {}, pair_snapshots or {}, pair_sessions or {}

    def write(self) -> list[str]:
        gaps = {cue: gap_rows(cue, table.rows()) for cue, table in sorted(self.tables.items())}
        public = [g for cue, rows in gaps.items() if cue not in self.private_gaps for g in rows]
        for cue, snapshots in self.private_gaps.items():
            snapshots.write(GAP_FIELDS, gaps.get(cue, []))
        rbi, fbil = (_by_date(self.tables[c].rows()) if c in self.tables else {} for c in (RBI_CUE, FBIL_CUE))
        overlap = overlap_rows(rbi, fbil)
        _write(self.checks_folder / GAPS_FILE, GAP_FIELDS, public)
        _write(self.checks_folder / OVERLAP_FILE, OVERLAP_FIELDS, overlap)
        counts = Counter((g[0], g[2]) for rows in gaps.values() for g in rows)
        return (
            self._write_trading_dates()
            + self._write_pairs()
            + [
                "gaps: " + (", ".join(f"{cue} {kind} {n}" for (cue, kind), n in sorted(counts.items())) or "none"),
                f"USD/INR RBI against FBIL: {len(set(rbi) & set(fbil))} dates compared, "
                f"{dict(Counter(o[1] for o in overlap)) or 'no difference'}",
            ]
        )

    def _write_pairs(self) -> list[str]:
        lines, unverified = [], []
        for index, pair in sorted(self.pairs.items()):
            if pair.official is None:
                unverified.append(index)
                continue
            if not {pair.official, pair.yahoo} <= set(self.tables):
                continue
            official, yahoo = self.tables[pair.official].rows(), self.tables[pair.yahoo].rows()
            calendar = self.pair_sessions.get(index)
            rows = pair_rows(index, official, yahoo, calendar.is_session if calendar else None)
            if index in self.pair_snapshots:
                self.pair_snapshots[index].write(PAIR_FIELDS, rows)
            lines.append(pair_summary(index, rows, compared_dates(official, yahoo)))
        return lines + ([f"unverified (Yahoo only): {', '.join(unverified)}"] if unverified else [])

    def _write_trading_dates(self) -> list[str]:
        if self.trading_dates is None or not {SP500_CUE, NASDAQ100_CUE} <= set(self.tables):
            return []
        days = us_trading_dates(self.tables[SP500_CUE].rows(), self.tables[NASDAQ100_CUE].rows())
        _write(self.trading_dates, TRADING_DATE_FIELDS, days)
        nasdaq_only = sum(1 for _, in_sp500, _ in days if not in_sp500)
        return [f"US trading dates: {len(days) - nasdaq_only} S&P 500 dates, {nasdaq_only} Nasdaq-only dates listed"]


def _by_date(rows: list[dict[str, str]]) -> dict[str, str]:
    return {r["value_date"]: r["value"] for r in rows}


def _write(path: Path, fields: tuple[str, ...], rows: list[tuple]) -> None:
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(fields)
    writer.writerows(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.part")
    temporary.write_text(out.getvalue(), encoding="utf-8")
    temporary.replace(path)  # never a half-written report
