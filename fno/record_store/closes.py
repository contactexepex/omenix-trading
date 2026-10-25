"""Story DR1's first dataset: A4h's close read (`fno/close_read/`), certified from the NSE index-list answers A4h
already saves (`closes/<yyyy>/<mm>/<day>.first.raw.json` and `.recheck.raw.json`): the shadow phase, A4h's code
unchanged. Those files are A4h's canonical JSON of the parsed answer (sorted keys), not NSE's own byte stream, so
integrity means "matches its receipt". A4h's own rules decide what a valid answer is (`read_answer`: NSE's stamp of
that day at or after 15:30, every index with its fields, and since A4h-2 a day range that holds the open and the last);
this adds the sanity check and, for the certified record, NSE's official files within A4h's tolerance: for NIFTY 50
and NIFTY BANK the last against the official close, the high and low against the official high and low, and the
previous close against the previous session's official close (rules version 2: FL1-1f's evening reads them, so they
are certified like the close; a field an older record lacks is skipped, as A4h's confirm does). Lines name indices,
fields and differences, never a level.

Which passing read is the record (the A4h builder's objection, 23 Oct): A4h rechecks at 16:00 because NSE's list can
still change after 15:30, and both reads carry the same stamp (23 Oct: "23-Oct-2026 15:30" at 15:40 and at 16:00),
so the stamp cannot order them. A value that changes after the 15:30 close is NSE's correction, so the provisional
record is the latest passing read, with any difference named; it never blocks. The certified record is the read
closest to NSE's official file. The certifier never alerts: A4h's overdue rule already alerts a day the official file
does not confirm."""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import date

from ..close_read.answer import Refused, difference, read_answer
from ..close_read.constants import INDICES, READ, RECHECK, TOLERANCE
from ..close_read.official import OfficialCloses
from ..close_read.records import raw_path, record_path
from ..storage.raw_store import RawFileStore
from .constants import CERTIFIED, DATA_AREA
from .models import CheckResult, Record, StagedVersion
from .rules import Choice, DatasetRules, SourceUnreadable

DATASET = "closes"
MAX_MOVE = 0.20  # NSE's widest index circuit band: a close more than 20% from its open is not a real close
AGREE = "{count} passing version(s) agree on {names}"
SUPERSEDED = "the later read supersedes the earlier ({changes})"
OFFICIAL = "closest to NSE's official file {filename}, within {tolerance}"
OFFICIAL_CHECK = "official file"
UNREADABLE = "NSE's official index-close files could not be read ({kind})"
MATCHES, DIFFERS, NO_A4H = "matches A4h's record", "differs from A4h's record (it cites {which})", "A4h wrote no record"


def a4h_raw_paths(session: str) -> list[str]:
    day = date.fromisoformat(session)
    return [f"{DATA_AREA}/{raw_path(day, which)}" for which in (READ, RECHECK)]


class ClosesRules(DatasetRules):
    name, version = DATASET, "2"
    live_from = date(2026, 10, 22)  # A4h's first raw answer (its first read, 22 Oct)

    def __init__(self, official: OfficialCloses, previous_session: Callable[[date], date]):
        """`previous_session`: NSE's calendar step back, for the previous close's official file."""
        self.official, self.previous_session = official, previous_session
        self._read: dict[date, tuple | None] = {}  # one read of each official file per run (judge 561's note)

    def checks(self, session: str, level: str, data: bytes) -> list[CheckResult]:
        day = date.fromisoformat(session)
        try:
            payload = json.loads(data)
        except ValueError:
            return [CheckResult("layout", False, "not JSON")]
        try:
            values = read_answer(payload, day).values
        except Refused as refused:
            return [CheckResult("layout", True), CheckResult("stamp and indices", False, str(refused))]
        results = [CheckResult("layout", True), CheckResult("stamp and indices", True), _sanity(values)]
        if level == CERTIFIED:
            results.append(self._agreement(day, values))
        return results

    def choose(self, session: str, level: str, passing: list[tuple[StagedVersion, bytes]]) -> Choice:
        """Passing versions come in read order (first, then recheck)."""
        day = date.fromisoformat(session)
        checked = [n for n in INDICES if n.checked]
        values = [read_answer(json.loads(data), day).values for _, data in passing]
        if level == CERTIFIED:
            filename, official = self._official(day)  # passing versions passed the official check: the file is there
            gaps = [max(abs(v[n.listed]["last"] - official[n.official]["close"]) for n in checked) for v in values]
            best = min(range(len(passing)), key=lambda i: (gaps[i], i))  # equal quality: the read A4h's record cites
            return Choice(passing[best][0], OFFICIAL.format(filename=filename, tolerance=TOLERANCE))
        changes = [_change(n.listed, values[0][n.listed], values[-1][n.listed]) for n in checked
                   if values[0][n.listed] != values[-1][n.listed]]  # fmt: skip
        if changes:
            return Choice(passing[-1][0], SUPERSEDED.format(changes=", ".join(changes)))
        names = ", ".join(n.listed for n in checked)  # equal values: the first read, the one A4h's record cites
        return Choice(passing[0][0], AGREE.format(count=len(passing), names=names))

    def _official(self, day: date) -> tuple | None:
        """The day's official file, read once per run; every read failure is SourceUnreadable, never "not yet"."""
        if day not in self._read:
            try:
                self._read[day] = self.official.values(day)
            except Exception as failure:  # noqa: BLE001 - any read failure stops the session loudly, never "not yet"
                raise SourceUnreadable(UNREADABLE.format(kind=type(failure).__name__)) from failure
        return self._read[day]

    def _agreement(self, day: date, values: dict) -> CheckResult:
        found = self._official(day)
        previous = self._official(self.previous_session(day)) if _has_previous(values) else None
        if found is None:
            return CheckResult(OFFICIAL_CHECK, False, "no official index-close file in Drive yet")
        if _has_previous(values) and previous is None:
            return CheckResult(OFFICIAL_CHECK, False, "no official index-close file in Drive for the previous session")
        filename, official = found
        previous_name, previous_values = previous or ("", {})
        for index in (n for n in INDICES if n.checked):
            theirs = _official_fields(official.get(index.official) or {}, previous_values.get(index.official))
            for field, mine in values[index.listed].items():
                if field not in theirs or mine is None:
                    continue
                if theirs[field] is None:  # judge 554's note: the previous close's file is the previous session's
                    source = previous_name if field == "previous_close" else filename
                    return CheckResult(OFFICIAL_CHECK, False, f"{index.listed} {field} not in {source}")
                gap = abs(mine - theirs[field])
                if gap > TOLERANCE + 1e-9:
                    return CheckResult(OFFICIAL_CHECK, False, f"{index.listed} {field} differs by {gap:.2f}")
        return CheckResult(OFFICIAL_CHECK, True)


def _has_previous(values: dict) -> bool:
    return any(values[n.listed].get("previous_close") is not None for n in INDICES if n.checked)


def _official_fields(today: dict, previous: dict | None) -> dict[str, float | None]:
    """Each recorded field's official counterpart: the close, the day range, the previous session's close."""
    return {"last": today.get("close"), "high": today.get("high"), "low": today.get("low"),
            "previous_close": (previous or {}).get("close")}  # fmt: skip


def _change(name: str, earlier: dict, later: dict) -> str:
    """Which field changed and by how much (a difference, never a level); judge 543: an open-only change is named."""
    fields = [f"{field} {_moved(earlier[field], later.get(field))}" for field in sorted(earlier)
              if earlier[field] != later.get(field)]  # fmt: skip
    return f"{name} {', '.join(fields)}"


def _moved(earlier: float | None, later: float | None) -> str:
    if earlier is None or later is None:
        return "missing in one read"
    return difference(earlier, later)


def _sanity(values: dict) -> CheckResult:
    """Positive values for every index; the 20% band only for the indices NSE's circuit bands cover (NIFTY 50 and NIFTY
    BANK): INDIA VIX can move more than 20% in a day around a shock, and its list value is never certified."""
    for index in INDICES:
        last, opened = values[index.listed]["last"], values[index.listed]["open"]
        if last <= 0 or opened <= 0:
            return CheckResult("sanity", False, f"{index.listed} is not positive")
        if index.checked and abs(last / opened - 1) > MAX_MOVE:
            return CheckResult("sanity", False, f"{index.listed} closed more than {MAX_MOVE:.0%} from its open")
    return CheckResult("sanity", True)


class A4hRecordComparison:
    """The shadow's comparison: does the certifier choose the raw answer A4h's own record cites?"""

    def __init__(self, drive: RawFileStore):
        self.drive = drive

    def __call__(self, session: str, record: Record) -> str:
        data = self.drive.get(f"{DATA_AREA}/{record_path(date.fromisoformat(session))}")
        if data is None:
            return NO_A4H
        document = json.loads(data)
        if document.get("raw_sha256") == record.chosen.sha256:
            return MATCHES
        return DIFFERS.format(which=document.get("read", "another read"))
