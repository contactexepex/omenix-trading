"""`python -m fno desk book1 [--day D]` (story E5): Book 1's decision for a day (D2 through D3, committed). Paper only:
nothing here places an order. The daily run (`python -m fno daily run`, story O1) runs it right after the pack."""

from __future__ import annotations

from datetime import date

NOT_COMMITTED = (
    "F&O Book 1 {day}: decision NOT committed: {reason}. It is not public, so it is not on time unless pushed before "
    "E3's deadline, and a daily run in this checkout stops at its first commit until this is resolved. {fix}"
)
NO_DRIVE = (
    "F&O Book 1 {day}: nothing decided: Drive could not be read ({reason}). Fix: restore Drive's settings or access, "
    "then rerun `fno desk book1`"
)
FIX = "Fix: remove the cause, then rerun `fno desk book1` (it commits the recorded decision, never a new one)"


def add_book1_command(actions) -> None:
    decide = actions.add_parser("book1", help="Book 1's decision for a day (D2 on its approved versions, committed)")
    decide.add_argument("--day", type=date.fromisoformat, help="the session day (default: today in IST)")
    decide.add_argument("--commit-run", metavar="RUN_ID", help="commit a run on disk only, as recorded (story E5b)")
    decide.set_defaults(func=cmd_book1)


def cmd_book1(args) -> int:
    """A failed commit gives one alert, the same line printed and exit code 1, never a traceback (story E5b). Deciding
    first downloads the private records from Drive (story E2c); `--commit-run` reads none of them, so it works with
    Drive down (judge 163 note b)."""
    from ..composition import build_alert_sender
    from ..config import load_app_config
    from ..desk.daily_ports import CommitFailed
    from ..desk.pending_commit import PendingChanged
    from ..desk.private_files import PrivateFilesUnavailable
    from ..desk.wiring import download_private_records
    from ..models import now_ist
    from .book1 import CommitRunRefused
    from .book1_wiring import build_book1

    day = args.day or now_ist().date()
    try:
        files = None if args.commit_run else download_private_records(day)  # C2's view, counts and pack from Drive
        book1 = build_book1(load_app_config(), files=files)
        print(book1.commit_run(day, args.commit_run) if args.commit_run else book1.decide(day))
    except CommitRunRefused as refused:
        print(refused)
        return 1
    except PrivateFilesUnavailable as unavailable:  # a CommitFailed too, but nothing was decided (judge 163 note a)
        return _alerted(build_alert_sender(), NO_DRIVE.format(day=day, reason=unavailable))
    except CommitFailed as failed:
        fix = "" if isinstance(failed, PendingChanged) else FIX
        return _alerted(build_alert_sender(), NOT_COMMITTED.format(day=day, reason=failed, fix=fix).rstrip(" "))
    return 0


def _alerted(alerts, text: str) -> int:
    alerts.send(text)
    print(text)
    return 1
