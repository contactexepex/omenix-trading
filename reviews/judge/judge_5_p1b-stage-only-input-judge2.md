# Judge 5: P1b stage-only input (judge #2)

Branch `story/P1b-stage-only-input`, SHA `64faaa1dbaf0ffa2921a7bc4fb937277c881b065`: story `f744831`, workflow
`9712bd4`. **PASS**, lane 1. The story text was judged first, against P1's gap list and the owner's go/no-go on the
first real promote. Then the diff.

## Criteria

| Claim | Verdict | Evidence |
|---|---|---|
| Story text: scope, gap list | MET | One input; "no unit test covers the workflow" is honest; the credential gap is restated from P1 |
| 1: `promote` is a boolean, default false; off means stage only | MET | YAML parse: `type: boolean, default: False`. Promote step `if: ${{ !inputs.dry_run && inputs.promote }}`. `inputs.*` keeps its boolean type for `workflow_dispatch` (not `github.event.inputs`, which is a string) |
| 2: on means P1 behaviour | MET | Stage keeps `continue-on-error`. The fail step's `if` is unchanged (`steps.stage.outcome != 'success' && !inputs.dry_run`), so a failed stage still fails the run whatever `promote` is |
| 3: `dry_run` unchanged | MET | The dry-run step and its `if` are untouched |
| 4: nothing else changes | MET | `git diff origin/main...HEAD --stat`: this workflow (+6/-1) and the story only. Triggers: `['workflow_dispatch']` only; no schedule |
| Merged P1 code is what was judged | MET | `git diff be69c3a a6a502f -- fno tests .github` is empty |

Gates on the branch (it has a `.yml` change, so the full set): 235 passed; `ruff check`, `check_imports`,
`check_numbers`, `test_code_size` clean; record scan clean on both files.

## Findings

None blocking or should-fix.

## Minor

1. The last step's name still says "(the promote step has run either way)". That is no longer true when
   `promote` is false. The `days` input description says "to stage and promote". Fix the wording on the next touch.

## Plants

None in code (a workflow condition, no test harness). Checked by reading and by parsing: with the gate removed, the
promote step would run on every non-dry dispatch; with `github.event.inputs.promote` used instead, the string "false"
would be truthy. Neither is the case here.

## Notes

1. A stage-only run writes no Record file, manifest row or revision (`cmd_stage` commits nothing). It still holds the
   owner Drive credential that can write `raw/`; that is the P1 gap, not new.
2. The first `promote: true` dispatch is still the owner's go/no-go. I trigger nothing.
