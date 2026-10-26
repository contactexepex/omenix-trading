# Judge 11: P1c stage-only labels (judge #2)

Branch `story/P1c-stage-only-labels`, SHA `f1d71afb84424a499e9993eee414ab3aec90605c`; `pipeline-staging.yml`
(labels only) plus the P1b story. **FAIL** (round 1), lane 1, on one should-fix: a false statement in the story. The
workflow change itself is correct.

## Criteria

| Item | Verdict | Evidence |
|---|---|---|
| Labels fixed (`days` description, last step name) | MET | diff: 2 strings |
| Behaviour unchanged | MET | YAML parse: every step's `if` is identical to the P1b I passed; triggers `['workflow_dispatch']` only |
| "No alert on a failed stage-only run" decision documented | MET (the decision) | A manual dispatch whose last step exits 1 shows red to the dispatcher. That is reasonable until the workflow is scheduled |
| The decision's stated reasons are true | **NOT MET** | finding 1 |

Gates (a `.yml` changed, so the full set): 235 passed; `ruff check`, `check_imports`, `check_numbers`,
`test_code_size` clean; record scan clean on both files.

## Findings

1. **Should fix: the P1b story says an alert step "would need the Slack secret in a step that today holds only the
   Drive ones". That is false.** `FNO_SLACK_BOT_TOKEN` is in the **job-level** `env` of `stage-and-promote` (YAML
   parse: the job env holds the four Drive settings and `FNO_SLACK_BOT_TOKEN`; no step has its own `env`), so every
   step, `stage` included, already holds it. Fix: delete that clause. The remaining reason (a manual dispatch, a red
   run, nobody waiting on an unattended run) carries the decision on its own.

## Notes

1. Least privilege (not a finding): because the env is job-level, the `stage` step holds the Slack token although it
   never posts. Moving the Slack token to the promote step's own `env` would narrow it. That is the owner's call;
   with the accepted shared Drive credential it is a small gain.
2. H1 is withdrawn; DOC2 is at round 2 (judge 9, Addendum 1).
