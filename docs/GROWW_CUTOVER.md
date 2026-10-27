# Groww cutover plan

The owning document for one question: **how each Groww routine is pointed at this repository's `main`, what must hold while it
runs, and what to check live afterwards.** `docs/RUN_LOCATIONS.md` says where each source runs and links here; the daily candle
routine is described in `docs/GROWW_CANDLE_ROUTINE.md`; the sign-in count is measured in section 5 below.

**How sure each statement is.** *Verified* = read in the file named. *Inferred* = taken from a docstring or doc; this repository
cannot see the sessions or routines, so the owner confirms it at cutover. Nothing here has been run: **no Groww call was made to
write this document** (the rule below), and `pytest` never calls Groww.

## 1. Rules that hold for every Groww routine (verified: CLAUDE.md, `GROWW_CANDLE_ROUTINE.md`)

- **The Groww key stays in the session's environment** (`GROWW_API_KEY` with `GROWW_TOTP_SECRET`, or the key with `GROWW_API_SECRET`,
  or `GROWW_ACCESS_TOKEN`; names only, in `fno/shared/constants.py`). Never in the repository, a GitHub Actions secret, `config.yaml` or chat.
- **No hand-run Groww command from 09:15 to 15:35 IST** (owner, 25 Oct 2026). In market hours only the scheduled routines call Groww; no live test,
  probe, download, backfill or check by hand. A **failed scheduled** command may be re-run by hand so no data is lost, but only that same command,
  and only after 15:35 IST. Everything marked "verify live" below waits until after 15:35 IST.
- **Read-only towards Groww**: the clients are `ReadOnlyGroww` (`intraday/read_only.py`); nothing here places, modifies or cancels an order.
- **Every push** is `git pull --no-rebase origin main` then `git push origin HEAD:main`, record scan on, never `--no-verify`.
- **Alerts** go to #fno-desk with `FNO_SLACK_BOT_TOKEN`; a routine that writes Drive also needs the four `FNO_GDRIVE_*` owner OAuth settings.
- **Install** in the session: `sh ops/routine_setup.sh --groww` (hashed `requirements-groww.lock`). Without the SDK a command stops loudly.

## 2. What "point it at this repository" means, the same for each routine (inferred: the routines live outside this repository)

1. In the routine's definition, change the repository it clones and runs from the old one to `exepex/omenix-ingestion`, branch `main`.
2. Keep the key and the Drive and Slack settings in the session environment as they are; add none to GitHub.
3. Run the install line above, then the routine's command (section 3).
4. Commit only the routine's own output paths (section 3), then the standard pull-and-push.
5. Keep the routine's schedule, but check it against the market-hours rule: a routine must not need a hand-run Groww call during 09:15-15:35 IST.
6. Pause the same routine in the old repository the moment the new one is live, so two systems never write the same Drive folder.

## 3. The routines (command: verified in the CLI help; schedule and the old setup: inferred, owner confirms)

| Routine | Command in this repository | Writes | Notes |
|---|---|---|---|
| 3 pm quote recorders: NIFTY (A4, A4b) and the index slots BANKNIFTY, FINNIFTY, MIDCPNIFTY (A4c) | `python -m fno quotes record` (`--window NAME` for a named window of `config.yaml` `quotes.windows`; `--source nse` is the NSE recorder, the workflow) | raw quote files to Drive; markers in the repository | `DATA_USE_MAP.md`: NIFTY on Groww is **deferred** until the NSE recorder has run and been compared; A4c is recorded from 19 Oct 2026. The recorders run in the 15:01-15:13 window, inside market hours: scheduled only. |
| Candle backfill (A16b) | `python -m fno intraday backfill` | raw candles to Drive; `research/data/intraday/rv-candle/` and `research/data/manifests/groww-candles/` | `GROWW_CANDLE_ROUTINE.md` owns it: daily about 21:40 IST, after the `index-closes` workflow; the one-time 2020-onward backfill is run once by hand after 15:35 IST. |
| Intraday marks (A16) | `python -m fno intraday run --until HH:MM` (and `intraday rv`, `intraday heartbeat-check`) | 78 slot files a session to Drive; its own manifests | `DATA_USE_MAP.md`: **deferred**, the live in-session recorder is not scheduled. It runs inside market hours: scheduled only. |
| The daily run's Groww children | the commands above, one process each (the docstring of `groww_sign_in.py` names NIFTY, A4c, v4, E3, A16b) | as above | Inferred: this repository does not define the daily run; each child is one process and so one sign-in. |
| Pre-open capture | `python -m fno preopen record` | pre-open values; its own manifests | About 08:36-09:12 IST, before the market-hours window. Reads Groww for the 09:15 value through `preopen/wiring.py`. |

## 4. After 15:35 IST: what to verify live, in this order (one person or session, each step read-only)

1. `python -m fno groww-check`: signs in once, prints the field names of one chain leg and one quote, no secret. If it fails, stop: the key, the
   TOTP secret or the SDK is wrong; do not run the others.
2. For each routine that ran on schedule that day: its output exists where the table says (Drive file, manifest row, committed rows), and the
   run log has no Groww sign-in alert line (`providers/groww_sign_in.py`: first failure per token day is alerted once).
3. The candle routine: run its first scheduled session (or, once, the same command by hand after 15:35 IST); check that a session's raw 15-minute
   and 1-minute candle files are in Drive, the RV row is committed, and its manifest rows are whole.
4. A day later: the morning routines (pre-open) again, and a second candle run, to see the second sign-in of the token day does not repeat.
5. Compare the first NSE and Groww 3 pm chains before enabling the Groww NIFTY recorder (the owner's deferral).

## 5. Sign-in measurement (offline: read from the code and docs only; no Groww call)

Groww allows **150 sign-ins per 24 hours** (`groww_sign_in.py`, citing the 22 Oct probe note).

**What the code does (verified for the first two sentences, strong evidence).** `GrowwSignIn` signs in **once per process and token day** (the token day runs 06:00 to 06:00
IST); a failed sign-in is remembered, waits 5 then 10 minutes, and a process makes **at most 3 tries a day**. By the list in `docs/stories/R1d-groww-and-the-rest.md` (a named test for it is planned, not built), every composition root builds exactly
one provider (`intraday/wiring.py`, `intraday/backfill_wiring.py`, `quotes/index_wiring.py`, `quotes/window_wiring.py`, `preopen/wiring.py`,
`providers/__init__.py`, `groww_check.py`), so the number of sign-ins a day is the number of **processes** that touch Groww, times at most 3 when
everything fails. There is **no count across processes**.

**The tally** (the docstring of `groww_sign_in.py`, judge 637 m1; the process counts come from the routines' schedules, which this repository cannot
see: *some evidence*, reasoning from the docstring):

| Source of Groww processes on a session day | No reruns (my reading) | With reruns (the docstring's figure) |
|---|---|---|
| A16 intraday: 7 fires, each up to 2 h 45 min, rerun at the tool's 2-hour limit | 7 | 21 |
| The daily run's Groww children (NIFTY, A4c, v4, E3, A16b) | 5 | 10 |
| Pre-open capture | 1 | 1 |
| The school's 4 slots | 4 | 4 |
| By hand after 15:35 IST | 2 | 2 |
| The 3 pm quote recorders | counted inside the daily run's children | |
| The candle routine (21:40 IST, one sign-in a run) | counted as A16b above | |
| **Processes** | **19** | **38** |
| **Sign-ins if every one succeeds** | **19** | **38** |
| **Tries if every sign-in fails all 3 times** | 19 x 3 = 57 | **38 x 3 = 114** |

**Result.** A normal day is **19 to 38 of 150 (13 to 25%)**: the docstring itself says "a normal day: about 38", counting the reruns; my no-rerun column
is an extra reading of the same numbers. The worst case, every sign-in failing all 3 tries, is **114 (76%)**, still under the cap with a margin of 36. **The owner is right that no sign-in ledger is needed for the planned routines.** What would break it is not the planned load but a
**restart storm** outside the plan: about 110 extra processes in one token day (a loop that restarts `intraday run` or the candle routine, or a person
re-running commands by hand in a cycle). Each such process signs in on its own and nothing counts across processes. That is a reasoning-only risk (no
measurement exists). If the owner wants a guard anyway, the smallest mechanism is the parked R1d2: a day ledger that records each sign-in (committed and
union-merged, a malformed line counted as a sign-in so it fails closed) and refuses at a number below 150, with room left for the hand-run reads after
15:35 IST. It needs a commit path from the routine containers, which is not known here, so it is not recommended before the first week of real
counts. A cheaper first step, not built: have `groww-check` print how many sign-ins this token day's runs show in the run logs.

**Evidence strength.** The one-per-process rule, the 3-try cap and the single-provider roots: **strong** (code read and tested). The process counts per
source: **some** (a docstring written for a worst-case argument, not a measurement). The 150 a day cap itself: from the 22 Oct probe note named in
the docstring, not re-measured. Whether a failed sign-in counts against Groww's 150: assumed yes (the conservative reading).
