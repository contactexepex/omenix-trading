# Judge 650: GW1a, Groww guard core (GW1 parts 1-4 alone), `story/gw1a-groww-guard-core` at 98e5dcfcb (round 1 of 2, judge K)

**PASS, lane 1.** 1 minor. A narrow check against the code I judged in 637 and 637.1. I did not read judge I's verdict.

**Gates.** A trial merge of 98e5dcfcbe881e4039f082f1d37b52185e6b5edf into origin/main dd8992423 is clean (6287424db). On it, with
the Slack token set:
- `pytest -n auto`: 16,756 passed, 1 skipped, 13 xfailed, exit 0.
- ruff check and format are clean. `check_imports` (2,779 files), `check_records` (9,325 files) and `check_numbers` are clean.
- **No test posted to Slack** (00:53:23-01:02:42 UTC): #fno-intraday and #fno-forecast are empty. #fno-desk holds one
  "DRY RUN, 2026-10-22 replay" line, the orchestrator's rehearsal series that was already posting before my runs.
- No changed `fno/` file is in `FREEZE_v4.md`.

| Asked | Verdict | Own evidence |
|---|---|---|
| The same code as judged | MET | `groww_sign_in.py` is byte-identical to round 2 (33f34e571). `git diff 33f34e571 98e5dcfcb` on `groww_rate_guard.py`, `groww.py`, `providers/__init__.py` and `feed_wiring.py` removes only the quiet-window parts: the `quiet` argument and slot, `_quiet.check()`, the `expiries` wait, `MarkQuietWindows` in `get_provider`, and the feed probe's switch to `get_provider`. `groww_check.py` stays as on main. Nothing else changed |
| No quiet windows, no pace change | MET | `groww_quiet_windows.py` does not exist on the branch. The diff against main touches no `groww_source.py`, `recorder.py`, `source.py`, `claims.py`, `pacing.py` or `manifest_commit.py`. A16 keeps 5/s, and its claim rule stays as on main |
| 3 sign-in tries a day | MET | `TRIES_A_DAY = 3`, waits of 5 then 10 minutes, so tries at +0, +5 and +15 min. Then "no more tries until 06:00 IST" for that process. A16's next fire is a new process with its own 3. The docstring's worst case is 38 processes × 3 = 114, under 150 |
| Parts 1-4 as passed | MET | the SDK 1.5 `GrowwAPIRateLimitException` carries `code "429"`, which `is_rate_limit` catches. The 60 s pause raises before any send. `api` is the `ReadOnlyGroww` allow-list. The sign-in alert carries the class name only |

**Plants:** 8 of mine, 8 caught:
- no 429 detection; a pause of 1 s;
- 4 tries; no doubling; Groww's text in the alert;
- `api` without the allow-list; a swallowed next-year 429; `get_provider` without the alert.

**Minor:**
- **m1:** the header says judges 637 and 638 "found nothing in these parts at 01477b7cf". I judged 5d5d054ae (637) and 33f34e571 (637.1), not 01477b7cf. Name the heads judged.

**Note, said plainly:** GW1a alone does not meet the owner's rule. Its own Known limits say so. A16 still asks at 5/s and still takes an unclaimed mark, and nothing keeps the 3 pm readers out of A16's marks. GW1a makes a clash stop at the first 429 and ends the sign-in storm. It does not prevent the clash; that is GW1's parts 5-6, still blocked by 637.1 B1 (`fills_by`).
