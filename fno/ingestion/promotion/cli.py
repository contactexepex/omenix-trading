"""`python -m fno stage <dataset>` and `python -m fno promote <dataset>` (docs/PIPELINE_DESIGN.md, Phase 1).

`stage` fetches a dataset's sessions from NSE into Staging only. `promote` runs what is staged through the checks into
the write-once Record, commits the manifest rows it wrote and posts any file that did not make it to #fno-desk."""

from __future__ import annotations

from datetime import date, timedelta

from fno.ingestion.storage.librarian_cli import SIGN_IN_REFUSED, print_now
from fno.ingestion.storage.manifest_commit import exit_for_commit
from fno.ingestion.storage.owner_token import DriveSignInRefused
from fno.ingestion.storage.raw_source import RawSourceUnavailable
from fno.shared.config import load_app_config
from fno.shared.models import today_local

REJECTED_ALERT = "Omenix F&O promotion gate ({dataset}): files were NOT promoted to the record: {lines}"
ALERT_LINES = 5  # the alert names the first few; the run log has all of them


def add_promotion_parsers(subparsers) -> None:
    from fno.ingestion.promotion.wiring import PROMOTABLE_DATASETS

    for name, help_text in (("stage", "fetch a dataset into Staging only"),
                            ("promote", "promote staged files through the checks into the Record")):  # fmt: skip
        parser = subparsers.add_parser(name, help=help_text)
        parser.add_argument("dataset", choices=PROMOTABLE_DATASETS)
        parser.add_argument("--from", dest="start", type=date.fromisoformat, required=True,
                            help="YYYY-MM-DD first session (required: never all history)")  # fmt: skip
        parser.add_argument("--to", dest="end", type=date.fromisoformat, default=today_local() - timedelta(days=1),
                            help="YYYY-MM-DD (default: yesterday)")  # fmt: skip
        parser.set_defaults(func=cmd_stage if name == "stage" else cmd_promote)


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

    recorder, what, committed, refused = build_manifest_recorder(), f"promote {args.dataset}", [], False
    try:
        run = build_promotion_run(args.dataset, load_app_config(args.config).get("promotion", {}).get("max_lag_days"))
        report = run.promote(args.start, args.end)
    except DriveSignInRefused as exc:
        out(SIGN_IN_REFUSED.format(reason=exc.reason))
        refused = True
    finally:
        committed.append(recorder.commit(what))
        out(committed[0])

    def alert(text: str) -> None:
        out(build_alert_sender().send(text))

    if refused:
        return exit_for_commit(committed, 1, alert, what)
    out("\n".join(report.lines()))
    if report.problems():  # notes (failed copies on days the Record holds) are log lines only
        lines = "; ".join(report.problems()[:ALERT_LINES])
        alert(REJECTED_ALERT.format(dataset=args.dataset, lines=lines))
    return exit_for_commit(committed, 0 if report.complete else 1, alert, what)
