# Judge 670: REH1s, the guard pins the 3 pm recorders (story/reh1s-guard-recorders @ e8f3d5531), judge E

**PASS (round 1; 1 minor). Lane 1** (the rehearsal's guard over outside services; judge 1 of 2). Judge E, own
session; judge F's verdict not read. Story and code judged together.

## Criteria

| # | Criterion | Result | My evidence |
|---|---|---|---|
| S1 every index and v4 recorder pinned | MET | `builders()` adds BANKNIFTY, FINNIFTY, MIDCPNIFTY and NIFTY weekly (`RECORDED_INDEX_OPTIONS`, `WEEKLY_NAME`), and the v4 window's recorder, each required to be a `RecordedRecorder`. Without the mode each is a `QuoteSnapshotRecorder` (test). The planted-break count is 12 |
| S2 no SDK, no live fallback | MET | The new fresh-process test: six recorders, each `RecordedRecorder` over an `NSEProvider` whose call is refused. The SDK line appears 3 times |
| Building calls nothing | MET | `GrowwProvider` signs in lazily (`GrowwSignIn` on first use, `groww.py:138`), so the guard's builds reach no service |
| No real-run change | MET | The diff touches `fno/rehearsal/guard.py` only, besides tests and the story |
| Gates | MET | Trial merge 97c4c008b (e8f3d5531 + origin/main b729d06b9): ruff clean, format clean (2,741 files), check_imports clean (2,897 files), record scan clean (9,503 files). Full suite with the token kept: **17,510 passed, 13 xfailed, 0 failed** |

## Plants

6 planted, each alone on `tests/rehearsal` (244 tests), restored after. All 6 caught:
- S1, the index recorders unwrapped (`index_wiring.py`): 4 failed.
- S2, the v4 window recorder unwrapped: 4 failed.
- S3, the guard without the index rows: 2 failed.
- S4, the v4 row renamed: 1 failed.
- S5, the weekly row dropped: 2 failed.
- S6, the v4 row accepting any form: 1 failed.

No plant let a live call through (it would reach NSE).

## Findings

**Minor 1. "Every 3 pm recorder" leaves out one: NSE's public chain recorder (story O6).** Strong evidence.
- `quotes record --source nse` runs every day beside Groww's and builds `composition.build_nse_quote_recorder`.
- It has no guard row. Today it is wrapped only because it shares `_quote_recorder` with the pinned "3 pm recorder":
  my probe under the mode gives `RecordedRecorder`.
- So a change that built it outside `_quote_recorder` would not stop a rehearsal. The HTTP guard would still refuse
  its live calls.
- Fix: one more row, `"NSE's 3 pm recorder": (lambda: build_nse_quote_recorder(load_app_config()),
  (RecordedRecorder,))`, with the count at 13. Otherwise, reword the claim to the five the orchestrator named.

## Answer

Yes: under the mode, each index recorder and the v4 window's recorder must be its recorded form or the rehearsal
stops. With no Groww SDK, each one's NSE fallback is refused before any call is sent. The real run is unchanged.

## Addendum 1

Minor 1 follow-up, commit 87ec0493a on `story/reh1qs-minors`. **PASS, 1 minor (a citation).**

- **Fixed.** `builders()` has the row "NSE's 3 pm recorder" (`build_nse_quote_recorder`, required to be a
  `RecordedRecorder`), and the planted-break count is 13. The fresh-process test now also builds it: it is
  recorded over its `NseQuoteProvider`, whose call is refused.
- **Plants:** M1 (the row removed) 2 failed; M2 (the recorder unwrapped in `composition.py`) 6 failed.
- **Minor:** the story's S3 says "judge 669 m1 for REH1s". REH1s's judge E verdict is 670. Fix it with the next
  text change.
- Gates: trial merge 0454aa763 (story/reh1qs-minors adc5063a5 + origin/main 5c613c6b4), token kept: ruff, format (2,744 files), check_imports (2,900 files) and the record scan (9,513 files) clean; **17,528 passed, 13 xfailed, 0 failed**. Only `87ec0493a^..87ec0493a` judged; judge F not read.
