"""`python -m fno forecast-v5-v1 capture | report | freeze` (story G14). `capture` writes today's five rows before
14:30 IST only while `FREEZE_v5_v1.md` holds: a planned "no row" (the cutoff, no record yet, a record frozen after
today) prints "nothing written:" and exits 0, so O1 records it `refused`; a fault (a frozen file moved, a broken
record, a different row already written) exits 1, so O1 records it `failed` (amendment 2; criterion 7). `report`
prints the scores and the measure-gap table; `freeze` writes the freeze record once, after `FREEZE_v4.md`."""

from __future__ import annotations

REFUSED = "v5 V1 candle forecasts {day}: nothing written: {why}"
FAILED = "v5 V1 candle forecasts {day}: FAILED, no row written: {why}"


def add_forecast_v5_v1_parser(subparsers) -> None:
    parser = subparsers.add_parser("forecast-v5-v1", help="G14: V1's forecasters on the candle history (measurement)")
    actions = parser.add_subparsers(dest="forecast_v5_v1_cmd", required=True)
    actions.add_parser("capture", help="record today's five rows (today only, before 14:30 IST, frozen only)")
    actions.add_parser("report", help="QLIKE against A16's live RV, and the candle / live measure gap")
    actions.add_parser("freeze", help="write FREEZE_v5_v1.md once, after FREEZE_v4.md")
    parser.set_defaults(func=cmd_forecast_v5_v1)


def cmd_forecast_v5_v1(args) -> int:
    return {"capture": _capture, "report": _report, "freeze": _freeze}[args.forecast_v5_v1_cmd]()


def _capture() -> int:
    from ..config import ROOT
    from ..forecast_v4_rules.capture import CaptureRefused
    from ..forecast_v4_rules.records import RecordConflict
    from ..models import now_ist
    from .capture import capture
    from .freeze import FUTURE, FreezeBroken, NotFrozen, check
    from .records import capture_platform
    from .wiring import FREEZE_FILE, build_day, writer

    now = now_ist()
    try:
        frozen_on = check(ROOT, FREEZE_FILE)
        if frozen_on > now.date():
            raise NotFrozen(FUTURE.format(name=FREEZE_FILE.name, day=frozen_on))
        added = capture(build_day(now.date()), now, capture_platform(), writer())
    except (CaptureRefused, NotFrozen) as refused:
        print(REFUSED.format(day=now.date(), why=refused))
        return 0
    except (FreezeBroken, RecordConflict) as fault:
        print(FAILED.format(day=now.date(), why=fault))
        return 1
    print(f"v5 V1 candle forecasts {now.date()}: {added} rows written (live; a measurement, never a v4 member)")
    return 0


def _report() -> int:
    from .wiring import build_report

    print("\n".join(build_report()))
    return 0


def _freeze() -> int:
    from ..config import ROOT
    from ..forecast_scoring.v4.freeze_check import byte_checked
    from ..models import now_ist
    from .freeze import NotFrozen, record_text
    from .wiring import FREEZE_FILE, V4_FREEZE_FILE

    if FREEZE_FILE.exists():
        print(f"{FREEZE_FILE.name} already written: a freeze record is never rewritten (a new one is a new version)")
        return 1
    if not V4_FREEZE_FILE.is_file():
        print(f"{FREEZE_FILE.name} not written: {V4_FREEZE_FILE.name} is not in this tree yet (amendment 1, section 3)")
        return 1
    try:
        text = record_text(ROOT, V4_FREEZE_FILE.read_text(encoding="utf-8"), byte_checked(ROOT), now_ist().date())
    except NotFrozen as refused:
        print(f"{FREEZE_FILE.name} not written: {refused}")
        return 1
    FREEZE_FILE.write_text(text, encoding="utf-8")
    print(f"{FREEZE_FILE.name} written; commit it alone, with nothing else staged")
    return 0
