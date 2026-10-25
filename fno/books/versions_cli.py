"""`python -m fno versions register ...` and `python -m fno versions check` (story D6): register a book's version
before its first counted decision (commit the registry right after), and check the registry. Registering only
records which components a book runs on; it changes no rule and places no order."""

from __future__ import annotations

import argparse
import json
from datetime import date

from ..constants import BOOKS

EXIT_REFUSED = 2


def _book(text: str) -> str:
    from .version_registry import is_known_book

    if not is_known_book(text):
        raise argparse.ArgumentTypeError(
            f"{text!r} is not one of {', '.join(BOOKS)} or a school:<driver code>@<version>"
        )
    return text


def add_versions_parser(subparsers) -> None:
    versions = subparsers.add_parser("versions", help="the books' version registry (story D6)")
    actions = versions.add_subparsers(dest="versions_cmd", required=True)
    actions.add_parser("check", help="read journal/versions.csv and list each book's versions")
    register = actions.add_parser("register", help="append a version row (commit journal/versions.csv at once)")
    register.add_argument("book", type=_book)
    register.add_argument("version_id")
    register.add_argument("--starts-on", type=date.fromisoformat, required=True)
    register.add_argument("--components", required=True, help='JSON object, e.g. {"model": "...", "playbook": "..."}')
    register.add_argument("--reason", required=True)
    versions.set_defaults(func=cmd_versions)


def cmd_versions(args) -> int:
    from ..composition import build_version_registry
    from ..config import ROOT
    from ..research_engine.ledger import Git
    from .version_registry import VersionError, VersionRow

    registry = build_version_registry()
    try:
        if args.versions_cmd == "register":
            components = json.loads(args.components)
            head = Git(ROOT).head()  # the components are frozen in this commit
            registry.append(VersionRow(args.book, args.version_id, args.starts_on, head, components, args.reason))
            print(f"registered {args.book} {args.version_id} from {args.starts_on}: commit journal/versions.csv now")
            return 0
        for row in registry.rows():
            print(f"{row.book} {row.version_id} from {row.starts_on} (components {row.registered_in_commit[:10]})")
    except (VersionError, ValueError) as refused:
        print(f"refused: {refused}")
        return EXIT_REFUSED
    return 0
