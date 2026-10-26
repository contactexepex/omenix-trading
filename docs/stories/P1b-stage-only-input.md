# P1b: stage-only first dispatch for pipeline-staging.yml

Lane 1 (a workflow that calls Drive; the write-once Record). Branch `story/P1b-stage-only-input`. Follow-up to P1
(`docs/stories/P1-staging-record-split.md`). Story text first; the one workflow change follows once it is accepted.

## Problem

`pipeline-staging.yml` always runs `promote` after `stage`. `stage` writes only the Drive `staging/` area, never the
Record, so a stage-only run validates the NSE fetch, the Drive write and the staging layout with no write-once risk.
`promote` is the only step that can write the Record; its first real run is a separate owner decision.

## Claims

1. A new boolean `workflow_dispatch` input `promote`, default **false**. With it false the `promote` step does not run,
   so a dispatch only stages.
2. With `promote` true the workflow behaves as P1 left it (stage, then promote even if stage failed, then fail the run
   if stage failed).
3. `dry_run` is unchanged (CLI `--help` only, no Drive).
4. No other workflow, no schedule, no Python code and no test changes; the workflow stays `workflow_dispatch` only.

## Gap list

- No Python or test change, so no unit test covers the workflow; the check is the YAML parse in the review and the first
  dispatch (owner coordinated). The judge reads the diff (about 10 lines).
- It does not add a Record-only credential (P1 gap list: credential separation).

## Follow-up (labels and the failure signal)

Two labels made stale by the `promote` input were corrected (the `days` description and the last step's name). A failed
stage-only run posts nothing to #fno-desk, by design for now: the run is a manual dispatch, its last step exits 1, so the
run turns red in GitHub and the dispatcher sees it at once. An alert step is not added: nobody is waiting on an
unattended run. Revisit when the workflow is scheduled.
