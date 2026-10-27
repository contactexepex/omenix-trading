"""`python -m fno news probe-outlets [--include-refusing]` (NP4a): one front-page request to each listed outlet. Prints
one line of counts by fixed code and, because the allowlist is public, one `domain: code` line for each outlet.
Nothing is written and nothing is committed; the owner reads the log."""

from __future__ import annotations

from fno.ingestion.news import codes

STOPPED = "news probe-outlets stopped: {code}"


def add_probe_parser(actions) -> None:
    probe = actions.add_parser("probe-outlets", help="one front-page request to each listed outlet (story NP4a)")
    probe.add_argument("--include-refusing", action="store_true",
                       help="also look once at the outlets marked fetch: false (a report for the owner)")  # fmt: skip
    probe.set_defaults(func=cmd_probe_outlets)


def cmd_probe_outlets(args, out=print) -> int:
    from fno.ingestion.news.pages.wiring import build_outlet_probe

    try:
        report = build_outlet_probe(args.include_refusing)()
    except Exception as unexpected:  # noqa: BLE001 - never a traceback in a public log
        out(STOPPED.format(code=f"{codes.UNEXPECTED} {type(unexpected).__name__}"))
        return 1
    out(report.line())
    for line in report.outlet_lines():
        out(line)
    return 0
