# Judge 220: W3b, the Forecast lab screen (exepex/omenix-dashboard story/w3b-forecast-lab at e384453, from main 7ea7194)

**Verdict: PASS.** I checked a read-only clone at e384453: `npm run typecheck` is clean and `npm test` gives
**492 passed, 0 failed, 0 skipped** (the builder claimed 492). The orchestrator's checks:

| Check | Result | Evidence |
|---|---|---|
| Verdicts only from the backend, no score computed | MET | `view.ts` and `question-view.ts` map the payload only. `bestOf` filters `scores.comparisons` by the backend's `verdict`, and `questionOf` prints `mean_loss`, `mean_diff`, `interval` and `p_value` as sent. No arithmetic on scores beyond formatting |
| Ranks within a question only | MET | `ranked(s.per_forecaster)` sorts one question's rows by `mean_loss` (unscored last, no rank); no cross-question ordering exists |
| Late and breached answers shown, never counted | MET | `STATUS_NOTE` marks `late`, `breach` and `model_mismatch` as "not counted", and the answer is still shown. Coverage before a common start is a dash, never 0 |
| "Better needs the test to say so over many days, not one lucky month" | MET, one note | True for v4 (`PROTOCOL_v4.md` section 4 item 3: a claim needs at least 12 whole batches, a batch-means t p-value at or below the calibrated threshold, and at least 5 2% days) and for v2. Protocol v4 has no interval, so dropping the mockup's "whole interval below zero" is right. Note: v4 also needs the **minimum effect** (item 4: 3% for QLIKE, 2% for Brier); a significant but smaller gain is "real but too small to use", not better. Consider "…over many days, and by enough to matter" |
| Refactors | MET | `components/fno-common/` takes the section card, how-to and quiet-line parts and the shared layout out of the weather (the duplicates test would refuse a second copy). The weather imports them, and its tests and checks pass |
| Import-graph tests allowing `lib/fno-<screen>` by pattern | Not a loosening in effect | Home's and the Screener's lists exempt only two file names (`fixture-source`, `wiring`) under `lib/fno-*`. Every such screen is then held by the new `screens-import-graph.test.ts`: components reach no adapter, wiring or data client (transitively); exactly one W3 page loader reads the wiring; one adapter pick line. It finds screens by their wiring, so a new screen is checked without an edit, and its planted breaches are caught |
| `/us/forecast-lab` is a 404 | MET (code) | `page.tsx`: India-only `generateStaticParams`, `dynamicParams = false`, `notFound()` otherwise. Same as W3a |
| No strategy internals | MET | `FnoForecastLab`'s `x-never-sent` covers "how any forecaster forecasts: its inputs, method, prompts or fitted values". The screen shows names, answers, coverage and the backend's scores. An AI book's isolation label is shown as sent ("sealed same day (not full F1)"), not hidden |

**Notes (not should-fix):**
- **The minimum-effect wording** above.
- **Coverage of the pattern exemption.** A `lib/fno-<x>/` folder with a `fixture-source` but no `wiring.ts` would be
  exempt in Home's list yet not found by the per-screen test. It is harmless today, since nothing but a wiring reads a
  fixture-source. The per-screen test could also list folders without a wiring.
- **The dropped mockup views** (race chart, period chooser, the "costliest mistakes" sentences) are not invented on
  screen. They wait for the 2.9 proposal (judge 217 addendum 1), which is consistent.
