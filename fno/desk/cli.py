"""`python -m fno desk ...`: the one parser of the paper desk's commands (judge 73: one parser, each story adds its
command here, never a second `desk` parser). Each command sets its own handler on its own subparser. Never orders."""

from __future__ import annotations

from ..books.book1_cli import add_book1_command
from ..scorecard.cli import add_scorecard_command
from .pack_cli import add_pack_command

COMMANDS = (add_pack_command, add_scorecard_command, add_book1_command)  # stories E2, E6, E5 (E3 runs in `fno daily`)


def add_desk_parser(subparsers) -> None:
    desk = subparsers.add_parser(
        "desk", help="the paper desk's commands: packs, scorecards, Book 1's decision (never orders)"
    )
    actions = desk.add_subparsers(dest="desk_cmd", required=True)
    for add_command in COMMANDS:
        add_command(actions)
