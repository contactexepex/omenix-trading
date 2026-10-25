"""Write or check protocol v2's live-pack golden cases (ChatGPT review 29: live golden values separate from
`golden_iv30_rv20.csv`). Each case under `research/forecasts/v2/golden/<case>/` holds its inputs (an A4 snapshot in
A4's own layout) and its outputs (`pack.json`, `forecasts.csv`), computed on 13 Oct 2026 with the repository's
official closes through 12 Oct and the panel's past IV30, a fixed clock (15:05 IST) and a fixed calendar label.

    python tools/forecast_live_golden.py            # check: exit 0 when every case reproduces byte for byte
    python tools/forecast_live_golden.py --write    # (re)write inputs and outputs (a new protocol version only)

Case A: every field observed by 15:00:00. Case B: the 23 Nov ATM put arrived at 15:00:01 and India VIX is stamped
15:00:30, so both are left out (IV30 falls back to 27 Oct alone, flagged; no VIX).
"""

from __future__ import annotations

import csv
import io
import json
import sys
import tempfile
from datetime import date, datetime, time, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fno.config import ROOT, load_app_config  # noqa: E402
from fno.forecast.baseline_wiring import build_live_capture  # noqa: E402
from fno.models import IST  # noqa: E402
from fno.quotes.recorder import COLUMNS, DATASET, QuoteSnapshotRecorder  # noqa: E402
from fno.research_engine.implied_vol import Black76, OptionPricing  # noqa: E402
from fno.storage.raw_store import LocalFolderStore  # noqa: E402

GOLDEN = ROOT / "research" / "forecasts" / "v2" / "golden"
DAY, SNAPSHOT_ID, SPOT, RATE = date(2026, 10, 13), "nifty_20261013_145600", 22380.0, 0.065
FUTURES = {
    date(2026, 10, 27): (22400.0, 30000),
    date(2026, 11, 23): (22510.0, 4000),
    date(2026, 12, 29): (22650.0, 2000),
}
VOLS = {date(2026, 10, 27): 0.14, date(2026, 11, 23): 0.15}  # the two monthly expiries A4 captures
STRIKES = (22300.0, 22350.0, 22400.0, 22450.0)
FIXED_CLOCK = datetime(2026, 10, 13, 15, 5, tzinfo=IST)
CALENDAR_LABEL = "golden-fixture"  # the calendar's own bytes grow each year; the golden pins the transformation
CASES = {"case_a": {"late": None, "vix_time": "13-Oct-2026 14:59"},
         "case_b": {"late": (date(2026, 11, 23), 22400.0, "PE"), "vix_time": "13-Oct-2026 15:00:30"}}  # fmt: skip


def _mid(expiry: date, strike: float, kind: str) -> float:
    years = (expiry - DAY).days / 365
    sigma = VOLS[expiry] if strike == 22400.0 else 0.2
    return Black76().price(OptionPricing(0.0, FUTURES[expiry][0], strike, kind, years, RATE), sigma)


def _rows(late) -> list[dict]:
    rows, moment = [], datetime(2026, 10, 13, 14, 56, 0, tzinfo=IST)
    for expiry in VOLS:
        for strike in STRIKES:
            for kind in ("CE", "PE"):
                moment += timedelta(seconds=5)
                received = (
                    datetime.combine(DAY, time(15, 0, 1), tzinfo=IST) if late == (expiry, strike, kind) else moment
                )
                mid = _mid(expiry, strike, kind)
                row = dict.fromkeys(COLUMNS, "")
                row |= {"snapshot_id": SNAPSHOT_ID, "request_sent_at": moment.isoformat(),
                        "response_received_at": received.isoformat(), "expiry": expiry.isoformat(),
                        "strike": f"{strike:g}", "type": kind, "bid": repr(mid - 0.5), "ask": repr(mid + 0.5),
                        "spot": f"{SPOT:.2f}", "valid": "true", "provider": "golden-fixture"}  # fmt: skip
                rows.append(row)
    return rows


def write_inputs(case: str) -> None:
    spec = CASES[case]
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=COLUMNS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(_rows(spec["late"]))
    meta = {"snapshot_id": SNAPSHOT_ID, "started_at": "2026-10-13T14:55:58+05:30",
            "finished_at": "2026-10-13T15:00:02+05:30", "spot": SPOT, "india_vix": 15.1,
            "india_vix_time": spec["vix_time"], "futures": [{"expiry": e.isoformat(), "last": p, "volume": v}
                                                             for e, (p, v) in FUTURES.items()]}  # fmt: skip
    files = {f"{SNAPSHOT_ID}.csv": out.getvalue().encode(), f"nifty_{DAY:%Y%m%d}.canonical": SNAPSHOT_ID.encode(),
             f"{SNAPSHOT_ID}.meta.json": json.dumps(meta, indent=1, sort_keys=True).encode()}  # fmt: skip
    for name, data in files.items():
        path = GOLDEN / case / "quotes" / QuoteSnapshotRecorder.path(DAY, name, DATASET)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


def outputs(case: str, workdir: Path) -> dict[str, bytes]:
    capture = build_live_capture(load_app_config())
    capture.quotes, capture.root = LocalFolderStore(GOLDEN / case / "quotes"), workdir
    capture.calendar_sha256, capture.clock = CALENDAR_LABEL, lambda: FIXED_CLOCK
    capture.capture(DAY)
    folder = workdir / "research" / "forecasts" / "live_v2" / "2026"
    return {name: (folder / f"2026-10-13_{name}").read_bytes() for name in ("pack.json", "forecasts.csv")}


def main(argv: list[str]) -> int:
    problems = []
    for case in CASES:
        if "--write" in argv:
            write_inputs(case)
        with tempfile.TemporaryDirectory() as work:
            for name, data in outputs(case, Path(work)).items():
                path = GOLDEN / case / name
                if "--write" in argv:
                    path.write_bytes(data)
                elif not path.exists() or path.read_bytes() != data:
                    problems.append(f"{case}/{name} differs from the recomputation")
    print("\n".join(problems) or f"live golden cases unchanged: {', '.join(CASES)}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
