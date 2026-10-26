"""`python -m fno stage <dataset>` and `python -m fno promote <dataset>` (docs/PIPELINE_DESIGN.md, Phase 1).

`stage` fetches a dataset's sessions from NSE into Staging only. `promote` runs what is staged through the checks into
the write-once Record, commits the manifest rows it wrote and posts any file that did not make it to #fno-desk."""

from __future__ import annotations

from datetime import date, timedelta

from fno.ingestion.storage.librarian_cli import SIGN_IN_REFUSED, print_now
from fno.ingestion.storage.owner_token import DriveSignInRefused
from fno.ingestion.storage.raw_source import RawSourceUnavailable
from fno.shared.models import today_local

REJECTED_ALERT = "Omenix F&O promotion gate ({dataset}): files were NOT promoted to the record: {lines}"
ALERT_LINES = 5  # the alert names the first few; the run log has all of them


def add_promotion_parsers(subparsers) -> None:
    from fno.ingestion.promotion.wiring import DEFAULT_MAX_LAG_DAYS, PROMOTABLE_DATASETS

    for name, help_text in (("stage", "fetch a dataset into Staging only"),
                            ("promote", "promote staged files through the checks into the Record")):  # fmt: skip
        parser = subparsers.add_parser(name, help=help_text)
        parser.add_argument("dataset", choices=PROMOTABLE_DATASETS)
        parser.add_argument("--from", dest="start", type=date.fromisoformat, default=None,
                            help="YYYY-MM-DD (default: the dataset's first day)")  # fmt: skip
        parser.add_argument("--to", dest="end", type=date.fromisoformat, default=today_local() - timedelta(days=1),
                            help="YYYY-MM-DD (default: yesterday)")  # fmt: skip
        parser.set_defaults(func=cmd_stage if name == "stage" else cmd_promote)
        if name == "promote":
            parser.add_argument("--max-lag-days", type=int, default=DEFAULT_MAX_LAG_DAYS,
                                help="a file fetched later than this after its session is not promoted")  # fmt: skip
            parser.add_argument("--backfill", action="store_true", help="no lag limit (old sessions fetched today)")


def cmd_stage(args, out=print_now) -> int:
    from fno.ingestion.promotion.wiring import build_stager

    try:
        report = build_stager(args.dataset).stage(args.start, args.end)
    except DriveSignInRefused as exc:
        out(SIGN_IN_REFUSED.format(reason=exc.reason))
        return 1
    except RawSourceUnavailable as exc:
        out(f"stopped: {exc}. Run the same command again later.")
        return 1
    out("\n".join(report.lines()))
    return 0 if report.complete else 1


def cmd_promote(args, out=print_now) -> int:
    from fno.ingestion.composition import build_alert_sender
    from fno.ingestion.promotion.wiring import build_promotion_run
    from fno.ingestion.storage.wiring import build_manifest_recorder

    recorder = build_manifest_recorder()
    try:
        run = build_promotion_run(args.dataset, None if args.backfill else args.max_lag_days)
        report = run.promote(args.start, args.end)
    except DriveSignInRefused as exc:
        out(SIGN_IN_REFUSED.format(reason=exc.reason))
        return 1
    finally:
        out(recorder.commit(f"promote {args.dataset}"))
    out("\n".join(report.lines()))
    if report.problems():
        lines = "; ".join(report.problems()[:ALERT_LINES])
        out(build_alert_sender().send(REJECTED_ALERT.format(dataset=args.dataset, lines=lines)))
    return 0 if report.complete else 1
