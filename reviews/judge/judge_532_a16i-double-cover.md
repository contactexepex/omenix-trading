# Judge 532: A16i, double cover for every mark and an in-day recorder witness (PR #133)

**Scope:** story/a16i-double-cover at 2ae8a5cc (PR exepex/trading#133, builder session_01W5HZPYK8jCEaQT3ynFP8Wm), diff
merge-base..2ae8a5cc. Judge I (session_01MvZneCLZqBuiGyNxawdVee). Lane 1: a scheduled workflow with Slack alerts, and the
recorder's run window. Round 1 of 2.

**Verdict: FAIL.** 2 should-fixes. The design is right and safe; the fix's own wiring has no test, and ruff is red.

## Checked
| Point | Result | Evidence |
|---|---|---|
| Two fires cannot take one mark | MET | each mark is claimed (`GitMarkClaims`) before it is taken; a fire that loses the claim records `ALREADY` and takes nothing (`recorder.py:103-107`). Fires already overlapped (H:52 to H+2:05); the extra hour only lengthens them |
| No extra load on the key at 3 pm | MET | `covered_until` starts no new process. `prepare()` (sign-in, expiry plan) runs before each claim, but both are cached per process per day (`groww_source._plan`, `GrowwProvider.api`). So a longer-lived fire adds no Groww call; a fire that loses a claim makes none |
| Never past 15:35 | MET | `covered_until` caps at `SESSION_END` 15:35; a later `--until` stays the caller's. Plants caught: the cap dropped, a 30-minute extra |
| Every mark from 10:00 has two fires | MET | `test_every_mark_of_the_session_has_two_fires` simulates the fires as the story gives the routine's prompt (H:52, ending (H+2):05, 15:35 from 14:52); 09:15-09:45 need the owner's 08:22 fire, as the test says. The prompt is not in the repository, so the test proves the arithmetic on that schedule |
| Cron against IST | MET | `17,47 4-10 * * *` UTC = 09:47-16:17 IST; outside 09:45-15:45, or on a non-session (A7's calendar), `heartbeat-check` says "not watched" or "ok" |
| The token is never printed or written | MET | `FNO_SLACK_BOT_TOKEN` is in two step `env` blocks only; `check.out` holds the command's lines; `send()` returns a one-line outcome that never holds a credential (`alerts/sender.py:20`); the `${{ github.* }}` values in the fallback message are GitHub's own |
| "A16 15-minute marks" from 19 Oct | MET | `expectations.py`; plant (`None` again) caught |
| Full suite on full history | MET | Python 3.13, not shallow: 14,489 passed, 16 xfailed, 0 failed; check_imports and check_records clean. The builder's 3.11 and shallow-clone failures do not reproduce here |

## Findings
1. **Should-fix: the extra hour itself is untested.** My plant puts `cli.py` back to `recorder.run(args.until)`: the fix is gone, and all 433 intraday tests still pass. That is the 23 Oct loss again.
   - Fix expected: a test of `cmd_intraday run` with a fake recorder, showing it receives `covered_until(--until)` (e.g. `--until 14:05` gives 15:05).
2. **Should-fix: ruff fails.** `tests/health/test_expectations_and_cli.py:197` is 132 characters (E501, limit 120), so CI's ruff step is red.
   - Fix expected: wrap the line, then `ruff check fno tests tools` clean.

**Minor:** when `heartbeat-check` stops on a calendar error, it alerts itself but prints no `silent:` line, so the fallback step sends a second alert. That is harmless, but it is a duplicate.

## Plants
4 planted, 3 caught. The survivor is finding 1.

## Addendum 1: round 2 at 7b2a9e45

**Verdict: PASS, with one merge condition.**

- **Finding 1: FIXED.** `test_the_run_command_gives_the_recorder_the_covered_end_not_the_prompts_end` gives a 12:05 end and expects 13:05. My round-1 plant (cli.py back to `recorder.run(args.until)`) now fails it.
- **Finding 2: FIXED.** ruff check and format are clean.
- **Minor: FIXED, and safe.** The check step now also counts `15-minute recorder stopped, nothing recorded` (cli.py's `CALENDAR_STOP`) as "the command alerted itself". It cannot hide a real failure:
  - the line is printed only by `heartbeat_check`'s calendar stop, which announces it;
  - a crash, an install failure or an import error prints neither line, so the fallback alert still goes.
  - The one gap: when that announcement itself fails ("alert NOT sent"), the fallback is also held back. The same is true of the `silent:` line before this round. Minor; not new.
- **Merge condition: the PR conflicts with main** in `fno/health/expectations.py`. Both sides add one constant on the same line: `MARKS_FROM` here, `FLOW_HISTORY_FROM` on main.
  - The resolution keeps both lines unchanged. I tested exactly that merged tree (uncommitted, in a scratch worktree): full `pytest -n auto` 14,563 passed, 16 xfailed, 0 failed; ruff check and format, check_imports and check_records clean.
  - Any other resolution needs a look again.
