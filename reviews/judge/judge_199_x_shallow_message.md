# Judge 199: X shallow message, history tests fail in a shallow clone with the fixing command, at d79639d3

Judge C. Branch `story/x-shallow-message`, head `d79639d3`, on top of f01a0094 (work-register row). Lane 1 because
it edits tests.

**Verdict: PASS.**

## What changes

- New `tests/history.py`, `require_full_history`. When `git rev-parse --is-shallow-repository` says `true`, it calls
  `pytest.fail("shallow clone: run git fetch --unshallow origin main", pytrace=False)`. That is a failure, never a skip.
- A session fixture `full_history` in `tests/conftest.py`.
- `@pytest.mark.usefixtures("full_history")` on 9 tests, in 6 files. One `import pytest` is added to a file that
  lacked it.
- New `tests/test_history_guard.py`.
- One line in the `docs/JUDGE.md` merge procedure.

## Checks

| Check | Result |
|---|---|
| Only additions | `git diff --numstat` against the merge base shows 0 deleted lines. No test body, assertion or parameter changed; the 9 gain only the decorator. |
| Nothing skipped | In a real `--depth 1` clone of d79639d3 the full suite gives **6,514 passed, 9 errors, 0 skipped**. The 9 errors are exactly the 9 decorated tests. |
| The message | In the shallow clone each of the 9 stops with "shallow clone: run git fetch --unshallow origin main" and no traceback (checked on `tests/forecast/test_freeze.py`). |
| No other test is touched | The other 6,514 tests pass in the shallow clone, so the session fixture fails only the tests that ask for it. No undecorated test reads history in a way a shallow clone breaks. |
| The 25 tests in the 6 files, full clone | 25 passed. |
| Full suite on the branch, full clone, `-n auto` | 6,523 passed in 2 min 30 s. |
| ruff check, ruff format, check_imports | Clean: "All checks passed!", "1157 files already formatted", "clean: 1224 files". |
| The new guard test | Builds a real two-commit repository and clones it with `--depth 1`. The shallow clone raises with the exact message, and the full repository passes. |
| merge-tree with origin/main | Clean. |

## Notes (no change needed)

- The 9 show as **ERROR at setup**, not FAILED, because the check runs in a fixture. The run still fails (pytest's
  exit status is not 0) and the message is shown, so nothing passes silently.
- The fixture is session-scoped. Pytest therefore runs it before the module fixtures that read history (for example
  `committed` in `test_backfill.py` and `cases` in `test_structures_match_frozen.py`), so the clear message comes
  first.
- A test added later that reads history needs the decorator. Without it, such a test gives the old misleading error
  in a shallow clone, never a false pass. The JUDGE.md line tells the next reader what to run.

Would it change a trade? No. Test plumbing only; every check still runs.
