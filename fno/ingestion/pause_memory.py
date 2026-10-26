"""Wires the shared pacer's memory for one command (story R1b2): the committed pause log (read), this run's local
log (written), the #fno-desk alert sender, and whether the command is a live window (`LIVE_WINDOW_COMMANDS`)."""

from __future__ import annotations

from collections.abc import Sequence

from fno.ingestion.composition import build_alert_sender
from fno.shared.config import ROOT
from fno.shared.constants import LIVE_WINDOW_COMMANDS, PAUSE_LOG_PATH, PAUSE_LOG_RUN_PATH
from fno.shared.http_pacing import SHARED_PACER
from fno.shared.resilience.transition_log import LayeredLog

GLOBAL_OPTIONS_WITH_VALUE = ("--config", "--provider")  # the options `fno` takes before the command (cli.build_parser)


def command_words(argv: Sequence[str]) -> tuple[str, ...]:
    """The words that name the command: the first two arguments that are not options (and not an option's value)."""
    words, skip = [], False
    for argument in argv:
        if skip:
            skip = False
        elif argument in GLOBAL_OPTIONS_WITH_VALUE:
            skip = True
        elif not argument.startswith("-"):
            words.append(argument)
    return tuple(words[:2])


def is_live_window(argv: Sequence[str]) -> bool:
    words = command_words(argv)
    return " ".join(words) in LIVE_WINDOW_COMMANDS or " ".join(words[:1]) in LIVE_WINDOW_COMMANDS


def attach_pause_memory(argv: Sequence[str], pacer=SHARED_PACER, root=ROOT) -> None:
    """Called once by `main` before any command runs."""
    log = LayeredLog(root / PAUSE_LOG_PATH, root / PAUSE_LOG_RUN_PATH)
    pacer.attach(log, build_alert_sender(), live_window=is_live_window(argv))
