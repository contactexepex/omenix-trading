"""`python -m fno card daily [--on YYYY-MM-DD] [--post]` and `python -m fno card witness --on YYYY-MM-DD` (story T1).
Without `--post` the card is only printed: nothing is posted, saved or written. Paper only: a card never places,
modifies or cancels an order."""

from __future__ import annotations

from datetime import date

NOT_A_SESSION = "not a trading day: no card for {day}"
TEST_NEEDS_POST = "--test marks a live post: use it with --post (nothing done)"
POST_TODAY_ONLY = "--post issues only today's card ({today}, IST), not {day}'s: nothing done"
DRY_RUN = "dry run: nothing posted, saved or written (add --post to send it to #fno-desk)"


def add_card_parser(subparsers) -> None:
    card = subparsers.add_parser("card", help="the daily trade card, PAPER ONLY (story T1)")
    which = card.add_subparsers(dest="card_cmd", required=True)
    daily = which.add_parser("daily", help="build and print the day's card; --post sends it")
    daily.add_argument("--on", type=date.fromisoformat, help="the session (default today, IST)")
    daily.add_argument("--post", action="store_true", help="post to #fno-desk, save to Drive, write delivery metadata")
    daily.add_argument("--test", action="store_true", help="with --post: one live delivery check marked TEST")
    daily.set_defaults(func=cmd_card_daily)
    witness = which.add_parser("witness", help="the issuance witnesses of a day's cards (Slack and GitHub)")
    witness.add_argument("--on", type=date.fromisoformat, required=True, help="the session")
    witness.set_defaults(func=cmd_card_witness)


def cmd_card_daily(args, out=print) -> int:
    from ..desk.wiring import download_private_records
    from ..models import now_ist
    from .wiring import build_card_issuer, build_daily_card

    if args.test and not args.post:
        out(TEST_NEEDS_POST)
        return 2
    today = now_ist().date()
    day = args.on or today
    if args.post and day != today:  # today's records would be issued as another day's card
        out(POST_TODAY_ONLY.format(day=day, today=today))
        return 2
    download_private_records()  # story E2c: the trade counts come from the accounts in Drive
    prepared = build_daily_card().prepare(day)
    if prepared is None:
        out(NOT_A_SESSION.format(day=day))
        return 0
    card, text = prepared
    out(text)
    if not args.post:
        out(DRY_RUN)
        return 0
    result = build_card_issuer().issue(card, text, test=args.test)
    out("\n".join(result.lines))
    return 0 if result.sent and result.complete else 1


def cmd_card_witness(args, out=print) -> int:
    from .wiring import build_issuance_witness

    out("\n".join(build_issuance_witness().lines(args.on)))
    return 0
