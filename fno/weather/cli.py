"""`python -m fno weather capture | backfill` (story M1): the market weather as a scored forecaster. Research only:
it writes records and never places an order. The printed lines never show the private US-move flag."""

from __future__ import annotations

from datetime import date


def add_weather_parser(subparsers) -> None:
    parser = subparsers.add_parser("weather", help="the market weather: V6 probabilities, colour, drivers (M1)")
    actions = parser.add_subparsers(dest="weather_cmd", required=True)
    capture = actions.add_parser("capture", help="record today's weather (today only, before the 14:30 IST cutoff)")
    capture.add_argument("--day", type=date.fromisoformat, help="the day (default today; any other day is refused)")
    actions.add_parser("backfill", help="write the exploratory back-fill (before the first live record)")
    parser.set_defaults(func=cmd_weather)


def cmd_weather(args, out=print) -> int:
    if args.weather_cmd == "capture":
        return _capture(args.day, out)
    return _backfill(out)


def _capture(day: date | None, out) -> int:
    from ..forecast_v4_rules.capture import CaptureRefused
    from ..forecast_v4_rules.records import RecordConflict
    from ..models import now_ist
    from .capture import capture_weather
    from .drivers import us_move_flag
    from .wiring import (
        build_cue_reader,
        build_private_store,
        build_records,
        build_weather_days,
        build_writer,
        is_session,
        previous_regular,
    )

    now = now_ist()
    day = day or now.date()
    flag = lambda: us_move_flag(build_cue_reader(), day, live_only=True)  # noqa: E731
    try:
        lines = capture_weather(build_weather_days(), build_records(), day, now, is_session, build_writer(), flag,
                                build_private_store(), previous_regular)  # fmt: skip
    except CaptureRefused as refused:
        out(f"weather {day}: nothing written: {refused}")
        return 0  # a closed day or a late run is not a failure (as G3 and G7)
    except RecordConflict as conflict:  # a rerun after an input changed: the first record stays
        out(f"weather {day}: nothing written: {conflict}")
        return 1
    out("\n".join(lines))
    return 0


def _backfill(out) -> int:
    from .capture import backfill_weather
    from .wiring import build_records, build_weather_days, build_writer

    records = build_records()
    out("\n".join(backfill_weather(build_weather_days(), records, records.first_live(), build_writer())))
    return 0
