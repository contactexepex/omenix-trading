# Judge 683: O14, one retry policy for failed commands, story text (story/o14-retry-policy @ 912cb521f)

**FAIL on 4 should-fix, text round 1 of 2, judge F (judge E the other; not read). Lane 1.** Own session
(session_01A8XfbTUVgeeEpqatHaWbtP). Labels: strong, some, reasoning only.

## Facts checked (on main)

| Claim | Result | My evidence |
|---|---|---|
| The owner's row and words | TRUE | `DESK_DECISIONS.md:350`, quoted exactly |
| Section 2: 600 s per command; A4's 60 s gap; pack until 15:10; 429 pause 60 s; NSE 1 s spacing and 15-minute cool-off; GW1a +5/+10 minutes, 3 tries | TRUE | `steps.py:24`, `recorder.py:65`, `config.yaml:164`, `groww_rate_guard.py:15`, `http_pacing.py:16-23`, GW1a lines 30-31 |
| `fills_by` 15:20; `RETRIED_ON_RERUN` = exits and marks; `test_late_retries.py` | TRUE | `config.yaml:167`, `daily_run.py:84`, `tests/timetable/` |
| GW1a: 38 x 3 = 114 sign-ins, under 150 | TRUE | GW1a lines 35-37 |
| A22 "no retry of the whole command"; candle window "09:10:00-09:10:59" | **FALSE** | see finding 1 |
| Design: one interface (`RetryPolicy`) with one strategy, wired in composition roots; one alert, no text; `fills` and the school kept final (recommended) | SOUND | read |

Gates (trial merge with main; only `.md` changes): record scan clean (9,545 files); doc-reading tests 963 passed, 13
xfailed.

## Findings

1. **Should fix: A22 already retries inside its windows (strong evidence).**
   - `fno/preopen/run.py:1-6`: each part is read at its window's opening, then every 30 s, the last at its
     `last_read_margin`. CLAUDE.md's candle read is 09:10:00-09:10:45, with the window to 09:11:00; the story says
     09:10:59.
   - Section 4 still puts a second loop (5 s base) around each A22 read. That is the double retry the same table
     rejects for A4 ("an outer retry would start a second capture").
   - Fix: A22 is "not wrapped", like A4 (or the story replaces its loop explicitly), and the times are corrected.
2. **Should fix: retries add Groww calls, and A16's marks overlap the 3 pm capture (strong evidence).**
   - "A retry adds no call beyond what the step's first attempt would have made" holds for one attempt only. Each retry
     repeats the whole attempt: an A16 mark reads its chains and every picked contract
     (`intraday/groww_source.py:68-80`, which already asks once more for failed quotes). Five retries inside the 120 s
     window is up to 6 times the calls.
   - A16 marks every 15 minutes, including 14:30, 15:00 and 15:15. `config.yaml:15` already moved `v4` to 14:32
     "after A16's 14:30 mark (Groww cap; 25 Oct)". A retried 14:30 or 15:00 mark competes with the `v4` and 3 pm parts
     for Groww's per-minute budget, which risks the day's 3 pm record.
   - Fix: no Groww retry of a mark that overlaps a 3 pm or `v4` window (or one counted in a shared Groww call budget);
     state the calls per retry; add a criterion with a plant (a 15:00 mark retried during A4's window).
3. **Should fix: which record-writing steps may be retried is left to the code (reasoning only).**
   - Section 6 builds "the table of every step, safe or not" with the code. The steps write lane-1 records:
     `forecasts_v4`, `v4_release`, `book1`, the score steps, `recommend`, `premium_ranges`.
   - The default makes a timeout retryable. A child stopped at its 600 s limit may have uploaded to Drive before its
     commit, and a retry writes again.
   - The text judges cannot check that decision, and criterion 5 tests only one safe command step plus `exits`.
   - Fix: put the initial table in the text: each step, its write-once guard (file and rule), and safe or not, with
     not safe as the default. Add the plant "a not-safe step marked safe" to criterion 5.
4. **Should fix: the Groww child budget leaves no margin, and a child's sign-in failure is not detectable as written
   (some evidence).**
   - 114 + 12 x 3 = 150, exactly Groww's 24-hour limit (GW1a line 14: going over blocks the next morning).
   - The circuit is "per process". A retried child signs in afresh, so O14 must learn from the child that its failure
     was a sign-in failure. Section 5 does not say how (the class in the child's last line? its exit?). If it cannot
     tell, every retry of a failing Groww child spends 3 sign-ins, the very case the worst case counts.
   - Fix: say how the parent reads the child's failure class, never retry after a sign-in class, and leave a margin
     under 150, or recompute from GW1a's count.

## Minors

1. "The end of the run otherwise" is not a time. Name each step's deadline (for example `candles` and the close reads).
2. One owning document: section 2 restates other stories' loops; one line and a link each would do. Section 4's
   "O14 only counts its attempts in the escalation line" for the 3 pm parts is unclear, since they alert themselves.
   Say whether O14 sends anything for them.

## Addendum 1

**Text round 2 of 2 at story/o14-retry-policy @ ab97493c5, judge F: FAIL on 1 should-fix (1 minor). Lane 1.** I did
not read judge E. At most two rounds, so the owner decides.

| Finding | Answer | My check | Result |
|---|---|---|---|
| 1 A22 | not wrapped (its own 30 s loop); candle read 09:10:00-09:10:45, window to 09:11:00 | matches `preopen/run.py:1-6` and CLAUDE.md | **Accepted** |
| 2 Groww calls, A16 | at most 2 retries a mark inside 120 s, in the fire's process; none for the 14:30, 14:45, 15:00 and 15:15 marks; plant 10.5 | the marks are every 15 minutes (`slots.py`); `v4` at 14:32, the 3 pm parts and the snapshot are covered | **Accepted** |
| 3 Safe table | in the text, with each guard; not safe by default; a 600 s stop never retried; one test per safe row; plant (`card` marked safe) | 7 guard messages found in their packages; no Slack sender in `weather`, `price_distribution`, `premium_ranges`, `price_ranges`, `playbook` | **Accepted** (minor 1) |
| 4 Budget and a child's class | counted in sign-ins: 12 a day, worst case 129 of 150; the class read from the child's last line; an unknown class counts as a sign-in failure (fail closed); plant | read | **Accepted** |
| Minors | named deadlines; section 2 one line each; O14 sends nothing for the 3 pm parts | read | **Accepted** |

5. **Should fix: the deadline rule ignores the steps that run between the retried step and the limiting step (strong
   evidence: the step order).**
   - Section 3.1 allows a retry when `now + wait + expected <= the latest start of a later step`. It counts only the
     retried step's own time.
   - In `DAILY_RUN_STEPS` (`constants_operations.py:61-86`), `reviews`, `quotes_done`, `card`, `price_distribution`
     and `premium_ranges` run between `exits`/`trade_marks` and the school. All are capped at 15:25, the school's
     `SLOT_LAST_START`.
   - An `exits` retry that ends at 15:24 leaves those steps to finish after 15:25. The school then starts late, and
     `fleet/runner.py:107-114` makes no first seal for that session: the day's school record is lost.
   - That contradicts section 3.1's own line "A retry never moves a later step past its limit". The same holds for the
     retries of `reviews`, `card` and `price_distribution`.
   - Fix: the retry deadline is each later limit minus the expected times of the steps between, from the same
     run-log rule. Add the plant "an `exits` retry pushes the school past 15:25" to 10.2.

**Minor 1 (fix before the code round's PASS).** Section 6 marks `forecasts_v4_pack` "posts to Slack: no", but its
command (`forecast_v4_rules/cli.py:82`) runs `run_followups`. That can send W8's review alert
(`pack_wiring.py:179`, `pack_followups.review_w8`), guarded by a marker the first attempt writes to Drive. Correct the
row. Criterion 10.6's one-post test must cover that path, or the row becomes not safe.

Gates (trial merge with main; only `O14-retry-policy.md` changes): record scan clean (9,548 files); doc-reading tests
963 passed, 13 xfailed.

## Addendum 2

**Narrow round 3 (granted by the owner, 25 Oct) at story/o14-retry-policy @ 3f15306ae, diff ab97493c5..3f15306ae,
judge F: PASS (1 minor). Lane 1.** I did not read judge E.

| Item | Change | My check | Result |
|---|---|---|---|
| SF5: the steps between | 3.1: a retry is made only if `now + wait + expected(retried) + sum(expected(each step between)) <= L` for every later limit; a step not running today counts 0; the expected times use the same run-log rule; section 4's rows say "less the expected times of the steps between" | matches `DAILY_RUN_STEPS`: exits, then `trade_marks`, `reviews`, `quotes_done`, `card`, `price_distribution`, `premium_ranges`, then the school. Plant 10.2 (the steps between taken as zero) and one test per step (exits, `trade_marks`, `reviews`, `card`, `price_distribution`) | **Fixed** |
| Minor: `forecasts_v4_pack` posts | not safe: `run_followups` can send W8's alert | as I found (`pack_wiring.py:179`) | **Fixed** |
| `exits` row's Slack note | alerts only on a new event | `fno/desk/exits.py:195-197`: `new = journal.record_event(event)`; alert only `if new` | **True** |

The 600 s fallback for a step with no earlier run, summed over the steps between, can make a retry impossible on a
step's first live days. That fails safe (escalate, never late), so it is not a finding.

Gates (trial merge with main; only `O14-retry-policy.md` changes): record scan clean (9,610 files); doc-reading tests
966 passed, 13 xfailed.

**Minor.** The status line still says "pending the owner's word on a third round"; the owner granted it. Update it when
the file is next touched.
