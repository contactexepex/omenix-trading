# Judge 552: O8d, the desk run judged by when its decisions were collected

**Scope:** story/o8d-decisions-start at 5b491325 (builder session_012eM7Ti8ZaSVowgyMkgoGmM). The Claims are in
reviews/claude/response_332_o8d-decisions-start.md. The bug is the dry run's finding f3 (docs/dryruns/DRY1_2026-10-23.md). Lane 1. Round 1 of 2.
Judge K (session_019ZApRwkUiNMKDsf1k4W44z).

**Verdict: FAIL.** One should-fix, test only: the main claim (start, not finish) is not pinned by any test. The rule
itself is right. 2 minor.

## (a) The rule against E3's real contract
| Point | Result | Evidence |
|---|---|---|
| E3's rule | MATCHES | `daily_steps.collect_decisions`: `started > deadline + COLLECTION_GRACE` (30 s) fails closed. O8 now uses `judged(started_at, deadline + COLLECTION_GRACE)`, on time when `<=`. That is the same boundary, with E3's own constant imported |
| What a truly missed day looks like | CORRECT | E3's fail-closed path (`_all_late`) still records the decisions step, with every book `NO_DECISION_LATE`. Its start is after deadline + 30 s, so O8 reads LATE. A day with no decisions step is NOT_DUE until deadline + 30 s, then MISSED |
| The time measured | MATCHES within milliseconds | The run log's `started_at` is read by `daily_run.py:186` just before the step. E3 reads its own clock a few milliseconds later. See minor 1 |
| The 4 real logs | OK | 23 Oct: started 15:12:00.000257, finished 15:12:01.326838. On time under the new rule, late under the old one |

## (b) Tests and plants (mine, `tests/health`)
| Plant | Result |
|---|---|
| The grace dropped (bare deadline) | caught (5 fail) |
| The grace doubled | caught (1 fails) |
| **`finished_at` judged against deadline + grace (the start/finish mix-up)** | **SURVIVES (153 pass)** |
| "no decisions step" judged against the bare deadline | survives (minor 2) |

**Should-fix:**
- `_run_log` writes `started_at == finished_at`, and every real log finishes about 1.3 s after it starts, well inside the 30 s grace. So nothing tells the start from the finish.
- Expected: two cases with start and finish different.
  - Started at deadline + 29 s and finished at deadline + 31 s: OK.
  - Started at deadline + 31 s and finished at deadline + 31 s: LATE.
- The first case fails under the finish-based plant.

## (c) Other O8 checks
- None has the same mix-up.
- Quotes, pre-open, data and AI-book checks judge a **push** time against their deadline, which is the right measure: was it public by then.
- The forecast lab judges `generated_at` against the generation deadline.
- `MarksCheck` uses A16's own per-mark status.
- `run_failures` only dates rows by a run's start.

## Minor
1. The run log's start is read a few milliseconds before E3's own clock. A start in the last milliseconds before deadline + 30 s can read OK in O8 while E3 failed closed. In that case the result holds `NO_DECISION_LATE` for every book, with E3's `collected at ... after the deadline` reason. Reading that reason (or E3 recording its own start) would close the gap exactly. This is a negligible window today.
2. `absent(now, due, ...)` for a missing decisions step moved from the bare deadline to deadline + 30 s. That is consistent, but untested (my plant survives).
3. Observation, pre-existing and outside O8d: the desk check never looks at the books' own results. A day when the collector starts on time but a book had committed nothing visible by the deadline (`NO_DECISION_LATE`, "nothing visible") still reads OK here. If that should be a health miss, it is a separate story.

## Gates (my run, a trial merge with main 39b87915)
- `pytest -n auto`: 14776 passed, 1 skipped, 16 xfailed.
- ruff check, ruff format, check_imports, check_records (8887 files) and check_numbers: clean.

## Addendum 1: round 2 at fc91e2b2

**Verdict: PASS.** The should-fix is closed, minors 1 and 2 are taken, and minor 3 is noted in the register.

| Item | Result | My evidence |
|---|---|---|
| Should-fix: start versus finish is tested | MET | `_run_log` takes a separate finish. Start 29 s / finish 31 s is OK; 31/31 and 31/29 are LATE. My round-1 plant (judging `finished_at`) now fails 2 tests |
| Minor 1: E3's own verdict | MET | `_collected_late` reads a `NO_DECISION_LATE` book whose reason starts with E3's `COLLECTED_LATE` prefix (taken from the constant), and that wins over the start time. A book late for its own reason ("nothing visible ...") is not read as a late collection, and a test pins it |
| Minor 2: the missing step's deadline | MET | The edges at +29 s (NOT_DUE) and +30 s (MISSED) are tested. My plant (bare deadline) fails 1 test |

**Plants (mine, `tests/health`):** 7 of 8 caught.
- Caught:
  - the finish judged;
  - the grace dropped;
  - the grace doubled;
  - the missing step at the bare deadline;
  - E3's verdict ignored;
  - any late reason read as collected late.
- Survived (minor): not checking `decision == NO_DECISION_LATE`. It is harmless, because only E3's fail-closed path writes a reason with the `COLLECTED_LATE` prefix. The docstring says "every book", while the code takes any one; E3 writes all books alike, so the result is the same.

**Merge note:** a trial merge with main 4a85d79b conflicts in `docs/WORK_REGISTER.md` only (row 112, both sides edited). The merge must resolve it before landing.
- With the conflict left in, 5 tests fail: the conflict-marker test and 4 record-scan shards.
- Resolved by keeping both sides (my local trial only, never pushed), those tests and `tests/health` gave 179 passed.

**Gates (the same trial merge):**
- `pytest -n auto`: 14778 passed, 1 skipped, 16 xfailed, plus the 5 conflict-only failures above.
- ruff check, ruff format, check_imports, check_records (8891 files) and check_numbers: clean.

## Addendum 2: O8e at 782bb6632 (story/o8e-collected-late, 552.1's notes)

**Verdict: PASS.**
- **The docstring question:** verified. E3 writes `COLLECTED_LATE` only in `collect_decisions`'s fail-closed branch, through `_all_late` (daily_steps.py lines 96-97 and 122-124), for every book from one start time, before any per-book work. A book late for its own reason gets `NOT_COMMITTED`. So one book carrying the text is enough, and the new docstring says why.
- **A mixed log:** a log with the text on some books only cannot come from E3. It now reads LATE and is named "run log inconsistent: COLLECTED_LATE on some books only (...)".
- **Plants (mine, `tests/health`): 3 of 3 caught.**
  - The decision filter dropped (552.1's survivor): now caught.
  - A mixed log not named.
  - A full log named inconsistent.
- **Gates (a trial merge with main d76ef42d, no conflict):**
  - `pytest -n auto`: 14870 passed, 1 skipped, 15 xfailed.
  - ruff check, ruff format, check_imports, check_records (8902 files) and check_numbers: clean.
