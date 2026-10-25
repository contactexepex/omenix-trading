"""Protocol v4's freeze classes (story G6 freeze, section 2; judges 596-597): every file the v4 code reaches is in one
class, by what its bytes do. An import walk (`tests/forecast_scoring_v4/test_freeze_walk.py`) proves the classes cover
everything reached, so no file on a v4 input path is missed by hand.

- `BYTE_CHECKED_GLOBS`: v4's own files whose bytes decide a v4 value; a change breaks the freeze (a new version).
- `RECORDED`: shared files whose bytes decide a v4 value; the record holds each SHA-256 and its lock, and every report
  after the freeze prints the ones changed since (section 10's "recorded, not byte-checked", widened).
- `NOT_DECIDING`: composition roots, stores, alerts, clocks and plain shapes that compute no v4 value; named, not
  hashed; the walk stops at them."""

from __future__ import annotations

PROTOCOL = "research/forecasts/PROTOCOL_v4.md"

BYTE_CHECKED_GLOBS = (
    PROTOCOL,
    "research/forecasts/PROTOCOL_v4_calibration.md",
    "fno/forecast_v4/*.py",  # every rule and number of the protocol, the rate (pricing.py) included
    "tools/v4_*.py",  # the calibration tools and this freeze's tool
    "research/forecasts/v4_*.json",  # the calibration tools' committed tables
    "research/forecasts/v4_*.md",
    "tests/fixtures/forecast_v4/v4_golden.json",
    "fno/forecast_v4_rules/*.py",  # G7 and G7b: baselines, rule forecasters, outcomes' series, records, pack capture
    "fno/forecast_scoring/v4/*.py",  # G8: scoring, comparisons, the looks, day labels, deadlines, this check
    "fno/forecast_scoring/scores.py",  # G4's log-score clip and calibration bins in v4's reported scores (judge 177)
    "fno/intraday/realised_vol.py",  # A16's V1 arithmetic and void rule (judge 177)
    "fno/intraday/session_rv.py",
    "fno/intraday/status.py",
    "fno/intraday/slots.py",
    "fno/v4_pack/*.py",  # G10: the pack, its release, the day labels, the 15:10 deadline; the pack's IV30 feeds V2
    "fno/quotes/v4_extras.py",  # the v4 window's V4 expiry and future quote (G10 completion 3a)
    "fno/ai/v4_*.py",  # G11's v4-only files: AI rows and misses, the pack binding, the slots' registration
    "agents/forecast/book2_hybrid_v2.md",  # the AI books' v4 prompts: the registered forecasters themselves
    "agents/forecast/book3_ai_v2.md",
)

_V1_V3 = "named in FREEZE.md, FREEZE_v2.md or FREEZE_v3.md (byte-checked there or recorded with v1-v3's golden values)"
_IV30_HASH = "its bytes are in every pack's `iv30_method` (v4_pack/wiring.IV30_METHOD_FILES); v2's golden cases"
_A4 = "A4's baseline-bytes test (tests/quotes/test_recorder_baseline.py) and the pack's codec checks"
_AI = "the v1/v2 AI run's too; hashed with G11's slot rows (owner, 21 Oct 2026 (3); judge 597.1 m2); G11's tests"
RECORDED = {  # path -> what it decides and its lock
    "fno/constants.py": "question, slot and label names; protocol section 10's list; v4's tests read every name",
    "fno/desk/settlement.py": "V5's final settlement (`NseFinalSettlement`); section 10; E7's and G7b's tests",
    "fno/research_data/calendar.py": "the session set; section 10; A7's and v4's session tests",
    "fno/research_engine/implied_vol.py": "Black-76; section 10; v1 and v2 golden values",
    "fno/forecast/iv30.py": f"the EOD IV30 proxy and the IV30 interpolation; {_V1_V3}",
    "fno/forecast/live_pack.py": f"the pack builder's live quote reading; {_V1_V3}",
    "fno/research_engine/volatility_features.py": f"the IV30's volatility parts; {_V1_V3}",
    "fno/research_engine/close_series.py": f"the IV30's close series; {_V1_V3}",
    "fno/research_data/panel_reader.py": f"the EOD chains behind the premium ratio window; {_V1_V3}",
    "fno/research_data/quote_snapshots.py": f"the pack's quote snapshot at the cutoff; {_V1_V3}",
    "fno/research_engine/live_features.py": f"the pack's live ATM IV30 (V2's implied input); {_IV30_HASH}",
    "fno/research_engine/features.py": f"the feature interface the IV30 rule implements; {_IV30_HASH}",
    "fno/research_engine/event_features.py": f"imported by the live IV30 rule's module; {_IV30_HASH}",
    "fno/quotes/quote_validity.py": "W5's live two-sided quote for V4/V5 legs and the future; G7b's live-quote tests",
    "fno/research_data/expiries.py": "V4's and V5's listed expiries; G7b's terms tests",
    "fno/analytics.py": "`norm_cdf` in V5's option-implied probability; G7b's hand-computed probability tests",
    "fno/storage/creation_times.py": "V5's `first_seen_at` (Drive's creation time); G7b's outcome tests",
    "fno/storage/raw_source.py": "V5's settlement file path; E7's and G7b's tests",
    "fno/intraday/rv_table.py": "V1's outcome rows (A16's `rv/`); A16's tests",
    "fno/intraday/candle_rv_table.py": "W8's ratio window rows (A16b candles, backfill_window, judge 596); A16b tests",
    "fno/intraday/row_files.py": "the rv tables' row files (judge 596); A16's and A16b's tests",
    "fno/intraday/document.py": "a mark's document read by the session RV; A16's tests",
    "fno/intraday/snapshot_files.py": "the marks' snapshot files read by the session RV; A16's tests",
    "fno/intraday/clock.py": "the pack builder's clock check (honest times, protocol 1.6); A16's clock tests",
    "fno/intraday/ledger.py": "A16's 14:30 mark read by the pack's overlap watch; A16's tests",
    "fno/ai/receipts.py": "GitHub push times behind the 15:10 deadline (late = miss); the deadline tests",
    "fno/ai/versions.py": f"the AI forecaster versions and prompt hashes; {_AI}",
    "fno/ai/outcome.py": f"the AI books' outcomes; {_AI}",
    "fno/ai/scoring_gate.py": f"which AI days are scored; {_AI}",
    "fno/ai/stop_rule.py": f"the AI books' stop rule; {_AI}",
    "fno/ai/answer.py": f"an AI answer's form; {_AI}",
    "fno/ai/envelope.py": f"the sealed envelope; {_AI}",
    "fno/ai/seal.py": f"the seal; {_AI}",
    "fno/ai/submissions.py": f"which submissions count; {_AI}",
    "fno/ai/transcript_audit.py": f"the transcript audit; {_AI}",
    "fno/ai/audit_plan.py": f"the audit draw; {_AI}",
    "fno/ai/draw_seed.py": f"the audit draw's seed; {_AI}",
    "fno/ai/coverage.py": f"the stop rule's coverage; {_AI}",
    "fno/ai/pointer.py": f"the pointer an AI book is given; {_AI}",
    "fno/ai/paths.py": f"the AI record paths; {_AI}",
    "fno/ai/run_terms.py": f"the v4 AI run's commitment, reveal and fire terms (deadlines read from `terms`); {_AI}",
    "fno/ai/budget_stop.py": "whether an AI book fires on BG1's level: v4_fire logs a stop as a `not_fired` miss;"
    " G11 C8's tests (tests/ai/test_v4_budget_stop.py); BG1-u changed how the level is read (judge 606.1)",
    "fno/ai/record_writer.py": f"writes the AI books' collected records; {_AI}",
    "fno/ai/activity_log.py": "GitHub's activity log behind push times (late = miss); the deadline and receipt tests",
    "fno/ai/history.py": f"which earlier AI records exist; {_AI}",
    "fno/ai/close_archive.py": f"the audit draw's closes; {_AI}",
    "fno/ai/export.py": f"the sealed export; {_AI}",
    "fno/forecast/record_files.py": f"the forecast record files the AI books read; {_V1_V3}",
    "fno/forecast/schema.py": f"the record schema under schema_v2; {_V1_V3}",
    "fno/forecast/schema_v2.py": f"the record schema the AI timing reads; {_V1_V3}",
    "fno/research_data/panel_rows.py": f"the EOD panel's row rules; {_V1_V3}",
    "fno/research_data/panel_store.py": f"the EOD panel's file layout; {_V1_V3}",
    "fno/fo_bhavcopy.py": "parses NSE's daily F&O file: V5's `SttlmPric`; S1's protocol names it; E7's and A11's tests",
    "fno/storage/raw_library.py": "the archived raw file V5's settlement reads; O9's tests",
    "fno/quotes/recorder.py": f"A4's capture behind the pack (judge 597.2 m3); {_A4}",
    "fno/quotes/expiry_listing.py": f"which expiries the capture lists; {_A4}",
    "fno/quotes/market_levels.py": f"the captured spot and VIX levels; {_A4}",
    "fno/quotes/monthly_contracts.py": f"which monthly contracts are captured; {_A4}",
    "fno/quotes/slot.py": f"the capture's time slot; {_A4}",
    "fno/quotes/weekly.py": f"which weekly contracts are captured; {_A4}",
    "fno/research_data/release_times.py": "V5's `first_seen_at` fallback from A8's release log (protocol 1.5); A8 test",
    "fno/global_cues/table.py": "the provenance label `backfilled` W8's candle reader keeps (A16b rows); A17's tests",
    "fno/server_clock.py": "the checked host clock behind honest times (protocol 1.6); its clock tests",
}

NOT_DECIDING = {  # path -> why its bytes compute no v4 value
    "fno/config.py": "loads config.yaml; v4's settings are recorded with their values in the record",
    "fno/models.py": "the clock and plain value types",
    "fno/composition.py": "composition root (reached through v4_pack/cli.py)",
    "fno/daily/wiring.py": "composition root: the `daily.live_from` dates (recorded in the record)",
    "fno/storage/wiring.py": "composition root",
    "fno/storage/data_wiring.py": "composition root",
    "fno/storage/quote_wiring.py": "composition root",
    "fno/storage/data_store.py": "the write-once Drive store: moves bytes, checks their receipts",
    "fno/storage/drive_cache.py": "the verified Drive cache: moves bytes, checks their SHA-256",
    "fno/storage/receipts.py": "the receipt files' format",
    "fno/storage/raw_store.py": "the raw file store interface",
    "fno/health/evidence.py": "O8's evidence history: a reader of push times' shape",
    "fno/health/model.py": "O8's plain record types",
    "fno/rehearsal/receipts_wiring.py": "REH1's rehearsal wiring; never on a counted day",
    "fno/rehearsal/live_wiring.py": "REH1c's rehearsed live dates; a real run gets `daily.live_from` unchanged",
    "fno/rehearsal/v4_pack.py": "REH1's rehearsal excuses; never on a counted day",
    "fno/global_cues/reading.py": "M1's US flag on the card, outside its METHOD_FILES",
    "fno/global_cues/wiring.py": "composition root of the global cues (the card's flag)",
    "fno/quotes/window.py": "the capture window; the cutoff itself is enforced by `terms` in v4_pack/codec.py",
    "fno/research_engine/ledger.py": "git questions (this check's own reader)",
    "fno/intraday/wiring.py": "composition root of A16",
    "fno/intraday/backfill_wiring.py": "composition root of A16b (the X tool's reader)",
    "fno/intraday/candle_levels.py": "A16b's candle levels read by the X tool; X is frozen as a number in `terms`",
    "fno/weather/records.py": "M1's record writer: writes what its METHOD_FILES computed",
    "fno/weather/drivers.py": "the card's drivers, outside M1's METHOD_FILES",
    "fno/weather/model.py": "M1's plain record types",
    "fno/accounting/ledgers.py": "settlement.py's desk half: `NseFinalSettlement` (V5) does not use it",
    "fno/books/fills.py": "settlement.py's desk half: `NseFinalSettlement` (V5) does not use it",
    "fno/desk/execution.py": "settlement.py's desk half: `NseFinalSettlement` (V5) does not use it",
    "fno/desk/pricing.py": "settlement.py's desk half: `NseFinalSettlement` (V5) does not use it",
    "fno/desk/records.py": "settlement.py's desk half: `NseFinalSettlement` (V5) does not use it",
    "fno/constants_channels.py": "Slack channel IDs",
    "fno/constants_operations.py": "the daily run's step names and order",
    "fno/http_pacing.py": "network pacing",
    "fno/research_data/availability.py": "A8's availability rule; V5's fallback uses only `first_seen_times`",
    "fno/global_cues/collection.py": "the cue value shape (`SourcedValue`) beside the provenance label",
    "fno/storage/row_log.py": "where a cue table's rows are stored (repository or Drive); moves rows only",
    "fno/forecast_lab/wiring.py": "the paths of A8's release-check log, read by G7b's pack wiring",
    "fno/alerts/sender.py": "sends an alert line; decides nothing",
    "fno/pipeline/trigger.py": "fires a routine; decides nothing",
    "fno/budget/constants.py": "BG1's level names, read by the AI budget stop",
    "fno/budget/report.py": "the `MonthMeter` shape the AI budget stop reads; the meter itself is injected",
    "fno/budget/usage_ledger.py": "BG1's AI minutes, read for G11's cost line only",
    "fno/research_engine/statistics.py": "percentiles for G11's cost line only",
    "fno/intraday/pacing.py": "request pacing",
    "fno/quotes/capture_log.py": "the capture's log lines",
    "fno/storage/retry_policy.py": "network retries",
    "fno/storage/google_drive.py": "the Drive client",
    "fno/research_data/events.py": "the desk's event feature; the IV30 rule does not read it",
    "fno/providers/base.py": "the provider interface: quotes as received, checked by the pack's codec (byte-checked)",
    "fno/quotes/book_fetch.py": "fetches quotes as received; the pack's codec checks every value and time",
    "fno/quotes/capture_extras.py": "records quotes as received; the pack's codec checks every value and time",
    "fno/quotes/future_quotes.py": "fetches the future's quote as received; the pack's codec checks it",
    "fno/quotes/snapshot_rows.py": "the quote file's row layout; the pack's codec checks every value and time",
}
