"""`python -m fno news read-pages [--apply] [--limit N]` (NP4b): a page-read pass over the Record. Without `--apply`, it
is the PROBE: it fetches pages (real, guarded, paced, capped requests to listed outlets) and writes nothing. The line
it prints is counts and fixed codes: no title, link, key or host. Exit 1 only for what needs fixing by hand or a
reader that gets nothing; a run cut short by its budget or its read cap is alerted to #fno-desk as the same line."""

from __future__ import annotations

from fno.ingestion.news import codes
from fno.ingestion.news.reads.limits import PAGES
from fno.ingestion.storage.row_log import TableFileBroken

ALERT = "Omenix F&O news read-pages: {line}"
STOPPED = "news read-pages stopped: {code}"


def add_read_parser(actions) -> None:
    read = actions.add_parser("read-pages", help="read the pages of listed outlets for facts (story NP4b)")
    read.add_argument("--apply", action="store_true", help="write read files (default: probe, write nothing)")
    read.add_argument("--limit", type=int, default=PAGES, help=f"pages to read this run (at most {PAGES})")
    read.set_defaults(func=cmd_news_read_pages)


def cmd_news_read_pages(args, out=print) -> int:
    from fno.ingestion.composition import build_alert_sender
    from fno.ingestion.news.reads.wiring import build_read_pass
    from fno.shared.models import now_utc

    try:
        report = build_read_pass().run(now_utc().date(), args.apply, max(0, min(args.limit, PAGES)))
        line, ok, attention = report.line(), report.ok, report.needs_attention
    except TableFileBroken:
        line, ok, attention = STOPPED.format(code=codes.MANIFEST_BROKEN), False, True
    except Exception as unexpected:  # noqa: BLE001 - never a traceback in a public log; the message may carry a URL
        line, ok, attention = STOPPED.format(code=f"{codes.UNEXPECTED} {type(unexpected).__name__}"), False, True
    out(line)
    if attention:
        out(build_alert_sender().send(ALERT.format(line=line)))
    return 0 if ok else 1
