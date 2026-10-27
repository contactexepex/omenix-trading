"""`python -m fno news seed-companies [--apply]` (NP3a): the first company list from NSE's own archived lists. Report
only without `--apply`. The line it prints is counts and a fixed code: no symbol and no company name, because the list
is the owner's private content."""

from __future__ import annotations

from fno.ingestion.news import codes
from fno.shared.models import now_utc

LINE = (
    "news seed-companies ({mode}): stocks {stocks}, indices {indices}, "
    "names given their full form {renamed}, rows skipped {skipped}"
)
STOPPED = "news seed-companies stopped: {code}"


def add_seed_parser(actions) -> None:
    seed = actions.add_parser("seed-companies", help="the first company list from NSE's archived lists (story NP3a)")
    seed.add_argument("--apply", action="store_true", help="write companies-v1.json (default: report only)")
    seed.set_defaults(func=cmd_seed_companies)


def cmd_seed_companies(args, out=print) -> int:
    from fno.ingestion.news.companies.wiring import SeedFailed, seed_companies

    try:
        seed = seed_companies(args.apply, now_utc().date())
    except SeedFailed as stopped:
        out(STOPPED.format(code=stopped))
        return 1
    except Exception as unexpected:  # noqa: BLE001 - the message of a Drive error can name a path
        out(STOPPED.format(code=f"{codes.UNEXPECTED} {type(unexpected).__name__}"))
        return 1
    mode = "written" if args.apply else "report only"
    out(LINE.format(mode=mode, stocks=seed.stocks, indices=seed.indices, renamed=seed.renamed, skipped=seed.skipped))
    return 0
