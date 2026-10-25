# Judge 275: G11 round 1, the AI books' v4 rows (story/g11-ai-books-v4 at 8f8cc4fe)

Judge B, 16 Oct 2026. Lane 1 (forecast records). Claims: `reviews/claude/response_255_g11-round-1-v4-rows.md`.
Builder: session 013xqaNTCbSBytKgqpfaYFqZ (G11 owner from 16 Oct). Round 2a (fa758dcc) is on hold at the
orchestrator's request and is not judged here.

**Verdict: PASS.** It may land before the v4 freeze as switched-off code (ruling below).

| Item | Result | Evidence |
|---|---|---|
| One row per started question for a settled book-day, in G7's schema and G8's folder | MET | `v4_rows` builds each row with G7's own `records.record` (range checks reused); the question list is passed in; G8's `ForecastFiles` reads the test's rows |
| The status is F1's gate as is; every failure is a miss, never a gap | MET | scored gives `ok`; `late`, `not_fired`, `no_submission`, `not_revealed`, `invalid`, `model_mismatch` and `exposed` keep their names; a transcript breach is `breach`; a stop-rule day is `stopped` (read from the audit's notes). G8 reads any non-`ok` status as no forecast (`inputs.py:69`), and G8's look counts a row of any status (judge 211) |
| A pending day writes no row | MET | `PENDING` returns None; rows never change, so it waits |
| An unknown outcome is refused | MET | `ValueError`, nothing written |
| A scored day missing one answer is that question's `invalid` row | MET | test |
| Written once; out of range refused before writing | MET | `records.write`, `RecordConflict`; `InvalidRecord` before any file |

**My mutations (real cases, all caught):**
- The stop-rule detection removed: 1 test fails.
- The missing-answer `invalid` fallback removed: 1 test fails.
- A pending day treated as settled: 3 tests fail.

## Ruling: may round 1 land before the v4 freeze as switched-off code? **Yes**, on two conditions

1. **It touches no frozen file and nothing calls it.** True on 8f8cc4fe: one new module, `fno/ai/v4_rows.py`, plus
   its tests. No FREEZE list or protocol names `fno/ai/` (grep), and no caller exists until round 2.
2. **It decides which AI book-days count as misses, so it belongs in the v4 freeze.** Protocol v4 section 10 hashes
   "every G7 and G8 file that decides a v4 baseline, outcome or score". `v4_rows.py` decides an AI slot-day's status,
   which G9's caps and G8's look count. Landing it before the freeze is the better order: the freeze checklist (R2/G7)
   should list `fno/ai/v4_rows.py`, or state in writing why not. After the freeze, a change to it is a new version.

## Carried forward to round 2 (recorded, not findings here)

- G10 part 2 (judge 274 addendum 1): the AI writers are pack readers, so round 2's writer must call the `fno/v4_pack/`
  guard (another or an empty `pack_sha256` refused), with a test.
- `write_book_day` writes question by question. A `RecordConflict` on a later question leaves earlier questions'
  identical rows as they were (no-op), so no half-day of new rows can appear. Keep it that way when round 2 adds
  `pack_sha256`.

**Gates (run by me on 8f8cc4fe):** 7,369 passed. The 3 failures are the A14c stress-factor tests (`tests/risk`), red
on main when this branch was cut and since fixed on main (00a2995e). Run the full suite on the merged tree. `ruff
check`: clean. `ruff format --check`: 1,315 files already formatted. `check_imports`: clean.
