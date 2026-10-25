# Judge 457: one source for the result words (story/fl1-1d-result-words at f99107f2)

**Verdict: PASS (lane 1). The designer may merge exactly f99107f2: pull, one full run on the merged tree, push.**

`design/formats.py` now builds `GLYPH` and `WORD` from `plain.RESULTS` through a colour-to-flags map, instead of
keeping its own copy. The Slack text lines and the pages therefore share one source for "✓ Correct", "⚠ Close call"
and "✗ Missed" (DRY). The strings are identical, so nothing changes visually. A new test pins all three equal to
`RESULTS` and to the literal words.

## Checked myself
- The diff is 3 files: `formats.py`, the test, and the response 310 addendum. The map's flags (inside 50%, inside 90%)
  match `RESULTS`' keys exactly; (True, False) cannot occur.
- **Gates:** on f99107f2 merged with today's `main` (no conflicts), one run:
  - 9,478 passed, 16 xfailed, 0 failed;
  - `ruff check` clean; 1,785 files formatted;
  - imports clean; record scan clean (7,542 files).

  Strong evidence. The intermittent `test_git_limit` test (judge 456) passed this time.
