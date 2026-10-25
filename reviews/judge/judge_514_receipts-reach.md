# Judge 514: receipts reach (story/receipts-reach)

**Scope:** story/receipts-reach at 910ee216 (builder session_013xqaNTCbSBytKgqpfaYFqZ), the diff against main.
Story, caller table and Claims: `docs/stories/O-receipts-reach.md`. Lane 1 (G13b and G13d seals are evaluation
records; the health check). One judge: Judge J (session_01Qg4Gxun1NvGRrtS9C68Dc1). Round 1 of 2. Due on main before
30 Oct.

**Verdict: PASS.** No blocking and no should-fix findings; 2 minor.

## Criteria
| # | Claim | Result | Evidence |
|---|---|---|---|
| - | The defect | MET | Live, on main's old reader: the 16 Oct NIFTY `.canonical` commit 2ec7c6e6d2 gives `ReceiptUnknown: no push ... in GitHub's activity log` |
| 1 | Reach back to the commit's date | MET | Live, the branch's reader through `Evidence`'s history: 16 Oct pushed 09:36:02, 19 Oct 09:28:00 and 21 Oct 09:27:55 UTC, matching the story. 25 pages for the first question (32 s); the next two reuse them (0.5 s). Plants caught: a fixed 10-page reach, pages not kept, no clock margin |
| 2 | Named answers | MET | `ReceiptOutsideLog` only when the push is not found and the log has really ended; `ReceiptNotFound` otherwise; a later push never taken (`before` holds the commit). Plants caught: no outside-log answer, a later push accepted, the evidence kind lost, not-committed as a plain unknown |
| 3 | Seals store only answers (G13b and G13d) | MET | A final `NOT_PUSHED` needs `now > deadline`; `OUTSIDE_LOG` is final and named; a failed read (an `GitFailed` from `committed_at` included) is retried, then left open, and after 7 days it is reported `NOT_RECORDED`, never stored late. Plants caught: unreadable stored late, no retry in the check, not-pushed final before the deadline, answers retried, outside-log left open |
| 5 | Rate limit | MET as stated | The header shows 15,000 an hour here; about 3 pages a day back |
| 6 | Limits said plainly | MET | GitHub's retention is unmeasurable on an 11-day-old repository; `ReceiptOutsideLog` names the day it matters |
| - | Gates (my run, a separate worktree) | MET | pytest -n auto: 13,423 passed, 16 xfailed. ruff check and format, `check_imports` and `check_records` are clean |

## Minor
- (a) `SEAL_READ_ATTEMPTS = 3` in `fno/price_ranges/wiring.py` is not pinned: setting it to 1 survives. The check's own
  retry loop is tested. Losing it only leaves a seal open until the next run, never a wrong record. One assertion on
  `build_seal_check(...).attempts` would pin it.
- (b) `PAGE_CAP`, the guard against a "next" link that never ends, is untested: removing it survives.

## Plants
14 planted, 12 caught. The survivors are minors (a) and (b).

## Notes
- After this change, a commit whose receipt GitHub never logged is stored late once the deadline has passed. Before
  it, it was stored late after 7 days. The seal runs a day or more after each deadline, well after the log updates.
- The health check's daily problem count (9-10 from 18 to 22 Oct) should fall once this merges. The story says
  plainly that the share caused by this defect is not proven.

## Addendum 1

**Scope:** story/receipts-reach-minors at 74706a51, off main d4de3952. Tests and story text only: two test files and
8 lines of the story.

**Verdict: PASS.**

- **Minor (a), fixed.** `test_the_wiring_reads_a_failed_seal_evidence_three_times` pins `SEAL_READ_ATTEMPTS`; my plant
  setting it to 1 is caught.
- **Minor (b), fixed.** `test_the_page_cap_stops_a_log_that_runs_on_and_says_so` pins `PAGE_CAP`; my plant removing
  the check is caught.
- **My run:** `tests/ai`, `tests/health`, `tests/price_ranges` and `tests/premium_ranges` give 361 passed; ruff check
  and format are clean. I did not re-run the full suite for a test-only change; the builder reports 13,425 passed.
