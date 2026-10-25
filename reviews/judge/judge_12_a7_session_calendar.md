# Judge 12: story A7, every component uses the session calendar

**Verdict: PASS.** No blocking or should-fix findings; 4 minor findings.

**What I judged.** Trading `main` after merge b4cc269 (story commit e1fd4e1) and the later routine change 04bc172.
Claims: `reviews/claude/response_39_2026-10-13-a7-session-calendar.md`. I read in full the diff of
`fno/quotes/recorder.py` and `fno/quotes/cli.py`, plus `tests/quotes/test_recorder_calendar.py`, the routine section
of CLAUDE.md and the live trigger.

## Checks run by the judge

```
$ git diff --quiet e1fd4e1^ HEAD -- tests/quotes/test_recorder_baseline.py tests/quotes/test_quote_recorder.py tests/fixtures
A4 tests + fixtures unchanged since before A7
$ python -m pytest -q tests/quotes                        31 passed
$ python -m pytest tests/quotes/test_recorder_calendar.py -v   15 passed, including:
  test_a_special_saturday_session_is_recorded_with_a_canonical_snapshot
  test_a_weekday_holiday_records_nothing_and_never_asks_the_provider
  test_a_session_without_same_day_trades_is_kept_incomplete_retried_and_ends_none
  test_the_command_exits_non_zero_and_alerts_on_the_cross_check
  test_a_day_outside_the_calendar_fails_loudly_and_says_what_to_add
  test_with_the_real_calendar_the_baseline_bytes_are_unchanged[december|none|normal|retry]
$ python -m pytest -q                                     428 passed;  ruff, import check clean
list_triggers: "F&O 3 pm quote recorder (daily 14:48 IST; calendar decides)", cron "CRON_TZ=Asia/Kolkata 48 14 * * *"
```

## Criteria

| # | Criterion | Builder's claim | Judge's own evidence | Result |
|---|---|---|---|---|
| 1 | A special Saturday session with same-day trades is recorded, with a canonical snapshot | `recorder.py` session kinds; test | Test passes: 12 rows, complete, canonical set. `record()` asks `_session_kind` before anything else (diff read). | MET |
| 2 | A weekday holiday records nothing: "not a trading day" | test with a provider that fails on any call | Test passes; no files are written and the provider is never asked. | MET |
| 3 | A session with no same-day trades is kept with complete=false and the reason, exits non-zero, and is never silently skipped | `failures.append(NO_SAME_DAY_TRADES)`; CLI exit 1 plus alert | Test passes: every attempt in the window is kept, the reason is in each meta, and the day's canonical is `none`. The command exits 1 and sends one alert, including under `--outside-window`. | MET |
| 4 | All A4 tests and the four byte-identical baselines pass unchanged | A4 tests untouched; the no-calendar mode keeps A4's inference | Unchanged per my `git diff --quiet` from the parent of e1fd4e1; they pass. The baselines also give the same bytes with the real calendar injected. | MET |
| 5 | A day outside the calendar fails loudly | `CalendarError`; CLI message, alert, exit 1 | Test passes: nothing is recorded, the message names the 2027 circular and the file, and the alert is sent. An invalid calendar file also stops the run. | MET |

## The builder's doubts, judged

1. **Trigger was weekdays only.** Resolved. The live trigger now fires daily
   (`CRON_TZ=Asia/Kolkata 48 14 * * *`), and CLAUDE.md says "every day; the calendar decides". The trigger's stored
   prompt is now stale, see finding 1.
2. **No-calendar mode kept for the A4 tests.** Acceptable, with reasoning. Criterion 4 as written requires the A4
   tests to stay unchanged, and `test_the_app_builds_the_recorder_with_the_repository_calendar` proves the app always
   injects the calendar. Even so, production code still holds a mode that only tests use (finding 2).
3. **A missing Groww login now alerts and exits 1 instead of a quiet "not a trading day".** Correct and intended:
   this is exactly criterion 3's "never silently skipped". The owner should expect an alert on the first real run if
   the Groww credentials are absent.
4. **Muhurat skipped; short special sessions would be attempted after their close.** The muhurat handling is
   correct. The short-session risk is real: a special session that closes before 14:55 (the 2024 DR drills ended at
   12:30) has same-day trades, so its post-close book could pass validity and become the day's "3 pm" canonical
   snapshot. This is rare, and the fix needs session hours in A1's calendar (finding 3).
5. **Calendar fingerprint not in meta.** Acceptable, because criterion 4 requires byte-identical baselines. It could
   still be written to a separate file beside the snapshot without touching the baseline (finding 4).
6. **Yearly calendar update.** Stated. The 1 Jan 2027 stop is loud and tells the operator what to add. A December
   reminder belongs to O1 or the routine.

## Claims vs reality

- **"A4 tests ... untouched (`git diff --quiet origin/main -- ...` passes)"**: true. I checked it against the parent
  of e1fd4e1, which is a stricter base.
- **"15 passed / 16 passed / 404 passed"**: the 15 and 16 match my runs. The full suite is 428 at today's `main`,
  all passing.
- **"No other scheduled component exists in the code today"**: consistent with my grep. `coverage.py` already uses
  the calendar, and the shared `build_session_calendar()` is in `fno/storage/wiring.py`.

## Project rules and engineering standards

- **Size:** `recorder.py` is 217 lines and `cli.py` 69, both under 350.
- **Wiring:** the calendar is injected through the composition root.
- **Constants:** messages are module constants and session kinds come from `fno/constants.py`.
- **Single purpose:** `record_today` and `exit_code` each do one thing.
- **DRY:** `build_session_calendar()` is shared with coverage.
- No breach.

## Findings (all minor)

1. **Minor (orchestrator's trigger, not A7's code).** The trigger's stored prompt still says to follow CLAUDE.md
   section "3 pm quote recorder (weekday routine, story A4)". That section is now titled "(daily routine, stories A4
   and A7)". The prompt also tells the session to post any non-good result itself, while the command now posts the
   two calendar alerts on its own, so alerts can arrive twice. Expected: update the trigger prompt to match CLAUDE.md
   steps 2 and 4.
2. **Minor.** The recorder keeps a weekday-inference mode used only by the A4 tests. Expected, when the story owner
   allows it: change the A4 tests to inject an explicit "weekdays are sessions" calendar fake, then delete the
   inference branch. The baseline bytes would stay the same, as the builder's real-calendar test already shows.
3. **Minor (A1 scope).** The calendar has no session hours, so a short special session that ends before 14:55 would
   be captured after its close. Expected: session hours (at least the close time) in the calendar, and a recorder
   rule that records only when 14:55-15:10 lies inside the session.
4. **Minor.** Record `calendar_sha256` beside each day's snapshot in a separate small file, so results that depend
   on the calendar can be tied to its version without changing the baseline bytes.
