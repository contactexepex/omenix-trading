# Judge 4: P1b stage-only input, branch `story/P1b-stage-only-input`, SHA 64faaa1

**PASS, lane 1, judge 1.** I judged the story text (f744831) first, then checked the workflow change (9712bd4) against
it. The branch diff against `main` is `.github/workflows/pipeline-staging.yml` (+6/-1) and the story file; nothing
else.

## Criteria

| Claim | Verdict | Evidence |
|---|---|---|
| 1 `promote` input, default false, skips promote | MET | Parsed YAML: `promote: (boolean, False)`; the promote step's `if:` is `!inputs.dry_run && inputs.promote` |
| 2 `promote: true` behaves as P1 left it | MET | Stage keeps `continue-on-error: true`, so the promote step's implicit `success()` still holds when stage fails. The final "fail the run" step is unchanged |
| 3 `dry_run` unchanged | MET | The dry-run step and its `if:` are unchanged; every Drive step still requires `!inputs.dry_run` |
| 4 nothing else; dispatch only | MET | Parsed `on:` has `workflow_dispatch` only. No other workflow, Python or test file in the diff |
| Gap list honest | MET | No unit test covers YAML; the credential gap (from P1) is restated |

## Findings

None blocking or should-fix. Minor, label-only (behaviour is correct):
1. The final step's name, "(the promote step has run either way)", is false when `promote` is false. Suggested name:
   "Fail the run when staging stopped".
2. The `days` input description says "to stage and promote". It should say "to stage (and promote, if set)".
3. A stage-only run that fails posts nothing to #fno-desk (only `promote` alerts), so the failure shows only as a red
   run. This is acceptable for a dispatch someone is watching; say it in the gap list if you want it on record.

## Plants

None: this is a YAML-only change with no test harness. I verified it by parsing the YAML and reading every step's
`if:` condition.

## Notes

Process: the workflow commit was pushed before the story was judged. That matters little here, because the change is
one hunk, but it is the third time story-first was not followed.
