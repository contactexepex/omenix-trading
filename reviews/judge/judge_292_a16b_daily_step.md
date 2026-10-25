# Judge 292: A16b-d, the candle back-fill as the daily run's last step (story/a16b-daily-step at ab5d2891)

**Verdict: PASS. Lane 1 (Groww, the daily routine). The builder may merge after the full gates pass on the exact
pushed tree. O1's owner checks the CLAUDE.md clause.**

## Story text first
The owner's rule of 16 Oct ("external data must be up to date") and DESK_DECISIONS rows 60 and 206 (no broker key in
GitHub) leave only O1's daily run, and the orchestrator chose that (option (a)). WORK_REGISTER: one builder. "Nothing
else runs `intraday backfill`": I found no caller in `.github/workflows/`, and the CLAUDE.md change is the only text
change.

## Criteria
| # | Criterion | Result | Evidence |
|---|---|---|---|
| 1 | `candles` is the tuple's last step; Alerted(NotBefore(15:33, CommandStep(intraday backfill))) | MET | `constants_operations.py`, `daily/wiring.py`; `CATCH_UP_FROM` comes from A16's `slots.py` (last mark + 3 min) |
| 2 | One source for the pathspecs | MET | `candle_folders()` in `backfill_daily.py`, used by `backfill_wiring.py` |
| 3 | Deferred means failed, one alert, the next step still runs; a clean run commits only its own files | MET | `tests/daily/test_candle_step.py` |
| 4 | No Groww import in the daily run's naming | MET | the test probes `backfill_daily`. I also imported `fno.daily.wiring` in a fresh interpreter: no Groww module loaded (its wiring imports are lazy) |
| 5 | First real run cited | after merge | criterion 5 is checked in the claims after the first routine |
| 6 | Gates on a trial merge with main | MET | 7756 passed; ruff, check_imports and format clean |

**Timing claims checked:**
- 1.9 s a session is consistent with response 122's 45 min 16 s for about 1,430 sessions.
- The 429 evidence (two runs at once lost 74-87 of about 224 quotes) is cited from `claims.py`.
- 15:33 equals A16's last mark (15:30, about 53 s) plus 3 minutes.

## Planted mutations (all reverted)
| Mutation | Caught |
|---|---|
| `NotBefore` does not wait | yes, 2 failed |
| Start moved to 15:10 (inside A16's marks) | yes, 3 failed |
| A pathspec widened to `research/` | yes, 1 failed |

## Notes (not should-fix)
1. `CANDLE_FOLDER` repeats `fno/intraday/wiring.py`'s `INTRADAY_FOLDER` (the same path), because that module imports
   Groww code. A shared constant in a Groww-free module would be DRY. This is small, and it is the same reason
   `backfill_daily.py` exists.
2. **Every session-day routine now ends at about 15:34, not about 15:20**, as the text states. It is a routine-time cost
   only, but the owner should know.
3. **Under O2's lock rule** this step is a `CommandStep` (it runs alone, with the run's thread asleep), so a stopped
   back-fill's locks follow O2's command rule. O2's tuple-driven kill cases now include `candles`.
4. **A gap of more than about 300 sessions passes O1's 600 s limit.** It commits nothing, but its Drive copies stay
   (stated, not guarded). That is acceptable for a daily catch-up.
