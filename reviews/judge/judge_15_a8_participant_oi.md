# Judge 15: story A8, positioning data source (participant open interest)

**Verdict: FAIL.**
- **Should fix, builder side (1):** files NSE rewrote after the decision time are used at the default time without a
  flag.
- **Pending, not builder defects (2):** Drive coverage, which waits on the owner's upload route, and the measured
  release rule, which needs 20 measured days.
- **Minor (2).**

The parser, the coverage check, the look-ahead guard and the fingerprints all check out.

**What was judged:** trading `main` after commits e5cc852 to 96753c5, with the builder's claims in
`reviews/claude/response_40_2026-10-13-a8-participant-oi.md`. I read in full `fno/research_data/availability.py` (73
lines) and `positioning.py` (37 lines), and the parser's interface. All A8 files are under 350 lines; the largest is
`participant_oi.py` at 152.

## Checks run by the judge

```
$ python -m pytest -q tests/research_data/test_participant_oi.py tests/research_data/test_participant_oi_availability.py tests/test_participant_oi_coverage.py
32 passed
$ curl https://nsearchives.nseindia.com/content/nsccl/fao_participant_oi_12102026.csv   -> 200, 984 bytes
  sha256 8ceb5e8a…3897 = tools/nse_raw_download/manifest_participant_oi.csv row 2026-10-12 = release_checks.csv first row
$ curl -I …fao_participant_oi_15012024.csv  -> last-modified: Wed, 15 Jan 2025 13:30:03 GMT
  = research/data/participant_oi/archive_last_modified_2026-10-13.csv row 2024-01-15 (the builder's rewrite example is real)
```

**Hand re-read of `tests/fixtures/nse/fao_participant_oi_03012022.csv` (the story's "judge verifies").** I read the
FII row and compared it with the parser's output:

| Column order as printed in the file | Raw value | What the parser returns |
|---|---|---|
| Future Index Long / Short | 127535 / 55563 | `future_index` (127535, 55563) |
| Future Stock Long / Short | 913854 / 711756 | `future_stock` (913854, 711756) |
| Option Index Call Long, Put Long, Call Short, Put Short | 306326, 342071, 216510, 230730 | `option_index_call` (306326, 216510); `option_index_put` (342071, 230730) |
| Option Stock Call Long, Put Long, Call Short, Put Short | 43094, 42159, 54464, 34277 | `option_stock_call` (43094, 54464); `option_stock_put` (42159, 34277) |
| Totals | 1775038 / 1303300 | (1775038, 1303300) |

The interleaved call and put columns are mapped correctly. DII's values 819 / 80747 / 0 also match.

**Release-time evidence file.** `research/data/participant_oi/release_checks.csv` exists. It has 2 rows: 12 Oct
present, which does not count as measured; and 13 Oct absent. `participant-oi rule` reports the default rule with 0 of
20 days measured. Nothing uses the data for decisions yet; E6, F2 and the AI books are later stories.

## Criteria

| # | Criterion | Builder's claim | Judge's own evidence | Result |
|---|---|---|---|---|
| 1 | Coverage from 2019 to today: every session present or a sourced exception; damaged files fail | NSE archive: 1,929 of 1,929 sessions. Drive: 0 (pending upload) | Coverage tests pass (missing day, flipped byte, file for the wrong day, fingerprint mismatch). I did not re-download all 1,929 files; my sampled file matches the manifest. The Drive half is not done. | NOT MET (pending the owner's Drive route) |
| 2 | Parser equals a hand reading of three real files (2019, 2022, 2026) | Test with 56 numbers per file | My own hand reading of the 2022 FII and DII rows matches (table above); the test passes | MET |
| 3 | Day D's decision never sees D's file unless the measured rule allows it | Default rule met; measured rule built, not yet in force | `NextSessionRule.usable_from(D)` = next session at 15:00 (`availability.py:55-56`). `as_of` asks the rule before fetching (`positioning.py:31-33`), so D's file is never read for D's decision. Tests pass, including the weekend and holiday cases. The measured rule needs 20 bracketed days. | Default part MET; measured part NOT MET (pending 20 days) |
| 4 | Raw files stored unchanged with SHA-256, like A1 | Manifest of 2,842 days; the library refuses different bytes; coverage fails on a fingerprint mismatch | The 12 Oct file I downloaded has the manifest's SHA-256; the fingerprint check is read and tested | MET |

## The builder's main doubt: is the next-session rule honest for history?

My answer is reasoning based on the builder's evidence, which I spot-checked. Last-Modified is when NSE **last** wrote
the file, so it is an upper bound on when today's bytes became public.

- **For 1,824 of 1,929 days (94.6%)**, the file was last written before the next session's 15:00. Today's bytes were
  therefore public by the time the default rule allows their use. **The default rule is honest for those days.**
- **For 105 days**, today's bytes were written after that moment. One example is 15 Jan 2024, rewritten on 15 Jan
  2025, which I confirmed with my own request.
  - A first version may well have been public on time, but there is no way to know whether its numbers equal today's.
  - Using today's bytes at the next session's decision time can therefore use numbers nobody had then. That is a
    look-ahead on content.
  - **The default rule is not proven honest for those days.**

**This belongs in A8.** The story's context says the design requires "release time, coverage and archive stability
checked" before any use, and the builder already has the evidence file. The fix is small:

- treat each day's Last-Modified (plus a margin) as a lower bound on when its current bytes may be used;
- or mark those days unusable for history.

Either way, record it so that the E6 study and the AI roles inherit it rather than each re-deciding it (finding 1).

## Claims vs reality

- **"Every one of the 1,929 sessions … none on a closed day":** consistent with the manifest and my sample. The full
  re-download was not repeated.
- **"Parser reads all 1,929 exactly", plus the rounding tolerance of 2:** the test cases cover the listed variants. A
  tolerance of 2 is justified by the per-participant rounding the builder found (805 files exact, 991 off by 1, 131 off
  by 2). For files already in the manifest, the fingerprint check is the stronger guard.
- **"Lag counted in sessions, not hours":** the code and tests agree. A weekend cannot hide a late file.
- **Routine created at 17:11 IST:** the orchestrator says so. I did not re-list the triggers for this verdict.
- **Commit 96753c5 lacks the trailer:** confirmed (minor finding 3).

## Engineering standards

- `AvailabilityRule` is an interface with two strategies; the wiring sits in `fno/composition.py`.
- `PointInTimeParticipantOi` depends on callables and the rule, not on concrete stores.
- Every file is under 350 lines.
- No breach found.

## Findings

1. **Should fix: files rewritten after the decision time are used at the default time without a flag.**
   - Evidence: the 105 days in `archive_last_modified_2026-10-13.csv`, for example 2024-01-15, which I confirmed live.
   - Expected:
     - The point-in-time reader (or the rule) uses max(rule time, the file's recorded Last-Modified + margin) for
       history, or refuses those days.
     - The recorder stores Last-Modified and SHA-256 on first sight, so a later rewrite is detected (a new hash for a
       seen day).
     - Add a test with one rewritten day.
2. **Pending (criterion 1, Drive half):** waits on the owner's Drive upload route. When it lands, re-run
   `data-coverage` and commit the output.
3. **Pending (criterion 3, measured half):** waits on 20 bracketed days from the 17:11 routine (about four weeks).
4. **Minor:** commit 96753c5 has no co-author trailer.
5. **Minor:** the decision time of 15:00 is an assumed constant (`fno/composition.py:34`) until E3 freezes the
   timetable. E3 must update it, and the rule's records should name the decision time they assumed.
