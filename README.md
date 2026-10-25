# Omenix F&O (India) — data-ingestion backend

Part of **Omenix**: Omenix F&O (this repository), the Omenix stock prediction backend and the one Omenix dashboard
(`exepex/omenix-dashboard`). The Python package is `fno` and the Slack channel is #fno-desk.

This repository is the **data-ingestion backend** for the owner's personal F&O research on NSE. It fetches Indian F&O
and market data from NSE (and Groww, for market data only) and archives it **write-once to Google Drive**, the system
of record, keeping one SHA-256 receipt per Drive file in GitHub. It never places, modifies or cancels orders; Groww is
used for market data only.

## Layout

```
fno/
  shared/            building blocks shared across the app
    config.py          settings (config.yaml, allowed keys only)
    constants.py       fixed strings, enum values, environment-variable names, channel IDs
    constants_channels.py  the extra Slack channel IDs the record scan allows
    models.py          core value types and time helpers (IST)
    analytics.py       Black-Scholes, Greeks, implied volatility, chain metrics
    fo_bhavcopy.py     NSE F&O daily file reader (old and current formats)
    http_pacing.py     polite HTTP pacing (one request a second per site)
    record_scan/       public-record safety scan: patterns, scanner, which files (story O5)
    alerts/            alert sender to Slack #fno-desk
    numbering/         central number registry helpers
  ingestion/         the fetch workflows and their plumbing
    cli.py             the command-line entry point (python -m fno <command>)
    composition.py     composition root: picks concrete classes for the app's services
    providers/         market data: Groww, NSE public, NSE quotes, sample
    storage/           raw file stores and sources (NSE archives, local folder, Google Drive), the Drive cache
    quotes/            3 pm option-chain quote recorder
    intraday/          15-minute NIFTY snapshots and realised variance
    preopen/           GIFT Nifty and NSE pre-open capture
    close_read/        index closes read from NSE after 15:30
    circulars/         NSE and SEBI circulars
    filings/           company filings archive (XBRL into Drive)
    fo_masters/        F&O ban list and market lot sizes
    flow_history/      FII/DII flow history
    global_cues/       overnight global cues
    vix_history/       India VIX daily history
    research_data/     participant OI, FII derivative stats and other reference datasets
    pipeline/          fires routines on new data in Drive
tools/               NSE raw-file downloader, import-graph check, public-record scan, number check
tests/               unit and integration tests
.github/workflows/   one GitHub Actions workflow per data source (schedules disabled during migration)
```

## Workflows (what each fetches)

Thirteen workflows in `.github/workflows/`, one per data source. **Their schedules are commented out ("DISABLED for
migration; re-enable at cutover"); they run only by `workflow_dispatch` for now.** Each fetches only its own source,
archives it to Drive, and commits only its own output paths (manifest rows, receipts, run logs).

| Workflow | Command | Fetches |
|---|---|---|
| `index-closes` | `data-librarian index-close`, `pipeline index-closes` | daily index close files (including the India VIX close) |
| `quote-recorder-nse` | `quotes record --source nse` | 3 pm NIFTY option-chain bid/ask quotes from NSE's public chain |
| `vix-history` | `vix-history fill` / `sweep` | India VIX full daily OHLC history |
| `fo-masters` | `fo-masters` | NSE F&O ban list and market lot sizes |
| `participant-oi-watch` | `participant-oi check-once` | watches when NSE's participant-wise OI file appears |
| `participant-oi-release` | `participant-oi watch`, `data-librarian participant-oi` | participant-wise OI (FII, DII, pro, client) at its release time |
| `participant-oi-sweep` | `participant-oi sweep` | participant-wise OI back-fill sweep |
| `flow-history` | `data-librarian participant-volume` / `fii-stats`, `flows table` | participant-wise volume and FII derivative statistics history |
| `flows-download` | `data-snapshot fii-dii-cash-by-session` / `fpi-daily-by-session` | FII/DII cash and NSDL FPI daily flows |
| `global-cues` | `global-cues fill` | overnight global cues (US 10-year, Brent, USD/INR, US and Asian indices) |
| `circulars` | `circulars` | NSE and SEBI circulars; F&O ones kept in Drive |
| `filings-archive` | `filings probe` / `archive` / `day-lists` | company filings: results and shareholding XBRL, announcements, board meetings |
| `data-checks` | `data-cache sync` | integrity re-check of files brought into the verified Drive cache |

One source does **not** run as a GitHub workflow: the **Groww 15-minute/1-minute NIFTY candles** are collected by a
scheduled Claude session (`python -m fno intraday backfill`), because Groww needs a broker key and the rule is "no
broker key in GitHub, ever". See [`docs/GROWW_CANDLE_ROUTINE.md`](docs/GROWW_CANDLE_ROUTINE.md).

## Commands

```bash
sh tools/routine_setup.sh --groww                # install deps into every Python on PATH, check imports, hooks on
python -m fno --help                             # every command; python -m fno <command> --help for one
python -m fno drive-check                         # check the Google Drive archive can be read (prints no secrets)
python -m fno groww-check                         # check the Groww data connection (prints no secrets)
python -m fno chain NIFTY                         # print an option chain around the money (root `provider`)
python -m fno data-coverage [--from --to]          # raw NSE files missing or damaged in Drive, against the NSE calendar
python -m pytest -q -n auto                       # tests (parallel, pytest-xdist)
ruff check fno tests tools                        # lint (format with ruff format)
python tools/check_imports.py                     # import-graph check
python tools/check_records.py [--staged | PATH] [--alert]  # public-record scan: no secrets, personal data or broker IDs
```

The gates before pushing code: `python -m pytest -q -n auto`, `ruff check fno tests tools`,
`python tools/check_imports.py`, and on `main` `python tools/check_numbers.py` (see `docs/JUDGE.md`, "Merge
procedure"). A change of Markdown files only skips the full suite (see `CLAUDE.md`, "Code").

## Data and secrets

- Market data provider: `nse` (free public NSE website), `groww` (Groww Trade API), `sample` (offline, tests only),
  `auto` (Groww when its credentials are set, else NSE). The 3 pm recorder has its own setting `quotes.provider`.
- Raw NSE files go through `fno/ingestion/storage` (local folder, Google Drive, then NSE itself); reads use the
  service account, uploads sign in as the owner (`python -m fno data-librarian`).
- Credentials (`GROWW_*`, `FNO_GDRIVE_*`, `FNO_SLACK_BOT_TOKEN`) live only in environment variables or
  `~/.trading.env`, never in files. F&O alerts go only to Slack #fno-desk.
- Every committed file outside `fno/`, `tests/` and `tools/` is a record and must pass `tools/check_records.py`
  (no secrets, personal data or broker IDs). The scan runs as a git pre-commit hook in every session (`.githooks/`,
  turned on by `.claude/settings.json`) and in the tests; a refusal is posted to #fno-desk.

## Working rules

Working rules for every session and agent: `CLAUDE.md` and `AGENTS.md`. The review process and lanes: `docs/JUDGE.md`.
Where the data comes from: `docs/DATA_SOURCES.md`; what is collected and its history: `docs/DATA_USE_MAP.md`.

## History

The first version of this tool was an intraday option-buying desk, later redesigned into a forecasting and paper
desk. Those forecasting, desk and dashboard functions were removed when this repository became data-ingestion-only;
the history is preserved in git.
