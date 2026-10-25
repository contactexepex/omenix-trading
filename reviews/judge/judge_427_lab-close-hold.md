# Judge 427: hold FL1-1's lab_close (story/lab-close-hold at 64dd4a61)

**Verdict: PASS (lane 1: schedule config). Merge before 14:33 IST on 22 Oct.**

The change is one config line, `daily.live_from.lab_close` from "2026-10-22" back to null, plus the matching pin in
`tests/daily/test_steps.py`. It follows the owner's decision f21a8966 (row 274: "Hold go-live for HTML").

## Checked myself (strong evidence)
- **Scope.** Only `lab_close` changes. `price_distribution`, `price_distribution_scores`, `price_ranges` and
  `price_range_scores` stay at "2026-10-22" (judge 425). E8 stays off.
- **Test.** The pin test now expects `lab_close` None and the other four on 22 Oct, so a wrong date in either
  direction fails. No other test changed.
- **Gates.** On 64dd4a61 merged with today's `main` (62a07d6c, no conflicts), one run:
  - 8,941 passed, 17 xfailed;
  - `ruff check` clean; 1,658 files formatted;
  - imports clean; record scan clean (7,329 files).
- **Later go-live stays clean.** When `lab_close` gets its own date X, FL1's report covers days from X only. Its
  `issues_from` is G13b's 22 Oct, so the first report checks seals of real issues (from 22 Oct on) and sends no false
  "missing" alerts. G13b's ranges and scores keep building from 22 Oct, so the HTML report starts with history.
