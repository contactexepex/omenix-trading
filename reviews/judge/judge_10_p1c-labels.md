# Judge 10: P1c stage-only labels, branch `story/P1c-stage-only-labels`, SHA f1d71af

**PASS, lane 1 (a workflow that calls Drive), judge 1.** Diff against `main`: `.github/workflows/pipeline-staging.yml`
(2 label lines) and `docs/stories/P1b-stage-only-input.md` (+8 lines).

| Check | Verdict | Evidence |
|---|---|---|
| Labels only; no behaviour change | MET | Parsed YAML: `workflow_dispatch` only; every step's `if:` is the same as at P1b (`!dry_run && promote` on promote) |
| `days` description accurate | MET | "to stage (and to promote, when the promote input is on)" |
| Last step name accurate | MET | "(when promote is on, the promote step has run either way)" |
| No alert for a failed stage-only run: reason stated | MET | P1b story "Follow-up": it is a manual dispatch, the run turns red, and an alert would need the Slack secret in a Drive-only step; revisit when scheduled. Reasonable, and recorded as a decision |

Findings: none. Plants: none (labels and text only; checked by YAML parse).

## Addendum 1: correction to my PASS on f1d71af

**My PASS was wrong on one criterion; P1c is now FAIL until the story text is fixed.** The P1b story's reason for not
alerting, that an alert "would need the Slack secret in a step that today holds only the Drive ones", is false.
`FNO_SLACK_BOT_TOKEN` is set in the job-level `env:` of `stage-and-promote` (`pipeline-staging.yml`, job env, next to
the four Drive settings), so every step already holds it. I accepted the reason without checking it; judge #2 caught
it, and I have now verified it myself. The label fixes themselves are still correct. The fix expected: restate the
reason truthfully (for example, a manual dispatch whose red run the dispatcher sees, revisited when scheduled), or add
the alert.

## Addendum 2: SHA ebfafca

**PASS.** f1d71af..ebfafca changes only the P1b story's follow-up paragraph (-3/+2 lines). The false Slack-secret
clause is deleted. The remaining reason (a manual dispatch, a red run the dispatcher sees, nobody waiting on an
unattended run, revisit when scheduled) is true. The workflow is identical to f1d71af, which I verified in round 1:
labels only, every step condition unchanged.
