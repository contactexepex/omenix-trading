"""`python -m fno forecast-v4 capture | backfill | backfill-implied` (stories G7 and G7b): protocol v4's forecasts."""

from __future__ import annotations

BACKFILL_IMPLIED_WRITER = "forecast-v4-backfill-implied"  # the receipts' writer field


def add_forecast_v4_parser(subparsers) -> None:
    parser = subparsers.add_parser("forecast-v4", help="protocol v4's phase-1 baselines and rule forecasters (G7)")
    actions = parser.add_subparsers(dest="forecast_v4_cmd", required=True)
    actions.add_parser("capture", help="record today's v4 forecasts (today only, before the 14:30 IST cutoff)")
    actions.add_parser("backfill", help="write the exploratory back-fill (before the first live day)")
    actions.add_parser("backfill-implied", help="write V2/V3's exploratory raw and premium-adjusted implied to Drive")
    actions.add_parser(
        "capture-pack", help="record today's pack-derived v4 rows to Drive (after the release, by 15:10)"
    )
    parser.set_defaults(func=cmd_forecast_v4)


def cmd_forecast_v4(args) -> int:
    commands = {"capture": _capture, "backfill": _backfill, "backfill-implied": _backfill_implied,
                "capture-pack": _capture_pack}  # fmt: skip
    return commands[args.forecast_v4_cmd]()


def _capture() -> int:
    from ..models import now_ist
    from .capture import CaptureRefused, capture_day
    from .wiring import build_v4_forecasts, v4_writer

    now = now_ist()
    day = now.date()  # today only: a later day would be a forecast without its previous close
    try:
        added = capture_day(build_v4_forecasts(day), day, now, v4_writer())
    except CaptureRefused as refused:
        print(f"v4 forecasts {day}: nothing written: {refused}")
        return 0  # a closed day or a late run is not a failure (as G3's capture)
    print(f"v4 forecasts {day}: {added} rows written (live, exploratory until v4 is frozen)")
    return 0


def _backfill() -> int:
    from .backfill import backfill, backfill_days
    from .records import first_live_day
    from .wiring import V4_FOLDER, build_v4_forecasts, v4_writer

    forecasts = build_v4_forecasts()
    days = backfill_days(forecasts, first_live_day(V4_FOLDER))
    added = backfill(forecasts, days, v4_writer())
    print(f"v4 back-fill: {len(days)} days, {added} rows added (labelled backfill_exploratory)")
    return 0


def _backfill_implied() -> int:
    from ..storage.data_wiring import build_data_store, receipt_folder
    from .wiring import build_implied_backfill, first_live_implied_day

    backfill, last_close = build_implied_backfill()
    days = backfill.days(last_close, first_live_implied_day(receipt_folder()))
    paths = backfill.write(backfill.rows(days), build_data_store(BACKFILL_IMPLIED_WRITER).put)
    print(f"v4 implied back-fill: {len(days)} days, {len(paths)} files in Drive (labelled backfill_exploratory)")
    print("commit their receipts: receipts/data/v4/records/backfill/")
    return 0


def _capture_pack() -> int:
    """O1's `forecasts_v4_pack` step: "nothing written:" marks a refusal (the step alerts); a system_late day is no
    refusal (the day is out for everyone); a changed row for the day is a failure (exit 1)."""
    from ..models import now_ist
    from ..storage.raw_store import RawFileConflict
    from .pack_capture import CaptureRefused, ChangedRow, capture_pack
    from .pack_wiring import build_pack_capture, run_followups

    day = now_ist().date()
    built = build_pack_capture(day)
    for line in built.settled:  # the refit day's ratios and V5's outcomes, settled before the day's rows
        print(line)
    if built.refused is not None:
        print(f"v4 pack forecasts {day}: nothing written: {built.refused}")
        return 0
    code = _capture_day(day, built, capture_pack, (CaptureRefused, (ChangedRow, RawFileConflict)))
    for line in run_followups(day, built.eod, built.put):  # the drift pairs and W8's review, whatever the rows did
        print(line)
    return code


def _capture_day(day, built, capture, errors) -> int:
    from ..constants import V4_DAY_A
    from ..models import now_ist

    refused, changed = errors
    if built.inputs.release_label != V4_DAY_A:
        print(f"v4 pack forecasts {day}: no pack today ({built.inputs.release_label}), no row: the day is out for "
              "everyone")  # fmt: skip
        return 0
    try:
        paths = capture(built.forecasts, built.inputs, now_ist, built.get, built.put)
    except refused as why:
        print(f"v4 pack forecasts {day}: nothing written: {why}")
        return 0
    except changed as why:
        print(f"v4 pack forecasts {day}: stopped: {why}")
        return 1
    print(f"v4 pack forecasts {day}: {len(paths)} files written or already the same (live, exploratory until frozen)")
    return 0
