"""`python -m fno news fetch` (story P2a): each private feed once, raw bytes to Staging. Prints one line of counts by
fixed code; exit 0 only when every feed was fetched or unchanged. Any other outcome, and a feed list that cannot be
used, is alerted to #fno-desk as the same line: no feed, URL, query or title is ever printed."""

from __future__ import annotations

from datetime import date

from fno.ingestion.news import codes
from fno.ingestion.news.feeds import FeedListError
from fno.ingestion.storage.row_log import TableFileBroken
from fno.shared.models import now_utc

ALERT = "Omenix F&O news fetch: {line}"
PROMOTE_STOPPED = "news promote stopped: {code}"
PROMOTE_ALERT = "Omenix F&O news promote: {line}"
STOPPED_LINE = "news fetch stopped: {code}"


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
    check = actions.add_parser(
        "check-manifest", help="exit 0 only when the news manifest is whole (the workflow's commit guard)"
    )
    check.set_defaults(func=cmd_news_check_manifest)


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


def cmd_news_check_manifest(args, out=print) -> int:
    """The promote workflow commits the manifest only when this says it is whole, so a promote killed mid-write can
    never publish a torn line. Judged on the file, not on promote's exit code: a rejection still commits good rows."""
    from fno.ingestion.news.record.manifest import NewsManifest
    from fno.ingestion.news.wiring import POLL_LOG_FOLDER

    whole = NewsManifest(POLL_LOG_FOLDER).well_formed()
    out("news manifest: whole" if whole else f"news manifest: {codes.MANIFEST_BROKEN}")
    return 0 if whole else 1
