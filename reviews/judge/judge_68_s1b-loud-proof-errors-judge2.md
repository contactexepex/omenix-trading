# Judge 68: S1b loud proof errors (code, lane 1, sole judge)

Frozen SHA `cead192` (branch `story/S1b-loud-proof-errors`, with main `bb083f6` merged in). Reviewed
`git diff origin/main cead192`:
- the catch-alls are removed from `NseCopyProof.promoted` and `NewsPollProof.promoted` (news keeps only
  `except PollRejected`);
- `StagingCleanup._one` wraps `proof.promoted`: on any `Exception` it keeps the copy and counts `proof_error`;
- `ok` turns false on a proof error;
- there is a new contract row, E6.

**Gates (cleared `__pycache__`):** 1236 passed; ruff check and format clean; imports clean (502 files); code size
passed; contract plants all ok.

## The orchestrator's question: can removing the catch-alls get a copy trashed that was not trashed before?

**No.** Strong evidence: I traced every path and ran a test of my own.

- **An `Exception` inside a proof.** Before, the proof caught it and returned False, so the copy was kept. Now it
  reaches `_one`, which counts it and returns before `trash` (`cleanup.py:99-103`), so the copy is kept. The trash
  call is reached only after `promoted` has returned, and only when it returned a truthy value.
- **A partial evaluation.** The news proof's `all(...)` over a generator raises out of the middle of the loop. No True
  is ever produced, so the copy is kept, as before. `NseCopyProof` returns either `==` or `any()`, both plain bools,
  and nothing returns True on an exception path.
- **`BaseException`** (`KeyboardInterrupt`, `SystemExit`). The old `except Exception` did not catch it either.
  Before and after, it propagates and ends the run, so no later copy is examined or trashed.

  My test: three copies, where `a` raises `RuntimeError`, `b` raises `KeyboardInterrupt`, and `c` is proven. The run
  stopped at `b` and the trash list was empty.
- **Exceptions after the decision.** `trash()` is unchanged: `_remove` counts a failure and the copy stays. The
  report's `line()` only reads counts. Listing errors in `archive_paths` and `stamps` are unchanged and still end the
  run.
- **`PollRejected`** answers False, so the copy is kept. Only the news parser raises it; the planner raises
  `RawFileConflict`, which is now a proof error, so that copy is kept too.

**My plants (4 of 4 killed):**

| Plant | Tests failed |
|---|---|
| an error treated as promoted | 3 |
| `proof_error` not turning the run red | 3 |
| no catch in `_one` (errors crash the run) | 3 |
| the news catch-all put back | 1 |

The known behaviour change is accepted, and the story states it: a damaged poll that is not a refused poll now turns
every run red until it is fixed. That is loud, not silent: the copy is kept and an alert is sent.

**Verdict: PASS** (`cead192`).
