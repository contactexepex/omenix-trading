# Judge 672: REH1s, the rehearsal guard pins every 3 pm recorder, story and code (story/reh1s-guard-recorders @ e8f3d5531)

**PASS, judge F (judge E the other; not read). Lane 1.** Own session (session_01A8XfbTUVgeeEpqatHaWbtP). Labels:
strong, some, reasoning only.

| Check | Result | My evidence |
|---|---|---|
| S1: every 3 pm recorder pinned | MET | `guard.builders()` gains BANKNIFTY, FINNIFTY, MIDCPNIFTY and NIFTY weekly (`RECORDED_INDEX_OPTIONS`, `WEEKLY_NAME`) and the v4 window's, each required to be `RecordedRecorder` under the mode; without the mode each builds `QuoteSnapshotRecorder` as today (test); planted-break count 12 |
| S2: no Groww SDK, no live fallback | MET | `test_guard_recorders.py` (fresh process): all six recorders are `RecordedRecorder` over an `NSEProvider` whose call is refused by the HTTP guard; the SDK line printed once per builder (3) |
| No real-run change | MET | only `fno/rehearsal/guard.py` changes (rows); building a recorder makes no call, and the existing "3 pm recorder" row already built the same provider path at guard time |
| gates | MET | trial merge with main b729d06b9 (clean): **17,509 passed, 1 skipped, 13 xfailed** (token kept); ruff, format (2,741 files), `check_imports`, `check_records` (9,503 files) clean |

## Plants

4 planted on e8f3d5531 (`tests/rehearsal`): **4 caught**. The guard without the index rows; the guard without the v4
row; the index recorders unwrapped in `index_wiring.py` (the regression the guard exists for); the v4 window's recorder
unwrapped in `window_wiring.py`.
