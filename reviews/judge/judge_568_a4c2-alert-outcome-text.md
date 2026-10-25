# Judge 568: A4c-2, the 3 pm index alert names each index's outcome, story text (story/a4c-alert-outcome @ febd67b9)

Judge F. Round 1 of 2. Lane 1 (an alert to #fno-desk, the 3 pm record). Section "### A4c-2" of
`docs/stories/A-data-foundation.md`, plus one `WORK_REGISTER` row. Labels: **strong**, **some**, **reasoning only**.

## Verdict: FAIL (1 blocking, 2 minor). A text fix; I re-judge it at once.

Gate (text only): the doc-reading tests gave **829 passed**, 15 xfailed; the record scan is clean (8976).

The defect is real; I checked it in the code at febd67b9 [strong]:
- `IndexRecording.run` returns "too early" for every index when `(start - now) > MAX_EARLY_WAIT_SECONDS`
  (`indices.py:52-53`).
- `close_day` is skipped for it (`DONE_WITHOUT_ATTEMPT`, `indices.py:26`, `:66-68`), so no none marker exists.
- Yet `INDEX_ALERT` (`indices_cli.py:17-19`) opens with "not recorded today (canonical none)" for every index that
  `_missing` counts, and "too early" is not one of the `QUIET_STATUSES`.
- The criterion 2 edges match the code's `>`: at 14:41:00 the gap is exactly 1200 s, so the run waits; at 14:40:59
  it is 1201 s, so it is "too early".
- Leaving the root cause to O1 (the indices part has no `not_before`) is right: it is O1's file, under one builder
  per function.

## Blocking

**B1. No gap list (quality rule 2, `docs/JUDGE.md`; as in judges 353, 355, 431 and 440).** Every requirement must
map to a criterion or to "Out" with its reason. At least these:
- A4c's alert contract: one alert naming every index not recorded, and exit 1 if any;
- O1's part contract: what a "too early" exit does to the indices part's outcome and to the day's last line;
- O2's unsent-alert text (criterion 5);
- fixed strings as named constants at the top of the module (CLAUDE.md, "Code");
- the public-record rule: the lines O1 commits to `journal/runs/` hold names and statuses only;
- A4f's weekly slot: the weekly index gets the same wording;
- the 350-line limit;
- quality rules 4, 5, 6 and 8 (DRY2's 14:38 case is the natural real sample).

## Minor

1. **Say what the reader should do.** The point of the fix is that "too early" means "a rerun before 15:13 still
   records". Let the alert say that in a few words (for example "rerun before 15:13"), or state why not. A true but
   unhelpful alert still sends the owner to the code [reasoning only].
2. **State the exit code.** "Too early" counts as missing today, so the part exits 1. Say that it stays so, and make
   it a criterion. It is the signal O1 uses to report the part, and the day ends "day done with problems" until the
   O1 fix lands.

## Addendum 1: text round 2 at a2e3061e

**Verdict: PASS for the A4c-2 story text. Code may come.** I judged only the text commit. The draft code commits on
the branch (2425cc96, 8ca0ba05) are judged in the code round.

Doc-reading tests on a2e3061e: **829 passed**, 15 xfailed.

| Finding | Answer | My check | Result |
|---|---|---|---|
| B1: no gap list | 12 rows, each to a criterion or to Out (the root cause, to O1's R1) | read; every item I named maps | **Accepted** |
| Minor 1: what to do | "a rerun from 14:41 to 15:13 records it", both times from the constants | true to the code: a start from 14:41:00 waits (`>`), and A4c's stop is inclusive (judge 441) | **Accepted** |
| Minor 2: the exit code | criterion 6: exit 1 with exactly one alert | read | **Accepted** |

New in the text: one `earliest_waiting_start` in A4's recorder, which O1's 14:44 builds on. It is right: one
subtraction, not two. Criterion 8 pins it for both windows.

For the code round, the claims must show:
- DRY2's 14:38 lines replayed;
- a planted bug per criterion;
- that O1's pinned 14:38 and 14:44 are unchanged by whichever branch merges second.
