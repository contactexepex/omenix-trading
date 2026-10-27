# Judge 64: CP1 pause the circulars cron (code), round 1 at 8297459: PASS

**Lane 1, one judge (judge #1)** (a schedule that calls an outside service). Branch `story/CP1-pause-circulars`, frozen SHA 8297459, merge base d4a71cb. The owner's decision was relayed by the orchestrator (27 Oct).

## Scope (strong evidence)
Three files and nothing else (`git diff --stat`):
- `.github/workflows/circulars.yml`: the `schedule:` block becomes a comment that says why and how to re-enable it; `workflow_dispatch` and its `dry_run` input are kept, and the job is untouched.
- `docs/RUN_LOCATIONS.md`: the circulars row says PAUSED.
- `tests/test_circulars_paused.py`, a new file.

No other workflow is touched.

## Checks (strong evidence)
- `yaml.safe_load` gives triggers `['workflow_dispatch']`, inputs `['dry_run']` and jobs `['circulars']`. There is no `schedule` key, so there is no empty schedule for GitHub to reject.
- Gates: ruff, format and check_imports are clean; 1158 passed; `check_numbers` is clean.
- Plants:
  - schedule restored (uncommented) → 2 failed;
  - an empty `schedule:` key added → 1 failed.

## Why the pause loses nothing yet, and when it starts to (some evidence: code read, dates inferred)
- Failing runs already capture nothing: they fail closed with "no receipts under it". Pausing them stops red runs and alerts and loses nothing compared with running them.
- **NSE:** every run asks 14 days back (`circulars/capture.py:18`, `WINDOW`). A gap of up to 14 days is recovered by the first green run.
  - `receipts/data/` holds only `vix`: no circulars receipt has ever been committed. Runs have been red since at least 26 Oct.
  - So the first green run must happen by about **9 Nov 2026**. After that, NSE circulars from the start of the gap fall out of the window and are lost from capture.
- **SEBI:** its page lists 25 circulars. A long enough pause can push some off the page.
- **In every case:** the "first seen" time recorded for anything issued during the pause will be the resume time, not the publication time. This is the data-quality cost of the outage, not of the pause.

## Recommendations (not blocking)
1. Make the deadline impossible to miss. For example, the pin test could fail after 2026-11-07 ("the pause outlived the NSE 14-day window; re-enable or decide"), or the deadline could go in the workflow comment and RUN_LOCATIONS. Today nothing forces the re-enable.
2. CLAUDE.md says "each workflow now runs on its cron schedule". With circulars paused that is no longer true. A one-line note, or a link to RUN_LOCATIONS, would keep the rule doc true. This is a rule-document change, so it is the orchestrator's call.

## Hard lines
No order path, no secret, no Groww call, and no change to a recorded file or a receipt.

## Verdict: PASS round 1 at 8297459
