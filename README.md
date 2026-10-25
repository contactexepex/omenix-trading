# Omenix F&O (India)

Part of **Omenix**: Omenix F&O (this repository, the F&O backend), the Omenix stock prediction backend
(`contactexepex/agentic-stock-prediction`) and the one Omenix dashboard (`exepex/omenix-dashboard`). The Python
package stays `fno` and the Slack channel stays #fno-desk.

The owner's research and paper-trading tool for NSE index options (NIFTY first). Goal: find trades that are
profitable after charges, slippage and 31.2% tax, prove them on real historical data, then on paper. If paper trading
shows no net profit, the tool is shut down. It never places, modifies or cancels orders; Groww is used for market
data only.

> Reality check: SEBI's studies found about 9 in 10 individual F&O traders lost money
> (`reports/Retail FnO losses and safeguards.md`). Nothing here is assumed to work until the data says so.

## Where things stand

- Design: `docs/DESK_DESIGN.md` (v2.1 plus section 12: three paper books, rules, hybrid and fully AI, compared on two
  scoreboards). Owner decisions: `docs/DESK_DECISIONS.md`. Work plan: `docs/IMPLEMENTATION_PLAN.md` and
  `docs/stories/` (being rewritten for the three books). Working rules: `AGENTS.md`, `CLAUDE.md`.
- Research: `research/` (one folder per study, the trial ledger `research/LEDGER.md`, experiment 1's protocol).
- Reviews between Claude and ChatGPT: `reviews/`. Daily conversation logs: `conversations/`.

## Commands

```bash
sh tools/routine_setup.sh --groww                # install into every Python on PATH, check imports, hooks on
python -m fno chain NIFTY                         # option chain around the money (root `provider` in config.yaml)
python -m fno daily run                           # the whole desk day, run by the daily routine (story O1)
python -m fno quotes record                       # 3 pm quote recorder (story A4); one of the daily run's quote parts
python -m fno quotes report                       # half-spread by distance from the money, from recorded days
python -m fno intraday run --dry-run /tmp/a16     # 15-minute snapshots (story A16); --dry-run: no Drive, no commit
python -m fno account show book1_rules          # a book's paper account: cash, closed equity, open legs (E1)
python -m fno groww-check                         # check the Groww data connection (prints no secrets)
python -m fno drive-check                         # check the Google Drive archive can be read (prints no secrets)
python -m fno data-coverage [--from --to]          # raw NSE files missing or damaged in Drive, against the NSE calendar (A1)
python -m fno nifty-panel --to YYYY-MM-DD [--from --raw-folder]  # NIFTY option-chain panel from the raw files (A3)
python -m fno research run 2026-10-12-experiment-1 --period discovery|challenge  # policies, controls, verdict (B3)
python -m fno research validate-live F1_live_atm_iv_minus_rv20  # a live 15:00 feature against its close version (B7)
python -m fno forecast-scores run|summary [--as-of --send]  # forecast scores (G4); secondary to net profit
python -m fno card daily [--on YYYY-MM-DD] [--post]  # daily trade card, PAPER ONLY (T1); a dry run without --post
python -m pytest -q -n auto && ruff check fno tests tools # tests (parallel) and lint; python tools/check_imports.py checks imports
python tools/check_records.py [--staged | PATH] [--alert]  # public-record scan: no secrets, personal data or broker IDs (O5)
```

## Routines

- **Daily desk routine** (daily 14:05 IST, cloud routine; the NSE calendar decides the day): `python -m fno daily run`
  records the 3 pm quotes, runs the paper desk and posts the card (see `CLAUDE.md`, "Daily desk routine"). Recorded
  files are never edited.

## Data and secrets

- Market data: `nse` (free public NSE website), `groww` (Groww Trade API), `sample` (offline, tests only), `auto`
  (Groww when its credentials are set, else NSE). The recorder has its own setting `quotes.provider`.
- Raw NSE files go through `fno/storage` (local folder, Google Drive, then NSE itself); reads use the service account,
  uploads sign in as the owner (`python -m fno data-librarian`, story A9); see `fno/storage/README.md`.
- Credentials (`GROWW_*`, `FNO_GDRIVE_*`, `FNO_SLACK_BOT_TOKEN`) live only in environment variables or
  `~/.trading.env`, never in files. F&O output goes only to Slack #fno-desk.
- The repository is public: every committed file must pass `tools/check_records.py` (records, i.e. everything outside
  `fno/`, `tests/`, `tools/`, against every pattern; code against credential shapes). It runs as a git pre-commit hook
  in every session (`.githooks/`, turned on by `.claude/settings.json`), in the tests and in CI
  (`.github/workflows/checks.yml`); a refusal is posted to #fno-desk.

## Layout

```
fno/
  composition.py     composition root of the app (picks concrete classes); storage/wiring.py for raw data
  cli.py             the commands above
  providers/         market data: Groww, NSE public, sample
  quotes/            3 pm quote recorder and spread report (story A4)
  intraday/          15-minute quote recorder, slot ledger and realised variance (story A16)
  storage/           raw file stores and sources (NSE archives, local folder, Google Drive)
  fo_bhavcopy.py     NSE F&O daily file reader (old and current formats)
  research_engine/   ledger guard (B4), features F1-F3 (B1), monthly cycles, structures SF/SC/BF and the cycle
                     simulator (B2), policy runner, controls, bootstrap and verdict (B3), live 15:00 features (B7)
  record_scan/       public-record safety scan: patterns, scanner, which files (story O5)
  alerts/            alert sender to Slack #fno-desk (used by the record scan; P4 extends it)
  accounting/        research ledgers
  books/             the three books' Rs 5 lakh paper accounts and their single-writer lock (story E1)
  risk/              risk manager per book: owner limits, drawdown brake, stress and exposure, margin room (C2)
  forecast/          forecast protocol code (G1, frozen), baselines and history back-fill (G2), Book 1's capture (G3)
  forecast_scoring/  forecast scores, comparisons and the weekly summary (G4): research/forecasts/scores/<day>.json
  analytics.py       Black-Scholes, Greeks, implied volatility, chain metrics
  costs.py           Groww and statutory charges
  config.py          settings (`config.yaml`, allowed keys only)
tools/               NSE raw-file downloader, import-graph check, public-record scan
research/            studies, ledger, recorded data
journal/<book>/account/  each book's paper account (cash ledger, positions, equity history, desk fills and events):
                     kept in Google Drive, downloaded here git-ignored, never committed (E2c)
journal/<book>/daily_totals.csv  the account's only public part: closed equity and trade and fill counts per day (E2c)
journal/<book>/owner_overrides.csv  the owner's written restarts of that book's drawdown brake (C2)
tests/               unit and integration tests
```

## History

The first version of this tool was an intraday option-buying desk. Its own backtest lost money (219 trades,
-Rs 1.95 lakh; `reports/2026-10-12-backtest-analysis.md`), and it was removed on 12 Oct 2026 by owner decision D3
(design: `docs/CLEAN_SLATE_DESIGN.md`). Its last commit is `184ff7e9acca6fd1b47598f69fbac5bb1b3b5914`; to look at or
run it, use a separate folder: `git worktree add ../trading-legacy 184ff7e9acca6fd1b47598f69fbac5bb1b3b5914`.
