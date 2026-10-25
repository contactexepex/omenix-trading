"""The capture-gate command's one option, in a module that imports nothing heavy so `python -m fno school` can build its
parser without loading the gate: both `quality.command` (run on its own) and the school subcommand take it from here."""

import argparse
from datetime import date


def add_through(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--through",
        type=date.fromisoformat,
        default=None,
        help="last day (default: today once past 15:15 IST, else yesterday)",
    )
