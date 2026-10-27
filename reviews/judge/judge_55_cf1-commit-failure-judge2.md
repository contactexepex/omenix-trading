# Judge 55: CF1 commit-failure signalling, code (one judge, judge #2)

Branch `story/CF1-commit-failure-signalling`, SHA `d94db2979758e88382ac22cde6d185ca0d849f97` (characterisation
`62f5af0`, then the change). Lane 1. **FAIL** (round 1) on 2 small should-fix: one tightens a test, one corrects the
story text. The helper and its seven caller paths hold every plant in both directions.

## Gates (`__pycache__` cleared)

882 passed; ruff check and format clean; imports clean; code size passed.

## 1. No false red

`commit_failed` is `" NOT committed" in line`, and that mark is read from the `NOT_COMMITTED` template itself.
- The pushed line (`COMMITTED_AS`, "committed and pushed") and the empty line (`NOTHING_AS`, ": nothing new to
  commit") cannot contain it.
- Labels are fixed constants, and the `reason` text appears only inside the `NOT committed` line.
- So a real success or empty-diff line cannot be classed as failed: MET, by construction.
- The caller tests feed the three real lines from a throwaway git repository.
- Over-matching plants fail: the mark "NOT" fails 9 tests, the mark "committed" fails 23.

## 2. No false green: every edited caller is pinned

| Plant | Failed |
|---|---|
| any -> all / no alert / code not raised / a second alert | 2 / 10 / 8 / 9 |
| bypass in: librarian / data-snapshot / revisions sweep / promote, the refused sign-in / promote / nsdl-backfill / intraday rv / intraday report | 1 each |

**But there is one failed-commit path that still exits 0 (F2).** It is outside the edited callers, but it contradicts
the story's "the only uncovered case" claim.

## 3. Single definition, no over-match

The mark does not match the sync's "NOT pulled or committed" (it lacks " NOT committed" as written), "NOT archived" or
"NOT promoted". The intraday committer builds its failure line from the same `NOT_COMMITTED` template, so it is
matched. MET.

## 4. The guard test

It is not vacuous: it finds 8 or more real pairs and checks the exact P2d shape, and a masked pair planted in
`ops/commit_news_record.sh` fails 4 tests. **But three masked shapes slip past it (F1).**

## Findings

1. **F1 (should fix, test only): the guard misses three masking shapes.** Run through its own `problems()` (scratch
   script, not committed):
   - a pair split by a line continuation (`git pull ... && \` then `git push ...`, then `exit "$broken"`): slips;
   - `git pull ... && git push ... || true` as the last line: slips, though `|| true` makes the step green whatever
     happens;
   - `git pull ... && git push ...; exit 0` on one line: slips.

   None of these is in the repository today; I grepped for all three. But the guard exists to stop the pattern coming
   back, and `|| true` is the most likely "quick fix" someone would write. Fix:
   - join `\` continuations before scanning;
   - flag a pair followed on its line by `|| true`, `|| :`, `; exit 0` or `; true`;
   - add a test case for each shape.
2. **F2 (should fix, story text, or a ruling): the intraday sync's foreign-staged refusal is a failed commit that
   ends green.** `GitLedgerSync.commit` returns `FOREIGN_STAGED` ("... NOT pulled or committed: N file(s) staged that
   are not the recorder's ...") instead of committing (`intraday/sync.py:48-61`). `recorder._close` appends it to the
   outcome's lines without changing the status (`recorder.py:226`), and CF1 deliberately does not match it. So that
   run exits 0 with the rows not committed. It is alerted once per run by the sync itself, so it is not silent, but it
   is green. The story's honest-limit statement (the only uncovered case is a crashed commit step) is therefore not
   accurate. Either:
   - (a) the orchestrator rules it stays green-with-alert and the story names it as the second uncovered case; or
   - (b) intraday's report also treats the `FOREIGN_STAGED` line as a commit failure (exit 1, with the sync's alert
     counted as the one alert).

   I lean to (b): CF1's own rationale, "a green run with a failed commit is a silent failure", applies to its exit code
   just as much.

## 5. The honest limit (a crashed commit step)

Confirmed red. In `run_librarian`, `cmd_promote` and `cmd_data_snapshot` the commit runs in `finally`; if the run or
the commit raises, the exception propagates past `return exit_for_commit(...)`, so the process exits with a
traceback, non-zero. Together with F2, that is the complete list of uncovered cases I found.

**Verdict: FAIL** (round 1). F1 is a test-only tightening; F2 is a ruling plus story text, or a small intraday change.
