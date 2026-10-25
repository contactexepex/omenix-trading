"""Commands for the daily forecasts (stories G2 and G3):

python -m fno forecast capture [--day YYYY-MM-DD] [--run-id ID]   # protocol v2 live capture (the Actions job)
python -m fno forecast snapshot-ready [--day YYYY-MM-DD]           # exit 0 once the day's canonical A4 snapshot is in
python -m fno forecast backfill [--check]                          # the history back-fill for evaluation
"""

from __future__ import annotations

from datetime import date


def add_forecast_parser(subparsers) -> None:
    forecast = subparsers.add_parser("forecast", help="daily forecasts: Book 1's capture and the history back-fill")
    actions = forecast.add_subparsers(dest="forecast_cmd", required=True)
    capture = actions.add_parser("capture", help="record the v2 live forecasts for a trading day (default: today, IST)")
    capture.add_argument("--day", type=date.fromisoformat, help="YYYY-MM-DD (default: today in IST)")
    capture.add_argument("--run-id", help="the GitHub Actions run, to save the run summary in Drive's pipeline area")
    ready = actions.add_parser("snapshot-ready", help="exit 0 once the day's canonical A4 snapshot is in")
    ready.add_argument("--day", type=date.fromisoformat, help="YYYY-MM-DD (default: today in IST)")
    backfill = actions.add_parser("backfill", help="write (or --check) the baselines' and Book 1's history records")
    backfill.add_argument("--check", action="store_true", help="recompute and compare with the committed file")
    forecast.set_defaults(func=cmd_forecast)


def cmd_forecast(args) -> int:
    commands = {"capture": _capture, "snapshot-ready": _snapshot_ready, "backfill": _backfill}
    return commands[args.forecast_cmd](args)


def _snapshot_ready(args) -> int:
    from ..models import now_ist
    from ..storage.wiring import build_quote_store
    from .capture import load_snapshot

    return 0 if load_snapshot(build_quote_store(), args.day or now_ist().date()) else 1


def _capture(args) -> int:
    from ..config import ROOT, load_app_config
    from ..models import now_ist
    from ..research_engine.ledger import Git
    from .baseline_wiring import build_live_capture, save_capture_summary
    from .freeze_v2 import NotFrozen, NotYetFrozen, require_version_frozen

    started = now_ist()
    try:  # records count only under a frozen protocol; a shallow clone cannot prove it, so it refuses too
        require_version_frozen(ROOT, Git(ROOT).head())
    except NotYetFrozen as waiting:
        print(f"Omenix F&O forecasts v2 (GitHub Actions): nothing recorded: {waiting}")
        return 0
    except NotFrozen as problem:
        print(f"Omenix F&O forecasts v2 (GitHub Actions): not recorded: protocol freeze check failed: {problem}")
        return 1
    lines = build_live_capture(load_app_config()).capture(args.day or started.date())
    print("\n".join(lines))
    if args.run_id:
        print(save_capture_summary(args.run_id, started, " | ".join(lines)))
    return 0


def _backfill(args) -> int:
    from ..config import ROOT, load_app_config
    from .backfill import BACKFILL_FILE, backfill_records
    from .baseline_wiring import build_baselines, build_forecast_history, panel_pack_sha256
    from .record_files import records_gzip

    history = build_forecast_history(load_app_config())
    data = records_gzip(backfill_records(history, build_baselines(history), panel_pack_sha256()))
    path = ROOT / BACKFILL_FILE
    if args.check:
        same = path.exists() and path.read_bytes() == data
        print(f"back-fill {'unchanged' if same else 'DIFFERS from the committed file'}: {BACKFILL_FILE}")
        return 0 if same else 1
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    print(f"wrote {BACKFILL_FILE} ({len(data):,} bytes)")
    return 0
