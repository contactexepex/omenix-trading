# Judge 474: O1-publish-branch, every run publishes to main (story/o1-main-branch at 67b3539a)

**Verdict: PASS. Lane 1 (schedules and outside services). Round 1 of 2. Merge go, before Fri 08:36 IST.** No
should-fix. Two notes. Main is red on 3 tests that fail without this change too (below).

## Criteria
| Criterion | Result | Evidence |
|---|---|---|
| Fetch, unshallow, pull, compare and push all target main, never the checkout's branch | MET | `Git.target = PUBLISH_BRANCH` in `unshallow`, `push`, `unpushed`, `unpushed_files`; `GitCommitter._commit` and `_push`; `daily_wiring`'s pack pull; `GitDecidedRuns`; `PlaybookGit.observed`. `Git.branch()` is removed, and no `abbrev-ref` caller is left in `fno/` or `tools/` (git grep) |
| A checkout on an unpublished branch commits and pushes to origin main, and publishes nothing under its own name | MET | `test_session_branch.py` on real repos; the builder reproduced today's "couldn't find remote ref" on the old code |
| Decided runs and the playbook read main | MET | test 3; plants P3 and P4 are caught |
| Every other committer already targets main | MET | `manifest_commit.TARGET_BRANCH`, `numbering BRANCH`, `ai/transport BRANCH`, `intraday/heartbeat` (default "main"), `price_ranges/wiring` (fetches "main"): git grep finds no other push, pull or fetch of a computed branch |

## Plants: 7 planted, 6 caught
| Plant | Caught |
|---|---|
| P1: push to the checkout's branch | yes (2 failed) |
| P5: `unpushed` compares the checkout's branch | yes (2 failed) |
| The committer's pull uses the checkout's branch | yes (2 failed) |
| P3: `PlaybookGit.observed` pulls the checkout's branch | yes (1 failed) |
| P4: `GitDecidedRuns` fetches the checkout's branch | yes (1 failed); my first version of this plant fetched origin's HEAD, which is main, so it changed nothing and I re-planted it |
| P2: the pre-commit pull removed entirely | **no**, see note 1 |

## Gates
Trial merge with main at 64ea6be4 (removed):
- ruff check, format, check_imports and check_numbers are clean;
- pytest: 9,820 passed, 16 xfailed, 3 failed.
  - All 3 also fail on plain main 932c8d81, without this change: `factory/test_repository_records` (trial count),
    `research/test_ledger_guard`, and `forecast_v4_rules/test_v4rules_phase2` (a G7 record row with no method hash).
  - The builder reported 2 of them; the third is new on main since its run.
  - None touches the changed files. They are main's, for the main steward.

## Notes (not blocking)
1. **`test_a_session_branch_pulls_main_before_it_commits` does not prove "before".** With the pull before the commit
   removed, the test still passes: the push is refused, and `_push`'s retry pulls main and pushes again. The outcome
   the test checks (both writers' commits on main) holds either way, and the target of that pull is covered by the
   third plant. Assert that no push was refused, or rename the test.
2. **"main" is now a constant in five places:** `PUBLISH_BRANCH`, `TARGET_BRANCH`, numbering's `BRANCH`, the AI
   transport's `BRANCH` and the heartbeat's default. One shared constant would stop them drifting. That's a later
   clean-up, not this urgent fix.

## Addendum 1

**Test-only follow-up 0e807720 (story/o1-main-branch): PASS. Note 1 closed.**

- **The test now proves "before".** The diff touches only `tests/timetable/test_session_branch.py`: the run's commit
  must have exactly one parent, the other writer's newest main commit.
- **Survivor now caught.** At 0e807720 the 4 tests pass. With the pre-commit pull removed (the plant that survived
  judge 474), 1 test fails.
- ruff is clean.
- Note 2 (the five "main" constants) stays a later clean-up, agreed by the builder.
- **Merge timing:** the orchestrator's decision (wait for a green main; the red-main exception only with the one known,
  independent failure). My reading of the code, sent to the orchestrator: the first run this bug affects is Friday's
  14:05 desk run, not the 08:36 pre-open, which commits through `GitManifestRecorder` (already "main").
