"""The evidence of one stress-factor run (story A14c): `stress_evidence_<run day>.csv` (the largest needed factor per
structure and width, and per reproduction window), `stress_files_<run day>.csv` (every session's file and SHA-256)
and a Markdown summary. Deterministic: the same files give byte-identical output, so a second run changes nothing."""

from __future__ import annotations

import csv
import hashlib
import io
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from ..research_engine.cycles import EXIT_MIN_DAYS
from .held_rise import MIN_DAYS_TO_EXPIRY, Holding

# Response 77's hand-run windows (entry days) and its figures, measured as (scan + exposure) gross read to the window's
# end (response 235: they reproduce to 0.001 with that measure); this run's figure is the needed factor
WINDOWS = (
    ("Jan-Apr 2020 COVID", date(2020, 1, 1), date(2020, 4, 30), 1.265),
    ("May-Jun 2024 election", date(2024, 5, 1), date(2024, 6, 30), 1.407),
    ("Sep-Oct 2026 calm", date(2026, 9, 1), date(2026, 10, 31), 1.127),
)
WINDOW_STRUCTURES, WINDOW_WIDTHS = ("SF", "SC", "BF"), (100.0, 200.0, 300.0)  # response 77's set
HOLDING_COLUMNS = ("scope", "structure", "width", "needed_factor", "entry", "expiry", "exit", "peak_day",
                   "entry_margin_rs", "peak_margin_rs")  # fmt: skip


@dataclass(frozen=True)
class Evidence:
    csv_text: str
    files_text: str
    markdown: str

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.csv_text.encode("utf-8")).hexdigest()

    def write(self, folder: Path, run_day: date) -> None:
        folder.mkdir(parents=True, exist_ok=True)
        for name, text in ((f"stress_evidence_{run_day}.csv", self.csv_text), (f"stress_files_{run_day}.csv",
                           self.files_text), (f"stress_evidence_{run_day}.md", self.markdown)):  # fmt: skip
            (folder / name).write_text(text, encoding="utf-8")


def best_per_key(holdings: Sequence[Holding]) -> list[Holding]:
    """The largest needed factor per (structure, width), largest first; ties by the earlier entry."""
    best: dict[tuple[str, float], Holding] = {}
    for h in sorted(holdings, key=lambda h: (h.entry, h.structure, h.width)):
        key = (h.structure, h.width)
        if key not in best or h.needed > best[key].needed:
            best[key] = h
    return sorted(best.values(), key=lambda h: (-h.needed, h.structure, h.width))


def window_best(holdings: Sequence[Holding], first: date, last: date) -> Holding | None:
    inside = [h for h in holdings if first <= h.entry <= last and h.structure in WINDOW_STRUCTURES
              and h.width in WINDOW_WIDTHS]  # fmt: skip
    return max(inside, key=lambda h: (h.needed, -h.entry.toordinal()), default=None)


def build_evidence(run_day: date, holdings: Sequence[Holding], files: Mapping[date, str], unrounded: float,
                   decision: tuple[float, float, str], dropped: Sequence[str], mode: str) -> Evidence:  # fmt: skip
    rows = [("all", h) for h in best_per_key(holdings)]
    windows = [(name, window_best(holdings, first, last), hand) for name, first, last, hand in WINDOWS]
    rows += [(name, h) for name, h, _ in windows if h is not None]
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(HOLDING_COLUMNS)
    for scope, h in rows:
        writer.writerow((scope, h.structure, f"{h.width:g}", f"{h.needed:.6f}", h.entry, h.expiry, h.exit, h.peak_day,
                         f"{h.entry_margin:.2f}", f"{h.peak_margin:.2f}"))  # fmt: skip
    files_out = io.StringIO()
    files_writer = csv.writer(files_out, lineterminator="\n")
    files_writer.writerow(("session", "file", "sha256"))
    for day in sorted(files):
        files_writer.writerow((day.isoformat(), f"nsccl.{day:%Y%m%d}.i1.zip", files[day]))
    markdown = _markdown(run_day, holdings, files, unrounded, decision, dropped, mode, windows)
    return Evidence(out.getvalue(), files_out.getvalue(), markdown)


def _markdown(run_day, holdings, files, unrounded, decision, dropped, mode, windows) -> str:
    factor, computed, status = decision
    lines = [
        f"# Stress factor run {run_day} ({mode})",
        "",
        "Rule (story A14c; owner, 16 Oct 2026, decision 07f62385): the largest stress factor a held position needed, "
        "the smallest k with max(0, k x scan - NOV) + min(0, NOV) + k x exposure of its entry parts at least what C2 "
        f"counts on every later day held; entry on every session (first monthly expiry {MIN_DAYS_TO_EXPIRY}+ days out) "
        f"to the last session {EXIT_MIN_DAYS}+ days before expiry, every structure and width C2 trades, rounded up "
        "to the next 0.05.",
        "",
        f"- Sessions read: {len(files)} ({min(files)} to {max(files)}), each file's SHA-256 in the files CSV",
        f"- Holdings completed in this run: {len(holdings)}; dropped (named below): {len(dropped)}",
        f"- Largest needed factor (unrounded, carried across runs): {unrounded:.6f}; computed {computed:g}",
        f"- Factor in force: {factor:g} ({status})",
        "",
        "| Window | Response 77 (gross, to window end) | Needed factor, this run | Holding |",
        "|---|---|---|---|",
    ]
    for name, h, hand in windows:
        found = "no holding in this run" if h is None else f"{h.needed:.3f}"
        what = "" if h is None else f"{h.structure} {h.width:g} entered {h.entry}, peak {h.peak_day}"
        lines.append(f"| {name} | {hand} | {found} | {what} |")
    if dropped:
        lines += ["", "Dropped positions (a day's margin could not be computed):", ""]
        lines += [f"- {reason}" for reason in sorted(dropped)]
    return "\n".join(lines) + "\n"
