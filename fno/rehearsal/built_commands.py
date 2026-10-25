"""Whether fno has a command yet (story REH1j): a step not live in real runs whose command is not built is reported
"not built" in a rehearsal, never run and never failed. fno's own parser decides, never an error text. The walk goes
word by word: while the parser reached has subcommands, the next word must be one of them; it stops at the first word
that is not a subcommand (an option such as `--day`, or a value) of a parser with none. The path is built when it
ends on a parser that needs no further subcommand and a handler (`set_defaults(func=...)`) is set on it or on a group
above it (`quotes` dispatches its subcommands itself). So a missing child under a real parent
(`margins stress-broker-check`) and a prefix of a real command (`margins`) are not built; `pricedist record --day D
--live` is. Two edges differ from argparse, on purpose and with no step affected: a top-level option before the
command (`--config x chain`) reads as not built, and an extra value after a full command (`closes read extra`) as
built; a step's command never has either."""

from __future__ import annotations

import argparse
from collections.abc import Callable, Sequence

NOT_BUILT = "no command '{command}' in fno"


def is_built(arguments: Sequence[str], parser: Callable[[], argparse.ArgumentParser] | None = None) -> bool:
    if parser is None:
        from ..cli import build_parser as parser
    reached = parser()
    handled = reached.get_default("func") is not None
    for word in arguments:
        commands = _subcommands(reached)
        if commands is None or word not in commands.choices:
            break  # an option or a value; or a word that is no subcommand: the group then still needs one
        reached = commands.choices[word]
        handled = handled or reached.get_default("func") is not None
    commands = _subcommands(reached)
    return handled and (commands is None or not commands.required)


def _subcommands(parser: argparse.ArgumentParser) -> argparse._SubParsersAction | None:
    found = [action for action in parser._actions if isinstance(action, argparse._SubParsersAction)]
    return found[0] if found else None
