# Judge 546: DR1-1 shadow steps (records certify --since, routine lines)

Judge B, 23 Oct 2026. Story/dr1-1-shadow-steps at c4bc48e58, judged against story/dr1-1-closes-records 4703dbc6e
(judge 543.1 PASS); lane 1 (schedules and the routines that call Drive and Slack).

**Verdict: FAIL, round 1 of 2: one should-fix.**

## What meets the brief

- **`--since N`:** certifies every NSE session from `max(today - N, live_from)` to today through the real
  `SessionCalendar.sessions(start, end)` (it exists, in `fno/research_data/calendar.py:48`). It prints one line per
  session, alerts each not-pushed or conflict line as in round 2, and exits 1 while any session is not recorded.
- **`live_from`:** declared on `DatasetRules`; the closes' value is 22 Oct, A4h's first raw.
- **Routine lines:** they commit only `receipts/records/` through the command and leave the stored prompts unchanged.
  The evening runs provisional at 19:53, after A4h's 16:00 recheck (my 543 note). The morning runs certified after
  step 1b archives the official file.
- **Gates on c4bc48e58 (run by me):** 14,648 passed, 1 skipped, 16 xfailed; ruff, format and check_imports clean.

## SF1 (should-fix): the morning catch-up reports today as "NOT recorded" every trading day, exit 1, posted to #fno-desk

- **Path:** the morning runs `records certify closes --since 7 --level certified --commit` at about 08:45. `_sessions`
  ends the window at `today`, and today is a session on every trading morning.
  - A4h's raw answers for today do not exist until 15:40, so today gives `NOT recorded: no staged version`, and the
    command exits 1.
  - The new CLAUDE.md lines say to post every "NOT recorded" line except "no official index-close file in Drive yet".
    So every trading morning posts a false problem to #fno-desk and logs it, and a real missed session is buried
    among the false ones.
- **Reproduced** (scratch test on c4bc48e58, real session calendar, day 2026-10-26, a Monday, 23 Oct's read saved
  with its official file): exit 1, with `closes 2026-10-23 certified: recorded ...` followed by
  `closes 2026-10-26 certified: NOT recorded: no staged version`.
- **Test it must pass:** on a morning when every earlier session in the window is recorded, `--since 7 --level
  certified` exits 0 and prints no line for today's session. The window covers only sessions whose close can exist
  (those before today, or today only after its close).
- **Fix (reasoning only):** end the window at the previous session (for example, `--since` taking an `--until
  yesterday`, or excluding a session whose 15:30 close is still in the future by the IST clock).

## Notes

- The excepted reason is matched inside a longer line ("no version passed: <file>: official file: no official
  index-close file in Drive yet; ..."), so the routine must match by substring. The CLAUDE.md wording, "unless its
  reason is", reads as an exact match; "contains" would be clearer.
- `--since` with `--day` sets the window's end to `--day`. That is fine, but undocumented in `--help`.

## Addendum 1

**Verdict: PASS** on story/dr1-1-shadow-steps at f522ac795 (round 2 of 2; main with DR1-1 f7f35710 merged in). It
closes SF1 and both notes.

- **SF1 met:** `_sessions` now ends a certified window at the day before `--day` (the calendar drops non-sessions),
  while a provisional window still ends at `--day`.
  - The tests use NSE's real calendar: Fri 23 Oct gives 22 Oct as the last session, Mon 26 Oct gives Fri 23 Oct, and
    21 Oct (after the 20 Oct holiday) gives 19 Oct. Each exits 0, with no line for today.
  - The evening provisional window still includes today, and that is tested.
  - My plant "the window ends today" fails 3 tests.
- **Notes closed:** CLAUDE.md now says the reason "contains" the excepted text, and the `--since` help names the window
  for each level. Against main, the CLAUDE.md change is only the two DR1 routine lines.
- **Gates on f522ac795 (run by me):** 14,713 passed, 1 skipped, 16 xfailed; ruff, format and check_imports clean. It
  merges cleanly with current main.
