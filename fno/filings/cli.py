"""`python -m fno filings <action>`: the company filings archive (story A12). Research data only; nothing here trades.

- `archive`: the Nifty 500's results and shareholding XBRL files into Drive (resumable; stops at its time limit);
- `day-lists`: NSE's all-company announcement and board-meeting lists, one file per day, into Drive;
- `table`: one company's reported figures as known at a moment, read only from Drive;
- `probe`: one request to each NSE list this archive reads, to see whether NSE answers from this machine.

Every run commits the manifest rows it wrote. A refused Drive sign-in, NSE refusing us, or a failed list or file
alerts #fno-desk; reaching the time limit during the backfill does not (the next scheduled run resumes).
"""

from __future__ import annotations

import time
from datetime import date, datetime, timedelta

from ..models import IST, now_ist, today_local
from .runs_cli import add_archive_parsers

PROBE_SYMBOL = "TCS"
PROBE_ATTEMPTS, PROBE_PAUSE_SECONDS = 2, 30
PROBE_LINES = "{name}: {outcome}"


def add_filings_parser(subparsers) -> None:
    filings = subparsers.add_parser("filings", help="company filings archive: NSE XBRL into Drive (story A12)")
    actions = filings.add_subparsers(dest="action", required=True)
    add_archive_parsers(actions)
    table = actions.add_parser("table", help="a company's reported results as known at a moment (from Drive)")
    table.add_argument("symbol")
    table.add_argument("--as-of", type=_moment, default=None, help="YYYY-MM-DDTHH:MM (IST; default: now)")
    table.add_argument("--standalone", action="store_true", help="standalone figures (default: consolidated)")
    table.set_defaults(func=cmd_filings_table)
    probe = actions.add_parser("probe", help="whether NSE's filing lists answer from this machine (no Drive)")
    probe.set_defaults(func=cmd_filings_probe)


def _moment(text: str) -> datetime:
    moment = datetime.fromisoformat(text)
    return moment if moment.tzinfo else moment.replace(tzinfo=IST)


def cmd_filings_table(args) -> int:
    from ..constants import CONSOLIDATED, STANDALONE
    from .wiring import build_results_table

    consolidation = STANDALONE if args.standalone else CONSOLIDATED
    rows = build_results_table().as_of(args.symbol, args.as_of or now_ist(), consolidation)
    print(f"{args.symbol} {consolidation}: {len(rows)} periods (newest version public at the moment asked)")
    for row in rows:
        f = row.figures
        print(
            f"{f.period_end} filed {row.filed_at:%Y-%m-%d %H:%M} revenue {f.revenue} net profit {f.net_profit} "
            f"debt {f.total_debt} cash {f.cash} operating cash flow {f.operating_cash_flow} ({f.cash_flow_months} m)"
        )
    return 0


def cmd_filings_probe(args, sleep=time.sleep) -> int:
    from .wiring import build_filing_indexes

    since = today_local() - timedelta(days=3 * 366)
    indexes = build_filing_indexes()
    answered = sum(_probe(index, since, sleep) for index in indexes)
    return 0 if answered == len(indexes) else 1


def _probe(index, since: date, sleep) -> bool:
    """One list, tried again once after a pause: a single slow answer is not "NSE refuses this machine"."""
    for attempt in range(PROBE_ATTEMPTS):
        try:
            outcome = f"answers: {len(index.filings(PROBE_SYMBOL, since))} {PROBE_SYMBOL} filings in 3 years"
            print(PROBE_LINES.format(name=index.name, outcome=outcome))
            return True
        except Exception as exc:  # noqa: BLE001 - a probe reports any failure as a line, never a traceback
            print(PROBE_LINES.format(name=index.name, outcome=f"FAILED (try {attempt + 1}): {type(exc).__name__}"))
            sleep(PROBE_PAUSE_SECONDS)
    return False
