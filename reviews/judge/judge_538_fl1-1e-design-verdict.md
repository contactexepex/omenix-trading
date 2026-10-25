# Judge 538: FL1-1e design part (the evening verdict first), story/fl1-1e-design-verdict

- **Judge:** E (session_01HkXMVPDEqVsmJZtghFrGzM), lane 1, round 1 of 2
- **Head judged:** 21e9009f (5dec6667 plus "a past day's check is named"), merged with main daee2aeb for testing
- **Claims:** reviews/claude/response_330_fl1-1e-design-verdict.md
- **Verdict: FAIL** (one red gate, two untested promises; the design itself reads right)

## Gates (merged head 0fb0e6fc)
- pytest -n auto: **19 failed**, 14565 passed. All 19 are `tests/school/reports/test_editions.py`.
  The same 19 fail on the branch head alone; main passes 23 of 23. Cause (strong evidence: the diff):
  `tests/forecast_lab/design_builders.py` now gives every fake index a `result`. The school tests build
  their editions from `design_builders.page`, so the text line gains "today closed 22,302.00 (NSE's official
  close; G13b's score follows): ✓ Correct" and no longer matches `tests/school/reports/golden/*.txt`.
  Response 330 states no suite result ("result in the commit message's addendum"; there is none).
- ruff check, ruff format --check, check_imports, check_records: clean.

## Findings
1. **F1 (blocking): the red suite above.** Fix one of two ways: keep `page()`'s default as it was, with the
   new `result` only where a test asks for it; or update the school golden files, agreed with their owner
   (MS-P1j) and with the text line's new words checked by hand. Do not regenerate them blind.
2. **F2 (blocking, the orchestrator's point 3): "unchecked is always the first line" is not pinned.**
   Plant P4 put "last checked: ..." above the red `nocheck` line and every test passed. Pin the order:
   the red line's index is below "last checked" and every other line of the card's body.
3. **F3 (blocking, the owner's option A): a close call's verdict is not pinned.** Plant P3 made an amber
   day read "inside “almost certainly”: no" and "verdict: ✗ wrong"; every test passed. Option A's whole
   point is "✓ right" over the amber chip. Pin one amber case: "most likely: no", "almost certainly: yes",
   "✓ right" in green, with the amber chip below it.
4. **F4 (minor, for the today-verdict branch):** `morning_check` uses `close_label(checked, view)`. A
   provisional close in the morning would say "the official file confirms it in tomorrow morning's report",
   counted from the morning's own day. Confirm the morning's check is always on the official close, or word it.

## Checked and right (code read plus plants)
- No past day as "today": `result_of` reads only `IndexView.result`, and its fallback is gone (P1 caught,
  3 tests). `day_word` names any day other than `view.day` (P2 caught).
- The verdict comes from the model's `inside_50`/`inside_90` via `status()`. Those are set in builder.py
  from the sealed band against the close, so no design-side recomputation.
- The unchecked reason is the builder's `IndexView.unchecked`, else "today: not checked (no verdict)"
  (P5 caught). The red line is present (P10 caught). With no check, the page prints no verdict and no "why".
- Order verdict → why (P8 caught). Back-tested stays apart in the chip (P6 caught) and in the method line.
- Friday never says "tomorrow" (P7 caught). The morning's "Last session's check" is present (P9 caught).
- Text is escaped; every file is under 350 lines; no secret, order or channel change.

## Plants: 10 planted, 8 caught, 2 survived (P3 amber verdict, P4 red-line order)

## To pass (round 2)
F1, F2 and F3, with the full suite green on the branch merged with main. F4 can be answered in the
today-verdict branch.

## Addendum 1

- **Head judged:** a8ed3186 (6c7495f8 plus a8ed3186), round 2 of 2
- **Verdict: PASS. Merge only after story/ms-p1g-editions-test (c115ff2b)**
- **Gates:** run on a8ed3186 merged with main 3d1afd85 and c115ff2b:
  - pytest -n auto: 14587 passed, 0 failed;
  - ruff check, ruff format --check, check_imports, check_records: all clean.
  - Without c115ff2b, 14 page-hash assertions fail in tests/school/reports/test_editions.py (48 passed). These tests pin the old design's bytes. The golden text is byte-identical again. So the merge order is a condition of this PASS.
- **F1 fixed:** the fakes carry a check only when asked (`page(..., checked=True)`). The school text needs no golden change.
- **F2 fixed:** red line < "last checked" < method line is pinned. Plant P4 (named line above the red line) now fails 1 test.
- **F3 fixed:** one close call is pinned: "most likely: no", "almost certainly: yes", "✓ right" in green, before the amber chip. Plant P3 now fails 1 test.
- **F4 fixed in code, the claimed test is missing (minor):** `morning_check` labels a provisional close "the official file has not confirmed it yet". Two plants survived, both 3823 passed:
  - P11: back to the report's name;
  - P12: provisional called "NSE's official close".

  Response 330 says "with a test", but no morning test sets `provisional`. Not blocking: on main, own_check.py:66 builds the morning's check with `provisional=False` always, so the path cannot be reached today. Add the pin in the FL1 builder's today-verdict branch or the next design change.
- **Plants:** 2 of 2 round-1 survivors now caught; 2 new F4 plants survived (above).

## Addendum 2

- **Head checked:** ae13294a, a delta check since a8ed3186 (orchestrator, 23 Oct). It already contains main
  a19b74bb, with FL1-1e's builder branch on it; main has not changed in forecast_lab since.
- **Verdict: PASS. Merge go.**
- **Gates:**
  - tests/forecast_lab, tests/school and tests/e2e_acceptance: 3858 passed, 0 failed;
  - ruff check, ruff format --check, check_imports: clean;
  - the designer's full suite: 14,649 passed (one full run per merge: the orchestrator's merge run).
- **Delta read:**
  - The words come from plain.py (YES_NO, VERDICTS, UNCHECKED, PROVISIONAL, OFFICIAL, morning_report). The
    copies are gone and so is every `getattr`.
  - The red line prints plain's UNCHECKED sentence with the report's name, never the raw code (judge 545's
    note).
  - The chip counts over its own scored window, not the chart's 10 days.
  - A cue's level no longer carries the change's unit.
  - The F4 test exists (0b45d56e).
- **Plants (3 of 3 caught):**
  - R1, the raw code on the red line: 1 failed;
  - R2, Friday reads "tomorrow": 2 failed;
  - R3, the chip counted over the chart's window: 1 failed.
- **Next:** FL1-1f adds `unchecked_why` (the reader's own reason, e.g. A4h's sync problem) and
  `no_verdict_words`. Once it merges, the page's red line should use those, so it says why as well as what.
