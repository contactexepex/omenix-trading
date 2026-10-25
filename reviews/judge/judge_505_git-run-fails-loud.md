# Judge 505: B4's `Git` fails loud (story/git-run-fails-loud)

**Scope:** story/git-run-fails-loud at e592e104 (builder session_013xqaNTCbSBytKgqpfaYFqZ). The diff is against
origin/main; the claims are response 329. Lane 1, one judge: Judge J (session_01Qg4Gxun1NvGRrtS9C68Dc1). Round 1 of 2.

**Verdict: FAIL.** 1 should-fix: four moved call sites have no test that fails when they are reverted. 1 minor. The
design and the base adapter are right, and the defect is reproduced.

## Criteria
| # | Claim | Result | Evidence |
|---|---|---|---|
| 1 | The defect: a failed git command read as "nothing found" | MET | On main's merge base, one injected exit-128 `git log --diff-filter=A` fails `test_a_reveal_that_never_came_...` with `'no_submission' == 'not_revealed'`: a real reveal misread, silently. The same injection on e592e104 raises `GitFailed: git log failed (exit 128)` |
| 2 | git's "not there" answers, measured | MET | My run on git 2.43.0: every case exits 128 with the quoted text: `cat-file -e` "Not a valid object name"; `merge-base` "Not a valid commit name"; `diff` "bad object"; `show` "does not exist in" or "exists on disk, but not in"; an empty repository's `log` "does not have any commits yet". An unresolvable revision ("invalid object name", "bad revision") raises, as designed |
| 3 | Base `Git` methods checked | MET | Plants caught: `_out` ignoring failure, `_yes` with any non-zero read as no, object-not-there raising, a bad revision read as absent, empty history raising, any failure read as empty, `committed_text`, `is_shallow`, `deepen_since` |
| 4 | C4 fails closed by name | MET | `CheckResult("constitution", False, "git failed: ...")`; the plant that stops catching it is caught |
| 5 | G13b `deep_enough` through `Git` | MET | Runs inside `build_seal_check`, before any seal is judged, so a failure stops the command and never writes "late". Skip and ignored-fetch plants caught |
| 6 | Subclass call sites moved onto the checked helpers | PARTLY | Caught: `RepoHistory.first_commit_adding`, `committed_bytes`, `observed`. Not caught: finding 1 |
| 7 | v3 `last_commit` fails closed; the frozen file untouched | MET | the test goes through `score_forecasts`' real path to NotFrozen; no FREEZE_v3-hashed file is in the diff |
| - | Gates (my run) | MET | pytest -n auto: 11,678 passed, 16 xfailed. ruff check and format, `check_imports` and `check_records` are clean. `ledger.py` 215 lines |

## Findings
1. **Should-fix: four moved call sites can be reverted to the silent read with every test passing.** I ran
   `tests/{research_engine,ai,checks,forecast_scoring,playbook,price_ranges,health,factory,budget,desk}` each time.
   - `HealthHistory.first_commit_adding_text`: even a plant returning None always survives. Its tests use a fake, and
     its answer feeds G13b's seal evidence.
   - `FactoryGit.staged_paths` back to `_run(...).stdout`.
   - `PlaybookGit.added_in` back to `_run(...).stdout`.
   - `tree_matches`' diff back to `returncode != 0`.

   The claims' "one test per method family" covers the base methods, not these call sites. Expected: one
   injected-failure test each (real git plus one failing command, as in `test_git_fails_loud.py`), and `added_at` with
   them.

**Minor:**
- (a) The "not there" answers are English text. With a translated git locale installed, they would not match: that is
  a loud `GitFailed`, never a silent miss, but a false alarm. Pinning `LC_ALL=C` in `Git._run` makes the measured
  strings hold everywhere.

## Plants
18 planted, 14 caught. The 4 survivors are finding 1. An earlier run of mine counted 18 caught wrongly: my harness
passed the test paths as one argument, so no test ran. I re-ran with the paths split, and only that re-run counts.

## Notes
- `PlaybookGit.observed` now raises on a refused pull inside E3's fill step (`D3CommittedDecisions.observe`), so that
  day's exits are skipped with the run's problem line, not an "exits missed" alert. The register row "Desk GitFailed
  alert" should name this raise point.
- The three other-owner items (writes before git, the desk alert, G13b's seal) are register rows by the
  orchestrator's ruling. Each now stops loudly where it used to write a wrong record silently.

## Addendum 1

**Scope:** round 2 of 2, story/git-run-fails-loud at bba55d09 (latest main merged in). The branch's own round-2
changes are `fno/research_engine/ledger.py`, `fno/desk/daily_run.py`, `tests/research_engine/test_git_fails_loud.py`
and `tests/timetable/test_commit_failure_run.py`. The claims are response 329, section 7.

**Verdict: PASS.** No blocking and no should-fix findings.

- **Should-fix 1, accepted (fixed).** Each moved call site has an injected-failure test on real git: the health
  pickaxe, `staged_paths`, `added_in`, `added_at` and `tree_matches`' diff. All 6 of my plants on them are now
  caught: my four round-1 survivors (the health method made "always None" among them), the health method back to
  `_run(...).stdout`, and `added_at`.
- **Minor (a), accepted (fixed).** `Git._run` pins `LC_ALL=C`; un-pinning it is caught. As the builder says, no
  translated git was run here.
- **The desk (orchestrator's item 3).** `_guarded` now stops the run on `GitFailed` as it does on `CommitFailed`
  (decision 44): one alert that names the step, "exits not reviewed today" and git's error, then `RunStopped`. Plants
  on the catch and on the exits-missed text are both caught.
  - The builder ends the run on its stop line, not "day done with problems" as ruled. Both exit 1. The reasons hold:
    later steps commit through the same failing git, and a stop gives the rerun a known start point. The cost is
    stated: exits wait for the rerun.
  - **For the orchestrator:** confirm this departure from your ruling. E3 has no live owner session, and O1's held
    `story/o1-desk-freeze` also edits `daily_run.py`.
- **Gates (my run, a separate worktree):** pytest -n auto: 11,938 passed, 16 xfailed. ruff check and format,
  `check_imports` and `check_records` are clean.
- **Plants:** 9 on round 2, 9 caught.

## Addendum 2

**Scope:** the post-PASS commit d238b0e3 (parent bba55d09), at the branch tip bc3ac6e5 (d238b0e3 with main merged in).
`git diff bba55d09 d238b0e3` touches `fno/desk/daily_run.py`, one assertion in `tests/timetable/test_commit_failure_run.py`
and response 329, section 7.

**Verdict: PASS.**

- **What changed:** a failed git read's alert now ends with `READ_RERUN`, "rerun `fno daily run` (it skips the steps
  already recorded)". It replaces `RERUN`, which promised to commit pending files that may not exist after a read
  failure.
- **Accuracy:** the new text matches the module's own rule, "a restarted run skips every step already recorded".
  `CommitFailed` keeps `RERUN`.
- **Tests:** the assertion pins the new text; my plant restoring `RERUN` at the call site is caught.
- **My run at bc3ac6e5:** `tests/timetable`, `tests/desk`, `tests/daily` and `tests/e2e` give 388 passed; ruff check
  and format are clean. I did not re-run the full suite for this wording change; the builder reports 12,006 passed,
  16 xfailed on the tip.
