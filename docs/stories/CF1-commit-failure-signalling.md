# CF1: a failed manifest commit must not end a run green (PLAN)

PLAN for the orchestrator's check before any code. Lane 1, **two judges** (a behaviour change on the commit and alert path of several LIVE
scheduled workflows). Found by the P2d judges' F1 finding and my audit of every `.commit(` and `.publish(` caller: a `git pull && git push`
masked by a later command is gone (P2d fixed the one instance); this story closes the other half of the same class, in Python.

## The problem

`GitManifestRecorder.commit` never raises: on a failed pull or push it returns a line `"<label> NOT committed: <step> failed: ..."`. Seven
callers read that line and fail (preopen, close-read, receipt repair, fo-masters, circulars, flow-history tables, filings via
`problem_of`), and claims read it structurally. **Four callers print it and ignore it in their exit code:**

| Caller (command) | Used by | Today's exit code comes from |
|---|---|---|
| `run_librarian` (`data-librarian`) | flow-history, index-closes, participant-oi-release | the fill report |
| `cmd_data_snapshot` (`data-snapshot`) | flows-download | the snapshot result |
| `cmd_data_revisions` sweep (`data-revisions`) | flow-history, index-closes | revisions stored, unanswered, stopped |
| `cmd_promote` (`promote`) | pipeline-staging (manual) | `report.complete` |

Plus two to decide: the intraday recorder (its `sync.commit` line is appended to the outcome lines; the exit code comes from
`outcome.status in GOOD_OUTCOMES`, so a failed sync is ignored too; it runs in Groww routine containers, not workflows) and `nsdl-backfill`
(a hand command, no workflow). Effect, as far as I can tell: Drive saved the file, the manifest rows lived only in the runner checkout and
were lost, the run was green and silent; the coverage check and receipt repair recover them later. **Recoverable but silent, which this project forbids.**

## The fix

- **One definition.** `manifest_commit.commit_failed(line) -> bool` next to the `NOT_COMMITTED` template it reads (the marker is derived
  from the template, so they cannot drift), and `exit_for_commit(line, code, send_alert)` returning `max(code, 1)` and sending ONE
  #fno-desk alert (the fixed line, counts and codes only) when the line is a failure; unchanged when it is not.
- **Callers:** the four above call it; the intraday recorder and `nsdl-backfill` too if the characterization confirms they ignore the line
  (reported either way). The seven existing callers keep their own `" NOT committed"` constants, because swapping them is a separate
  behaviour-preserving refactor; a test pins that each equals the helper's marker, so a changed template cannot silently disable one.
- **Not touched:** what a caller prints, its other exit conditions, the committer itself.

## Order of work (one judge-flight)

0. **Characterization first, on today's code (as for R1d):** per caller, a normal commit gives today's exit code, AND a "NOT committed" line
   gives the SAME code (this pins the bug). Merge-independent; plants prove the pins bite.
1. The helper and the callers, with the opposite assertions: a normal run still exits as before (**no live run turns red**) and a
   "NOT committed" line exits 1 with exactly one alert. Plants: the failed line ignored, the success line treated as failure, no alert, two alerts.
2. The guard test I proposed and the orchestrator approved: scan `.github/workflows/` and `ops/` for a `git pull ... && git push ...` that is
   not the last command of its run block (retry loops that end in `exit 1` are the stated exception), so the masking pattern cannot return.

## Risks, said plainly

- **The fix may turn a currently green run red.** If a push has been failing silently on a live job, it becomes visible on its next run. That is the
  fix working, and the owner should be told in those words, not discover it.
- **A false failure would be worse than none.** A success line must never match; the test uses the real committer's success and "nothing new to
  commit" lines, not strings I invented.
- **Groww rule:** the intraday recorder is a Groww caller. I run no Groww command by hand and no recorder; the change is exercised by pytest only.

## Gates

Full suite, ruff, imports, numbers, size, record scan; characterization pins per caller; mutation plants for every line above; two judges.
