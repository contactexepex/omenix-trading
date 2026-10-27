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

## CF1 as built

- **The definition** (`storage/manifest_commit.py`): `NOT_COMMITTED_MARK`, read from the `NOT_COMMITTED` template (so it cannot drift from the
  message), `commit_failed(line)` and `exit_for_commit(lines, code, send_alert, what)`. True only for the committer's own "NOT committed"
  line; False for "committed and pushed", for "nothing new to commit" and for other lines that say "NOT" (the intraday sync's foreign-staged
  line has its own once-per-run alert and is deliberately not this signal). Tests use the three REAL lines, made by the real committer in a throw-away
  git repository (`tests/ingestion/commit_failure/real_lines.py`), never a string written by hand.
- **Callers changed:** `run_librarian` (`data-librarian`), `cmd_data_snapshot`, `data-revisions sweep`, `cmd_promote` (including its refused-sign-in
  path), `nsdl-backfill`, the intraday `report` and its `rv` path. A crash is red already, so the commit is still made in a `finally` and the
  signal applies to the normal and the stopped paths. The seven callers that already read the line are untouched; a test pins that each keeps a marker
  that matches the failure line and neither of the other two.
- **Live workflows whose exit code can now change, only on a failed commit line:** `flow-history.yml` (`data-librarian`, `data-revisions`),
  `index-closes.yml` (`data-librarian`, `data-revisions`), `participant-oi-release.yml` (`data-librarian`), `flows-download.yml`
  (`data-snapshot`). Manual: `pipeline-staging.yml` (`promote`). The intraday recorder runs in Groww routine containers, not workflows; no Groww
  command was run, the change is exercised by pytest only.
- **Proof:** per caller, both directions on the real lines: a pushed commit and an empty diff leave the exit code exactly as it was, with no
  alert; a failed commit gives exit 1 and exactly one alert (promote and nsdl-backfill also keep their own problem alert, so two when both occur;
  the intraday recorder sends one for a whole run however many marks failed). The guard test (`tests/test_no_masked_pull_push.py`) scans every
  workflow and `ops/` script and is shown to catch the exact pattern of the P2d F1 finding and to accept the two safe shapes. Plants fail a test for:
  the mark, "any" turned into "all", the alert removed, the exit code lowered, and the helper bypassed in each of the seven edited paths.
- **Guard test blind spots closed (judge 55 F1):** a `\` continuation is joined before the scan, and a pair followed by `|| true`, `|| :`,
  `; exit 0` or `; true` is flagged even as the last command; one case each.
- **Named as uncovered (judge 55 F2, awaiting the orchestrator's ruling):** the intraday sync's FOREIGN_STAGED refusal ("NOT pulled or committed":
  another writer staged files, so the recorder pulled and committed nothing) still ends green. It is not silent: the sync posts its own alert once per
  run. Counting it as a failure would change a Groww routine's exit code for a case already alerted; I recommend leaving it named here.
- **Not done, listed:** swapping the seven already-correct callers to the helper (a later behaviour-preserving refactor); failing a run when the
  commit itself crashes (it is already red); the Python committer's other callers' own alert wording.

## Gates

Full suite, ruff, imports, numbers, size, record scan; characterization pins per caller; mutation plants for every line above; two judges.
