# Judge 658: REC1c text amendment (the evening check), story/rec1c-evening-check at adaf0cb62 (judge J, round 1 of 2)

**FAIL** (text), lane 1: 3 should-fix, 2 minor. The amendment commit changes only `docs/stories/REC1-recommender.md`
(+51). Its diff from d82e459d also carries main's merge. Doc-reading tests on the head: 932 passed, 13 xfailed.

## The orchestrator's questions
| Question | Answer | My evidence |
|---|---|---|
| Can the check count a candidate outside the fixed set? | No, by the text, but S2 | Item 3 reads only the record's listed candidates. A school outcome must name the same `decision_sha256`, `driver_id` and `road`. `OutcomeRecord.decision_sha256` is "the sealed decision file the entry rests on" (`fno/school/contracts/records.py:65`), and that is the candidate's own seal hash. The open gap is more than one outcome per candidate (S2) |
| Can a ticket count as a trade? | No | Item 3: `is_ticket` is reported apart as a ticket, and criterion (b) tests it |
| Can "abstaining saved/cost" appear before every candidate closes? | No, by the text; m1 | "once complete" only; `incomplete` and `not known yet` give no total line. The file still holds a partial total (m1) |
| Is the CLAUDE.md line consistent with the evening routine? | Not yet | S1 |
| Is it acceptable that 20:05 never shows the same day's check? | Yes (reasoning only) | A school position closes at an exit or at expiry, mostly after the day, so a same-evening check would nearly always say `not known yet`. The 08:50 edition shows the latest checks (REC1d), and the text states the gap |
| The brake rule | Agreed | It matches judge 654.1's open point, with a test and a plant |

## Findings
**S1 (should fix) The step's place and its commit contradict each other.**
- Item 2 says "right after `lab close` (and `release-check`)", and also "the edition's receipts are committed before
  it, as today".
- Today the edition's receipts and the release logs are committed in the evening's step 3, after `release-check`.
- A check placed between `release-check` and step 3 runs while the edition's receipts are still uncommitted, and its
  own push (pull, then push) races them.
- Fix: put the step after step 3's commit and push, as a step "3b", and name its commit: only
  `receipts/data/recommend/`, by its own command. Also say that step 4's notes cover its alert and exit 1.

**S2 (should fix) The outcome match is not one-to-one.**
- `OutcomeRecord` carries `corrects` (the SHA-256 of a record it replaces), and the text never says how a correction
  is counted. Both records could be added, or the stale one used.
- Fix: per listed candidate, resolve corrections first, so the replaced record drops out. Exactly one live record means
  closed. None means open. Two or more live records, or a record that names the candidate's seal under another driver
  or road, means `data_check_failed` and an alert.
- Add a plant: a correction counted twice.

**S3 (should fix) The 60-session limit ends silently.**
- A candidate that never closes is re-checked for 60 sessions. The text does not say what the last check writes.
- A missing outcome cannot be told apart from an open position, so a day can drop out of the series with no verdict.
  That is a silent skip, and criterion 12 forbids it ("missing record ... `data_check_failed`").
- Fix: the 60th check writes a final file with `data_check_failed` ("never closed in 60 sessions") and alerts it.
- Also say whether `incomplete` is final once its listed candidates have closed. Otherwise it is re-checked, and
  rewritten as a new file, every evening for 60 sessions.

**m1 (minor)** Item 4's "the total over the closed trades" is also in a `not known yet` file. Name it "closed so far"
and keep it out of every line, so no reader takes it for the day's total.
**m2 (minor)** Say that "never fails the evening edition" includes the week's LR1 section, and REC1d's 08:50 read of
a check file that is missing or `data_check_failed`.

## Plants
None (a text round). For the code round: a correction counted twice (S2); the 60th check silent (S3); a ticket counted
as a trade; a candidate not listed but matched; the abstention line before complete.

## Notes
- I did not coordinate with any other judge.

## Addendum 1: text round 2 (the last) and code round 1, story/rec1c-evening-check at ae07ae8d8
**Text: PASS. Code: FAIL**, lane 1: 1 should-fix, 1 minor. Trial merge with main 9b511a70 (97d678c9): 17,243 passed,
1 skipped, 13 xfailed; ruff, format, check_imports (2,856 files), check_records (9,443) and check_numbers clean.
- **Text.**
  - S1 closed: step 3b runs after step 3's push and makes its own commit; the CLAUDE.md line matches, with exit 1
    covered by step 4.
  - S2 closed: corrections resolve to one live outcome.
  - **The rejected half of S2 is right; I withdraw it.** One sealed decisions file holds every driver and road of
    the session, so other candidates' outcomes rightly share its `decision_sha256`. The match is seal, driver and
    road. My Z5 (road ignored) and Z6 (seal ignored) are each caught.
  - S3 is closed in the text. m1 and m2 are closed.
- **Code: the orchestrator's questions, each with my evidence.**
  - Only listed candidates are checked: `check` iterates `record.candidates` only.
  - A ticket is never a trade: Z1 and Z17 are caught, and an open ticket keeps the day open (Z8).
  - The abstention line appears only for a final day: `answer_text` runs only on FINAL, `closed_so_far` is in no
    other line, and the sign flip Z11 is caught.
  - The brake: Z14 is caught.
  - Corrections, an orphan, two live outcomes and an untraded mismatch fail the day: Z2, Z3, Z4 and Z7 are caught.
- **S1 (should fix) A missed evening still lets a day leave the window silently.**
  - `CheckRun._recorded_days` takes only the last 60 sessions, and `last` is true only while the day is the oldest
    of them.
  - If the check does not run on that one evening (a routine failure, a refused push), the day is 61 sessions back
    on the next run and is never looked at again. Its latest check stays `not_known_yet`, and nothing is alerted.
  - My probe, with the builder's harness and the window shrunk to 5: checks on sessions 1, 2 and 3 say
    `not_known_yet`; the 5th session's evening is missed; sessions 5 and 6 print "no recorded day waits for a
    check". There is no final file and no alert.
  - That contradicts the text's "no day leaves the window silently".
  - Fix: pick every receipted day whose latest check is not final, from a lookback longer than the window, and treat
    any day 60 or more sessions back as `last`. Add the plant "the last evening missed".
- **m1 (minor)** A day failing for a data reason (`TWO_LIVE`, `ORPHAN`, an untraded mismatch) is not transient, yet
  it is retried and alerted every evening until the 60th session. Consider writing it final at once; a read error
  stays retried.
- **Plants: 17 of 17 caught (Z1-Z17).** Run in their own worktree with PYTHONDONTWRITEBYTECODE=1.
- Slack, with the token set (1792894919-1792895449): only REH1 "DRY RUN ... replay" posts in #fno-desk, as before.
  None comes from `tests/recommend`.

## Addendum 2: code round 2 (the last), story/rec1c-evening-check at 33f0252db
**PASS**, lane 1: S1 and m1 closed; 1 minor. Trial merge with main 48acc7d3 (1158d830): 17,431 passed, 1 skipped,
13 xfailed; ruff, format, check_imports (2,884 files), check_records (9,473) and check_numbers clean.
- **S1 closed.** `_recorded_days` now reads every receipted recommendation up to the check day, however old. A day 60
  or more sessions back gets `last` on the next evening that runs.
  - My probe again (window shrunk to 5, the 5th session's evening missed): the next run writes final
    `data_check_failed` "never closed in 5 sessions" and alerts it; the evening after says nothing waits.
  - My plant M1b (old days dropped by session count) is caught by `test_the_last_evening_missed_still_ends_the_day_final`.
- **m1 closed.** `DataDisagrees` (two live outcomes, an orphan correction, an untraded mismatch) is final at once;
  read errors stay retried. My M2 is caught.
- **K's m1** holds as well: a past-day `--on` counts only check files made by then. My M3 is caught.
- **Plants: 20 of 21 caught.** Z1-Z17 are caught again on the new code, as are M1b, M2 and M3.
  - M1 survives: it keeps only the last 60 *recorded* days. In live use every session is recorded, so that would
    bring the round-1 bug back, but no test has more than 60 recorded days.
  - **m2 (minor, test only):** add one test with more than 60 receipted days, each with a final check or with an old
    open day.
- Note: each evening reads the latest check file of every recorded day through the verified Drive cache, so the reads
  grow by about 250 a year. Cheap now; worth a "final" index once it matters.
- Slack, with the token set (1792896399-1792896956): only REH1 "DRY RUN ... replay" posts in #fno-desk and
  #fno-forecast, as before.
