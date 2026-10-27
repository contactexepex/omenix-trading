"""`python -m fno news fetch` (story P2a): each private feed once, raw bytes to Staging. Prints one line of counts by
fixed code; exit 0 only when every feed was fetched or unchanged. Any other outcome, and a feed list that cannot be
used, is alerted to #fno-desk as the same line: no feed, URL, query or title is ever printed."""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

from fno.ingestion.news import codes
from fno.ingestion.news.companies.cli import add_seed_parser
from fno.ingestion.news.feeds import FeedListError
from fno.ingestion.news.pages.cli import add_probe_parser
from fno.ingestion.news.planning.cli import add_plan_parser
from fno.ingestion.news.reads.cli import add_read_parser
from fno.ingestion.news.resolve.cli import add_resolve_parser
from fno.ingestion.storage.row_log import TableFileBroken
from fno.shared.models import now_utc

ALERT = "Omenix F&O news fetch: {line}"
PROMOTE_STOPPED = "news promote stopped: {code}"
PROMOTE_ALERT = "Omenix F&O news promote: {line}"
CLUSTER_ALERT = "Omenix F&O news cluster: {line}"
CLUSTER_STOPPED = "news cluster stopped: {code}"
STOPPED_LINE = "news fetch stopped: {code}"


class WindowInFuture(Exception):
    """The requested window end is later than the current hour."""


def _utc_moment(text: str) -> datetime:
    moment = datetime.fromisoformat(text)
    if moment.tzinfo is None:
        raise ValueError("the window end needs a zone, for example 2026-10-27T12:00:00+00:00")
    return moment.astimezone(UTC)


def add_news_parser(subparsers) -> None:
    news = subparsers.add_parser("news", help="news feeds into Staging (story P2a; the Record is the gate's alone)")
    actions = news.add_subparsers(dest="news_action", required=True)
    fetch = actions.add_parser("fetch", help="each private feed once, raw bytes to Staging only")
    fetch.set_defaults(func=cmd_news_fetch)
    promote = actions.add_parser("promote", help="staged polls through the article gate into the Record (story P2b2)")
    promote.add_argument("--from", dest="start", type=date.fromisoformat, required=True,
                         help="YYYY-MM-DD first day (required: never all history)")  # fmt: skip
    promote.add_argument("--to", dest="end", type=date.fromisoformat, default=None,
                         help="YYYY-MM-DD (default: today, UTC: the day polls are staged under)")  # fmt: skip
    promote.set_defaults(func=cmd_news_promote)
    cluster = actions.add_parser("cluster", help="recent articles into one write-once cluster file (story P2d)")
    cluster.add_argument("--as-of", dest="as_of", type=_utc_moment, default=None,
                         help="the window end, ISO with a zone (default: now, floored to the hour)")  # fmt: skip
    cluster.set_defaults(func=cmd_news_cluster)
    check = actions.add_parser(
        "check-manifest", help="exit 0 only when the news manifest is whole (the workflow's commit guard)"
    )
    check.add_argument(
        "folder", nargs="?", type=Path, default=None, help="the manifest folder (default: the repository's)"
    )
    check.add_argument("--file", default=None, help="the manifest file in that folder (default: articles.csv)")
    check.set_defaults(func=cmd_news_check_manifest)
    batches = actions.add_parser(
        "repair-batches", help="cut a half line off the end of a receipt batch file (the workflow's commit guard)"
    )
    batches.add_argument(
        "folder", nargs="?", type=Path, default=None, help="the batch folder (default: the repository's)"
    )
    batches.set_defaults(func=cmd_news_repair_batches)
    add_seed_parser(actions)
    add_plan_parser(actions)
    add_probe_parser(actions)
    add_resolve_parser(actions)
    add_read_parser(actions)


def cmd_news_fetch(args, out=print) -> int:
    from fno.ingestion.composition import build_alert_sender
    from fno.ingestion.news.wiring import build_news_fetch

    try:
        report = build_news_fetch().run()
        line, ok = report.line(), report.ok
    except FeedListError as stopped:
        line, ok = STOPPED_LINE.format(code=stopped), False
    except Exception as unexpected:  # noqa: BLE001 - never a traceback in a public log; the message may carry a URL
        line, ok = STOPPED_LINE.format(code=f"{codes.UNEXPECTED} {type(unexpected).__name__}"), False
    out(line)
    if not ok:
        out(build_alert_sender().send(ALERT.format(line=line)))
    return 0 if ok else 1


def cmd_news_promote(args, out=print) -> int:
    """One line of counts by fixed code; exit 0 only when nothing was left unpromoted; alerted as the same line."""
    from fno.ingestion.composition import build_alert_sender
    from fno.ingestion.news.record.wiring import build_news_promotion

    try:
        report = build_news_promotion().promote(args.start, args.end or now_utc().date())
        line, ok = report.line(), report.ok
    except FeedListError as stopped:
        line, ok = PROMOTE_STOPPED.format(code=stopped), False
    except TableFileBroken:
        line, ok = PROMOTE_STOPPED.format(code=codes.MANIFEST_BROKEN), False
    except Exception as unexpected:  # noqa: BLE001 - never a traceback in a public log; the message may carry a URL
        line, ok = PROMOTE_STOPPED.format(code=f"{codes.UNEXPECTED} {type(unexpected).__name__}"), False
    out(line)
    if not ok:
        out(build_alert_sender().send(PROMOTE_ALERT.format(line=line)))
    return 0 if ok else 1


GUARD_ALERTS = {  # fixed texts: codes only, never a row, a path or a title
    codes.BATCH_TORN: "Omenix F&O news record: batch_torn; a receipt batch file ended in a half line, which was not "
    "committed; the file it named has no receipt until a later run saves it again "
    "(data-cache sync --unreceipted lists it)",
    codes.MANIFEST_BROKEN: "Omenix F&O news promote: news manifest: manifest_broken; commit skipped; "
    "re-run the same --from..--to range to repair (a later run heals only the days its range covers)",
    codes.MANIFEST_ROW_SKIPPED: "Omenix F&O news promote: news manifest: manifest_row_skipped; commit skipped; "
    "a row of the manifest is not whole: fix by hand",
}


def cmd_news_check_manifest(args, out=print) -> int:
    """The promote workflow commits the manifest only when this says it is whole, so a promote killed mid-write can
    never publish a torn line. It judges the file, not promote's exit code: a rejection still commits good rows. A
    broken manifest is loud: exit 1 and an alert."""
    from fno.ingestion.composition import build_alert_sender
    from fno.ingestion.news.record.manifest import FILE_NAME, NewsManifest
    from fno.ingestion.news.wiring import POLL_LOG_FOLDER

    problem = NewsManifest(args.folder or POLL_LOG_FOLDER, args.file or FILE_NAME).problem()
    if problem is None:
        out("news manifest: whole")
        return 0
    out(f"news manifest: {problem}")
    out(build_alert_sender().send(GUARD_ALERTS[problem]))
    return 1


def cmd_news_repair_batches(args, out=print) -> int:
    """Run by the commit step before the receipts are added: a batch file a killed run left with a half line last has
    that fragment cut off (never a whole line), so it never reaches main; exit 1 and an alert, because the file the
    fragment named has no receipt until a later run saves it again (`data-cache sync --unreceipted` lists it)."""
    from fno.ingestion.composition import build_alert_sender
    from fno.ingestion.storage.batch_receipts import BATCH_FOLDER, cut_torn_tails
    from fno.ingestion.storage.data_wiring import RECEIPTS_FOLDER
    from fno.ingestion.storage.wiring import REPOSITORY

    cut = cut_torn_tails(args.folder or REPOSITORY / RECEIPTS_FOLDER / BATCH_FOLDER)
    if not cut:
        out("news receipt batches: whole")
        return 0
    out(f"news receipt batches: {codes.BATCH_TORN} in {len(cut)} file(s); the half line was not committed")
    out(build_alert_sender().send(GUARD_ALERTS[codes.BATCH_TORN]))
    return 1


def cmd_news_cluster(args, out=print) -> int:
    """One line of counts by fixed code; exit 0 only when the file was written or already there; else alerted."""
    from fno.ingestion.composition import build_alert_sender
    from fno.ingestion.news.cluster_record.wiring import build_news_cluster

    this_hour = now_utc().replace(minute=0, second=0, microsecond=0)
    as_of = args.as_of or this_hour
    try:
        if as_of > this_hour:  # only a closed window is clustered: a future end would write a file that later conflicts
            raise WindowInFuture
        report = build_news_cluster().run(as_of)
        line, ok, alert = report.line(), report.ok, report.alert_text()
    except WindowInFuture:
        line = CLUSTER_STOPPED.format(code=codes.WINDOW_IN_FUTURE)
        ok, alert = False, line
    except Exception as unexpected:  # noqa: BLE001 - never a traceback in a public log; the message may carry a URL
        line = CLUSTER_STOPPED.format(code=f"{codes.UNEXPECTED} {type(unexpected).__name__}")
        ok, alert = False, line
    out(line)
    if not ok:
        out(build_alert_sender().send(CLUSTER_ALERT.format(line=alert)))
    return 0 if ok else 1
