# Judge 485: MS-P1c, the dashcam

**Scope:** story/ms-p1-dashcam at eddd7d3a (builder session_01WeFYCqffRe7et1nfSJyuv5). The diff is 756e6545..eddd7d3a,
`fno/school/dashcam/` and `tests/school/dashcam/` only (a's code is judge 479's). It carries a's PASSed round-2 code
(35458460); a's later commits change story text only. Lane 1 (records). Round 1 of 2, after early findings that I sent
on 4bfbba77. Judge J (session_01Qg4Gxun1NvGRrtS9C68Dc1).

**Verdict: PASS.** No blocking and no should-fix findings; 3 minor.

## Criteria
| # | Criterion | Result | Evidence |
|---|---|---|---|
| 1 | Write-once; other bytes are `ReplayConflict`, "rule broken" | MET | `store.seal` judges the remote receipt before Drive is touched; a Drive conflict after a failed push is also caught (`test_a_rerun_with_other_records_after_a_failed_push_...`); plants 1, 2, 4 caught |
| 2 | The receipt is pushed before `seal()` returns | MET | `publish` returns only what `published()` finds on the fetched `origin/main`, else `SealNotPushed`; plant "seal without push" caught |
| 3 | Forged or stale seals refused against the remote receipt | MET | `SealChecker` compares commit, SHA-256 and time with the receipt's add commit on the remote; 5 plants (each field, the time, the SHA) caught |
| 4 | Rerun safety | MET | same records: same seal; a fresh checkout makes no second receipt; a failed push is pushed by the rerun; a shallow clone is deepened or refused by name. My own depth-1 probe now names the real add commit, and the original seal checks valid (it was refused on 4bfbba77) |
| 5 | `pushed_at` labelled commit time | MET in c | `PushedReceipt.pushed_at`: "commit time, not push time; the proof is the remote receipt". See minor 2 for a's contract |
| 6 | Single-process counts file | MET as an assumption | stated in Claims and accepted by the orchestrator; j tests it. See minor 1 |
| 7 | Counts file: record scan clean, codes and whole numbers only | MET | the test runs the scan; session and slot filter, slot check and rewrite guard plants caught |
| 8 | Replay reads exactly what was sealed; conformance | MET | `find` per a's contract; tamper and stale-cache tests; read SHA plant caught |
| - | Gates (my clean run) | MET | pytest -n auto: 10,347 passed, 16 xfailed. ruff check and format, `check_imports` and `check_records` are clean. Largest file 87 lines |

## Minor (no round needed)
1. `counts.py` does not say in its docstring that it assumes one writer. The assumption lives only in the story.
   A one-line "why" comment would keep j from relying on an atomicity it does not have.
2. For a's builder, not c's: `fno/school/contracts/seal.py` labels `Seal.pushed_at` "when its receipt reached the
   remote". c fills it with the commit time, as the orchestrator accepted. d's fill port reads `Seal`, so the
   contract's comment should say "commit time; the remote receipt is the proof".

3. No test covers `_push_unpushed` refusing to push when the pull is refused (a checkout with other unpushed
   changes). The code is right, but the guard that keeps unjudged work off `main` is untested.

## Plants
22 planted on eddd7d3a, 22 caught:
- 18 from round 1, re-planted on the new code (one of them, "no fetch", rewritten to fit it);
- 4 on the shallow fix (no deepen, not refused, deepen skipped, the checker letting a shallow refusal through).

One malformed plant of mine was redone.

On 4bfbba77, 5 of 18 had survived; all 5 are now caught.

## Notes
- My first full suite on this tip showed 22 failures. That run overlapped my plant run in the same worktree, which
  edits files mid-run. The clean re-run above is the result.
- The orchestrator asked whether c's tests prove that `seal()` returns only after a successful push. Confirmed at
  eddd7d3a:
  - `test_a_receipt_that_cannot_be_pushed_gives_no_seal`, `test_a_push_that_failed_earlier_is_pushed_by_the_rerun`
    and `test_find_is_none_for_a_file_whose_receipt_never_reached_the_remote` raise or return None on a committed
    but unpushed receipt.
  - Plants caught: a seal made without the push, `published()` reading the local HEAD, and `publish` falling back to
    the local commit.
  - One survivor, in another property: dropping `_push_unpushed`'s pull-refusal check, which would push a checkout
    carrying other unpushed commits. The code is right; a test is worth adding with j (minor 3).
- `_push_unpushed` pulls and pushes once beside A16f's own retrying `_publish`. It is small, and the remote check
  decides the result, so this is not a finding.

## Addendum 1

**Scope:** the MS-P1c follow-up, story/ms-p1-dashcam-followup at 71ddc707 (diff against main: `counts.py`,
`publisher.py`, one test).

**Verdict: PASS.** No findings.

- **Minor 1, fixed.** `counts.py`'s docstring states the one-writer assumption (MS-P1j's single runner, which also
  commits the file) and why: the exists-then-write is not atomic.
- **Minor 3, fixed.** `_push_unpushed` now raises `SealNotPushed` carrying the pull's own refusal text, where it used
  to return None. The test commits unjudged work on top of an unpushed receipt and reruns `seal()`. The refusal names
  `unjudged.txt`, the remote's `main` is unchanged, and the foreign commit is not on it.
  - Plants caught: back to `return None`; the pull refusal ignored, which pushes the foreign commit; the refusal text
    dropped.
  - The fourth plant, `abort_merge` dropped, survives. It matters only when the pull starts a merge and that merge
    conflicts; this refusal comes earlier. Not a finding.
- **Minor 2** (a's `Seal.pushed_at` comment) is a's, outside this branch.
- **Gates (my run):** pytest -n auto: 10,952 passed, 1 skipped (part d's test), 16 xfailed. ruff check and format,
  `check_imports` and `check_records` are clean.
