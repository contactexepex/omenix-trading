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

## Addendum 1: round 2, a34b886 (PASS)

SHA `a34b886318c4f09d55081f2894637b7386d4daab`. The only changes since `d94db29` are in
`tests/test_no_masked_pull_push.py` and the story. **Gates** (`__pycache__` cleared): 883 passed; ruff check and
format clean; imports clean.

**F1: my three shapes are caught.** Run through `problems()` (scratch script, not committed):

| Shape | Result |
|---|---|
| A `\` continuation, then `exit "$broken"` | flagged |
| A `\` continuation as the last command | accepted (safe) |
| `\|\| true` / `\|\| :` / `; exit 0` / `; true` | each flagged |
| `\|\| exit 1` last / the retry loop | accepted (safe) |

The implementer reports that plants dropping the swallowed check or the continuation join fail the tests.

**One shape still slips, same class (a non-blocking recommendation):** `git pull ... && git push ... || echo failed`
as the last line is accepted. `echo` exits 0, so the step is green whatever happens, exactly like `|| true`. The
guard lists endings that swallow a failure, and any always-succeeding command after `||` (`echo`, `printf`, `logger`)
gets past it. Nothing of the kind is in the repository today. Recommended follow-up: invert the rule to an allow
list. After a pair, the line may carry only nothing, or `|| exit <non-zero>`; anything else is flagged. That closes
the whole class. I do not block on it: CF1's code is sound, every shape seen so far is caught, and the repository is
clean today.

**F2: resolved as option (a).** The story names the `FOREIGN_STAGED` refusal as uncovered: it ends green, and it is
alerted once per run by the sync itself. The implementer's reason is sound: counting it would change a Groww
routine's exit code for a case that is already alerted. The story's limits are now accurate. If the orchestrator rules
(b) instead, that is a separate small change.

**Verdict: PASS** (lane 1, CF1, judge #2).

## Addendum 2: 4f9d6b1, F2 built as option (b) (PASS)

SHA `4f9d6b1fef5f526ab39e3d99090a1ad2190944a7`, which replaces `a34b886`. The implementer reports that the
orchestrator ruled F2 option (b). The orchestrator's last message to me said (a). Either way, this SHA is sound, and
the difference is the orchestrator's to confirm.

The change: `FOREIGN_STAGED_MARK` is read from the sync's own template (" NOT pulled or committed"), and
`refused_for_foreign_staging(line)` uses it. Intraday `report` and the `rv` path now exit at least 1 when the refusal
line is present, with no second alert (the sync alerts once per run). **Gates** (`__pycache__` cleared): 888 passed;
ruff and imports clean.

| Plant | Failed |
|---|---|
| The mark returns False / the mark widened to " NOT" / the exit not raised | 3 / 1 / 2 |
| An extra alert / the `rv` path bypasses the new check | 3 / 1 |
| Carried: the committer mark widened to "NOT" | 11 |

The no-false-red, no-false-green and single-definition properties all still hold. The committer's mark still matches
only its own line, and the sync's mark is a separate, explicit second signal.

**Text nit for the merge:** the story says "the only green-without-commit case is a crashed commit step (it is red
already ...)", which contradicts itself. It should read "the only not-committed case without a commit alert is a
crashed commit step, which is red from its traceback."

**Verdict: PASS** on `4f9d6b1` (lane 1, CF1, judge #2), and on `a34b886` if (a) stands.
