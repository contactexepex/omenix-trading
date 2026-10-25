# Judge 530: MS-INS part e follow-up, the review's sources from MS-P1j

**Scope:** story/ms-ins-review-sources at f67ee2a5 (builder session_01LH7m9r5TCAKgZbeHVYkiTD), one commit on main
26830d25. Lane 1 (the instructor's evaluation records). The Claims are "INS-e follow-up: the review's sources from
MS-P1j" in docs/stories/MS-market-school.md. Judge K (session_019ZApRwkUiNMKDsf1k4W44z). Round 1 of 2.

**Verdict: PASS.** No blocking or should-fix findings. 2 minor.

## Criteria
| Claim | Result | My evidence |
|---|---|---|
| A separate root without an import cycle | MET | `instructor/review_wiring.py` imports MS-P1j's `school/wiring.py` (`build_unfilled_entries`). Only `instructor/__main__.py` imports it. check_imports is clean |
| The unfilled entries reach the paired comparison | MET | `_review` passes `sources.unfilled(first, last)` to `rows`. The key is `(driver, road, entry session)` on both sides: `UnfilledEntries` adds `(driver_id, record.road, record.session)`, and `paired.values.road_slot` builds `(decision.driver_id, record.road, record.session)` |
| The three counts are printed per driver | MET | `build_review(..., sources.counts)` reads the committed `opportunity.csv` through `SealedDayInputs.counts`. The test prints "eligible 3, fillable 3, executed 0" and no "not supplied" |
| Unchanged without sources | MET | `review_sources` None gives `frozenset()` and None counts, which are the earlier defaults |
| Read-only | MET [from the code] | `build_unfilled_entries` builds the books with `committer=None`. `SchoolAccounts.entries` pulls the account files from Drive into the local cache under the lock, writes no record, and a failed pull stops by name. An account never opened gives (): its fired entries count as unfilled, which is right |

## Plants (mine, `tests/school/instructor` and `fleet`): 6 of 6 caught
- The unfilled entries dropped from `rows`.
- The counts dropped.
- The entry point without sources.
- `UnfilledEntries`' key order swapped.
- The counts root ignored.
- The range cut to its first day.

## Minor
1. `--review --write` writes the write-once `paired` file from today's ledgers and corrections. A rerun of the same range after a later fill or correction would differ and be refused. This was already true of corrections, and the ledgers now add to it. If the review's file is meant to be rewritable, it needs a range-and-as-of key, or the cut-off. Not for this piece.
2. A review that covers the current session before its fills are booked counts the sealed entries as unfilled. The review is meant for past ranges, so a line in the command's help would suffice.

## Gates (my run, a trial merge of f67ee2a5 with main 9ca95051)
- `pytest -n auto`: 14450 passed, 1 skipped, 16 xfailed.
- ruff check, ruff format, check_imports, check_records (8667 files) and check_numbers: clean.
