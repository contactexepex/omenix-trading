# Judge 517: MS-P1g follow-up, the instructor's why lines

**Scope:** story/ms-p1g-why-lines at 85b88f95 (builder session_01WeFYCqffRe7et1nfSJyuv5), diff origin/main...85b88f95.
Lane 1 (Slack reports, counting records). Round 1 of 2. Judge H (session_01KNkZVoWvXMkoihKrrXk5Xa).

**Verdict: PASS**, with 4 minor notes. The first is a merge instruction the orchestrator must act on.

## Checked
| Item | Result | Evidence |
|---|---|---|
| Why lines verbatim, rule drivers only, after the counts, no header when there are none | MET | `evening.py:_why`; 4 tests; 3 plants caught (header always on, role filter off, call removed) |
| The stub can't show a false "no reasons" | MET | `why() -> ()` gives no header and no line, byte-identical to the section without a source (`test_no_instructor_lines_means_no_header_and_no_change`). It reads as nothing, never as "none found" |
| Runbook step for new card versions | MET | It is in MS-P1j's list: new D6 rows per driver version, committed after the card; until then `comparison_card_mismatch` |
| Deleted card hashes to "" and gives `comparison_card_mismatch` | MET | `test_a_card_deleted_after_the_rows_...`; this pins judge 495.1's minor |
| Gates | MET | pytest -n auto: 13,799 passed, 16 xfailed. ruff, check_imports and check_records are clean |

## Minor
- **(a) The merge with story/ms-p1j-ins-wiring is not a textual conflict in `report_inputs.py`.**
  - My trial merge of eb5ec57a into this tip auto-merges that file and leaves **two** `def why` in `SealedDayInputs`
    (lines 50 and 56). The later one, this stub returning `()`, would silently replace j's real `why`.
  - It is caught on the merged tree by `ruff check` (F811 redefinition) and by j's
    `test_the_day_inputs_pass_the_instructor_s_why_lines_through_and_none_without_a_source` (fails).
  - The story's "merging main into it takes theirs" is wrong. Whoever merges second must delete the stub by hand. The
    only textual conflict is in `docs/stories/MS-market-school.md`.
- **(b) A line whose first word isn't a known driver id raises.** j's `role_of` is a plain dict lookup: my run with
  "Overall: a quiet day" gives `KeyError`. The guard keeps the edition, but the whole school section is lost for the
  day. Part e's contract makes every line start with a driver id. Skipping an unknown id would be more robust.
- **(c) The section trusts the source on privacy.** It doesn't scan the lines for a strike or price. That is consistent
  with the story, but no test in g plants a line with a strike. One test on part e's side should pin it.
- **(d) The runbook step says "version id one higher".** D6 also refuses a row whose `starts_on` isn't after the
  book's previous row (`_check_order`). Add "starts_on later than the previous row" so the step can't fail at
  registration.

## Addendum 1

**Re-check:** story/ms-p1g-why-lines at 5bf325d9 (merges main with j's ins-wiring, 486b0f4f). **Verdict: PASS.**
Lane 1.

**Gates (my run):** pytest -n 6: 14,463 passed, 1 skipped, 16 xfailed. ruff, check_imports and check_records are clean.
- **The skip** is `tests/intraday/test_feed_tls.py:190`, `importorskip("growwapi")`: the Groww SDK isn't installed in
  this container. That is environment only and unrelated to this branch.

**My round-1 minors:**
- (a) **ACCEPTED.** The stub `why` is gone. `fno/school/fleet/report_inputs.py` isn't in the diff against main, so there
  is no duplicate `def why`.
- (b) **ACCEPTED.** A line whose first word isn't a known driver is withheld and counted ("n why lines withheld: unknown
  driver"), never raised. The fleet total and the footer survive. Plant (`KeyError` no longer caught) caught.
- (c) **ACCEPTED.** A `LEAK` filter withholds and counts strikes with CE/PE, "strike", "premium", "price N" and "at N".
  A ticket line with a rupee figure is left out. Part e's real `LINE` and `TICKET_LINE` are pinned against the filter.
  Plants (leak filter off, ticket-rupee filter off, withheld notes dropped) caught.
- (d) The runbook `starts_on` note: unchanged here. It belongs to j's runbook; the orchestrator has it.

**Minor (new):** the filter misses a strike written without CE/PE or the word "strike". My run:
`"... why: the 51200 put was thin"` is shown. Part e's templates never write that, so this is a second line of defence
only. Adding `\b\d{4,6}\s+(?:put|call)s?\b` would close it.

**Plants:** 5, all caught.
