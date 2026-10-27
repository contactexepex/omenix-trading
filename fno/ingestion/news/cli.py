"""`python -m fno news fetch` (story P2a): each private feed once, raw bytes to Staging. Prints one line of counts by
fixed code; exit 0 only when every feed was fetched or unchanged. Any other outcome, and a feed list that cannot be
used, is alerted to #fno-desk as the same line: no feed, URL, query or title is ever printed."""

from __future__ import annotations

from fno.ingestion.news.feeds import FeedListError

ALERT = "Omenix F&O news fetch: {line}"
STOPPED_LINE = "news fetch stopped: {code}"


def add_news_parser(subparsers) -> None:
    news = subparsers.add_parser("news", help="news feeds into Staging (story P2a; the Record is the gate's alone)")
    actions = news.add_subparsers(dest="news_action", required=True)
    fetch = actions.add_parser("fetch", help="each private feed once, raw bytes to Staging only")
    fetch.set_defaults(func=cmd_news_fetch)


def cmd_news_fetch(args, out=print) -> int:
    from fno.ingestion.composition import build_alert_sender
    from fno.ingestion.news.wiring import build_news_fetch

    try:
        report = build_news_fetch().run()
        line, ok = report.line(), report.ok
    except FeedListError as stopped:
        line, ok = STOPPED_LINE.format(code=stopped), False
    out(line)
    if not ok:
        out(build_alert_sender().send(ALERT.format(line=line)))
    return 0 if ok else 1
