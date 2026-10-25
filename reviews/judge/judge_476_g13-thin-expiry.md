# Judge 476: G13 thin later expiry is a note, not a failure

**Scope:** story/g13-thin-expiry at 3e493108 (builder session_01UkTaDeTRF9ksDgQB9cTU5C). New
`fno/price_distribution/thin_expiry.py`, plus the recorder's split of problems into problems and notes. Lane 1 (the
exit code decides O1's failed step and alert). Round 1 of 2.

**Verdict: FAIL.** The code is correct as read, but three of its four conditions are untested (standing rule, 22 Oct:
an uncaught plant on what decides a result is a should-fix; tests need no re-freeze).

## Checked
- **Real data (22 Oct Drive records, run by me).** `_sort` gives:
  - FINNIFTY: no problems, and one note: `2026-11-23: no strike with both a call and a put used: no parity forward`.
  - NIFTY, BANKNIFTY and MIDCPNIFTY: no problems and no notes.

  The strings match the record's problems exactly. OK expiries carry `reason: None`, so `e["reason"]` cannot raise.
- **Record unchanged.** The record keeps `status: problems` and the problem, so nothing on file is rewritten. A rerun
  sorts the stored problems the same way, so judge 310's rerun rule holds for real problems. No reader in `fno/`
  filters on a record's status: the readers work per row.
- **Gates (my run):** 9821 passed, 16 xfailed, 1 failed. The failure is
  `test_every_committed_g7_record_row_carries_this_trees_method_hash`, and it fails on origin/main too (I ran it
  there): not this branch's. `ruff check`, `ruff format --check` and `check_imports` are clean. Files are under 350
  lines.

## Plants: 7, 3 caught
- **Caught:** nearest = latest expiry; notes not printed; a rerun still failing on a thin expiry.
- **Survived:**
  - `NO_QUOTES` dropped from THIN_REASONS;
  - NOT_ELIGIBLE expiries counted as the nearest;
  - the nearest-OK guard removed;
  - the nearest included in the slice (equivalent while the guard stands).

## Should-fixes (each a test; the code needs no change)
1. **A thin later expiry with reason NO_QUOTES is a note.**
   - Defect: dropping NO_QUOTES passes every test.
   - Test it must pass: a record whose nearest expiry is OK and whose later expiry is `missing` with reason
     NO_QUOTES gives exit 0 and one `note:` line.
2. **An ineligible expiry is never "the nearest".**
   - Defect: counting NOT_ELIGIBLE expiries passes every test. On a day when the near month is not eligible, the
     thin rule would then compare against the wrong expiry, and a thin far month would fail the step.
   - Test it must pass: expiries [NOT_ELIGIBLE, OK, thin NO_FORWARD] give exit 0 and a note for the thin one.
3. **A thin later expiry still fails when the nearest is not OK.**
   - Defect: removing the guard passes every test.
   - Test it must pass: expiries [missing NO_FORWARD, missing NO_FORWARD] give exit 1, with both listed as problems
     and no note.

**Next:** tests 1-3 with the plants caught, then round 2. Merge after Mon 26 Oct's run, outside 14:00-16:15
(orchestrator's call).

## Addendum 1

**Scope:** story/g13-thin-expiry at 9cc3169c, round 2 of 2. The builder's message named 74ff3fd7; the branch head is
9cc3169c. The change is tests only (`test_recorder.py` +27/-1) and the code is unchanged from 3e493108.

**Verdict: PASS.** It may merge (orchestrator's call on timing).

- The three required tests are present: a NO_QUOTES later expiry is a note; an ineligible expiry is never the
  nearest; with no usable nearest expiry, every thin expiry fails.
- My 7 plants re-run: 6 caught. The one survivor, "nearest itself in the slice", is equivalent: the nearest-OK guard
  returns before the slice whenever the nearest is not OK, and that guard is now tested.
- tests/price_distribution: 116 passed. `ruff check` and format are clean.
