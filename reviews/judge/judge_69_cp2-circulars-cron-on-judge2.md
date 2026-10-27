# Judge 69: CP2 re-enable the circulars cron (lane 1, a schedule change; sole judge)

Frozen SHA `c07e721` (branch `story/CP2-circulars-cron-on`, base main `9849d69`). Reviewed
`git diff origin/main c07e721`, which touches five files: `circulars.yml`, `RUN_LOCATIONS.md`, the swapped test and
one line in `test_groww_consolidation.py`.

**Gates (cleared `__pycache__`):** 1235 passed; ruff clean; imports clean (502 files).

## The four checks asked

1. **Only the schedule is restored.** `git diff 643e25d c07e721 -- .github/workflows/circulars.yml` (the file before
   CP1) is one added three-line comment and nothing else. The `schedule:` block and its cron `"30 2-16 * * *"` are
   byte for byte the pre-CP1 lines. That is 02:30-16:30 UTC, which is 08:00-22:00 IST, as the comment says.
2. **Nothing else changed.** `permissions`, `concurrency` (`group: circulars`), the secrets (the four `FNO_GDRIVE_*`
   and `FNO_SLACK_BOT_TOKEN`) and every step are identical to pre-CP1.
3. **No Groww.** No `groww` appears in the workflow, so the market-hours rule does not apply to this cron.
4. **The test pins the right thing.** `test_circulars_scheduled.py` asserts that `schedule` is exactly
   `[{"cron": "30 2-16 * * *"}]` and that `workflow_dispatch` stays. My plants: a changed cron hour fails 1 test, and
   a commented-out schedule fails 1 test. The paused-state test is removed in the same commit, as its own docstring
   required.

## The evidence for "safe to turn on"

- **Verified on main:**
  - `7ac833b` adds 131 receipt files. 32 are under `receipts/data/circulars`, and every one has the writer
    `rebuild-receipts`, so they are visible as rebuilds.
  - `703f8cd` adds 2 receipts from a circulars run on 27 Oct.
- **Not verifiable here** (Drive and the Actions run): that `data-cache sync` passes for the four prefixes, and that
  run 40485789651 went green. These are the implementer's claims, consistent with `703f8cd` existing. A green
  capture commit could not have been made while the circulars sync still failed closed.
- **The `test_groww_consolidation.py` line:** test-only. A future day keeps the stop time from passing whatever the
  real clock says. The test used `date(2026, 10, 27)`, and the recorder stops at 15:30 IST that day, so it fails after
  that. This review ran at about 15:47 IST, which fits the reported failure. No production code is touched.
- **The doc line** now says "back on" and keeps the ~9 Nov window note. It is one line in the owning table.

**Verdict: PASS** (`c07e721`).
