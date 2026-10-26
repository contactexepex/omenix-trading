# Groww candle routine (A16b)

The owning document for the daily Groww candle collection. Every other place gives one line and a link here.

## What it collects

Groww's **15-minute and 1-minute NIFTY candles**, turned into a candle-close realised-variance (RV) row per session.
Raw candles are archived write-once to Google Drive; the derived rows and manifests are committed to GitHub, like
every other source.

- Command: `python -m fno intraday backfill` (daily-append mode; `fno/ingestion/intraday/backfill_cli.py:22-26`).
- Raw candles → Drive only, content-addressed, at `groww/indices/nifty-candles-15m/...` and `.../nifty-candles-1m/...`
  (`fno/ingestion/intraday/candle_archive.py:21,47-54`). Never committed to GitHub.
- Committed output paths (the only paths this routine `git add`s):
  - `research/data/intraday/rv-candle/` — the per-session RV rows and `deferred.csv`
    (`fno/ingestion/intraday/candle_rv_table.py:18`, `backfill_daily.py:11-13`).
  - `research/data/manifests/groww-candles/` — `nifty-15m.csv`, `nifty-1m.csv`
    (`fno/ingestion/intraday/candle_archive.py:23`, `backfill_daily.py:14`).

Read-only towards Groww: the backfill holds a `ReadOnlyGroww` client that allows only reads
(`fno/ingestion/intraday/read_only.py:13,24`); it never places, modifies or cancels an order.

## How it runs: a scheduled Claude session, not a GitHub workflow

Unlike the thirteen workflow-based sources, this routine runs as a **scheduled Claude session** (the same model the
deferred 3 pm Groww quote recorder uses — the other Groww job that is a session, not a workflow), because it needs a
Groww broker key and the repository
rule is **"no broker key in GitHub, ever"** (`.github/workflows/quote-recorder-nse.yml:2,44`) — a GitHub Actions
secret would break that rule and the hard line "secrets never in files or chat" (CLAUDE.md). So:

- The Groww key lives in the **session environment only** — never in the repository, in GitHub Actions secrets, in
  `config.yaml`, or in chat.
- The session runs `python -m fno intraday backfill`, then pushes its two output paths with the standard rule:
  `git pull --no-rebase origin main` then `git push origin HEAD:main`, record scan on, never `--no-verify` (CLAUDE.md).

## Schedule

- **Daily, after NSE's index-close file is archived.** The per-session cross-check reads that file, which is archived
  by ~21:00 IST (`backfill_cli.py:16` `SESSION_SETTLED = 21:00`; `backfill.py` `NSE_FINAL_AT`); before it, the day is
  deferred, not written (`latest_finished`, `backfill_cli.py:51-53`).
- The `index-closes` workflow archives that file at **21:11 IST** (`.github/workflows/index-closes.yml`, cron
  `41 15 * * *` UTC). Run this routine **after** it — suggested **21:40 IST** (`16:10` UTC) — so the file is already in
  Drive and the candle run reads it rather than re-fetching from NSE (avoids writing an index-close manifest row this
  routine does not own).
- IST = UTC + 5:30. 21:40 IST → cron `10 16 * * *` (jitter the minute off the hour, as the workflows do).

### Market-hours rule — satisfied automatically

CLAUDE.md forbids any hand-run Groww command 09:15–15:35 IST; in market hours only scheduled jobs call Groww. This
routine runs **after 15:35 IST** (≈21:40), so it is compliant by construction. One scheduled run = **one Groww
sign-in** (well under the 150/day limit); candle fetches are paced ≤2 calls/second
(`fno/ingestion/intraday/candle_source.py`), under Groww's 10/second and 300/minute limits. A **failed** scheduled run
may be re-run by hand — the same command only — but only after 15:35 IST.

## Secrets it needs (by name; never store a value anywhere)

- **Groww** (one usable set; `fno/ingestion/providers/groww.py` `has_groww_credentials`): `GROWW_API_KEY` +
  `GROWW_TOTP_SECRET` (recommended; auto-renews the token daily), or `GROWW_API_KEY` + `GROWW_API_SECRET`, or
  `GROWW_ACCESS_TOKEN` (manual, expires next day). Names in `fno/shared/constants.py:14-17`.
- **Drive write** (owner OAuth, all four required): `FNO_GDRIVE_FOLDER_ID`, `FNO_GDRIVE_OAUTH_CLIENT_ID`,
  `FNO_GDRIVE_OAUTH_CLIENT_SECRET`, `FNO_GDRIVE_OAUTH_REFRESH_TOKEN`.
- **Slack alerts** → #fno-desk (`C0C89E8QCCD`): `FNO_SLACK_BOT_TOKEN`.

## Setup in the session

Install the base and Groww dependencies through every interpreter the routine calls:

```sh
sh ops/routine_setup.sh --groww
```

This installs `requirements.txt` + `requirements-groww.txt` with `--use-pep517` (a bare
`pip install -r requirements-groww.txt` fails on the container's setuptools). Without the Groww SDK, the backfill stops
loudly (`providers/groww.py`, "Install the Groww SDK first").

## One-time historical backfill (2020 → now)

The series starts 2020-01-01 (`backfill.py` `SERIES_START`). `docs/DATA_USE_MAP.md` records ~1,684 sessions
(2020–2025) already in Drive, so **check existing Drive coverage before a full re-run** — already-written sessions are
skipped (`backfill.py`), so a re-run is safe but wasteful.

- Run it **once, by hand, after 15:35 IST** (the market-hours rule): `python -m fno intraday backfill --from 2020-01-01`.
- It is long-running (years of candles). If it approaches a time limit, chunk it with `--from/--to` across several
  evening runs. The daily routine then keeps it current.

## Status

**Prepared, not live.** The thirteen GitHub Actions workflows were re-enabled at cutover (26 Oct 2026; two steps that
fire Claude routines stay `if: false` in `participant-oi-release.yml` and `participant-oi-sweep.yml`). This routine is
not: to enable it, set the Groww key in the session environment, schedule the daily 21:40 IST session,
and run the one-time historical backfill once.

### Known limitation (honest)

The live Groww fetch path cannot be exercised before cutover: it needs the Groww key and must run after 15:35 IST, and
`pytest` never calls Groww live. The command loads and its plumbing is covered by tests, but the first real
fetch→Drive proof happens at cutover, after the key is set — the same accepted limitation as the full-history derived
steps in the other workflows.

## Not part of this routine

- The **3 pm NIFTY option chain** from Groww (`quotes record`) stays **deferred** by the owner's cutover plan (run the
  NSE recorder and compare first); see `docs/DATA_USE_MAP.md`.
- The **live 15-minute recorder** (`intraday run`, A16) captures live option-chain *quote snapshots* during the
  session — a separate, long-running in-session job, not candle collection, and not built here.
