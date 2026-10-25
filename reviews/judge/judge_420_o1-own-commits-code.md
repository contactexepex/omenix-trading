# Judge 420: O1 G4 code, the run's own unpushed commits (story/o1-own-commits at 863b689c)

**Verdict: PASS. Lane 1. The builder may merge after the full gates pass on the exact pushed tree.** The text is judge
419.

| Criterion | Result | Evidence |
|---|---|---|
| One committer per run, shared | MET | `fno/daily/wiring.py` builds one `GitCommitter(git, OwnUnpushed(...))` for the parts and passes it to `build_daily_run(git_committer=...)`, where `PendingCommitter` wraps it |
| Own commits remembered by content; strangers refused | MET | `commit_paths` → `own.remember(OwnCommit(subject, file SHA-256s))`; `_refuse_stray` accepts any remembered commit by the exact `_own` check (same subject, each file's content), and anything else is still a stray (decision 51) |
| Cleared once origin holds everything | MET | `own.pushed()` after a successful push, or when nothing is ahead (judge 419 note 2) |
| Survives a same-container rerun | MET | written atomically (temp file plus `os.replace`) and read back by a new committer |
| Git-ignored, never committed | MET | `.gitignore` holds `journal/runs/.own/`; I checked `git check-ignore` on the real repository |
| The wording | MET | `NOT_PUSHED` "committed, NOT pushed (the next push carries it)" only when `CommitFailed.unpushed`; otherwise the "NOT committed" hand fix as before |
| Book 1's own decision commit not covered, and said so | MET | `own_commits.py` docstring, E5b's stop (judge 419 note 3) |

**The path change from judge 419, accepted on evidence.** The builder found that at `journal/runs/.own_unpushed.json`
the suite went red: at least five readers glob `journal/runs/*.json` as dated run logs (for example
`fno/scoreboard/committed_runs.py:40`, "Invalid isoformat string"). A subfolder, `journal/runs/.own/unpushed.json`,
stays out of every such glob without patching each reader. This is the root-cause choice, and better than my path.

**Planted mutations, all caught:**
- own commits forgotten in `_refuse_stray`: 2 failed;
- the list never cleared: 1 failed;
- the content check dropped (`_own` always true): 3 failed;
- the not-pushed wording disabled: 1 failed.

**Gates on a trial merge with main:**
- 8809 passed, 17 xfailed, 0 failed; ruff and check_imports clean.
- The only merge conflict was in the claims file, `response_165`; both sides were kept.
- My trial commit in a throwaway worktree, never pushed, ran with hooks off. Nothing of it reached any branch.

**Notes (not should-fix):**
- O2's strict G4 xfail (`tests/e2e/test_hangs.py` on story/o2-failure-handling) must flip to the real assertion once
  this merges, as the builder says.
- The branch's claims file conflicts with main's, so resolve it on merge.
