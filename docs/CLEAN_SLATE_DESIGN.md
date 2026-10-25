# Clean slate: what the new system keeps, and what of the old system is removed

Status: **v2.1, agreed by ChatGPT (review 21); approved by the owner and built 12 Oct 2026** (see section 9). v1 request: `reviews/claude/response_24_2026-10-12-clean-slate.md`;
review: `reviews/chatgpt/review_20_2026-10-12-clean-slate.md`; this revision: `reviews/claude/response_25_2026-10-12-review-20.md`.
Nothing is removed until ChatGPT agrees and the owner approves. After approval: one cleanup commit, then a rewritten
implementation plan, regenerated stories, old issues #3-#21 closed as replaced and a clean issue set created.

Owner decision D3 (`docs/DESK_DECISIONS.md`): remove the old setup entirely; nobody uses it; the new desk starts clean.

## 1. Why remove instead of isolate

- The old system is an intraday **option-buying** desk on ~200 underlyings with chart rules. Its own 30-day backtest:
  219 trades, **-Rs 1.95 lakh**, rule hit rates 49-54% (no edge) (`reports/2026-10-12-backtest-analysis.md`). The
  approved design (v2.1 + section 12) trades protected NIFTY monthly structures decided once a day at about 3 pm.
- Fact check on "we almost lost all trades": the old **paper journal is empty** (`journal/trades.json` and
  `journal/shadow_trades.json` hold 0 trades). The loss evidence is the backtest above, not recorded paper trades.
- Keeping it means story E4's legacy parts (desk selector, legacy labels, watchdog tests) and permanent care so two
  desks never share one paper account. Removing it deletes that risk and that work. E4's **per-account single-writer
  lock and crash recovery are still needed** by the three new books and move into the new desk stories (section 5). Git history keeps every line; the last
  commit before removal is recorded in section 7 so anything can be recovered by hash.

## 2. Target layout after cleanup (no new behaviour, only re-homing)

```
fno/
  composition.py        NEW composition root for app services (replaces fno/live/services.py)
  storage/wiring.py     composition root for raw data stores and sources (unchanged)
  cli.py                commands at the cleanup commit: drive-check, groww-check, chain, quotes record|report
                        (approved stories add data-coverage (A1) and desk scorecard (E3) later)
  providers/            market data only (Groww, NSE public, sample for tests)
  storage/              raw file stores and sources (NSE archives, repository, Google Drive; uploads as the owner)
  fo_bhavcopy.py        NSE F&O daily file reader (old and UDiFF formats)
  research_data/        expiries, events calendar
  research_engine/      trial ledger and its guard
  accounting/           research ledgers
  quotes/               3 pm quote recorder (moved from fno/live/: recorder, report, cli, expiry_listing)
  analytics.py, costs.py, models.py, config.py, constants.py, http_pacing.py, env_file.py
```
New desk code (stories C-F, the three books) goes into new packages named by the rewritten plan, behind interfaces,
wired only in the two composition roots.

## 3. Kept: every existing function the new system uses

| Existing part | New home | Change | Used by (approved story / design) |
|---|---|---|---|
| `providers/` base, groww, public, `__init__` factory | same | remove old-desk hooks `Provider.forget()` and `Provider.live_quote()` (its docstring invites a last-price +/- slippage fallback, which the design forbids); no kept caller uses either (checked). Keep `quote_book` (A4, C3) | A4 recorder, `chain` and `groww-check` commands |
| `providers/sample.py` | same | test and offline use only; never evidence of quote capture (it has no `quote_book`) | tests |
| `providers/groww_check.py` | same | drop the live-prices check (needs the removed old feed) | owner's Groww credential check |
| `storage/*` | same | none | A1-A3 raw NSE files, Drive archive, quote store |
| `fo_bhavcopy.py` | same | none | A3, B1-B3 (proven identical on 128 overlap days) |
| `research_data/` | same | none | A6 events, expiries |
| `research_engine/` | same | none | B4 ledger guard |
| `accounting/` | same | none | C1 three ledgers |
| `live/quote_recorder.py`, `quote_report.py`, `quote_cli.py`, `expiry_listing.py` | `quotes/recorder.py`, `report.py`, `cli.py`, `expiry_listing.py` | move only; wiring moves to `composition.py`. The recorder's provider comes from its **own** setting `quotes.provider: auto` (today it reads `live.chain_provider: auto`), so its source does not change and the `chain` command keeps `provider: nse` | A4 (judge-passed), 3 pm routine |
| `analytics.py` | same | keep `norm_cdf`, `norm_pdf`, `bs_price`, `Greeks`, `bs_greeks`, `implied_vol`, `atm_iv`, `historical_vol` (pricing, IV, stress) and `put_call_ratio`, `max_pain`, `oi_walls`, `straddle_expected_move` (`chain` command); remove chart indicators `ema`, `rsi` (no kept caller; checked). `atm_iv` is today's-chain IV only, never a historical 30-day IV (section 4b) | B1, C2, section 12, `chain` |
| `costs.py` | same | none | all books' after-cost results, scoreboards A and B |
| `models.py` | same | remove `OptionQuote.fill_price()` (a slippage guess; no kept caller); keep quote, book, chain and context types | providers, recorder |
| `config.py` | same | remove profile merging (`profile`, `profiles` keys go); loader rejects removed keys with a clear error (test) | everywhere |
| `constants.py` | same | keep the 9 names kept code uses (`Direction`, `ENV_GROWW_*` x4, `RESEARCH_USER_AGENT`, `ENV_GDRIVE_*` x2, `MONTH_CODES`) and `ENV_FNO_SLACK_BOT_TOKEN` for E2. Remove the other 34 (checked by search): old enums (`OptionKind`, `OrderSide`, `TradeStatus`, `ExitReason`, `OiBuildup`, `SessionPhase`), news, shock, shadow, IV-snapshot and fill-mode names, `ENV_FNO_SLACK_CHANNEL_ID` and `ENV_FNO_SLACK_WEBHOOK_URL` (channel overrides; see 4b), `ENV_MOTHERDUCK_TOKEN`, old strategy and family names | everywhere |
| `http_pacing.py`, `env_file.py` | same | none | NSE downloads, `.env` loading |
| `notify.py` | removed | see section 4; E2 builds a plain-text #fno-desk poster behind an interface | (E2 later) |
| `tools/nse_raw_download/` | same | none | owner's data download |
| `research/` (all studies, ledger, data, experiment 1) | same | `research/2026-10-12-backtest/replay.py` imports the old desk, so it **will not run on main** after cleanup; its README gives the exact command to run it in a separate worktree at the pinned pre-cleanup commit (section 7) | evidence, B4, experiment 1 |
| `config.yaml` | same | keep `provider: nse` (unchanged, used by `chain`), new `quotes.provider: auto` (the value A4 uses today), `underlyings`, `lot_sizes`, `charges`, `slack` (fno-desk), `risk_free_rate`; remove the rest | |
| Docs: `DESK_DESIGN.md`, `DESK_DECISIONS.md`, this file | same | link fixes | |
| `IMPLEMENTATION_PLAN.md`, `docs/stories/` | same paths | **rewritten** after this design is approved | |
| `docs/JUDGE.md` | same | rewritten for stories (verdicts per story, no waves) | judge |
| `docs/DATA_SOURCES.md` | same | trimmed to sources the new system uses | |
| `reviews/`, `conversations/`, `research_notes/` | same | none (historical record; old links inside old reviews point to git history) | |
| `reports/`: backtest analysis (+ data json), strategy proposal, "Retail FnO losses and safeguards", `backtest-2026-10-12.md` | same | none | evidence cited by the design |
| Routine: 3 pm quote recorder (`trig_01M5iCBwkfvQhRFpdqBvzxEN`) | same | none; never paused or deleted for the cleanup. Audited (section 4a): it does not use any old deploy code | A4 |
| Slack channel #fno-desk | same | quiet until E2 | E2 |

## 4. Removed (and what, if anything, replaces it)

| Old part | Size | Why remove | Replacement in the new system |
|---|---|---|---|
| `fno/live/` except the quote files: runner, scanner, universe, shortlist, signals (12 rule files), exit policy, kill switch, risk gate, contract picker, paper desk, market view/backdrop/clock, move check, price watch, shock detector, alerts, results stores (incl. DuckDB), `services.py` | ~6,300 lines | rejected strategy (intraday option buying); its kill switch closes all trades, contrary to the approved entry-only brake | C2 risk manager per book (brake blocks entries only), C4 validity, E1 daily loop, E2 report |
| `fno/live/news/` (fast news watcher, classifier, impact) | | drives old automatic news exits (design forbids automatic AI/news exits) | news only as a dated input to F1 finding cards, built under F1 if needed |
| `fno/live/feeds/` (live prices, NSE feed, participant OI) | | intraday feeds for the old desk | A4 snapshot + NSE daily files. **Change from response 19:** FII/DII participant OI was "keep as data"; under a clean slate the old parser goes. A named future story (positioning data, before any E6, F1 or AI-book use) builds a new `RawFileSource` with point-in-time rules (release time, coverage check, archive stability). Spot check 12 Oct: NSE's archive served the file for 3 Jun 2019, 2 Jan 2020, 3 Jan 2022, 1 Oct 2025 and 9 Oct 2026; full coverage and release times are **not yet verified** |
| `fno/live/learning/` (IV history, trade stats, signal report, performance, news speed, view outcomes) | | grades the old desk; no IV-history data is in the repository (checked; untracked runtime files on the owner's old PC cannot be ruled out, and are not needed) | implied volatility from NSE daily files (A3/B1); E3 scorecard; scoreboards A and B |
| `fno/live/research/` (reads the stock tool's research from its repo or MotherDuck) | | old desk input | F1 may re-add a read-only source with point-in-time rules; never writes to the stock tool |
| `fno/backtest/` (Yahoo 5-minute bars, modelled option prices) | 434 | modelled prices, rejected strategy | research engine B1-B3 on real NSE option prices |
| `fno/deploy/`, root `deploy/` (PC watchdog, Windows/Linux schedulers, git sync) | 423 | runs the old desk on the owner's PC | where AI books run is decision D4, decided before books 2 and 3 |
| `fno/brief.py`, `html_report.py`, `snapshot.py`, `strategies.py`, `signals.py`, `journal.py`, `naming.py`, `notify.py`, `providers/cached.py` | ~2,090 | 9:25 brief, old candidates and old paper journal; `naming`, `cached` unused | E2 daily report (plain text to #fno-desk); D3 decision records |
| `cli.py` commands brief, daily, notify, paper, live, backtest, calibrate, deploy | | old desk | `chain`, `drive-check`, `groww-check`, `quotes` stay |
| Old tests (`tests/live/*` except the recorder test, `test_backtest`, `test_deploy`, `test_journal`, `test_notify`, `test_strategies`, and any others that only test removed code) | | test removed code | recorder test moves to `tests/quotes/` |
| `journal/trades.json`, `shadow_trades.json` (both empty) | | old journal | new decision records (D3) |
| `data/live/` (empty) and its `.gitignore` lines; `.gitignore` lines for desk logs | | old desk state | none |
| `judgments/wave-*` (27 files) | | verdicts on old waves | new verdicts per story (rewritten `JUDGE.md`) |
| Old brief outputs in `reports/` (`*-brief*`, `*-page.html`, `*-slack.md`, `*-candidates.json`) | | old desk output | E2 report |
| Docs `WAVES.md`, `SAFEGUARDS.md`, `NEWS_FEED_PLAN.md`, `AI_DESK_PLAN.md`, `AI_PLAN_REEVALUATION.md` | | plans for the old desk; the re-evaluation's conclusions already live in `DESK_DECISIONS.md` and design section 12 | |
| Story E4 ("retire or separate the old live desk"), **legacy parts only** (desk selector, legacy labels, watchdog tests) | | nothing old left to separate | E4's per-account single-writer lock, lease and crash recovery move into the new desk stories (section 5) |
| Requirements `duckdb`, `pytz`, `Pillow`, `psutil` | | used only by removed code (each re-checked by search before removal) | |
| Paused 9:25 brief routine `trig_01FVkQVHf8p4Vrae4ZTyuXkc` | | old brief | deleted |
| Old web brief Artifact | | old brief | **deleted only with the owner's explicit yes** (deletion breaks the link for everyone) |
| `CLAUDE.md` "Daily market brief" section; interface list `SignalRule`, `GuardRule`, `IntradayPriceFeed`; composition root `fno/live/services.py` | | old desk | composition roots `fno/composition.py` and `fno/storage/wiring.py`; interfaces `Provider`, `RawFileStore`, `RawFileSource`, `FoFileFormat` plus those the plan adds |
| `README.md` old sections (live desk, profiles, shadow book, paper loop, how a setup is chosen) | | old desk | short README: purpose, commands, layout, routines |

Old safety ideas are not lost: each is either already an approved rule of the new design (entry-blocking Rs 30,000
brake, Rs 10,000 per trade, 3 open trades, C2 stress, C4 liquidity and quote validity) or written down in the
retail-losses report for the plan to reuse.

## 4a. Dependency check (done 12 Oct 2026, by search of the code)

- Kept code that imports removed code: only `fno/cli.py` (old commands) and `fno/providers/groww_check.py` (its
  live-prices check imports `fno/live/feeds/live_prices.py`). Both are trimmed as described in section 3.
  `fno/storage`, `research_data`, `research_engine`, `accounting`, `fo_bhavcopy`, `costs`, `analytics`, `models`
  import nothing from the old desk.
- Research scripts: only `research/2026-10-12-backtest/replay.py` imports the old desk (`fno.live.services`,
  `fno.backtest`). `cost_table.py` and all other studies use only kept modules.
- The 3 pm recorder today is wired through the old desk's composition root (`fno/live/services.py`), so it depends on
  the whole old desk. The cleanup fixes this: `fno/composition.py` wires provider, quote store and NSE expiry
  fallback, nothing else.
- **Method limit (review 20):** a text search for dotted names misses relative imports. The cleanup commit is
  therefore checked by an import-graph script (acceptance criterion 1), not by search alone.
- **3 pm routine audit (12 Oct, read through the Routines API):** cron `48 14 * * 1-5` Asia/Kolkata, enabled, next
  run 13 Oct 14:48 IST; a fresh cloud session clones `exepex/trading`, checks out and pulls `main`, reads CLAUDE.md's
  recorder section, installs `requirements.txt` and `requirements-groww.txt`, runs `python -m fno quotes record`,
  commits `research/data/quotes/` and pushes to `main`; failures go to #fno-desk with `FNO_SLACK_BOT_TOKEN`. It uses
  no old deploy code. It depends on: CLAUDE.md's recorder section (kept word for word), both requirements files
  (only unused packages leave `requirements.txt`), and the command. Groww credentials come from the cloud
  environment, not from files.
- A trial version of the cleanup was drafted, then **undone before commit** on the owner's instruction to get this
  design approved first. Nothing has been removed.

## 4b. Old code with logic the new desk may need (checked one by one)

| Old module | Logic worth keeping | Proposal |
|---|---|---|
| `live/feeds/nse_feed.py` | NSE holiday list, lot sizes, F&O ban list from NSE's website | **Corrected (review 20):** no separate E1 calendar. Story A1 already specifies the one versioned calendar `research/data/calendar/nse_sessions.csv` (regular, special and muhurat sessions with source links). A small `SessionCalendar` interface reads it and is used by A1, B2, E1 and the A4 recorder. Today the recorder skips every weekend (it would miss a special Saturday session) and treats "no contract traded today" as a holiday; after A1 it asks the calendar and keeps the no-trade check as a fail-closed cross-check (disagreement = incomplete attempt with a reason). Tests include a special Saturday and a weekday holiday. NSE's holiday API may propose updates, never override the audited file. Ban list is for single stocks: not needed |
| `live/market_clock.py` | session phases in IST | Not needed: the new desk acts once at about 3 pm; the recorder already has its own 14:55-15:10 window |
| `live/contract_picker.py` | spread and open-interest filters per leg | The approved C4 validity check replaces it with stricter, tested rules (same-day trade, quote size, spread) |
| `live/results_store.py` | append-only JSONL records | D3 decision records are specified separately (one JSON file per decision, hashed); written new to that spec |
| `live/kill_switch.py`, `risk_gate.py`, `learning/performance.py` | stop rules | Replaced by approved C2 (entry-only Rs 30,000 brake, Rs 10,000 per trade, 3 open trades, stress). The old switch closes all trades, which the design forbids |
| `live/feeds/participant_oi.py` | FII/DII daily positioning | Rebuilt as a `RawFileSource` only if a story needs it (section 4) |
| `live/learning/iv_history.py` | ATM implied volatility per day | Removed. The plan defines **two different things**, never mixed: (1) historical implied volatility from NSE daily closing prices (B1, with expiry choice, past-only prices, rate, session calendar and missing-data rules) and the section 12.7 30-day ATM IV estimator; (2) forward IV from A4's recorded bid/ask quotes, with their provenance. `analytics.atm_iv` (today's chain) is neither |
| `naming.py` | Groww contract display names | E2 report can re-add a one-function formatter if wanted; 16 lines |
| `notify.py` | Slack posting with the F&O bot token (`FNO_SLACK_*`) | Removed whole. **Found by review 20:** it lets `FNO_SLACK_CHANNEL_ID` override the channel and accepts any `FNO_SLACK_WEBHOOK_URL`, so `FNO_*` alone does not guarantee #fno-desk. E2 writes a plain-text `DeskReportPoster` that posts only to the fixed channel ID `C0C89E8QCCD` from `config.yaml`, refuses any other channel and any webhook, reads only `FNO_SLACK_BOT_TOKEN`, never `SLACK_*`, and redacts the token in errors (tests for each) |

## 5. Changes this forces in approved stories (applied when the plan is rewritten)

- A4: paths `fno/live/quote_*.py` -> `fno/quotes/*`; wiring in `fno/composition.py`; provider from `quotes.provider`
  (same value as today). No behaviour change; the judge's pass is re-confirmed by criteria 2, 3 and 9 below.
- A1 and A4 (and E1, B2): one session calendar (section 4b).
- All stories: "wired in `fno/live/services.py`" -> `fno/composition.py`.
- E4's legacy parts dropped; response 19's G4 (legacy outputs) is moot. Its **per-account single-writer lock** (an
  operating-system lock with a lease per paper account), and restart after an interrupted write, become acceptance
  criteria of the new desk loop and decision records, with tests: two books started together both run (different
  accounts); two writers on one account cannot double-fill; a restart after an interrupted write neither loses nor
  repeats a fill. Design section 12.6 is updated to point there instead of to E4.
- E1 fills only from validated `quote_book` bids and asks, never from a last price or slippage guess (negative test).
- New story owed: positioning data (participant OI) with point-in-time rules, before any use (section 4).
- Decision records stay under `journal/` (new subfolders only, e.g. `journal/decisions/`), so C2, C4 and D3 paths do
  not change.

## 6. Acceptance criteria for the cleanup commit (judge-checkable)

1. **Import graph:** a script parses (AST) every surviving runnable `.py` file in `fno/`, `tests/`, `tools/` and
   `research/`, resolves relative and absolute imports, and fails on any import of a removed module. Exactly one file
   is classified **archival, not runnable on main**: `research/2026-10-12-backtest/replay.py` (listed by path in the
   script; its README gives the pinned-worktree command). Every other module, and only those, is imported in a loop
   and must import cleanly. Criterion 11 confirms nothing active invokes the archival file.
2. `python -m pytest -q` and `ruff check fno tests` pass; the A4 recorder tests pass with only their imports changed.
3. **At the cleanup commit only:** `python -m fno --help` lists `chain`, `drive-check`, `groww-check`, `quotes`
   (A1 adds `data-coverage` and E3 adds `desk scorecard` later). Each command's `--help` runs. The sample provider is
   a smoke check of the command wiring only, not evidence of quote capture.
4. No dead links: every relative Markdown link in `README.md`, `CLAUDE.md`, `AGENTS.md` and `docs/` resolves
   (checked by a small link-check script run once).
5. `config.yaml` loads and contains only the kept keys. The loader has a fixed list of allowed top-level keys
   (`provider`, `quotes`, `underlyings`, `lot_sizes`, `charges`, `slack`, `risk_free_rate`, plus keys later stories
   add with their tests); any other key, including each removed one (`profile`, `profiles`, `live`, `exits`, ...),
   raises a clear configuration error (parameterised test over every removed key).
6. Every removed requirement has no remaining import.
7. The 3 pm routine's command and output paths are unchanged.
8. **No data lost:** a manifest (path, size, SHA-256) of every tracked file under `research/data/`, `research/LEDGER.md`,
   `research/ledger.csv`, the kept `research/` studies, kept `reports/` and `accounting/`, taken before the cleanup,
   matches after it byte for byte. Any exception is listed and approved in advance (none expected).
9. **Recorder integration test:** with a deterministic fake provider that has `quote_book` (bid, ask, sizes, same-day
   trade times) and an NSE expiry fixture, `python -m fno quotes record` composition is tested end to end: normal
   day (canonical snapshot, complete=True), already recorded, incomplete then retried (immutable attempts), no
   same-day trades ("not a trading day"), December expiry fallback, provider failure, and a provider that fails on
   any order call. Output folder layout, CSV columns and metadata fields equal the pre-cleanup recorder's.
   Provider selection is tested through the real `fno/composition.py` and CLI wiring (fakes, no network): `chain`
   uses root `provider: nse`; `quotes record` uses `quotes.provider: auto`; with Groww credentials A4 selects Groww,
   without them NSE; changing root `provider` does not change A4, and changing `quotes.provider` does not change
   `chain`. Real Groww
   capture is verified separately by the 13 Oct routine run, not by this test.
10. **Routine audit:** the routine's stored prompt, repository, branch, commands, requirements and push target are
    re-read after the cleanup and still match (section 4a); it is not paused or deleted.
11. **Nothing old can run:** no routine, GitHub Actions workflow, CLI command, script or active instruction
    (`README.md`, `CLAUDE.md`, `AGENTS.md`, `docs/`) can start the old desk, brief or journal; the paused 9:25
    routine is deleted; no `E4` reference remains in active docs except as history.

## 7. Recovery

The commit hash before the cleanup is written into the README "History" line and the backtest replay README, with
the exact command `git worktree add ../trading-legacy <hash>` to run the old replay in a separate folder
(`git checkout <hash> -- <path>` restores any single part). Nothing in `research/data/` or recorded quotes is touched.

## 8. Approval and sequence

ChatGPT review 21: AGREED WITH CHANGES, no blockers; its three gate wordings are applied above (criteria 1, 5, 9).
Owner approval authorises this design, not a blind deletion: the cleanup commit is accepted only when all 11 criteria
pass and the judge confirms them. The 3 pm routine stays enabled throughout; recorded data is never changed.

## 9. As built (12 Oct 2026): differences from the text above, each with its reason

1. `parse_groww_book` removed, not moved to the Groww tests: its only caller was `Provider.live_quote`, removed per
   review 20 finding 5, so it became dead code. `parse_groww_quote_book` (used by `quote_book`) stays, with its tests.
2. `Direction` removed from `fno/constants.py`: its only remaining user is the archival replay.
3. Settings: `load_config` stays a plain reader, because research studies read their own frozen settings copies
   (`research/2026-10-12-backtest/inputs/config.yaml`) that keep the old keys; changing those files would break
   criterion 8. The app reads `config.yaml` through the new strict `load_app_config` (criterion 5). Checked: the old
   profiles never touched `charges`, and `cost_table.py` re-runs with byte-identical output.
4. `tests/research/test_opening_bridges.py` removed with the archive: it executes `replay.py`. It runs at the pinned
   commit (backtest README).
5. `tests/conftest.py` now protects `research/data/` and `journal/` from writes by tests.
6. Recorder baseline: the four scenarios' output files from the pre-cleanup recorder are committed in
   `tests/fixtures/quote_recorder_golden/`; `tests/quotes/test_recorder_baseline.py` requires identical bytes.

### 9b. After judge review 22 (F1: old Yahoo market-context code survived)

A whole-package scan (every function, class and constant in `fno/` against every caller in `fno/`, `tools/` and
`research/`, tests not counted as callers) found more than the judge named. Removed: `Provider.context()` and its
three implementations, `MarketContext`, `PublicData.all_indices/daily_closes/daily_history/vix`, `YAHOO_SYMBOLS`, the
Yahoo hosts in `http_pacing.py`, Groww's unused `PublicData` member; and, contrary to section 3, `analytics.atm_iv`,
`historical_vol` (B1 specifies realised volatility as root mean square, which this demeaned formula is not), `oi_walls`,
`costs.legs_breakdown/legs_charges` (B2 specifies `order_charges` per leg), `OptionQuote.spread_pct` and the unused
`ENV_FNO_SLACK_BOT_TOKEN` (E2 adds it with its code). Kept, with the story that uses each: `bs_greeks` (C2 delta and
vega limits), `accounting/ledgers.py` (C1), `research_data/events.py` (A6), `research_engine/ledger.py` (B4); these
are new-system parts built and tested before their callers exist.

## Appendix A. Every old code file and its verdict

Lines and descriptions are taken from each file's own header (12 Oct 2026). R = remove, K = keep, M = move.

| File | Lines | What it does | Verdict |
|---|---|---|---|
| `fno/live/runner.py` | 311 | market-hours loop: refresh, scan, exits, report | R |
| `fno/live/scanner.py` | 177 | one scan: universe, backdrop, shortlist, signals, contract, risk gate, paper trade | R |
| `fno/live/services.py` | 344 | old composition root | R (replaced by `fno/composition.py`) |
| `fno/live/universe.py`, `shortlist.py` | 74, 45 | ~200 F&O underlyings narrowed each scan | R |
| `fno/live/market_view.py`, `market_backdrop.py`, `models.py`, `indicators.py` | 87, 73, 196, 46 | votes into one view; sector, global, VIX context; 5-minute candle maths | R |
| `fno/live/market_clock.py` | 82 | trading session phases | R (see 4b) |
| `fno/live/contract_picker.py`, `move_check.py` | 183, 59 | one option to buy, stop and target; move needed vs likely | R |
| `fno/live/exit_policy.py`, `news_exit.py` | 72, 44 | stop/target/trailing exits; automatic news exits | R |
| `fno/live/kill_switch.py`, `risk_gate.py` | 45, 129 | close-all switch; old portfolio rules | R (C2 replaces) |
| `fno/live/paper_desk.py`, `results_store.py`, `duckdb_results_store.py` | 167, 108, 81 | old paper fills and JSONL/DuckDB results | R |
| `fno/live/price_watch.py`, `shock_detector.py` | 59, 60 | 20-second prices, sudden-move shocks | R |
| `fno/live/alerts.py`, `cli.py` | 100, 156 | old Slack alerts; `fno live` commands | R |
| `fno/live/signals/*` (12 files) | 719 | chart, news, research, positioning votes and guards (`SignalRule`, `GuardRule`) | R |
| `fno/live/feeds/*` (4 files) | 387 | Yahoo/Groww intraday prices, NSE reference data, participant OI | R (see 4b) |
| `fno/live/news/*` (12 files) | ~1,600 | fast news watcher, classifier, impact score | R |
| `fno/live/learning/*` (6 files) | 475 | IV history, signal hit rates, trade stats, go-live test, news speed | R |
| `fno/live/research/*` (5 files) | 478 | reads the stock tool's research (repo or MotherDuck) | R |
| `fno/live/quote_recorder.py`, `quote_report.py`, `quote_cli.py`, `expiry_listing.py` | 194, 48, 33, 54 | 3 pm quote recorder (A4) | M to `fno/quotes/` |
| `fno/backtest/*` (5 files) | 434 | Yahoo 5-minute replay with modelled option prices; calibration | R |
| `fno/deploy/*` (5 files), `deploy/desk.py`, `deploy/setup.py`, `deploy/README.md` | 423 | PC watchdog, OS schedulers, git sync, setup | R |
| `fno/brief.py`, `html_report.py`, `snapshot.py` | 302, 722, 114 | 9:25 brief: Markdown, HTML, PNG | R |
| `fno/strategies.py`, `signals.py` | 321, 141 | old candidate builder and directional bias | R |
| `fno/journal.py` | 320 | old paper journal (JSON) | R |
| `fno/notify.py`, `naming.py`, `providers/cached.py` | 98, 16, 51 | brief to Slack; contract names; chain cache (unused) | R (see 4b) |
| `fno/cli.py` | 194 | all commands | K, trimmed to 4 commands |
| `fno/providers/groww_check.py` | 50 | Groww credential and data check | K, live-prices part removed |
| everything else under `fno/` (excluding `cli.py`, `groww_check.py`) | ~2,300 | providers, storage, data readers, ledgers, maths, costs | K unchanged |

## Appendix B. Tests

| Test file | Verdict |
|---|---|
| `tests/live/test_quote_recorder.py` | M to `tests/quotes/`, imports updated, assertions unchanged |
| `tests/live/test_fills.py` | R, except its `parse_groww_book` case, which moves into `tests/test_groww_provider.py` (that parser stays) |
| `tests/live/*` (the other 18 files incl. `fakes.py`), `tests/test_backtest.py`, `test_deploy.py`, `test_journal.py`, `test_notify.py`, `test_strategies.py` | R (test only removed code) |
| `tests/test_analytics.py`, `test_providers.py`, `test_groww_provider.py`, `test_storage.py`, `test_drive_check.py`, `test_fo_bhavcopy.py`, `test_http_pacing.py`, `test_env_file.py`, `test_nse_raw_download.py`, `tests/research/*`, `tests/research_data/*`, `tests/accounting/*` | K unchanged |
| `tests/conftest.py` | K: the fixture that removes `GROWW_*` variables stays; the protected-path list drops `data/live` and keeps `journal` |

## Appendix C. `config.yaml`

| Key | Verdict |
|---|---|
| `provider` | K, unchanged `nse` (used by the `chain` command) |
| `quotes.provider` | NEW, `auto` (Groww when its credentials are set, else NSE): the exact value A4 reads today from `live.chain_provider` |
| `underlyings`, `lot_sizes`, `charges`, `slack` (`fno-desk`, `C0C89E8QCCD`), `risk_free_rate` | K |
| `profile`, `account`, `position_rules`, `holding`, `go_live_criteria`, `performance_kill`, `daily_limits`, `expiry`, `strategies`, `signals`, `liquidity`, `exits`, `live` (incl. `live.chain_provider`, replaced by `quotes.provider`), `profiles` | R: old desk limits and rules. The approved money rules (Rs 5 lakh, Rs 10,000 per trade, 3 open, Rs 30,000 brake, 31.2% tax) enter config only through C2 and the playbook, with tests |
