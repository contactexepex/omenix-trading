"""Write or check the forecast protocol's golden IV30 and RV20 values (story G1, judge 47).

python tools/forecast_golden.py            # check: exit 0 when every panel day equals the golden file
python tools/forecast_golden.py --write    # (re)write the file: only for a new protocol version or a named A11 revision
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fno.config import ROOT, load_app_config  # noqa: E402
from fno.forecast.golden import GOLDEN_FILE, differences, read_golden, write_golden  # noqa: E402
from fno.forecast.wiring import forecast_golden_rows  # noqa: E402

YEARS = list(range(2019, 2027))  # the panel's years at the protocol's writing


def main(argv: list[str]) -> int:
    rows = forecast_golden_rows(load_app_config(), YEARS)
    path = ROOT / GOLDEN_FILE
    if "--write" in argv:
        path.write_text(write_golden(rows), encoding="utf-8")
        print(f"wrote {len(rows)} days to {GOLDEN_FILE}")
        return 0
    problems = differences(read_golden(path.read_text(encoding="utf-8")), rows)
    print("\n".join(problems[:20]) or f"golden values unchanged on {len(rows)} days")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
