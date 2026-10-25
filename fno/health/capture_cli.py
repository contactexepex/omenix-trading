"""`python -m fno health capture-failed --run-id <id>` (story O10): run by the capture watcher (`capture-watch.yml`)
when a watched workflow's run did not succeed; `record-error` is the same row for a job that is not a workflow (a
Claude routine), which posts its own line. It appends the run's one row to the capture-error log (never twice for
the same run attempt) and posts one #fno-desk line unless every failed job ran its own alert step.
Exit 1 when GitHub could not be read or a needed line was not accepted, so the watcher's own alert speaks."""

from __future__ import annotations

ALREADY = "already recorded: {url}"
SUCCEEDED = "run {run_id} succeeded: nothing to record"


def add_capture_parser(actions) -> None:
    failed = actions.add_parser("capture-failed", help="record a failed capture run and alert if it posted nothing")
    failed.add_argument("--run-id", type=int, required=True, help="the watched workflow run's ID")
    failed.set_defaults(func=cmd_capture_failed)
    record = actions.add_parser("record-error", help="append one capture-error row (a routine's failure; no alert)")
    for name in ("job", "step", "kind"):
        record.add_argument(f"--{name}", required=True)
    record.add_argument("--message", default="", help="one line built from names, never a log or a value")
    record.add_argument("--run-url", default="", help="the run's or session's link, when there is one")
    record.set_defaults(func=cmd_record_error)


def cmd_capture_failed(args, out=print, runs=None, log=None, alerts=None) -> int:
    from ..alerts.sender import SENT
    from .run_failures import RunSourceError, alert_text, capture_error, needs_alert
    from .wiring import build_capture_error_log, build_run_source

    runs, log = runs or build_run_source(), log or build_capture_error_log()
    try:
        run, jobs = runs.run(args.run_id)
        error = capture_error(run, jobs)
    except RunSourceError as problem:
        out(f"capture-failed: {problem}")
        return 1
    if error is None:
        out(SUCCEEDED.format(run_id=args.run_id))
        return 0
    if log.has_run(error.run_url, error.kind):
        out(ALREADY.format(url=error.run_url))
        return 0
    log.append(error)
    out(",".join(error.row()))
    if not needs_alert(error, jobs):
        return 0
    sent = (alerts or _sender()).send(alert_text(error))
    out(sent)
    return int(sent != SENT)


def cmd_record_error(args, out=print, log=None, today=None) -> int:
    """For jobs that are not GitHub workflows (Claude routines): the row only; the caller posts its own one line."""
    from ..models import now_ist
    from .capture_errors import CaptureError
    from .wiring import build_capture_error_log

    error = CaptureError(today or now_ist().date(), args.job, args.step, args.kind, args.message, args.run_url)
    (log or build_capture_error_log()).append(error)
    out(",".join(error.row()))
    return 0


def _sender():
    from ..composition import build_alert_sender

    return build_alert_sender()
