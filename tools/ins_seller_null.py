"""The instructor's skewed-seller null grid (story MS-INS, part d; judge 516): every hold the frozen cards hold, loss
chances 0.05-0.2, 2,000 seeded runs a cell, through the shipped comparison code. Writes
research/school/instructor_seller_null.csv; the worst upper end, rounded up, is the rate seller rows print
(`SELLER_FALSE_POSITIVE_PCT`). Reproducible: the seeds are fixed. About 10 minutes on 4 processes.

    python tools/ins_seller_null.py [--processes 4]"""

import argparse
import csv
import sys
from multiprocessing import Pool
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fno.school.drivers.cards import CARDS_FOLDER, load_cards  # noqa: E402
from fno.school.instructor.paired.holds import hold_sessions  # noqa: E402
from fno.school.instructor.paired.nulls import seller_cell, seller_cells  # noqa: E402

OUTPUT = ROOT / "research" / "school" / "instructor_seller_null.csv"
HEADER = ("hold", "loss_chance", "sessions", "batch", "share", "wilson_upper")


def _run(cell):
    return (*cell, *seller_cell(*cell))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--processes", type=int, default=4)
    args = parser.parse_args()
    cards = load_cards(ROOT / CARDS_FOLDER).values()
    holds = [h for c in cards if (h := hold_sessions(c, cards))]
    with Pool(args.processes) as pool:
        rows = pool.map(_run, seller_cells(holds))
    with OUTPUT.open("w", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(HEADER)
        writer.writerows((h, p, n, b, f"{s:.4f}", f"{u:.4f}") for h, p, n, b, s, u in rows)
    worst = max(rows, key=lambda r: r[5])
    print(f"{len(rows)} cells; worst {worst[4]:.1%} (upper end {worst[5]:.1%}) at hold {worst[0]}, p {worst[1]}, "
          f"{worst[2]} sessions")  # fmt: skip
    return 0


if __name__ == "__main__":
    sys.exit(main())
