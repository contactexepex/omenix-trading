"""Command-line entry point: python -m fno <command>."""

from __future__ import annotations

import argparse
from datetime import date, timedelta

from fno.ingestion.circulars.cli import add_circulars_parser
from fno.ingestion.cli_stop import calendar_stop, command_name
from fno.ingestion.close_read.cli import add_closes_parser
from fno.ingestion.filings.cli import add_filings_parser
from fno.ingestion.flow_history.cli import add_flows_parser
from fno.ingestion.fo_masters.cli import add_fo_masters_parser
from fno.ingestion.global_cues.cli import add_global_cues_parser
from fno.ingestion.intraday.cli import add_intraday_parser
from fno.ingestion.pipeline.cli import add_pipeline_parser
from fno.ingestion.preopen.cli import add_preopen_parser
from fno.ingestion.providers import get_provider
from fno.ingestion.quotes.cli import add_quotes_parser
from fno.ingestion.research_data.calendar import CalendarError
from fno.ingestion.research_data.participant_oi_cli import add_participant_oi_parser
from fno.ingestion.storage.cache_cli import add_cache_parser
from fno.ingestion.storage.fingerprints_cli import add_fingerprints_parser
from fno.ingestion.storage.librarian_cli import add_librarian_parser
from fno.ingestion.storage.repair_cli import add_repair_parser
from fno.ingestion.storage.revisions_cli import add_revisions_parser
from fno.ingestion.vix_history.cli import add_vix_history_parser
from fno.shared.config import ROOT, load_app_config
from fno.shared.models import today_local


def _cfg(args) -> dict:
    """The settings, with `--provider` overriding the root `provider` (used by `chain` and `groww-check` only; the
    quote recorder has its own `quotes.provider`)."""
    return load_app_config(args.config, {"provider": args.provider} if args.provider else None)


def cmd_drive_check(args) -> int:
    from fno.ingestion.storage.drive_check import drive_check_lines

    lines = drive_check_lines()
    print("\n".join(lines))
    return 0 if lines[-1].startswith("inside it") else 1


def cmd_data_coverage(args) -> int:
    if args.filings:
        from fno.ingestion.filings.coverage_cli import cmd_filings_coverage

        return cmd_filings_coverage(args)
    from fno.ingestion.storage.coverage import report_lines
    from fno.ingestion.storage.wiring import build_coverage_check, build_manifest_recorder, coverage_datasets

    check = build_coverage_check()
    results = []
    for dataset in coverage_datasets():  # one progress line per dataset, so a long run shows where it is
        results.append(check.run(dataset, args.start, args.end))
        print(f"checked {results[-1].dataset}: {results[-1].expected} sessions", flush=True)
    print("\n".join(report_lines(results)))
    print(f"calendar sha256 {check.calendar.calendar_sha256()}")
    uncommitted = uncommitted_lines(build_manifest_recorder())
    for line in uncommitted:
        print(line)
    return 0 if all(r.ok for r in results) and not uncommitted else 1


def uncommitted_lines(recorder) -> list[str]:
    """Manifest rows written but not committed are not yet evidence: a fresh checkout would lack them."""
    return [f"NOT COMMITTED: {path} (rows written at save time; commit and push it)" for path in recorder.pending()]


def cmd_groww_check(args) -> int:
    from fno.ingestion.providers.groww_check import groww_check_lines

    for line in groww_check_lines(_cfg(args)):
        print(line)
    return 0


def cmd_chain(args) -> int:
    from fno.shared import analytics as an

    cfg = _cfg(args)
    provider = get_provider(cfg["provider"], cfg)
    u = args.underlying.upper()
    expiry = date.fromisoformat(args.expiry) if args.expiry else provider.expiries(u)[0]
    chain = provider.chain(u, expiry)
    atm, step = chain.atm_strike(), chain.strike_step()
    print(f"{u} {expiry}  spot {chain.spot:,.2f}  lot {chain.lot_size}  as of {chain.timestamp:%d %b %H:%M}")
    print(
        f"PCR {an.put_call_ratio(chain) or 0:.2f}  max pain {an.max_pain(chain):,.0f}  "
        f"straddle move +/-{an.straddle_expected_move(chain) or 0:,.0f}"
    )
    print(
        f"{'CE OI':>10} {'CE IV':>6} {'CE bid/ask':>16} | {'strike':^8} | {'PE bid/ask':<16} {'PE IV':>6} {'PE OI':>10}"
    )
    for k in chain.strikes():
        if abs(k - atm) > step * args.width:
            continue
        ce, pe = chain.get(k, "CE"), chain.get(k, "PE")

        def ba(q):
            return f"{q.bid or 0:.2f}/{q.ask or 0:.2f}" if q else ""

        print(
            f"{(ce.oi if ce else 0):>10,.0f} {(ce.iv or 0) if ce else 0:>6.1f} {ba(ce):>16} | {k:^8,.0f} | "
            f"{ba(pe):<16} {(pe.iv or 0) if pe else 0:>6.1f} {(pe.oi if pe else 0):>10,.0f}"
        )
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Every command fno has (`main` parses with it)."""
    p = argparse.ArgumentParser(prog="fno", description="Omenix F&O: Indian F&O market-data ingestion (research).")
    p.add_argument("--config", default=str(ROOT / "config.yaml"))
    p.add_argument("--provider", choices=["nse", "groww", "sample"], help="override the root provider (chain only)")
    sub = p.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("drive-check", help="check the Google Drive project folder can be read (prints no secrets)")
    d.set_defaults(func=cmd_drive_check)
    v = sub.add_parser(
        "data-coverage", help="list raw NSE files missing, damaged or unfingerprinted in Drive (read-only)"
    )
    v.add_argument(
        "--from",
        dest="start",
        type=date.fromisoformat,
        default=None,
        help="YYYY-MM-DD (default: each dataset's first day)",
    )
    v.add_argument(
        "--to",
        dest="end",
        type=date.fromisoformat,
        default=today_local() - timedelta(days=1),
        help="YYYY-MM-DD (default: yesterday)",
    )
    v.add_argument("--filings", action="store_true", help="the company filings archive instead (story A12)")
    v.set_defaults(func=cmd_data_coverage)
    g = sub.add_parser("groww-check", help="check the Groww data connection (prints no secrets)")
    g.set_defaults(func=cmd_groww_check)

    c = sub.add_parser("chain", help="print an option chain around the money")
    c.add_argument("underlying")
    c.add_argument("--expiry", help="YYYY-MM-DD (default: nearest)")
    c.add_argument("--width", type=int, default=8, help="strikes either side of ATM")
    c.set_defaults(func=cmd_chain)

    add_quotes_parser(sub)
    add_intraday_parser(sub)
    add_participant_oi_parser(sub)
    add_librarian_parser(sub)
    add_fingerprints_parser(sub)
    add_cache_parser(sub)
    add_repair_parser(sub)
    add_revisions_parser(sub)
    add_filings_parser(sub)
    add_pipeline_parser(sub)
    add_vix_history_parser(sub)
    add_global_cues_parser(sub)
    add_closes_parser(sub)
    add_fo_masters_parser(sub)
    add_circulars_parser(sub)
    add_flows_parser(sub)
    add_preopen_parser(sub)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except CalendarError as gap:  # story O8c: any command stopped by NSE's calendar prints one named line
        return calendar_stop(command_name(argv), gap)
