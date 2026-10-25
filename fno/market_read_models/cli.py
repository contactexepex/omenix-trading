"""`python -m fno market ...` (story P6): the NSE market read models for the dashboard's Screener and Markets.

market daily [--day D]          the routine: archive the session's NSE files (and any newer NSE version, A11) to
                                Drive, then publish (default: the last session before today, IST; run at 07:30 IST,
                                after NSE's late-evening rewrites)
market archive [--day D]        archive the session's NSE files to Drive only (no database: GitHub Actions runs it
                                before the database check, so an outage never leaves a gap in Drive)
market publish [--day D] [--local FOLDER]   build, validate and publish one session from the archived files
market compare --day D          compare the built blocks with the pinned W11 examples, field by field
market contract-check           compare the pinned W11 contract with the dashboard's published one
market look-up --day D          archive the own corporate-action lists of symbols with an unexplained jump
market db-check                 connect as the publisher (TLS, pinned roots) and read only its identity and rights
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from ..storage.raw_source import RawSourceCoolingOff, RawSourceUnavailable

DAILY_DATASETS = ("fo-bhavcopy", "index-close", "cm-bhavcopy", "security-delivery")
ARCHIVED = "{day}: the session's NSE files are archived in Drive"
ARCHIVE_FAILED = (
    "Omenix F&O market archive for {day}: NOT complete ({problem}); the publish step will say what it lacks"
)
SNAPSHOT_REFUSED = "{name}: not archived ({reason}); the other lists go on"
REVISIONS_UNANSWERED = "NSE did not answer the revision re-read of {count} file(s): {files}"
LOOK_UP_STOPPED = "look-up stopped, NSE did not answer"
DAILY_SNAPSHOTS = (
    "equity-list", "nifty500-list", "symbol-change", "corporate-actions", "fii-dii-cash-by-session",
    "fpi-daily-by-session",
)  # fmt: skip


def add_market_parser(subparsers) -> None:
    market = subparsers.add_parser("market", help="NSE market read models for the dashboard (story P6)")
    actions = market.add_subparsers(dest="market_cmd", required=True)
    daily = actions.add_parser("daily", help="archive the session's NSE files, then build, validate and publish")
    daily.add_argument("--day", type=date.fromisoformat, help="YYYY-MM-DD (default: the last session before today)")
    archive = actions.add_parser("archive", help="archive the session's NSE files to Drive (no database)")
    archive.add_argument("--day", type=date.fromisoformat, help="YYYY-MM-DD (default: the last session before today)")
    publish = actions.add_parser("publish", help="build, validate and publish one session from the archived files")
    publish.add_argument("--day", type=date.fromisoformat, help="YYYY-MM-DD (default: the last session before today)")
    publish.add_argument("--local", type=Path, help="publish to this folder instead of Azure")
    compare = actions.add_parser("compare", help="compare the built blocks with the pinned W11 examples")
    compare.add_argument("--day", type=date.fromisoformat, default=date(2026, 10, 12), help="YYYY-MM-DD")
    actions.add_parser("contract-check", help="compare the pinned W11 contract with the dashboard's")
    look_up = actions.add_parser("look-up", help="archive the own corporate-action lists the session needs")
    look_up.add_argument("--day", type=date.fromisoformat, required=True, help="YYYY-MM-DD")
    actions.add_parser("db-check", help="connect as the publisher and read only its identity and rights")
    market.set_defaults(func=cmd_market)


def cmd_market(args) -> int:
    handlers = {
        "daily": _daily, "archive": _archive, "publish": _publish, "compare": _compare,
        "contract-check": _contract_check, "look-up": _look_up, "db-check": _db_check,
    }  # fmt: skip
    return handlers[args.market_cmd](args)


def _publish(args) -> int:
    from ..config import load_app_config
    from ..desk.wiring import download_private_records
    from .wiring import build_market_run

    download_private_records()  # story E2c: Home's books are read from the accounts in Drive
    code, lines = build_market_run(load_app_config(), args.local).run(_day(args))
    print("\n".join(lines))
    return code


def _archive(args) -> int:
    day = _day(args)
    problem = _archive_session(day)
    print(ARCHIVE_FAILED.format(day=day, problem=problem) if problem else ARCHIVED.format(day=day))
    return 1 if problem else 0


def _day(args) -> date:
    """The session asked for, else the last session before today (IST)."""
    from ..models import now_ist
    from ..storage.wiring import build_session_calendar

    return args.day or build_session_calendar().previous_session(now_ist().date())


def _daily(args) -> int:
    from ..config import load_app_config
    from ..desk.wiring import download_private_records
    from .wiring import build_market_run

    download_private_records()  # story E2c: Home's books are read from the accounts in Drive
    code, lines = build_market_run(load_app_config()).run(_day(args), prepare=_archive_session)
    print("\n".join(lines))
    return code


def _archive_session(day: date) -> str | None:
    """Archives the session's files (with their manifest rows, committed); the first problem, or None."""
    from ..storage.wiring import build_librarian, build_manifest_recorder

    recorder = build_manifest_recorder()
    try:
        for name in DAILY_DATASETS:
            report = build_librarian(name, log=print).fill(day, day)
            if not report.complete:
                gaps = len(report.not_published), len(report.damaged), len(report.rejected)
                return f"{name}: {gaps[0]} not published yet, {gaps[1]} damaged, {gaps[2]} rejected"
        problems = [_archive_revisions(day), *_take_snapshots(day)]
        try:
            _archive_own_lists(day)
        except RawSourceUnavailable as failed:
            problems.append(f"own corporate-action lists: {failed}")
        return "; ".join(p for p in problems if p) or None
    except (RuntimeError, ValueError) as exc:
        return f"{type(exc).__name__}: {exc}"
    finally:
        print(recorder.commit(f"market daily {day}"))


def _take_snapshots(day: date) -> list[str]:
    """Today's copy of each latest-day list. A flows copy refused as covering a later session (a re-run of an old day
    after NSE moved on) is named and skipped; the other lists are still taken, and the publish step's own check says
    whether the session's flows are archived. A list NSE refused or did not answer is the run's problem (A9b), and
    the other lists are still taken unless NSE's host is paused."""
    from ..storage.session_filed_taker import LaterSession
    from ..storage.wiring import build_snapshot_taker

    problems = []
    for name in DAILY_SNAPSHOTS:
        try:
            print(build_snapshot_taker(name).take(day))
        except LaterSession as refused:
            print(SNAPSHOT_REFUSED.format(name=name, reason=refused))
        except RawSourceCoolingOff as paused:
            return [*problems, f"{name}: {paused}; the later lists not taken"]
        except RawSourceUnavailable as failed:
            problems.append(f"{name}: {failed}")
    return problems


def _archive_revisions(day: date) -> str | None:
    """Reads the session's files from NSE again: a version NSE rewrote after the archived one is kept as a revision
    (A11), so the publication uses NSE's latest version (judge 49: 12 Oct's index file, rewritten at 23:20 IST). A
    file NSE did not answer is the run's problem (A9b): the latest version cannot be confirmed."""
    from ..storage import wiring
    from ..storage.revision_source import sweep_revisions
    from ..storage.revisions_cli import revision_lines

    archive, unanswered = wiring.build_revision_archive(), {}
    for name in DAILY_DATASETS:
        source_type = wiring.FINGERPRINT_SOURCES[name]
        source = wiring.build_revision_capturing_source(source_type, archive)
        swept = sweep_revisions(source, [source_type.path_for(day)])
        unanswered.update(swept.unanswered)
        if swept.stopped:
            unanswered[source_type.path_for(day)] = swept.stopped
    print("\n".join(revision_lines(archive)) or f"{day}: no newer NSE versions")
    if not unanswered:
        return None
    return REVISIONS_UNANSWERED.format(
        count=len(unanswered), files="; ".join(f"{p}: {w}" for p, w in unanswered.items())
    )


def _db_check(args) -> int:
    from .wiring import build_database_check

    code, lines = build_database_check().run()
    print("\n".join(lines))
    return code


def _look_up(args) -> int:
    from ..storage.wiring import build_manifest_recorder

    recorder = build_manifest_recorder()
    try:
        _archive_own_lists(args.day)
        return 0
    except RawSourceUnavailable as failed:
        print(f"{LOOK_UP_STOPPED}: {failed}")
        return 1
    finally:
        print(recorder.commit(f"market look-up {args.day}"))


def _archive_own_lists(day: date) -> None:
    """Archives the own corporate-action list of each symbol with an unexplained jump in the session's window."""
    from ..config import load_app_config
    from ..storage.snapshot_source import CorporateActionsBySymbolSource
    from ..storage.wiring import build_own_list_taker
    from .wiring import build_session_rows_builder

    symbols = build_session_rows_builder(load_app_config()).symbols_to_look_up(day)
    taker = build_own_list_taker()
    for symbol in symbols:
        print(taker.take_path(CorporateActionsBySymbolSource.path_for_symbol(day, symbol)))
    print(f"{day}: {len(symbols)} own corporate-action list(s) archived")


def _compare(args) -> int:
    from ..config import load_app_config
    from .contract_examples import compare
    from .wiring import build_market_blocks, build_pinned_contract, build_session_rows_builder

    rows = build_session_rows_builder(load_app_config()).build(args.day)
    blocks = {key: payload for b in build_market_blocks() for key, payload in b.pages(rows).items()}
    total = 0
    for name, found in compare(blocks, build_pinned_contract().examples()).items():
        total += len(found)
        print(f"{name}: {len(found)} difference(s)")
        for path, ours, theirs in found:
            print(f"    {path}: ours {ours!r}, example {theirs!r}")
    return 0 if total == 0 else 1


def _contract_check(args) -> int:
    from .contract import drift
    from .wiring import build_pinned_contract, build_published_contract

    contract = build_pinned_contract()
    changed = contract.changed_files()
    if changed:
        print(f"the pinned copy differs from its pin: {', '.join(changed)}")
        return 1
    drifted = drift(contract, build_published_contract())
    print(f"pinned W11 contract {contract.version} (commit {contract.pin['commit'][:12]}): "
          + (f"the dashboard has changed {', '.join(drifted)}" if drifted else "same as the dashboard's"))  # fmt: skip
    return 1 if drifted else 0
