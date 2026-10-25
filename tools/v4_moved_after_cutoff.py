"""Protocol v4's "moved after cutoff" X (story G10): the nearest-rank 95th percentile of abs(ln(S_15:15 / S_14:30)) over
A16b's checked 2020-26 regular sessions (rows `ok` with `nse_check = checked`), levels by A16b's own rule (the close
of the candles ending at 14:30 and 15:15) from the Drive copies each row names. Read-only: no Groww, nothing archived.

    python tools/v4_moved_after_cutoff.py   # writes research/forecasts/v4_moved_after_cutoff.json
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fno.forecast_v4.cutoff_move import FLAG_QUANTILE, cutoff_move, moved_after_cutoff, nearest_rank  # noqa: E402
from fno.forecast_v4.terms import V4_CAPTURE_START, V4_COMMON_SNAPSHOT  # noqa: E402
from fno.intraday.backfill_wiring import INTRADAY_FOLDER, build_candle_archive  # noqa: E402
from fno.intraday.candle_levels import parse_candles, session_candles  # noqa: E402
from fno.intraday.candle_rv_table import CandleRvTable  # noqa: E402
from fno.intraday.slots import marks  # noqa: E402

OUT = ROOT / "research" / "forecasts" / "v4_moved_after_cutoff.json"
CHECKED, OK = "checked", "ok"
TABLE, MANIFESTS = "research/data/intraday/rv-candle", "research/data/manifests/groww-candles"
CONVENTION = "nearest rank: the ceil(0.95 n)-th smallest move, no interpolation; flagged when strictly above X"


def mark_index(day: date, at) -> int:
    return [m.time() for m in marks(day)].index(at)


def checked_moves(rows: list[dict], archive) -> dict[str, float]:
    loaded, moves = {}, {}
    for row in sorted(rows, key=lambda r: r["session"]):
        if row["status"] != OK or row["nse_check"] != CHECKED:
            continue
        day = date.fromisoformat(row["session"])
        if row["copy_15m"] not in loaded:
            loaded[row["copy_15m"]] = parse_candles(archive.load(archive.row_for(row["copy_15m"])).rows)
        levels = session_candles(day, loaded[row["copy_15m"]]).levels
        start, end = levels[mark_index(day, V4_CAPTURE_START)], levels[mark_index(day, V4_COMMON_SNAPSHOT)]
        if start is not None and end is not None:
            moves[row["session"]] = cutoff_move(start, end)
    return moves


def revision(path: str) -> str:
    return subprocess.run(["git", "log", "-1", "--format=%H", "--", path], cwd=ROOT, capture_output=True,
                          text=True, check=True).stdout.strip()  # fmt: skip


def main() -> None:
    rows = CandleRvTable(INTRADAY_FOLDER).rows()
    moves = checked_moves(rows, build_candle_archive())
    x = nearest_rank(list(moves.values()), FLAG_QUANTILE)
    flagged = sum(moved_after_cutoff(m, x) for m in moves.values())
    result = {
        "x": x, "sample_count": len(moves), "quantile": FLAG_QUANTILE,
        "convention": CONVENTION,
        "first_session": min(moves), "last_session": max(moves), "rows_read": len(rows),
        "flagged_in_history": flagged, "flagged_share": flagged / len(moves),
        "source": {"table": TABLE, "table_revision": revision(TABLE), "manifests_revision": revision(MANIFESTS)},
        "computed_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }  # fmt: skip
    OUT.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "source"}, indent=1))


if __name__ == "__main__":
    main()
