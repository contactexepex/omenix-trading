# Judge 28: R1b2 persisted pause (code), branch `story/R1b2-code`, SHA c3b50d8

**FAIL (round 1), lane 1, judge 1; 1 should-fix, nothing blocking.** 29 files: `LayeredLog`, `NsePacer.attach` plus the
live-window probe, `CircuitBreaker.check(force_probe)`, `pause_memory.py` wired from `main`,
`ops/commit_pause_log.sh`, and the new last step in 13 workflows. The design is implemented faithfully; one guarantee
is untested.

| Check | Verdict | Evidence (my own runs, in a separate worktree) |
|---|---|---|
| Gates | MET | 484 passed; ruff, check_imports, check_numbers, code size and format clean; `tests/characterization/` untouched (`git diff --quiet`) |
| The step: last, always, never fails the run, never without the record scan | MET | YAML parse: in all 13 workflows (not `data-checks`) it is the **last** step, `always() && !inputs.dry_run`, `continue-on-error: true`. The script sets `core.hooksPath .githooks` before any commit and never uses `--no-verify` |
| B1 git tests are genuine | MET | The bare origin plus two clones show: (a) a dirty log blocks `git pull --no-rebase` (the old design); (b) with rows pending only in the ignored file, the committer's pull succeeds and the step then merges rows once, header once |
| `check(force_probe)` | MET | One condition in `check`; once per host per process (`_Host.forced`); clean |
| Live set (8) | MET | Pinned by a test; dropping `preopen record` fails it |
| The 0.04 to 0.03 s timing change | ACCEPTED | Still meaningful: with spacing removed (a plant) the threads start 0.0 s apart and 4 tests fail; 0.03 s against a spacing above it only absorbs scheduler noise |
| Plants | 18 of 19 caught | LayeredLog writing or ignoring the committed file; `force_probe` ignored; unlimited forced probes; live window never or always; no log or alerts on the breaker; restored-message text; no spacing; the script without its dedupe, header guard, hooks path, local-file removal or pull; the workflow step without `always()` or `continue-on-error`. **Survivor: finding 1** |

## Findings

1. **Should fix: the production clock is not tested to be UTC.** Plant: `self._wall = wall_clock or self._derived_wall`
   (so the default `NsePacer()`, which is `SHARED_PACER`, uses `EPOCH + monotonic`). All 484 tests pass. The tests
   inject a `wall_clock`, so the default that the live workflows use is never checked. That default is the whole point
   of S1. With the regression, the committed log would carry year-2000 timestamps, and every restored pause would read
   as long expired: persistence silently off. Fix: a test that `NsePacer()`'s and `SHARED_PACER`'s wall clock is real
   UTC (within seconds of `datetime.now(UTC)`).

Minor:
- `commit_pause_log.sh` commits only the log, but `git push origin HEAD:main` also pushes any earlier local commits that
  failed to push. They were all made under the record scan and meant for `main`, so that is benign, but say it in the
  script's comment.
- The "old design" test uses `git add -N` on a new file. A case where the file is already tracked and modified would be
  the closer reproduction, but both show the refusal.

## Addendum 1: SHA 53c6478 (round 2 of 2)

**PASS, lane 1, judge 1.** c3b50d8..53c6478 changes only tests (3 files), a comment in `ops/commit_pause_log.sh`
and the story. `git diff c3b50d8 53c6478 -- fno .github ops` shows only the 2-line comment, so behaviour is
unchanged.
- **Finding 1 FIXED, and the test fails closed.** My plant (`self._wall = wall_clock or self._derived_wall`) now
  fails 1 test.
- **Minors FIXED.** The push note is in the script, and the tracked-and-edited reproduction of the refused pull is added.
- **Judge #2's S1 wiring tests catch breakage.** Replacing `attach_pause_memory(...)` in `cli.main` with `pass` fails
  4 tests.
- Gates: 490 passed; ruff, check_imports, check_numbers and code size clean; `tests/characterization/` untouched.
