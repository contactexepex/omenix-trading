"""Check the numbered series against their registries in `numbers/` (story O12); standard library only.

    python tools/check_numbers.py          # one line per problem, exit 1 when any; CI runs it on every push
    python tools/check_numbers.py --seed   # when O12 merges: register the files on main as `existing` history and
                                           # pin it in fno/numbering/seed_pins.json (a later run is a judged change)
    python tools/check_numbers.py --alert [--baseline DIR]
        # also post the problem lines to #fno-desk (story O12b); with --baseline, only the problems that DIR (a
        # checkout of the commit before) did not already have, so a red main is announced once, not on every push

Fails when a numbered file (or a numbered `## Addendum` heading) has no registry row, when a number is used twice
outside the seeded history, when the seeded history differs from its pin, when a series file is misnamed, or when a
row is malformed. A row with no file yet is a claim still being written. Ledger trials (story O12e): fails when a
whole-number trial id sits in no claimed block or in another experiment's block, or when two blocks overlap.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fno.numbering.check import check_numbers  # noqa: E402
from fno.numbering.seed import seed_registries  # noqa: E402

CLEAN = "number check: clean"
ALERT = (
    "Omenix F&O number check is red on main: {count} new problem(s). Register the file's number in numbers/ or rename "
    "it (numbers/README.md); the check names the file and line:\n{lines}"
)
FAILED = "number check: FAILED, {count} problem(s); claim numbers with tools/claim_number.py (docs/stories/O12)"


def main(argv: list[str] | None = None, alerts=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=ROOT, help="the checkout to check (default: this one)")
    parser.add_argument("--seed", action="store_true", help="register the files already present, as history")
    parser.add_argument("--alert", action="store_true", help="post the problem lines to #fno-desk (story O12b)")
    parser.add_argument("--baseline", type=Path, help="with --alert: skip problems this older checkout already had")
    args = parser.parse_args(argv)
    if args.seed:
        print(f"number seed: {seed_registries(args.root)} row(s) added")
    problems = check_numbers(args.root)
    for line in problems:
        print(line)
    print(FAILED.format(count=len(problems)) if problems else CLEAN)
    if args.alert:
        _alert(problems, args.baseline, alerts)
    return 1 if problems else 0


def _alert(problems: list[str], baseline: Path | None, alerts) -> None:
    """Posts the problems the baseline did not already have; nothing when there are none."""
    known = set(check_numbers(baseline)) if baseline else set()
    new = [line for line in problems if line not in known]
    if not new:
        return
    if alerts is None:
        from fno.composition import build_alert_sender  # only when posting: the plain check stays standard library

        alerts = build_alert_sender()
    print(alerts.send(ALERT.format(count=len(new), lines="\n".join(new))))


if __name__ == "__main__":
    sys.exit(main())
