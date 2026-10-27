"""`python -m fno staging cleanup [--apply] [--limit N] [--source TAG ...]` (story S1): staged copies older than 7 days
that are proven promoted are moved to Drive's trash. Report only unless `--apply`. Exit 1 when a removal or a read
failed (alerted by count)."""

from __future__ import annotations

from fno.ingestion.staging_cleanup.cleanup import DEFAULT_LIMIT

ALERT = "Omenix F&O staging cleanup: {line}; see {where}"


def add_staging_cleanup_parser(subparsers) -> None:
    staging = subparsers.add_parser("staging", help="the Drive staging area (story S1)")
    actions = staging.add_subparsers(dest="staging_action", required=True)
    cleanup = actions.add_parser("cleanup", help="move proven-promoted staged copies older than 7 days to the trash")
    cleanup.add_argument("--apply", action="store_true", help="really move them (default: report only)")
    cleanup.add_argument("--limit", type=int, default=DEFAULT_LIMIT, help="most copies examined in one run")
    cleanup.add_argument("--source", action="append", default=None, help="source tag (default: nse)")
    cleanup.set_defaults(func=cmd_staging_cleanup)


def cmd_staging_cleanup(args, out=print) -> int:
    from fno.ingestion.composition import build_alert_sender
    from fno.ingestion.staging_cleanup.wiring import build_staging_cleanup
    from fno.shared.alerts.run_location import run_location

    report = build_staging_cleanup(args.apply, args.limit).run(args.source or ["nse"])
    out(report.line())
    if not report.ok:
        out(build_alert_sender().send(ALERT.format(line=report.line(), where=run_location())))
    return 0 if report.ok else 1
