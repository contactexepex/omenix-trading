# Judge 3: DOC1 schedule status, branch `story/DOC1-schedule-status`, SHA 974978d

**FAIL (round 1), lane 1 (a rule document describing live workflows), one judge.** Text only: `CLAUDE.md` and
`README.md`, 4 lines each way.

## Criteria

| Criterion | Verdict | Evidence |
|---|---|---|
| The new wording matches the workflow files | MET | All 13 files under `.github/workflows/` have active `- cron:` lines (1-4 each). The only commented "cron" lines (`flow-history.yml:5`, `global-cues.yml:6`) are prose |
| No stale "schedules disabled" claim left in a functional document | NOT MET | `docs/GROWW_CANDLE_ROUTINE.md:88`, finding 1 |
| One owning document | MET | README now gives one line plus a pointer to `CLAUDE.md` "Ingestion workflows" |
| Gates (text-only rule) | MET | doc-reading tests: 15 passed; record scan clean on both files |

## Findings

1. **Should fix: `docs/GROWW_CANDLE_ROUTINE.md:88` still states that the workflows are disabled.** It reads "Like the
   thirteen GitHub Actions workflows ("DISABLED for migration; re-enable at cutover"), this routine is enabled at
   cutover". Leaving the routine's own "Prepared, not live" status is correct. The comparison clause, though, is a
   claim about the workflows, and it now contradicts `CLAUDE.md`. Drop the clause, or say "the workflows were
   re-enabled on 26 Oct 2026; this routine is not yet".
2. **Minor: say what is still off.** Two workflows keep one step disabled: the step that fires the Claude routine
   (`participant-oi-release.yml:95` and `participant-oi-sweep.yml:71`, both `if: false # DISABLED for migration ...
   repointed`). "Each workflow now runs on its cron schedule" is true; one clause naming these two disabled steps would
   stop a reader assuming the routine hand-off is live. (This corrects my earlier note in `judge_2_p1-story.md`, which
   called these two "jobs"; they are steps.)

## Plants

None: text-only change, judged by reading (JUDGE.md merge procedure).
