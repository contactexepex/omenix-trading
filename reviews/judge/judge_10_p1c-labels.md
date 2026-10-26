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
