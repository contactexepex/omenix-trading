"""`python -m fno data-librarian <dataset>`: fills a dataset's gaps in the owner's Google Drive from NSE (story A9).

Resumable: run it again after a stop and it fetches only what is still missing. The manifest rows it wrote are
committed and pushed at the end of every run, finished or stopped. A refused Drive sign-in stops the
run with a clear error and an alert to #fno-desk naming the owner's fix; nothing is skipped silently.
"""

from __future__ import annotations

from datetime import date, timedelta
from functools import partial

from ..alerts.sender import AlertSender
from ..models import today_local
from .manifest_commit import ManifestRecorder
from .owner_token import DriveSignInRefused
from .raw_source import RawSourceUnavailable

SIGN_IN_REFUSED = (
    "Omenix F&O: Google refused the Drive upload sign-in ({reason}), so the data librarian uploaded nothing more. "
    "The owner's consent has expired or was revoked. One-minute fix on your computer: "
    "python3 tools/gdrive_oauth_setup.py <client_secret JSON>, then put the new FNO_GDRIVE_OAUTH_REFRESH_TOKEN in the "
    "cloud environment's settings. To stop it expiring every 7 days, publish the OAuth app "
    "(Google Cloud console, OAuth consent screen, Publish app)."
)
SOURCE_STOPPED = "stopped: {error}. Run the same command again later to resume (only missing files are fetched)."


def add_librarian_parser(subparsers) -> None:
    from .wiring import LIBRARIAN_DATASETS, SNAPSHOT_DATASETS

    lib = subparsers.add_parser("data-librarian", help="upload a dataset's missing raw files to Drive (story A9)")
    lib.add_argument("dataset", choices=sorted(LIBRARIAN_DATASETS))
    lib.add_argument(
        "--from",
        dest="start",
        type=date.fromisoformat,
        default=None,
        help="YYYY-MM-DD (default: the dataset's first day)",
    )
    lib.add_argument(
        "--to",
        dest="end",
        type=date.fromisoformat,
        default=today_local() - timedelta(days=1),
        help="YYYY-MM-DD (default: yesterday)",
    )
    lib.set_defaults(func=cmd_data_librarian)
    snap = subparsers.add_parser("data-snapshot", help="archive today's copy of an NSE reference list (story P6)")
    snap.add_argument("dataset", choices=sorted(SNAPSHOT_DATASETS))
    snap.add_argument("--day", type=date.fromisoformat, help="YYYY-MM-DD the copy is filed under (default: today, IST)")
    snap.set_defaults(func=cmd_data_snapshot)


def cmd_data_librarian(args) -> int:
    from ..composition import build_alert_sender
    from .wiring import build_librarian, build_manifest_recorder

    build = partial(build_librarian, args.dataset, log=print_now)
    recorder, what = build_manifest_recorder(), f"data-librarian {args.dataset}"
    return run_librarian(build, build_alert_sender(), recorder, what, args.start, args.end)


def cmd_data_snapshot(args) -> int:
    from ..models import now_ist
    from .wiring import build_manifest_recorder, build_snapshot_taker

    recorder = build_manifest_recorder()
    try:
        print(build_snapshot_taker(args.dataset).take(args.day or now_ist().date()))
        return 0
    except (RawSourceUnavailable, ValueError) as exc:
        print(f"NOT archived: {exc}")
        return 1
    finally:
        print(recorder.commit(f"data-snapshot {args.dataset}"))


def print_now(line: str) -> None:
    """Progress shows at once even when the output goes to a log file (a run takes about an hour)."""
    print(line, flush=True)


def run_librarian(
    build, alerts: AlertSender, recorder: ManifestRecorder, what: str, start: date, end: date, out=print
) -> int:
    """Runs the librarian, then commits the manifest rows it wrote, whether the run finished or stopped."""
    try:
        return _fill(build, alerts, start, end, out)
    finally:
        out(recorder.commit(what))


def _fill(build, alerts: AlertSender, start: date, end: date, out) -> int:
    from .librarian import fill_report_lines

    try:
        report = build().fill(start, end)
    except DriveSignInRefused as exc:
        message = SIGN_IN_REFUSED.format(reason=exc.reason)
        out(message)
        out(alerts.send(message))
        return 1
    except RawSourceUnavailable as exc:
        out(SOURCE_STOPPED.format(error=exc))
        return 1
    out("\n".join(fill_report_lines(report)))
    return 0 if report.complete else 1
