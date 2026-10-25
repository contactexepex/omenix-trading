"""Command-line entry point: python -m fno <command>."""

from __future__ import annotations

import argparse
from datetime import date, timedelta
from pathlib import Path

from .ai.cli import add_ai_parser
from .ai_trading.cli import add_ai_trading_parser
from .books.cli import add_account_parser
from .books.versions_cli import add_versions_parser
from .budget.cli import add_budget_parser
from .capture_probes.command import add_probe_parser
from .cards.cli import add_card_parser
from .circulars.cli import add_circulars_parser
from .close_read.cli import add_closes_parser
from .config import ROOT, load_app_config
from .daily.cli import add_daily_parser
from .desk.cli import add_desk_parser
from .desk.private_files import PrivateFilesUnavailable
from .evaluation.cli import add_evaluation_parser
from .factory.cli import add_factory_parser
from .filings.cli import add_filings_parser
from .flow_history.cli import add_flows_parser
from .fo_masters.cli import add_fo_masters_parser
from .forecast.cli import add_forecast_parser
from .forecast_lab.cli import add_lab_parser
from .forecast_scoring.cli import add_forecast_scores_parser
from .forecast_scoring.v4.cli import add_forecast_v4_scores_parser
from .forecast_v4_rules.cli import add_forecast_v4_parser
from .forecast_v5_v1.cli import add_forecast_v5_v1_parser
from .global_cues.cli import add_global_cues_parser
from .health.calendar_stop import calendar_stop, command_name
from .health.cli import add_health_parser
from .intraday.cli import add_intraday_parser
from .itm_chance.cli import add_itmchance_parser
from .learning.cli import add_postmortem_parser
from .market_read_models.cli import add_market_parser
from .models import today_local
from .nse_margins.cli import add_margins_parser
from .pipeline.cli import add_pipeline_parser
from .playbook.cli import add_playbook_parser
from .premium_ranges.cli import add_premrange_parser
from .preopen.cli import add_preopen_parser
from .price_distribution.cli import add_pricedist_parser
from .price_ranges.cli import add_pricerange_parser
from .providers import get_provider
from .quotes.cli import add_quotes_parser
from .recommend.cli import add_recommend_parser
from .record_store.cli import add_records_parser
from .rehearsal.cli import add_rehearse_parser
from .research_data.calendar import CalendarError
from .research_data.participant_oi_cli import add_participant_oi_parser
from .research_engine.research_cli import add_research_parser
from .role_value.cli import add_role_value_parser
from .school.cli import add_school_parser
from .scoreboard.cli import add_scoreboard_parser
from .storage.cache_cli import add_cache_parser
from .storage.fingerprints_cli import add_fingerprints_parser
from .storage.librarian_cli import add_librarian_parser
from .storage.repair_cli import add_repair_parser
from .storage.revisions_cli import add_revisions_parser
from .v4_pack.cli import add_v4_pack_parser
from .vix_history.cli import add_vix_history_parser
from .weather.cli import add_weather_parser


def _cfg(args) -> dict:
    """The settings, with `--provider` overriding the root `provider` (used by `chain` and `groww-check` only; the
    quote recorder has its own `quotes.provider`)."""
    return load_app_config(args.config, {"provider": args.provider} if args.provider else None)


def cmd_drive_check(args) -> int:
    from .storage.drive_check import drive_check_lines

    lines = drive_check_lines()
    print("\n".join(lines))
    return 0 if lines[-1].startswith("inside it") else 1


def cmd_data_coverage(args) -> int:
    if args.filings:
        from .filings.coverage_cli import cmd_filings_coverage

        return cmd_filings_coverage(args)
    from .storage.coverage import report_lines
    from .storage.wiring import build_coverage_check, build_manifest_recorder, coverage_datasets

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


def cmd_nifty_panel(args) -> int:
    from .research_data.nifty_panel import PanelBuildError, build_nifty_panel, summary_lines
    from .research_data.panel_store import PanelRangeError
    from .storage import wiring

    fo_files, index_files = wiring.build_nifty_panel_files(args.raw_folder)
    rules = {"calendar": wiring.build_session_calendar(), "exceptions": wiring.build_file_exceptions()}
    try:
        panel = build_nifty_panel(fo_files, index_files, args.start, args.end, sink=wiring.build_panel_sink(), **rules)
    except (PanelBuildError, PanelRangeError) as exc:
        print(f"NOT built, nothing written: {exc}")
        return 1
    print("\n".join(summary_lines(panel)))
    return 0


def cmd_nifty_warmup(args) -> int:
    from .research_data.nifty_panel import PanelBuildError
    from .research_data.warmup_closes import build_warmup_rows, write_warmup_closes
    from .storage import wiring

    try:
        rows = build_warmup_rows(
            wiring.build_index_close_files(), wiring.build_session_calendar(), args.start, args.end
        )
    except PanelBuildError as exc:
        print(f"NOT written: {exc}")
        return 1
    path = write_warmup_closes(wiring.PANEL_FOLDER, rows)
    print(f"wrote {path.name}: {len(rows)} sessions, {rows[0][0]} to {rows[-1][0]} (index closes only)")
    return 0


def cmd_groww_check(args) -> int:
    from .providers.groww_check import groww_check_lines

    for line in groww_check_lines(_cfg(args)):
        print(line)
    return 0


def cmd_chain(args) -> int:
    from . import analytics as an

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
    """Every command fno has (`main` parses with it; REH1j's rehearsal walks it to tell a command not built yet)."""
    p = argparse.ArgumentParser(prog="fno", description="Omenix F&O: Indian F&O options research (paper trading).")
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
    n = sub.add_parser("nifty-panel", help="build the NIFTY option-chain panel from the raw NSE files (story A3)")
    n.add_argument("--from", dest="start", type=date.fromisoformat, default=date(2019, 1, 1), help="YYYY-MM-DD")
    n.add_argument("--to", dest="end", type=date.fromisoformat, required=True, help="YYYY-MM-DD: last day to include")
    n.add_argument("--raw-folder", type=Path, help="local project folder searched before Drive (its raw area)")
    n.set_defaults(func=cmd_nifty_panel)
    w = sub.add_parser("nifty-warmup", help="write the NIFTY 50 and India VIX closes before the panel (story A10)")
    w.add_argument("--from", dest="start", type=date.fromisoformat, default=date(2017, 1, 1), help="YYYY-MM-DD")
    w.add_argument("--to", dest="end", type=date.fromisoformat, default=date(2018, 12, 31), help="YYYY-MM-DD")
    w.set_defaults(func=cmd_nifty_warmup)
    g = sub.add_parser("groww-check", help="check the Groww data connection (prints no secrets)")
    g.set_defaults(func=cmd_groww_check)

    c = sub.add_parser("chain", help="print an option chain around the money")
    c.add_argument("underlying")
    c.add_argument("--expiry", help="YYYY-MM-DD (default: nearest)")
    c.add_argument("--width", type=int, default=8, help="strikes either side of ATM")
    c.set_defaults(func=cmd_chain)

    add_quotes_parser(sub)
    add_rehearse_parser(sub)  # story REH1
    add_intraday_parser(sub)
    add_account_parser(sub)
    add_desk_parser(sub)
    add_versions_parser(sub)
    add_evaluation_parser(sub)
    add_scoreboard_parser(sub)
    add_role_value_parser(sub)
    add_participant_oi_parser(sub)
    add_librarian_parser(sub)
    add_fingerprints_parser(sub)
    add_cache_parser(sub)
    add_repair_parser(sub)
    add_records_parser(sub)
    add_revisions_parser(sub)
    add_market_parser(sub)
    add_research_parser(sub)
    add_filings_parser(sub)
    add_pipeline_parser(sub)
    add_playbook_parser(sub)
    add_margins_parser(sub)
    add_ai_parser(sub)
    add_ai_trading_parser(sub)
    add_budget_parser(sub)
    add_forecast_parser(sub)
    add_forecast_v4_parser(sub)
    add_forecast_v5_v1_parser(sub)
    add_v4_pack_parser(sub)
    add_forecast_scores_parser(sub)
    add_forecast_v4_scores_parser(sub)
    add_vix_history_parser(sub)
    add_card_parser(sub)
    add_daily_parser(sub)
    add_weather_parser(sub)
    add_postmortem_parser(sub)
    add_global_cues_parser(sub)
    add_health_parser(sub)
    add_factory_parser(sub)
    add_pricedist_parser(sub)
    add_premrange_parser(sub)
    add_itmchance_parser(sub)
    add_pricerange_parser(sub)
    add_closes_parser(sub)
    add_lab_parser(sub)
    add_fo_masters_parser(sub)
    add_circulars_parser(sub)
    add_flows_parser(sub)
    add_preopen_parser(sub)
    add_school_parser(sub)
    add_recommend_parser(sub)
    add_probe_parser(sub)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except PrivateFilesUnavailable as unavailable:  # story E2c: a command that needs the paper records stops, named
        print(f"stopped: {unavailable}")
        return 1
    except CalendarError as gap:  # story O8c: any command stopped by NSE's calendar prints one named line
        return calendar_stop(command_name(argv), gap)
