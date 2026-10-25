# Judge 602: LR1 fetch-depth, the weekly post-mortem checks out full history (story/lr1-fetch-depth @ 44ecd6fb9)

**PASS (2 minor). Lane 1** (a workflow that calls Slack, Drive and the routine trigger). Judge F, own session
(session_01A8XfbTUVgeeEpqatHaWbtP). Labels: strong, some, reasoning only.

## Criteria

| # | Criterion | Result | My evidence |
|---|---|---|---|
| 1 | the job's checkout has the full history before G8's v4 report | MET | `postmortem-weekly.yml:46-48` `fetch-depth: 0` on step 0; the report step comes later in the same job |
| 2 | the fix is needed (the claim) | MET | on `story/v4-freeze` @ 25f6ffff9, `fno/forecast_scoring/v4/freeze_check.py` `protocol_problems` returns "shallow clone: ..." when `git.is_shallow()`, and `report` prints `FREEZE_BROKEN` with it (`v4/cli.py:58`, `wiring.py:103-110`); on main today the report reads no history, so depth 0 is harmless before the freeze merges |
| 3 | no other workflow has the same gap | MET | `grep` of `.github/workflows`: only `postmortem-weekly.yml` runs `forecast-v4-scores`; on the freeze branch `build_freeze_problems` is called only by `report` and `look` (no workflow runs `look`) |
| 4 | a test pins it | MET | `tests/learning/test_workflow_history.py`; my plants below |
| 5 | gates | MET | trial merge with main a68f77cf1 (clean): **16,069 passed, 1 skipped, 14 xfailed** (token kept); ruff, format (2,563 files), `check_imports`, `check_records` (9,163 files) clean |

## Story text (the orchestrator's question)

**Acceptable without a separate story text** [reasoning only]. The change is two YAML lines. It changes no record, no
trade, no secret and no outside call; it only gives a shallow checkout its full history, as five other workflows
already do (`checks.yml:25`, `forecast-capture.yml:72`, `forecast-scores.yml:34`, `panel-days.yml:44`,
`health-check.yml:28`). Quality rules 2-6 hold in small form:
- the one requirement is pinned by a test;
- the broken-code proof is the builder's plant plus mine;
- good and bad cases: depth 0 passes, depth 1 or 2 fails;
- the reason is in the commit and in the test's docstring.

A text round would add a cycle and nothing checkable.

## Minor

1. Record it in `docs/stories/LR-learning.md` (one line under LR1: the reason, the test, the commit) when that file is
   next touched, so the reason lives with the story and not only in the commit.
2. Rule 8, end to end: the first Saturday build after `story/v4-freeze` merges (10:41 IST) must print the freeze
   intact, not "shallow clone". Until the freeze merges, the 31 Oct run shows only that the job still runs.

## Plants

5 planted, one at a time, each restored: **5 caught**. They were: `fetch-depth: 1`; `fetch-depth: 2`; the `with:`
block removed; the checkout moved after the report; the v4 report step removed.

## Notes

- `fetch-depth: 0` costs only clone time on a 30-minute job. The repository's other full-history jobs run the same way.
