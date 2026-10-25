# Judge 554: DR1-1b, the closes certifier on A4h-2's official values (rules version 2)

Judge B, 24 Oct 2026. Story/dr1-official-values at 3b32d157f, judged as the delta on 1bfe74064 (main with A4h-2
72d769b8 merged, judge 544 PASS); lane 1 (evaluation records). Story: `docs/stories/DR1-design-staging.md` section 9.

**Verdict: PASS.** No blocking or should-fix finding.

## Claims vs reality

| Claim | Reality |
|---|---|
| The certified choice reads `.values(day)["close"]`, unchanged in meaning | True. My plant comparing against `high` instead fails 1 test |
| Rules v2: for NIFTY 50 and NIFTY BANK, high and low against the official high and low, and the previous close against the previous session's official close, within 0.01 | True. Field names match on both sides: A4h-2's `RANGE_FIELDS` (`high`, `low`, `previous_close`) and `OfficialValues` (`open`, `high`, `low`, `close`). `previous_session` is `SessionCalendar.previous_session` (`calendar.py:52`), wired in `wiring.py` |
| A missing previous-session file gives no certified record, named | True: "no official index-close file in Drive for the previous session"; tested |
| INDIA VIX is never certified and stays out of the 20% band | True: only `checked` indices are compared or banded; tested |
| A field missing in one read is named, not a crash | True (`_moved`) |
| Real-Drive dry run: 22 and 23 Oct, both levels, all recorded under v2 and matching A4h's record | Not re-run by me (it needs the owner's Drive credential); the code path is the one my plants exercise |

**My plants (`tests/record_store`):**

| Plant | Result |
|---|---|
| the previous file read for today instead of the previous session | 8 failed |
| previous close never checked | 8 failed |
| high and low swapped | 8 failed |
| low skipped | 1 failed |
| the certified choice measured against high | 1 failed |

**Gates on 3b32d157f (run by me):** 14,824 passed, 1 skipped, 16 xfailed; ruff, format and check_imports clean. It
merges cleanly with current main. `closes.py` stays well under 350 lines.

## Notes (not findings)

- When the previous session's file exists but lacks an index, the failure line names today's file ("previous_close not
  in <today's filename>"), not the previous session's. This is cosmetic; the check still refuses.
- Records written under rules v1 for 22 and 23 Oct (if any are committed before this merges) stay v1. Write-once, a v2
  record for the same key would be a conflict. Any re-certification under v2 needs a revision (section 2, "corrections
  are revisions"), not an overwrite.
