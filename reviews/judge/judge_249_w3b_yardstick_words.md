# Judge 249: W3b, the yardstick words (the Forecast lab follows G1's protocol v3)

Dashboard `story/w3b-yardstick-words` at e42264d (W3 builder 0134MoC6f7aAJVcHRBiyATo6; claims: response_36 addendum 2),
from main e425aea. Lane 1 (screen words). Judge D, 16 Oct 2026.

**FAIL: one should-fix** (small: words only).

- **MET:** the lede now reads "Each question has a yardstick fixed before any result, so you can see who beats it". It
  is true under PROTOCOL.md section 8, where v3's yardstick is Book 1. The yardstick is whatever forecaster the
  payload's `primary_baseline` names, a book included. The new `yardstick.test.ts` shows "Rule-based" in the overview
  and on each question. `tsc` passes and `npm test` gives 531/531.
- **Should-fix:** `KIND.baseline` is now "Baseline (plain history)" for **every** baseline. That is false for two of
  the three (`research/forecasts/PROTOCOL.md`):
  - **(a) risk-neutral** is read from option prices (line 82);
  - **(c)** is a simple statistical model, ordinary least squares (line 97);
  - only **(b) base rate** is plain history (line 93).
  The owner would read the options-implied baseline on Q1 and Q2 as "plain history". **Fix:** say "Baseline" alone, or
  name each baseline by what it is (for example "Baseline: option prices", "Baseline: past base rate", "Baseline:
  simple model"), and test one of each. The comment on `view.ts:61` says the same and needs the same fix.

## Addendum 1: head d1a645f (the should-fix fixed)

**PASS.** Every baseline is now "Baseline" beside its own name from the payload ("Option prices, premium removed",
"How often it happened", "Recent movement"), and the `view.ts` comment says the same. The test covers all three plus
"no 'plain history' anywhere in the rows". `npm test` 531/531.
