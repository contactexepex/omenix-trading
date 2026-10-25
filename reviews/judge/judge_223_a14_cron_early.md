# Judge 223: nse-margins cron moved earlier (story/a14-cron-early at a35e78cc, lane 1, schedule only)

**Verdict: PASS.**
- The crons change to `0 22 * * *` (03:30 IST, the previous UTC day) and `15 2 * * *` (07:45 IST retry); the
  08:30 retry is dropped.
- The workflow header and A14's text cite the measured late starts: 01:40 and 02:11 UTC crons began at 06:24-07:21
  UTC on 14-16 Oct, and the first 07:45 IST cron had not begun by 10:45 IST.
- No code changed.

The orchestrator's three checks:

1. **Does `due_session` take the IST date for a run that starts on the previous UTC day? Yes.**
   - `fno/nse_margins/wiring.py` passes `now_ist` to the job, and `due_session(now)` takes `now.date()`, which is
     the IST date.
   - I computed it directly: 2026-10-15 22:00 UTC is IST date 2026-10-16.
   - The workflow's librarian step uses `python -m fno margins nse-span --due-day`, the same `due_session(now_ist())`,
     so the archive and the compute agree on the day.
2. **The margin trade-off: keeping 03:30 is right.**
   - **Headroom on the file side:** all 2026 files were written 20:00-24:00 IST the evening before. The latest since
     2020 was 03:05, so 03:30 leaves 25 minutes even against that.
   - **The cost if a file is late:** one false "not archived" #fno-desk line, then the retry and the 7-day lookback
     catch up. No row is ever written from a late or missing file (fail closed), so no money decision is affected.
   - **Why not 04:00:** the measured delays reach about 5 h 10 min (02:11 to 07:21 UTC). 04:00 + 5:10 = 09:10, five
     minutes before the open; 03:30 + 5:10 = 08:40, 35 minutes before it.
   - So 03:30 is the better point: some evidence (three days of delays, 131 sampled file times).
3. **Dropping the 08:30 retry loses only a third attempt, and that attempt was not before the open anyway.**
   - At the measured delays, a 07:45 retry starts about 12:45-13:00 IST and an 08:30 one about 13:30-13:45, both
     after 09:15. Either could still serve the 15:00 decision.
   - With two runs, a failure of both (say Drive down twice) leaves the day without a row until the next day's run.
     C2 then refuses trades that need it, which fails closed. That is a small, safe loss.

**Note (pre-existing, not this change, reasoning only; check on the first weekend):**
- **The path:** a Saturday or Sunday run's `due_session` is Monday, and `pending_days` includes Monday. If Monday's
  `i1` file is not out yet (NSE writes it "18:00-03:05 IST before its day"), `_add_day` raises "not archived" and the
  run alerts. That could mean up to four false lines each weekend (two runs on two days). The old 07:45 schedule had
  the same path.
- **What to check:** whether 17-18 Oct's runs alert.
- **If they do:** skip a due day whose file is not yet expected, or run on weekdays only. This belongs to A14's
  owner.

## Addendum 1: head 4b314984 (one test added); the weekend note answered

**PASS stands for 4b314984.**

- **The added commit is a test only.** `test_the_main_cron_runs_on_the_session_s_own_ist_date_even_5_hours_late`
  reads the workflow's first cron from `nse-margins.yml` and checks two things, both on time and 5 hours late: the
  IST time is before 09:15, and `due_session` is that IST day. `tests/nse_margins` passes and `ruff` is clean. Because
  it reads the real workflow, a later cron change that breaks the rule fails this test.
- **The weekend note: answered, and I accept the answer.**
  - The builder read NSE's file stamp: `nsccl.20261012` (Monday 12 Oct) was created Friday 9 Oct, 22:36 IST.
  - So Monday's file is normally out before the Saturday run, which archives it; Sunday's run prints "nothing new".
  - An alert would come only if NSE publishes late, and that would be a true alert. The builder will check 17-18
    Oct.
  - I did not re-read the stamp myself: `span-bod.csv` holds no creation time, so this is the builder's evidence.
