"""Commands for participant open interest (story A8): `python -m fno participant-oi watch` (the release-time recorder),
`check-once` (one check per scheduled job run) and `rule` (the availability rule in force and its evidence)."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from pathlib import Path

from ..constants import RELEASE_REWRITTEN, RELEASE_UNREACHABLE
from ..models import IST, now_ist

DEFAULT_UNTIL, DEFAULT_EVERY_MINUTES = time(22, 0), 5
EVIDENCE_HELP = "write this run's log here instead of the committed evidence (story O6: the Actions copy)"
MOVED = "MOVED {day}: NSE rewrote the file at {newer:%Y-%m-%d %H:%M %Z} (recorded {recorded:%Y-%m-%d %H:%M %Z})"


def add_participant_oi_parser(subparsers) -> None:
    oi = subparsers.add_parser("participant-oi", help="NSE participant open interest: release times and the rule")
    actions = oi.add_subparsers(dest="oi_cmd", required=True)
    watch = actions.add_parser("watch", help="check NSE's archive until the day's file appears; log every check")
    watch.add_argument("--day", type=date.fromisoformat, help="YYYY-MM-DD (default: today; before noon IST, yesterday)")
    watch.add_argument("--until", type=time.fromisoformat, default=DEFAULT_UNTIL, help="HH:MM IST (default 22:00)")
    watch.add_argument("--every", type=int, default=DEFAULT_EVERY_MINUTES, help="minutes between checks (default 5)")
    watch.add_argument("--evidence-folder", type=Path, default=None, help=EVIDENCE_HELP)
    once = actions.add_parser("check-once", help="one check of the day's file, for a job run every 15 minutes")
    once.add_argument("--day", type=date.fromisoformat, help="YYYY-MM-DD (default: today; before noon IST, yesterday)")
    actions.add_parser("due-day", help="print the day whose file is still due (before noon IST, yesterday)")
    actions.add_parser("rule", help="print the availability rule in force and how many days are measured")
    sweep = actions.add_parser(
        "sweep", help="read every recorded file: flag moved write times, keep new versions (A11)"
    )
    sweep.add_argument("--evidence-folder", type=Path, default=None, help=EVIDENCE_HELP)
    compare = actions.add_parser("compare", help="the routine's release log beside the Actions copy's (story O6)")
    compare.add_argument("--evidence-folder", type=Path, required=True, help="the Actions copy's folder")
    oi.set_defaults(func=cmd_participant_oi)


def cmd_participant_oi(args) -> int:
    from ..composition import build_participant_oi_rule, build_release_time_recorder
    from ..storage.wiring import PARTICIPANT_OI_RELEASE_LOG, PARTICIPANT_OI_SWEEPS

    folder = getattr(args, "evidence_folder", None)  # same file names, another folder (O6)
    if args.oi_cmd == "compare":
        return _compare(PARTICIPANT_OI_RELEASE_LOG, folder / PARTICIPANT_OI_RELEASE_LOG.name)
    if args.oi_cmd == "sweep":
        return _sweep(folder / PARTICIPANT_OI_SWEEPS.name if folder else None)
    if args.oi_cmd == "due-day":  # one day for every step of a workflow run (judge 350 SF2)
        print(_due_day(now_ist()).isoformat())
        return 0
    if args.oi_cmd == "check-once":
        return _check_once(args.day or _due_day(now_ist()))
    from .release_times import MIN_MEASURED_DAYS, ReleaseLog, first_seen_times

    if args.oi_cmd == "rule":
        measured = len(first_seen_times(ReleaseLog(PARTICIPANT_OI_RELEASE_LOG).checks()))
        print(f"rule: {build_participant_oi_rule().describe()}; measured days: {measured} of {MIN_MEASURED_DAYS}")
        return 0
    day = args.day or _due_day(now_ist())  # a run GitHub starts after midnight watches the evening before (O10)
    until = datetime.combine(day, args.until, IST)
    recorder = build_release_time_recorder(
        folder / PARTICIPANT_OI_RELEASE_LOG.name if folder else PARTICIPANT_OI_RELEASE_LOG
    )
    rewritten = [c for c in recorder.recheck_recent(day) if c.outcome == RELEASE_REWRITTEN]
    for c in rewritten:
        print(f"REWRITTEN {c.day}: NSE's file changed after it was first seen (now {c.sha256[:12]})")
    check = recorder.watch(day, until, timedelta(minutes=args.every))
    if check is None:
        print(f"{day}: not a trading day; nothing checked")
    else:
        print(f"{day}: {check.outcome} at {check.checked_at:%Y-%m-%d %H:%M} IST {check.sha256[:12]}".rstrip())
    return 1 if rewritten or (check is not None and check.outcome == RELEASE_UNREACHABLE) else 0


def _due_day(now: datetime) -> date:
    from .release_check_once import due_day

    return due_day(now)


def _check_once(day: date) -> int:
    """Prints the check and posts each alert; fails (after alerting) when there was one, so the job shows it."""
    from ..composition import build_alert_sender, build_release_check_once

    result = build_release_check_once().run(day)
    print("\n".join(result.lines + result.alerts))
    sender = build_alert_sender() if result.alerts else None
    for alert in result.alerts:
        print(sender.send(alert))
    return 1 if result.alerts else 0


def _sweep(log: Path | None) -> int:
    from ..composition import build_last_write_sweep, participant_oi_last_writes
    from ..storage.revisions_cli import revision_lines
    from ..storage.wiring import build_manifest_recorder, build_revision_archive

    archive, recorder = build_revision_archive(), build_manifest_recorder()
    try:
        result = build_last_write_sweep(archive, log).run(participant_oi_last_writes())
        for day, recorded, newer in result.moved:
            print(MOVED.format(day=day, newer=newer, recorded=recorded))
        for day, why in result.unanswered.items():
            print(f"no answer {day}: {why}; check again next sweep")
        if result.stopped:
            print(f"STOPPED: {result.stopped}")
        print("\n".join(revision_lines(archive)))
        moved, unanswered = len(result.moved), len(result.unanswered)
        print(
            f"sweep: {result.checked} files checked, {moved} moved, {unanswered} unanswered, "
            f"{len(archive.stored)} new revisions"
        )
    finally:
        print(recorder.commit("participant-oi sweep"))  # the revision index rows
    return 1 if result.moved or result.unanswered or result.stopped or archive.stored else 0


def _compare(routine_log: Path, actions_log: Path) -> int:
    from .release_compare import ReleaseLogComparison
    from .release_times import ReleaseLog

    routine, actions = ReleaseLog(routine_log).checks(), ReleaseLog(actions_log).checks()
    print("\n".join(ReleaseLogComparison(routine, actions, timedelta(minutes=DEFAULT_EVERY_MINUTES)).lines()))
    return 0
