# Judge 542: O13, routine run logs in Drive and the hourly routine watcher (lane 1)

Verdict: **FAIL** at `aa49a433` (`story/o13-routine-logs`, PR 134). There are three must-fixes:
- the watcher never looks past midnight;
- the secret scrub is not pinned where it is used;
- names are checked after the command has already run.

Most of the build is sound. The table and the mutation results below show which parts I verified.

## Claims vs reality
| Claim / orchestrator's check | Reality | Status |
|---|---|---|
| Write-once Drive paths, `AreaStore(owner Drive, "logs/routines")`, `<day>/<routine>/<HHMMSS-token>/` | Met. Every file is a new path. The owner store refuses different bytes on an existing path (`GoogleDriveUploadStore`, verified in judge 242). | met |
| Secrets scrubbed before every put and every alert | Step files, `end.json` notes, Drive error lines and the in-run alert's lines are scrubbed in the code. **But `WATCH_FAILED` sends the exception text unscrubbed. Neither the step file's scrub nor the alert's scrub is tested (both of my mutations survive).** | **not met (must-fix 2)** |
| Exit code passed through | Met for valid names (my mutation is caught). **Not met when a name is invalid (must-fix 3).** | **partly** |
| `flock` on parallel steps | Met. Read-change-write runs under each routine's lock, and removing the `flock` is caught. | met |
| Watcher slot windows, grace and maximum durations against the live times | The start times match the instructions table (section 1). Grace is caught by my mutation. **A routine whose maximum runs past the last check of the day is never called stuck (must-fix 1).** `EARLY_MINUTES` and the schedule times are not pinned (follow-up). | **partly** |
| One alert only, in-run vs watcher | Met. The in-run alert writes `failed_key(routine, run)`, the watcher's FAILED uses the same key, and removing either side is caught. | met |
| Drive failure never stops a routine | Met. `NoDriveStore` without settings, and `_put` reports any error. The watcher with no Drive raises, so it alerts and exits 1. | met |
| 2 MB kept output | Met. `scrub` on 2.0 MB takes 0.2 s (my probe). | met |
| CLAUDE.md and the prompts unchanged until the owner approves | Met. Only a proposal file is included. | met |

## Must-fix
1. **The watcher only ever reads today, so a run that dies late in the day is never flagged.**
   - `findings()` uses `now.date()` alone.
   - participant-oi starts at 17:11 with a maximum of 400 minutes, so it can only become "stuck" at 23:51. The last check of that day is at 23:17, and from 00:17 the watcher reads the new day.
   - My probe: a participant-oi run with `begin.json` and no `end.json` (its session died silently, the exact case the watcher exists for) gives no finding at 23:17 on the 23rd, or at 00:17 or 01:17 on the 24th.
   - The same loss applies to anything left over when GitHub's schedule slips past midnight. The story itself records "hours late, 14-16 Oct".
   - Fix in the design: the watcher also checks the previous IST day until every routine's last start plus its maximum has passed and been checked. Markers are keyed by the run's day, as they already are.
   - Required test: the probe above alerts once after midnight.
2. **The scrub is not pinned where it is used, and one alert is not scrubbed.**
   - Removing `scrub(...)` from the step-file put (`run_log.py`) and from the in-run alert's lines (`cli.py`) both survive all 17 tests. The only scrub test calls `scrub()` directly.
   - `WATCH_FAILED` formats `f"{type(error).__name__}: {error}"` into a #fno-desk line with no scrub. A Drive sign-in error's text is outside this code's control.
   - Secrets in files and chat are a hard line, so this needs tests at the point of use:
     - a command whose output holds a token: the Drive step file and the posted line both show `[removed: ...]`;
     - the watcher's own error line is scrubbed.
3. **Names are checked only after the command has run.**
   - `--step` is checked in `RunFolder.step_file`, and `--routine` in `RunFolder.new`, both after `runner(args.command)`.
   - My probe with `--step Daily_Run -- true`: the command ran, then `ValueError` was raised.
   - So the routine sees a traceback and exit 1 instead of the command's 0. A failing command's own alert and its log are never written.
   - Check both names before running, at argparse or at the top of `cmd_run`, and test that a bad name exits non-zero without running the command.

## Follow-ups (not blocking)
4. **A step that finishes after `end` silently opens a new run.** `open_run` calls `begin` at the step's end time. This can happen with pre-open's `&` part if `end` comes first. The new folder has no `end.json`, so after 45 minutes it is a false "stuck" alert. Refuse or name it rather than open a new run.
5. **The schedule is not pinned.** Moving participant-oi to 07:11 survives, and so does `EARLY_MINUTES = 0`. Pin `ROUTINES` against the instructions table, or keep the times in one source the table quotes.
6. **Exit codes on a signal.** A signal-killed command returns a negative code. `sys.exit(-15)` gives 241, not the shell's 143. It is still non-zero, but it is not the command's code.
7. **A stale state file goes to the wrong day.** On a machine that keeps `work/routine-logs/`, a run never closed yesterday makes today's steps log into yesterday's folder. Cloud routine containers are fresh, so this matters only on local machines. Compare the day.
8. **Unchecked routine names in local paths.** `--routine` is used unchecked in local state and lock file names, for example `../x`. It is covered once must-fix 3 checks names first.

## Project rules
- 8 modules, 619 lines in all, every file under 350.
- One composition root (`fno/routine_logs/wiring.py`). A new class behind `RawFileStore` (`NoDriveStore`).
- Constants are at the top of each module.
- The workflow is read-only (`contents: read`), and `routine-watch` was added to capture-watch.
- No order code.
- The register row is present. The trial merge conflicted only in `docs/WORK_REGISTER.md`; I kept both rows.

## Gates
Trial merge with `origin/main` (28cf227d):
- `pytest -n auto`: 14647 passed, 1 skipped, 16 xfailed.
- `ruff check` and `ruff format --check`: clean.
- `check_imports`: clean.
- `check_numbers`: clean.

## Mutations by the judge (against `tests/routine_logs`, 17 tests)
- **Caught (5 of 9):**
  - exit code forced to 0;
  - `flock` removed;
  - the watcher's marker check removed;
  - grace removed;
  - the in-run marker not written.
- **Survived (4 of 9):**
  - the step-file scrub removed;
  - the alert-line scrub removed;
  - `EARLY_MINUTES = 0`;
  - the participant-oi start moved.

## Addendum 1

Round 2, at 4f21d0f1 (branch merged with main). **Verdict: FAIL on one new finding.**
- All three round-1 must-fixes are accepted.
- The new finding is one I should have raised in round 1: the watcher goes live with nothing logging yet.
- This is the second round, so under `docs/JUDGE.md` ("Rounds: at most two") the owner decides. There is no third round.

### Round-1 must-fixes: accepted, each checked
| # | Fix | My check | Result |
|---|---|---|---|
| 1 | The watcher reads yesterday and today. Each marker is keyed by the day of the expected start. | My midnight probe is now a test. My mutation making the watcher read today only is caught. | accepted |
| 2 | Scrub tested at the point of use, and `WATCH_FAILED` scrubbed | All three of my mutations (step file, in-run line, watcher error) are now caught | accepted |
| 3 | `type=name_argument` on `--routine` and `--step` | Removing it from `run --routine` is caught. A bad name exits 2 before the command starts. | accepted |

### Follow-ups 4-8: done, each caught by my mutations
- 4: an orphan step closes its own run.
- 7: a stale state file is not reused.
- 5: the schedule is pinned.
- 6: a signal kill exits 128+n.

### New must-fix: the watcher alerts on routines that do not log yet
- The routine-instruction change is still waiting for the owner's approval (`O13-routine-instructions.md`), so today no routine runs `routine-log begin`.
- Merging `routine-watch.yml` makes it live hourly at once, and every expected start is reported **missing**.
- My probe: the real `ROUTINES`, an empty Drive area, a trading day, checks every hour at :17. That gives **26 lines on #fno-desk** on the first day (13 starts yesterday and 13 today), then **13 a day**.
  - The 13 starts are a16-backup, pre-open, morning-forecast, 7 a16-recorder slots, daily-desk, participant-oi and evening-forecast.
- This continues until every routine's prompt is changed. The owner pastes the API-created prompts one at a time, so a routine not yet switched over keeps alerting.
- False alarms on the alert channel teach everyone to ignore it, which defeats the story's purpose.
- **Fix, in the design:** each routine is expected only from its own go-live date, for example a `routine_logs.live_from` per routine in `config.yaml` (the pattern the daily run already uses). Before that date the watcher prints "not live" for it.
- Required test: no finding for a routine before its date.
- The alternative is to merge without the schedule trigger and add it in the change that applies the routine instructions. That is weaker, because routines go live one by one.

### Follow-ups (new, not blocking)
- My mutation keying the watcher's marker by today's date survives. So does keying the in-run marker by the clock's date instead of the run's day. The code is right, but no test covers a finding alerted before midnight and seen again after it. Add one.

### Gates
Trial merge with `origin/main` (d974f0ed):
- `pytest -n auto`: 14697 passed, 1 skipped, 16 xfailed.
- `ruff check` and `ruff format --check`: clean.
- `check_imports`: clean.
- `check_numbers`: clean.
- 29 tests in `tests/routine_logs/`.

## Addendum 2

Advisory read for the owner at 37c68aab. This is not a third round: the owner decides the merge (`docs/JUDGE.md`). **My advice: the addendum-1 must-fix is fixed, so merging is safe.** One small follow-up.

| Item | My check | Result |
|---|---|---|
| Addendum-1 must-fix: the watcher only expects a routine from its own `routine_logs.live_from` date (`config.yaml`, all null) | My probe with the real config, the real `ROUTINES`, an empty Drive and a trading day, checked every hour: **0 alerts** (it was 26). With only `a16-recorder` live from today: 7 alerts, all for today. Yesterday is not expected before the go-live date, so going live does not raise an alarm for the day before. | fixed |
| Marker-day follow-up | The builder reports both of my surviving mutations are now caught. I did not re-plant them this time. | taken as reported |
| `step_tail("")` crash, found by the builder | `step_tail` now returns no lines when the failed step's file is not in Drive | fixed |
| The in-run failure line does not depend on `live_from` | `cmd_run` does not read the config, so a failing command still alerts at once | holds |

**Follow-up (not blocking):** `live_dates` takes any name. A misspelled key (my probe: `a16_recorder`) is never watched and gives no warning. Refuse names that are not in `ROUTINES`, and test that.

**Owner's step after merging:** set each routine's date on the day its prompt or CLAUDE.md section starts logging. Until then, a routine gives only the in-run failure line and no watcher alerts.

**Gates.** Trial merge with `origin/main` (c7580848):
- `pytest -n auto`: 14782 passed, 1 skipped, 16 xfailed.
- `ruff check` and `ruff format --check`: clean.
- `check_imports`: clean.
- `check_numbers`: clean.
