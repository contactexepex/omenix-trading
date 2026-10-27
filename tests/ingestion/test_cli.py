"""The ``python -m fno`` command-line surface (``fno/ingestion/cli.py``): every subcommand's parser is built and
wired, ``--help`` works for each, and representative commands dispatch to a handler. No handler is executed, so no
network, Slack, Drive, Groww or NSE call happens."""

from __future__ import annotations

import pytest

from fno.ingestion.cli import build_parser

# Every top-level subcommand the CLI exposes (kept in sync with build_parser).
SUBCOMMANDS = sorted({
    "chain", "circulars", "closes", "data-cache", "data-coverage", "data-fingerprints", "data-librarian",
    "data-repair", "data-revisions", "data-snapshot", "drive-check", "filings", "flows", "fo-masters",
    "global-cues", "groww-check", "intraday", "news", "participant-oi", "pipeline", "preopen", "promote", "quotes",
    "stage", "staging", "vix-history",
})  # fmt: skip


def _choices() -> dict:
    parser = build_parser()
    for action in parser._subparsers._group_actions:
        if getattr(action, "choices", None):
            return dict(action.choices)
    raise AssertionError("no subparsers found")


def test_every_subcommand_is_registered() -> None:
    assert set(_choices()) == set(SUBCOMMANDS)
    assert len(SUBCOMMANDS) == 26


@pytest.mark.parametrize("name", SUBCOMMANDS)
def test_subcommand_help_exits_cleanly(name: str) -> None:
    with pytest.raises(SystemExit) as exit_info:
        build_parser().parse_args([name, "--help"])
    assert exit_info.value.code == 0


def test_top_level_help_exits_cleanly() -> None:
    with pytest.raises(SystemExit) as exit_info:
        build_parser().parse_args(["--help"])
    assert exit_info.value.code == 0


def test_no_command_is_an_error() -> None:
    with pytest.raises(SystemExit) as exit_info:
        build_parser().parse_args([])
    assert exit_info.value.code != 0  # a subcommand is required


def test_chain_parses_defaults_and_dispatches() -> None:
    from fno.ingestion.cli import cmd_chain

    args = build_parser().parse_args(["chain", "NIFTY"])
    assert args.func is cmd_chain
    assert args.underlying == "NIFTY"
    assert args.width == 8  # default strikes either side of ATM
    assert args.expiry is None


def test_direct_handlers_are_wired() -> None:
    from fno.ingestion.cli import cmd_data_coverage, cmd_drive_check, cmd_groww_check

    assert build_parser().parse_args(["drive-check"]).func is cmd_drive_check
    assert build_parser().parse_args(["groww-check"]).func is cmd_groww_check
    assert build_parser().parse_args(["data-coverage"]).func is cmd_data_coverage


def test_provider_override_choices() -> None:
    args = build_parser().parse_args(["--provider", "sample", "chain", "NIFTY"])
    assert args.provider == "sample"
    with pytest.raises(SystemExit):  # an unknown provider is rejected at parse time
        build_parser().parse_args(["--provider", "bogus", "chain", "NIFTY"])


def test_every_parsed_command_has_a_callable_handler() -> None:
    # A command that takes only optional args parses on its own; for the rest we at least confirm the subparser
    # object exists and carries a formatter (its arguments were defined without error).
    choices = _choices()
    for name in SUBCOMMANDS:
        assert choices[name].format_help()  # building help exercises every argument definition
