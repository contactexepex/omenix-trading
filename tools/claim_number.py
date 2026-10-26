"""Claim the next number of a numbered series on `main` (story O12), before writing the file.

    python tools/claim_number.py claude-response g4-scoring --session session_01ABC
    python tools/claim_number.py judge-report g4-scoring --session session_01DEF --number 66   # an exact number
    python tools/claim_number.py judge-addendum round-2-fixes --session session_01DEF --report 270
    python tools/claim_number.py ledger-trial edge2-f7 --session session_01GHI --count 6   # a block of trial ids

Pushes one row to `numbers/<category>.csv` on `main` from a temporary worktree (your branch and files are untouched)
and prints the claimed number and the file to create. A refused push (someone claimed first) is retried on the new
`main`; the number is yours only when this prints "claimed". Exit 1 when nothing was claimed.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fno.shared.numbering.claim import CLAIMABLE, ClaimNotPushed, ClaimRequest  # noqa: E402
from fno.shared.numbering.git_main import GitFailed  # noqa: E402
from fno.shared.numbering.wiring import build_number_claimer  # noqa: E402

CLAIMED = "claimed: {category} {number} -> {name}\nnext: {step}"
NOT_CLAIMED = "number claim: NOT claimed ({reason}). Nothing was pushed: do not write the file; fix it and claim again."
# The last line is the verdict, so a reader of the output's tail never misses a failure (judge B, 22 Oct)
GIT_REASONS = {
    "commit": "the commit was refused, usually by the record-scan hook: git's output is above; a missing package "
    "means this Python lacks the requirements, so run `sh ops/routine_setup.sh`",
    "push": "main refused the push for a reason other than a lost race: git's output is above",
}


def main(argv: list[str] | None = None, claimer=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("category", choices=sorted(CLAIMABLE))
    parser.add_argument(
        "slug",
        help="the file's short name (lower-case, '-' or '_'); an addendum's short label; for ledger-trial, "
        "the experiment prefix the block is for",
    )
    parser.add_argument("--session", required=True, help="the claiming session's id, written in the row")
    parser.add_argument("--report", help="judge-addendum only: the judge report the addendum extends")
    parser.add_argument("--number", dest="exact", help="claim this number (ledger-trial: block a-b) exactly")
    parser.add_argument("--count", type=int, help="ledger-trial only: how many trial ids to claim (default 1)")
    parser.add_argument("--root", type=Path, default=ROOT, help="the git repository (default: this one)")
    args = parser.parse_args(argv)
    request = ClaimRequest(CLAIMABLE[args.category], args.slug, args.session, args.report, args.exact, args.count)
    try:
        claim = (claimer or build_number_claimer(args.root)).claim(request)
    except GitFailed as failed:
        print(failed.output)
        print(NOT_CLAIMED.format(reason=GIT_REASONS.get(failed.step, f"git {failed.step} failed: its output is above")))
        return 1
    except (ValueError, ClaimNotPushed) as reason:  # ValueError: a refused request or a broken registry
        print(NOT_CLAIMED.format(reason=reason))
        return 1
    step = CLAIMABLE[claim.category].next_step(claim.number, claim.name)
    print(CLAIMED.format(**vars(claim), step=step))
    return 0


if __name__ == "__main__":
    sys.exit(main())
