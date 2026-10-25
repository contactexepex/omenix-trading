# Judge 671: REH1q, a scheduled read pushed later still gets the day's answer, story and code (story/reh1q-scheduled-reads @ 569ba7b7a)

**PASS, judge F (judge E the other; not read). Lane 1.** Own session (session_01A8XfbTUVgeeEpqatHaWbtP). Labels:
strong, some, reasoning only.

| Check | Result | My evidence |
|---|---|---|
| The rule | MET | `serving.scheduled_pick`: the earliest answer saved within 60 s back to 10 min ahead of now (`is_near`, unchanged); else the latest saved at or before now on the same IST day; else none (`serving.py:36-46`); used by `recorded_closes` and `recorded_candles` |
| No look-ahead | MET | the fallback takes only `saved <= now`; a near answer saved ahead is still served only after the source sleeps to its save time (`recorded_closes.py:39-40`, `recorded_candles.py`, `_answer`); plant "a later answer allowed in the fallback" caught (5) |
| Never another day's | MET | the fallback filters on the IST date; plant dropping it caught |
| Today's behaviour kept when the day's read is near | MET | the near case still takes the earliest (plant "near takes the latest" caught); plant "no fallback" caught (5) |
| Real runs unchanged | MET | both sources exist only under the mode |
| gates | MET | trial merge with main 136cba224 (clean): **17,444 passed, 1 skipped, 13 xfailed** (token kept); ruff, format (2,730 files), `check_imports`, `check_records` (9,483 files) clean |

**Note (not a finding).** Serving the latest earlier answer to a read pushed late is faithful to what existed then, not
to what the day's own read got: a 15:40 read pushed past the 16:00 recheck is handed the recheck's answer, so A4h's
two reads can match in a rehearsal. It is no look-ahead and only rehearsals see it, as the story states.

## Plants

6 planted on 569ba7b7a (`tests/rehearsal`, `tests/intraday`, `tests/close_read`): **5 caught, 1 equivalent**.
Caught: another day's answer allowed; a later answer allowed in the fallback; the fallback taking the earliest; near
taking the latest; no fallback. Equivalent: the day taken in the clock's own zone instead of IST (callers pass IST
times, and these reads run 15:30-16:00, so the date is the same).
