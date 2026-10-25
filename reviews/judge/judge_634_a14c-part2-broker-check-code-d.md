# Judge 634: A14c part 2, the daily read-only Groww broker margin check, code round 1 (judge 1 of 2)

Branch `story/a14c-part2-broker-check` at `5f7dc5d7c`; claims `reviews/claude/response_291_...code.md`, "Round 2".
**FAIL, lane 1** (1 blocking, 1 should-fix, 3 minor). Judge session 01BvZZzF4XR48qNHNxLydQhf.

## Criteria

| Criterion (A14c part 2 text, criterion 10) | Verdict | Evidence |
|---|---|---|
| Read-only: only this caller's list reaches Groww | MET | `broker_port.py:16`, `read_only.py:37-50`; `place_order`, `get_order_list`, `get_positions_for_user` refused (test); SDK 1.5 `get_order_margin_details` posts to `/margins/detail/orders` only (read the installed source) |
| From 09:30 on a session day; no request at or after 14:50:00 | MET | `broker_check.py:66,136`; plants P1 (14:51), P15, P17 (09:00) caught |
| Pacing and request count vs Groww's 300/min and sign-in | MET | 1 quote + N baskets, 2 s apart (≤30/min); `providers/groww.py:140-146` signs in once per process, lazily; plant P11 caught |
| SPAN `max(0, scan-NOV)` within Rs 1; exposure at own NIFTY quote within 0.1% | MET | `broker_compare.py:35-42`; P2 (row's exposure), P8 (Rs 1.5), P9 (no NOV) caught; basket proved by source SHA-256 and three figures (`broker_basket.py:63-75`) |
| ffed1c8c1: empty day reads empty; a receipted file Drive lost refuses | MET | `broker_record.py:73-77`; P3 (shortcut always), P4 (incomplete sync accepted), P16 (`error` counted done) caught |
| Write-once O9 record with receipt; O1 commits only its receipts | MET | `DataStore.put`; `daily/wiring.py:144-151`; `CommandStep` commits paths on exit 1 too (`desk/daily_run.py:236`); P14 caught |
| Alert path: a mismatch sends one line, a failure none of its own | MET | `broker_check.py:145-156`; P10 caught |
| Failure lines say what happens next | NOT MET | finding 2 |
| Gates on a trial merge with main 378dbe30f | PARTLY | ruff, format, imports, records clean; full suite 16626 passed, 14 xfailed, 0 failed (with the Groww SDK installed); without it, finding 1 |

## Findings

1. **Blocking: the suite fails where CI runs it.** `build_broker_check` builds `GrowwProvider(cfg)` at once
   (`broker_wiring.py:30`), whose constructor imports `growwapi` (`providers/groww.py:130-133`); CI installs only
   `requirements.txt` (`checks.yml:35`; growwapi is in `requirements-groww.txt`). With `growwapi` blocked:
   `test_before_09_30_the_check_needs_no_drive_or_groww_settings` FAILS ("Install the Groww SDK first"); main's same
   tests pass (204 passed). The test's own claim (no Groww needed before 09:30) is false without the SDK. Fix: build the
   provider on first broker use (inside the client lambda), as Drive already is; prove it with the SDK absent.
2. **Should fix: the lines promise a same-day retry O1 never makes.** `broker_check.py:34,36-39` print "a rerun today
   retries them" / "asks them again", and the story's Idempotent bullet and O1's text say a same-day rerun retries.
   But `outcome()` sets no `retry` key (`daily/steps.py:45-54`), `RunLog.done` treats such a failed step as done
   (`desk/run_log.py:41-43,81-82`), the run skips done steps (`desk/daily_run.py:145`); only exits and marks retry
   (line 84). My script: a failed `margin_check` entry gives `done("margin_check") == True`. O1's alert carries this
   line to #fno-desk. Fix: say the truth (lost for the day; only a by-hand `margins stress-broker-check` before 14:50
   asks again), in the lines, the story and O1's text, with a test on the line.
3. Minor: the story says the step runs "about 14:35 IST, after the weather and the v4 forecasts"; `DAILY_RUN_STEPS`
   runs it third, before `weather` (`constants_operations.py:59-63`), about 14:06. Fix the text.
4. Minor (reasoning only): one NIFTY level at the start serves every basket; the builder's runs took 44.7-60.7 s, and a
   0.1% NIFTY move inside a minute gives a false "review the stress factor" line. Re-quote per basket (about 31
   requests, still far under the cap) or state the drift in the Monday sample.
5. Minor (rule 3): no self-review is stated for round 2's changes (ffed1c8c1, the merge, 5f7dc5d7c).

## Plants

17 planted, one at a time, restored each time: 16 caught. Survivor: P13, the order-verb second line in `ReadOnlyGroww`
removed; unreachable while the positive rule holds (no order name matches `get_*` or UPPER_CASE), as judged in 356.

## Notes

- Open item, not a finding: the market-hours sample (Mon 26 Oct about 10:00 IST) is owed; Sunday's GA000 refusal was
  handled as designed (15 `error` rows, exit 1, no own alert).
- The claims sit in a response file, not the story's Claims section (CLAUDE.md); routed so by the orchestrator.
- Independence: while reading the judge README's format I saw the index row of judge 630 (the other judge). Finding 4
  was in my notes before that; finding 1 I then checked myself with the run above. Nothing else of it was read.
- Gates first failed 2 + 9 errors in a shallow clone (freeze tests); after `git fetch --unshallow` all passed.

## Addendum 1: round 2 (the last), head `c2ed049e6`

**FAIL, lane 1** (1 should-fix, 1 minor). Every round-1 finding is fixed. The new should-fix comes from the dated-lot
check added for judge 630. After this round the owner decides (two-round rule).

| Round-1 finding | Verdict | Evidence |
|---|---|---|
| 1 Suite without the SDK | FIXED | `broker_wiring.py` builds Groww on first use (`functools.cache`). Full suite on a trial merge with main c709f11c3, `growwapi` blocked for every xdist worker by a PYTHONPATH shim: 16682 passed, 1 failed, `test_feed_tls`, a shim artifact (my first shim raised ImportError; `importorskip` skips only ModuleNotFoundError). With a ModuleNotFoundError shim that test skips: 264 passed, 1 skipped. Plant Q5 (eager provider) caught |
| 2 Retry promise | FIXED | `broker_check.py` `LOST`/`BY_HAND`; story Idempotent bullet; O1 text. The test feeds the real output through `outcome()` and `RunLog`: done, no retry. Plant Q4 caught |
| 3 Step time text | FIXED | story: "runs this step third ... right after the routine's 14:05 IST start and before the weather" |
| 4 One NIFTY level | FIXED | `Levels` before and after; a rate step inside the range is `error`. Plants Q1, Q2, Q7, Q8 caught |
| 5 Self-review | FIXED | response 291, "Self-review of rounds 2 and 3" |

**New findings**

1. **Should fix: the dated-lot check can lose the whole day, and the text says the lot file comes earlier than it does.**
   The check needs the day's own `fo_mktlots.csv` (`school/roads/lots.py`: no carry-over). Otherwise every basket is
   `error` "no dated NSE lot" with no request, and the day is lost. The story (A-data-foundation.md:2084) says "A20a
   archives it from 07:45 IST". On main, the manifest commits for the day's file are 21 Oct 19:46 IST (0dedeff7b),
   22 Oct 13:03 IST (277f31a37) and 23 Oct 13:00 IST (534438dad): never by 07:45, and once after the 14:05 step. Also,
   response 291:169 still says "a same-day rerun retries", which is the round-1 error again. Fix: state the measured
   arrival times and the loss risk in the text, and correct the claims' sentence. Then either the owner accepts losing
   a day when the file is late, or the check gets a source that is there by 14:05. Examples: O1 archives the lot file
   before `margin_check`, or the previous session's archived file is used for the basket's month, labelled. Test
   whichever is chosen.
2. Minor: `NOT_SAVED` always says "by hand before 14:50", even when the run itself ended past 14:50. A by-hand run's
   receipts are committed by no step: the line or the text should say to commit `receipts/data/margins/broker_checks/`.

**Gates (trial merge with main c709f11c3):** ruff, format, imports and check_records clean; full suite with the SDK
16683 passed, 13 xfailed, 0 failed. **Plants:** 8 new (Q1-Q8), all caught.
Open item, unchanged: the market-hours sample on Mon 26 Oct.

## Addendum 2: the follow-up the owner approved (25 Oct), `story/a14c-part2-followup` at `df106dc73`

**PASS, lane 1** (2 minor). I judged the delta c2ed049e6..df106dc73 commit by commit; judge M works apart.

| Commit | Verdict | Evidence |
|---|---|---|
| 3dfaa02f4 (630.1 minors) | MET | tests for the range's first end and the record's NIFTY columns |
| 99d0a211f (634.1) | MET | the story names A20a's measured slot times (07:45 started 12:46-13:03 IST; 11:15 at 15:18-16:09), the loss risk, and the 06:00 slot (judge 656) as the fix; `_then`: at or after 14:50 (clock or deadline) only "lost". Plant: clock check dropped, caught |
| 5748ff107 | MET | O1's paragraph is now one line and a link to the owning A14c text (owner's one-document rule) |
| 371f308ed + 9e2c535e2 | MET | the by-hand path is "rerun this same command before 14:50, commit its receipts". That matches DESK_DECISIONS 349 (owner: "if a scheduled command is failed, then a manual run should be allowed ... instead of missing data") and CLAUDE.md "How to work". The step's own command is what failed, and O1's rerun skips it (step 2b unaffected) |
| b195ad9a4 (BLOCKING fix) | MET | after GW1a, `GrowwProvider.api` is itself a `ReadOnlyGroww` with the recorder's list, so the old double wrap refused `get_order_margin_details` on every basket. The fix: `get_provider("groww", cfg, BROKER_CHECK_CALLS)`, with `allowed` passed to GW1's guarded client (default unchanged). The real-chain test (fake SDK, sign-in and 429 guards in place) asks one margin request and refuses order and account calls. Plants: the old wiring, `allowed` dropped in `get_provider`, `allowed` dropped in `GrowwProvider`; all caught |
| df106dc73 | MET | the default list never holds the margin call (test); plant: the default list widened, caught by 3 tests |

**Gates (trial merge with main, clean):** ruff, format, imports, check_records and check_numbers clean; with the
SDK 18063 passed, 13 xfailed, 0 failed; without it (a ModuleNotFoundError shim for every worker) 18062 passed,
1 skipped, 0 failed. **Plants:** 5, all caught.

**Minor (do not hold the merge):**
1. The by-hand text omits the rule's own limit: until O14 is live, or after O14's escalation (CLAUDE.md). Add those
   words when O14 lands.
2. `fno/providers/groww_sign_in.py`'s sign-in budget counts 5 daily-run Groww children (10 with a rerun), so
   `margin_check` is missing: 6 and 12, worst case about 40 x 3 = 120, still under 150. GW1's owner should correct
   the count.

Note: a conflict with GW1 parts 5-6 in `fno/providers/__init__.py` and `groww.py` is expected. The second merge
keeps both parameters and reruns the real-chain test.
