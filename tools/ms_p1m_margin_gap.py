"""Story MS-P1m's measure: A14-style ATM margin rows against the market school pilot's real legs (shorts one expected
move out; debit spreads one step out), per road, on archived beginning-of-day SPAN files. Read-only (Drive archive).

    python tools/ms_p1m_margin_gap.py <out.csv> [--every 12] [--from 2025-01-06] [--to 2026-10-21]

Per unit (lot 1), so the row/real ratio does not depend on the lot; C2's stressed margin at the factor 2.1."""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fno.composition import build_tradable_structures  # noqa: E402
from fno.constants import OPTION_CALL, OPTION_PUT  # noqa: E402
from fno.nse_margins.calculator import MarginOutsideModel, NseIndexOptionExposure, SpanMarginCalculator  # noqa: E402
from fno.nse_margins.prefetch import in_order, per_thread  # noqa: E402
from fno.nse_margins.span_file import read_span_file  # noqa: E402
from fno.nse_margins.wiring import build_drive_span_files, build_trading_days  # noqa: E402
from fno.research_engine.structures import Leg  # noqa: E402
from fno.risk.capital import stress_cap_per_lot  # noqa: E402
from fno.risk.inputs import RiskInputError  # noqa: E402
from fno.risk.margins import MarginParts  # noqa: E402

FACTOR, WORKERS, MAX_STEPS = 2.1, 8, 8
ROADS = ("NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY")
NEAR_SPOT = 0.05  # the strike step is read from the strikes listed within 5% of the index (judge 492)
COLUMNS = ("day", "road", "expiry", "kind", "structure", "width", "row_initial", "real_initial", "row_stressed",
           "real_stressed", "row_entry", "real_entry", "expected_move")  # fmt: skip
STRUCTURES = {s.code: s for s in build_tradable_structures()}
CALCULATOR = SpanMarginCalculator(NseIndexOptionExposure(), 1)
SKIPPED: Counter[str] = Counter()  # combinations not measured, by reason, printed at the end


def nearest(strikes, level: float) -> float:
    return min(strikes, key=lambda strike: abs(strike - level))


def strike_step(strikes, spot: float) -> float:
    """The expiry's own step: the most common gap between listed strikes near the index (ties: the smaller)."""
    near = [k for k in strikes if abs(k - spot) <= NEAR_SPOT * spot]
    gaps = Counter(round(b - a, 2) for a, b in zip(near, near[1:]))
    return min(gaps, key=lambda gap: (-gaps[gap], gap))


def pilot_legs(strikes, spot: float, move: float, width: float, step: float) -> dict[str, list[Leg]]:
    atm, up, down = nearest(strikes, spot), nearest(strikes, spot + move), nearest(strikes, spot - move)
    call, put = OPTION_CALL, OPTION_PUT
    return {
        "SC": [Leg(up, call, -1), Leg(down, put, -1), Leg(up + width, call, 1), Leg(down - width, put, 1)],
        "PCS": [Leg(down, put, -1), Leg(down - width, put, 1)],
        "CCS": [Leg(up, call, -1), Leg(up + width, call, 1)],
        "CDS": [Leg(atm + step, call, 1), Leg(atm + step + width, call, -1)],
        "PDS": [Leg(atm - step, put, 1), Leg(atm - step - width, put, -1)],
    }


def parts(span, expiry: date, legs, code: str, width: float, day: date) -> MarginParts:
    figure = CALCULATOR.per_lot(span, expiry, legs, day)
    cap = stress_cap_per_lot(code, width, figure.nov, 1)
    return MarginParts(figure.span, figure.nov, figure.exposure, code, False, cap)


def figures(row: MarginParts, real: MarginParts) -> list[str]:
    values = (row.initial(), real.initial(), row.stressed(FACTOR), real.stressed(FACTOR), row.at_entry(FACTOR),
              real.at_entry(FACTOR))  # fmt: skip
    return [f"{value:.2f}" for value in values]


def measure_expiry(span, road: str, expiry: date, kind: str, day: date):
    options = span.series[expiry]
    strikes = sorted({strike for strike, _ in options})
    atm = nearest(strikes, span.underlying)
    if (atm, OPTION_CALL) not in options or (atm, OPTION_PUT) not in options:
        return
    move = options[(atm, OPTION_CALL)].price + options[(atm, OPTION_PUT)].price
    step = strike_step(strikes, span.underlying)
    for width in (n * step for n in range(1, MAX_STEPS + 1)):
        for code, real in pilot_legs(strikes, span.underlying, move, width, step).items():
            row = STRUCTURES[code].legs(frozenset(options), span.underlying, width)
            if row is None:
                SKIPPED["the row's legs are not listed"] += 1
                continue
            try:
                found = figures(parts(span, expiry, row, code, width, day), parts(span, expiry, real, code, width, day))
            except (MarginOutsideModel, RiskInputError, KeyError) as exc:
                SKIPPED[type(exc).__name__] += 1
                continue
            yield [day, road, expiry, kind, code, f"{width:g}", *found, f"{move:.2f}"]


def measure_day(day: date, name: str, data: bytes):
    for road in ROADS:
        span = read_span_file(data, name, symbol=road, allow_short_option_minimum=True)
        monthly = [e for e in span.monthly_expiries if e > day][:2]
        weekly = [e for e in sorted(span.series) if e > day and e not in span.monthly_expiries][:2]
        for kind, expiries in (("monthly", monthly), ("weekly", weekly if road == "NIFTY" else [])):
            for expiry in expiries:
                yield from measure_expiry(span, road, expiry, kind, day)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("out", type=Path)
    parser.add_argument("--every", type=int, default=12)
    parser.add_argument("--from", dest="start", type=date.fromisoformat, default=date(2025, 1, 6))
    parser.add_argument("--to", dest="end", type=date.fromisoformat, default=date(2026, 10, 21))
    args = parser.parse_args()
    is_session = build_trading_days()
    every_day = (args.start + timedelta(days=n) for n in range((args.end - args.start).days + 1))
    days = [day for day in every_day if is_session(day)][:: args.every]
    with args.out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(COLUMNS)
        for day, (name, data) in in_order(per_thread(build_drive_span_files), days, WORKERS):
            if data is None:
                print(f"{day}: not in the archive")
                continue
            writer.writerows(measure_day(day, name, data))
    print("not measured:", dict(SKIPPED) or "none")
    return 0


if __name__ == "__main__":
    sys.exit(main())
