"""`python -m fno news resolve [--apply] [--limit N]` (NP2c): one resolve pass over the Record. Without `--apply` it
is the PROBE: it asks the resolver (a real, paced, capped request to the search service) and writes nothing. The line
it prints is counts and fixed codes: no title, link, key or host. Exit 1 only for what needs fixing by hand; links about
to leave the look-back unresolved are alerted to #fno-desk as the same line."""

from __future__ import annotations

from fno.ingestion.news import codes
from fno.ingestion.news.feeds import FeedListError
from fno.ingestion.news.resolve.run import CAP
from fno.ingestion.storage.row_log import TableFileBroken
from fno.shared.models import now_utc

ALERT = "Omenix F&O news resolve: {line}"
STOPPED = "news resolve stopped: {code}"


def add_resolve_parser(actions) -> None:
    resolve = actions.add_parser("resolve", help="resolve Google News links to the publisher's URL (story NP2c)")
    resolve.add_argument("--apply", action="store_true", help="write resolution files (default: probe, write nothing)")
    resolve.add_argument("--limit", type=int, default=CAP, help=f"links to resolve this run (at most {CAP})")
    resolve.set_defaults(func=cmd_news_resolve)


def cmd_news_resolve(args, out=print) -> int:
    from fno.ingestion.composition import build_alert_sender
    from fno.ingestion.news.resolve.wiring import build_resolve_pass

    try:
        report = build_resolve_pass().run(now_utc().date(), args.apply, max(0, min(args.limit, CAP)))
        line, ok, attention = report.line(), report.ok, report.needs_attention
    except FeedListError as stopped:
        line, ok, attention = STOPPED.format(code=stopped), False, True
    except TableFileBroken:
        line, ok, attention = STOPPED.format(code=codes.MANIFEST_BROKEN), False, True
    except Exception as unexpected:  # noqa: BLE001 - never a traceback in a public log; the message may carry a URL
        line, ok, attention = STOPPED.format(code=f"{codes.UNEXPECTED} {type(unexpected).__name__}"), False, True
    out(line)
    if attention:
        out(build_alert_sender().send(ALERT.format(line=line)))
    return 0 if ok else 1
