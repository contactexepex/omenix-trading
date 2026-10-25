"""The v4 freeze record's disclosure (protocol section 8; story G6 freeze, criterion 9): every exploratory back-fill and
every live row, report and Drive record made on or before the freeze day, read from the repository, never typed by
hand. Each repository source names its days, its row count, its method hashes and the SHA-256 of its rows, so the judge
and any later reader can check that the rows disclosed are the rows still there; a Drive file is named by its
receipt."""

from __future__ import annotations

import csv
import hashlib
import io
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from ...forecast_v4_rules.drive_records import BACKFILL_FOLDER, LIVE_FOLDER
from ...forecast_v4_rules.records import BACKFILL, LIVE
from ...storage.data_wiring import DATA_AREA, RECEIPTS_FOLDER

V4_RECORDS = "research/forecasts/v4"  # G7's and M1's CSV records, M1's day files under weather/
WEATHER_DAYS = f"{V4_RECORDS}/weather"
REPORTS = "research/forecasts/v4_scores"  # G8's reports (and looks, none before the freeze)
DRIVE_BACKFILLS = f"{RECEIPTS_FOLDER}/{DATA_AREA}/{BACKFILL_FOLDER}"  # G7b's Drive back-fills, one receipt per file
DRIVE_LIVE = f"{RECEIPTS_FOLDER}/{DATA_AREA}/{LIVE_FOLDER}"  # G7b's live rows, <forecaster>/<question>/<YYYY>/<day>
RECEIPT = ".sha256"
NONE = "- none"
TABLE_HEAD = "| Source | First day | Last day | Rows | Method SHA-256 (first 12) | Rows' SHA-256 |"


class DisclosureError(ValueError):
    """A record file the disclosure cannot read: named, so the freeze tool stops with the file, never a traceback."""


@dataclass(frozen=True)
class Rows:
    """One source's rows of one label: where, which days, how many, made by which method, and their fingerprint."""

    source: str
    first: str
    last: str
    count: int
    methods: tuple[str, ...]
    sha256: str

    def line(self) -> str:
        methods = ", ".join(f"`{m[:12]}`" for m in self.methods) or "none"
        return f"| `{self.source}` | {self.first} | {self.last} | {self.count} | {methods} | `{self.sha256}` |"


def csv_rows(root: Path, label: str, through: date | None = None) -> list[Rows]:
    """Per record file, its rows of `label` (live ones only up to `through`): the header and those rows, written back
    as CSV with "\\n" line ends, hashed."""
    found = []
    for path in sorted((root / V4_RECORDS).glob("*/*.csv")):
        name = path.relative_to(root).as_posix()
        header, *rows = _csv(path, name)
        picked = [r for r in rows if _wanted(dict(zip(header, r, strict=True)), label, through)]
        if picked:
            out = io.StringIO()
            csv.writer(out, lineterminator="\n").writerows([header, *picked])
            found.append(_rows(name, [dict(zip(header, r, strict=True)) for r in picked], out.getvalue()))
    return found


def _csv(path: Path, name: str) -> list[list[str]]:
    rows = list(csv.reader(io.StringIO(path.read_text(encoding="utf-8"))))
    if not rows or not {"day", "label"} <= set(rows[0]):
        raise DisclosureError(f"{name}: no header with `day` and `label`")
    if any(len(r) != len(rows[0]) for r in rows[1:]):
        raise DisclosureError(f"{name}: a row with another field count than the header")
    return rows


def weather_rows(root: Path, label: str, through: date | None = None) -> list[Rows]:
    """M1's day files of `label` as one source: the SHA-256 is over each file's path and bytes, in day order."""
    picked = []
    for path in sorted((root / WEATHER_DAYS).glob("*/*.json")):
        name = path.relative_to(root).as_posix()
        try:
            day = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as fault:
            raise DisclosureError(f"{name}: not JSON ({fault.msg})") from fault
        if _wanted(day, label, through):
            picked.append((name, path, day))
    if not picked:
        return []
    body = "".join(f"{name} {hashlib.sha256(path.read_bytes()).hexdigest()}\n" for name, path, _ in picked)
    return [_rows(f"{WEATHER_DAYS}/*/*.json", [d for _, _, d in picked], body)]


def _wanted(row: dict, label: str, through: date | None) -> bool:
    if "label" not in row or "day" not in row:
        raise DisclosureError(f"a record without `day` and `label`: {sorted(row)[:5]}")
    return row["label"] == label and (through is None or date.fromisoformat(row["day"]) <= through)


def _rows(source: str, rows: list[dict], body: str) -> Rows:
    days = sorted(r["day"] for r in rows)
    methods = tuple(sorted({r["method_sha256"] for r in rows if r.get("method_sha256")}))
    return Rows(source, days[0], days[-1], len(rows), methods, hashlib.sha256(body.encode("utf-8")).hexdigest())


def reports_through(root: Path, through: date) -> list[str]:
    """G8's report files dated on or before the freeze day (descriptive, exploratory)."""
    folder = root / REPORTS
    return sorted(p.relative_to(root).as_posix() for p in folder.glob("*.*") if _dated_on_or_before(p.stem, through))


def _dated_on_or_before(stem: str, through: date) -> bool:
    try:
        return date.fromisoformat(stem) <= through
    except ValueError:
        return False


def drive_files(root: Path, folder: str, through: date | None = None) -> list[str]:
    """Drive files by their receipts under `folder`: each path and the SHA-256 its receipt holds (the content stays in
    Drive); live files only up to `through`, by the day in their name."""
    rows = []
    for receipt in sorted((root / folder).rglob(f"*{RECEIPT}")):
        name = receipt.relative_to(root).as_posix()
        if through is not None and not _dated_on_or_before(receipt.name.split(".")[0], through):
            continue
        fields = receipt.read_text(encoding="utf-8").split()
        if not fields:
            raise DisclosureError(f"{name}: an empty receipt")
        rows.append(f"| `{name}` | `{fields[0]}` |")
    return rows


def disclosure(root: Path, frozen_on: date) -> str:
    """The record's disclosure section, as Markdown."""
    head = TABLE_HEAD + "\n" + "|---" * 6 + "|"
    drive_head = "| Receipt | File SHA-256 |\n|---|---|"
    backfill = csv_rows(root, BACKFILL) + weather_rows(root, BACKFILL)
    live = csv_rows(root, LIVE, frozen_on) + weather_rows(root, LIVE, frozen_on)
    drive_back, drive_live = drive_files(root, DRIVE_BACKFILLS), drive_files(root, DRIVE_LIVE, frozen_on)
    parts = [
        "### Exploratory back-fills in the repository (`backfill_exploratory`, never counted)",
        "\n".join([head, *(r.line() for r in backfill)]) if backfill else NONE,
        f"### Live rows made on or before {frozen_on} (before the freeze, never counted)",
        "\n".join([head, *(r.line() for r in live)]) if live else NONE,
        f"### G8's reports dated on or before {frozen_on} (exploratory)",
        "\n".join(f"- `{p}`" for p in reports_through(root, frozen_on)) or NONE,
        "### Exploratory back-fills in Drive (by receipt; never counted)",
        "\n".join([drive_head, *drive_back]) if drive_back else NONE,
        f"### Live rows in Drive made on or before {frozen_on} (by receipt; before the freeze, never counted)",
        "\n".join([drive_head, *drive_live]) if drive_live else NONE,
    ]
    return "\n\n".join(parts)
