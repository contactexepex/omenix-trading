# Where each data source runs

The owning document for one question: **which system runs each ingestion piece**, so the owner knows at cutover what picks
up this repository's code and what does not. Everywhere else, give one line and a link here.

**How sure each row is.** *Verified* means read in the file named. *Inferred* means taken from a docstring or a grep of this
repository; the owner confirms it at cutover, because this repository cannot see the other systems.

## 1. In this repository's GitHub Actions workflows (verified: all 14 files read)

Fourteen files sit in `.github/workflows/`. **Thirteen are the scheduled data-source workflows** CLAUDE.md counts (each has a
`cron:` schedule and `workflow_dispatch`). The fourteenth, `pipeline-staging.yml`, has `workflow_dispatch` only and no
schedule: it is the manual stage-then-promote tool (`python -m fno stage` / `promote`), not a data source, so CLAUDE.md's
"thirteen" is right if read as "thirteen scheduled sources"; it should say there is also one manual tool.

| Workflow | What it runs | Schedule (UTC cron, IST in the file's comment) |
|---|---|---|
| `circulars.yml` | NSE circulars | hourly 08:00-22:00 IST |
| `data-checks.yml` | the data checks and `data-cache sync` | 09:41 IST |
| `filings-archive.yml` | `filings probe`, `archive`, `day-lists` | every 6 hours |
| `flow-history.yml` | `data-librarian` participant-volume and fii-stats, `data-revisions sweep` | 21:30 and 07:15 IST |
| `flows-download.yml` | `data-snapshot fii-dii-cash-by-session`, `fpi-daily-by-session` | 21:10 IST |
| `fo-masters.yml` | `fo-masters` | 06:00, 07:45, 11:15, 18:45 IST |
| `global-cues.yml` | `global-cues fill` (the daily cues) | 03:41, 04:41, 14:11 IST |
| `index-closes.yml` | `data-librarian index-close`, `pipeline index-closes` | 21:11, 07:41, 11:41 IST |
| `participant-oi-release.yml` | `participant-oi watch`, `pipeline fire participant-oi-release` | 17:11 and 22:45 IST |
| `participant-oi-sweep.yml` | `participant-oi sweep` | 1st of the month, 05:37 IST |
| `participant-oi-watch.yml` | `participant-oi check-once` | every 15 min, 16:37-23:22 IST |
| `quote-recorder-nse.yml` | `quotes record --source nse` | 14:20 IST |
| `vix-history.yml` | `vix-history fill` and `sweep` | 07:11 IST |
| `pipeline-staging.yml` | `stage` / `promote` (manual only) | none |

These run this repository's code from the latest `main` at the start of each run, and the last step of thirteen of them
commits the persisted-pause log (`ops/commit_pause_log.sh`, story R1b2). They are the only runs where an NSE pause can be
remembered into the next run.

## 2. Not in any workflow (inferred; no file in `.github/workflows/` runs these commands)

| Piece | Where it runs (from) | Notes for cutover |
|---|---|---|
| Groww 3 pm quote recorders (NIFTY, the index slots, weeklies) | scheduled Claude sessions (`docs/GROWW_CANDLE_ROUTINE.md`: "the deferred 3 pm Groww quote recorder ... a session, not a workflow") | Needs the Groww key, which lives in the session environment only. Raw quote files go to Drive; spacing is visible in the files' `request_sent_at` column. |
| Groww candle backfill (A16b) | a scheduled Claude session (`docs/GROWW_CANDLE_ROUTINE.md`, verified in that document) | Commits its own rows and manifests. |
| Groww intraday marks (A16) and the daily run's Groww children | Claude sessions (`providers/groww_sign_in.py` docstring: "A16's 7 fires", "the daily run's Groww children") | Each command builds one Groww provider; the sign-in count is per process. |
| `closes read` / `closes read --recheck` | O1's `close_read` (15:40 IST) and `close_recheck` (16:00 IST) steps (`close_read/cli.py` docstring) | Reads NSE, not Groww. No receipts of it exist under `receipts/`, so its live behaviour cannot be compared from this repository. |
| Pre-open capture (`preopen record`, `global-cues preopen`) | A22's pre-open routine, about 08:36-09:12 IST (`global_cues/preopen_cli.py`, `preopen.py` docstrings) | In no workflow. The pause memory (R1b2) is only useful here if the routine commits the log: it must not be assumed. |
| NSDL FPI back-fill (`flows ... nsdl`) | by hand, one time (`flow_history/nsdl_backfill.py` docstring) | No schedule. |
| The dashboard | `exepex/omenix-dashboard`, a different repository | Whether it honours `RAW_FILE_SAVED=False` on a quote sidecar is not checked here (R1c follow-up). |

## 3. Why this matters to the resilience layer

- The shared library (`fno/shared/resilience/`) is in-process everywhere. Persistence of an NSE pause across runs needs a
  committing step, which only the workflows in section 1 have.
- Anything in section 2 adopts a change only when its session or routine next fetches `main`; the owner confirms each at
  cutover. Until then the proof for those pieces is offline (tests and mutation plants), plus the Drive-side checks named in
  the R1d story where a record shows the behaviour.
