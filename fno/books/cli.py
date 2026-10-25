"""Commands for the paper accounts: `python -m fno account init`, `show` and `top-up` (never orders)."""

from __future__ import annotations

import json

from ..constants import BOOKS

EXIT_BUSY = 3  # another writer holds the account: this run wrote nothing
EXIT_REFUSED = 1  # a book's top-up was refused: nothing written for it


def add_account_parser(subparsers) -> None:
    account = subparsers.add_parser("account", help="the three books' paper accounts (never orders)")
    actions = account.add_subparsers(dest="account_cmd", required=True)
    init = actions.add_parser("init", help="open each book's account once with risk.paper_account_rs and no positions")
    init.add_argument("--book", choices=BOOKS, action="append", help="only this book (repeatable); default all three")
    top_up = actions.add_parser("top-up", help="bring each book's capital to the books' paper account size (E1b)")
    top_up.add_argument("--book", choices=BOOKS, action="append", help="only this book (repeatable); default all three")
    actions.add_parser("move-to-drive", help="once (story E2c): upload the committed account files to Drive")
    show = actions.add_parser("show", help="cash, closed equity and open legs of one book (no marks needed)")
    show.add_argument("book", choices=BOOKS)
    account.set_defaults(func=cmd_account)


def cmd_account(args) -> int:
    from ..books.lock import AccountBusy
    from ..composition import build_paper_account, open_account_writer
    from ..desk.wiring import download_private_records
    from ..models import now_ist

    if args.account_cmd == "move-to-drive":
        return move_to_drive()
    files = download_private_records()  # story E2c: the accounts live in Drive
    if args.account_cmd == "show":
        print(json.dumps(build_paper_account(args.book).summary(), indent=1))
        return 0
    if args.account_cmd == "top-up":
        return top_up_books(args.book or BOOKS, files=files)
    status = 0
    for book in args.book or BOOKS:
        try:
            with open_account_writer(book, files=files) as writer:
                print(f"{book}: {'started' if writer.start(now_ist().date()) else 'already started; unchanged'}")
        except AccountBusy as busy:
            print(f"{book}: not written: {busy}")
            status = EXIT_BUSY
    return status


def top_up_books(books, root=None, files=None) -> int:
    """Story E1b: one line per book; the target is the books' paper account size, never typed."""
    from ..books.account import AccountError
    from ..books.lock import AccountBusy
    from ..composition import open_account_writer, paper_account_rs
    from ..config import ROOT
    from ..models import now_ist

    status, target = 0, paper_account_rs()
    for book in books:
        try:
            with open_account_writer(book, root or ROOT, files=files) as writer:
                when = now_ist()
                done = writer.top_up(when, target)
        except (AccountError, AccountBusy) as problem:
            print(f"{book}: refused: {problem}")
            status = EXIT_REFUSED
            continue
        if not done.amount:
            print(f"{book}: already at size Rs {target:,.2f}; unchanged")
            continue
        kind = "a further top-up" if done.further else "topped up"
        print(f"{book}: {kind} by Rs {done.amount:,.2f} at {when.isoformat()} to Rs {target:,.2f}")
    return status


def move_to_drive(root=None) -> int:
    """Story E2c, once at its merge: each account file to Drive (never overwriting other bytes) and each book's first
    `daily_totals.csv` written; then the account files are removed from the repository by hand (`git rm`)."""
    from ..config import ROOT
    from ..desk.private_files import DIFFERENT
    from ..desk.wiring import build_private_files
    from .daily_totals import write_daily_totals

    root = root or ROOT
    moved = build_private_files(root).move_accounts()
    for name, outcome in moved.items():
        print(f"{name}: {outcome}")
    if DIFFERENT in moved.values():
        return EXIT_REFUSED
    for book in BOOKS:
        print(f"written {write_daily_totals(root, book).relative_to(root)}: commit it")
    return 0
