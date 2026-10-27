# Judge 85: NP2d wrapper index (code, lane 1), judge #2

Frozen SHA `dbb4905` (branch `story/NP2d-wrapper-index`, from main without NP2c). Reviewed `git diff origin/main dbb4905`:
- `record/wrapper_index.py`, `writer.py`, `gate.py`, `wiring.py`;
- `ops/commit_news_record.sh` and `news-promote.yml`;
- the tests, rows X1-X6 and their plants.

The deleted judge files seen in that diff come only from an older base.

**Gates** (in the locked venv): 1596 passed; ruff clean; imports clean (551 files); code size passed; contract plants
all ok.

**My plants (4 of 4 killed):**

| Plant | Tests failed |
|---|---|
| revisions marked too | 2 |
| no mark on a NO_OP | 2 |
| the index's torn check off | 2 |
| `EXTRA_MANIFESTS` ignored by the guard | 3 |

## Checked and correct

- **(a) It only adds.** `_mark` runs after the article's own save or document, and writes only to `wrappers.csv`.
  The gate's torn check now covers both files before any write. A torn index stops the run, as the articles manifest
  does: that is intended. `mark` can only raise `RawFileConflict` if one key gets two SHA-256 values. It cannot, because
  it always hashes the write-once article file the Record holds.
- **(b) Idempotence:** a run killed between the two rows is repaired by the next promote of that poll (NO_OP, then
  mark; plant killed).
- **The S1 interaction is stated plainly** (story lines 31-33). See also the note below on a discarded index.
- **(e) Revisions:** marked only for the `RECORDED` status (plant killed).
- **(d)** `news-promote.yml` sets `EXTRA_MANIFESTS` to the index.

## Findings

1. **F1 (must fix): the rewritten commit guard dies when `wrappers.csv` does not exist, before committing or pushing
   anything.**
   - `check-manifest` calls a missing file "whole" (exit 0).
   - The loop then runs `git add "$manifest"` on a path that does not exist, which is fatal under `set -e`.
   - Reproduced with the real script in a scratch repository: `fatal: pathspec 'm/wrappers.csv' did not match any
     files`, **exit 128**, nothing committed, nothing pushed. The receipt batches and the articles manifest written
     that run never reach main.
   - That happens on every promote until the first Google News article has been recorded and committed: the file does
     not exist on main today (`research/data/manifests/news/` is absent). It also happens on a run whose index file is
     discarded.
   - Fix: `[ -e "$manifest" ] && git add -- "$manifest"`. The same latent bug applies to `$MANIFEST` itself, so let it
     cover both. Add a real-git test with the extra manifest missing, and a plant.
2. **F2 (must fix, text): the story says the resolve pass reads the index (line 26). Nothing on this branch does.**
   This branch is from main without NP2c, and NP2c's `run.py` (on its own branch, which I passed at `b1917e7`) reads
   the articles manifest. The fix the story is named for is therefore not delivered by NP2d alone. Say that the switch
   is an NP2c follow-up, name who owns it, and keep NP2c's "unexamined" alert until then.

## Notes (not blocking)

- **A discarded index loses every row of its run:** when the guard throws away a torn `wrappers.csv`, it drops all the
  index rows that run added, while `articles.csv` is still committed. The re-run of the same range that the
  `manifest_broken` alert asks for repairs them, but only within S1's 7 days. Say so next to the existing S1 sentence.
- **A format-1 file can be marked:** for a format-1 held article (no `wrapper_link`) re-seen in format 2, `mark` tests
  `is_resolvable` on the *new* article but hashes the held format-1 file. The index then points at a file the resolve
  pass will count as `not_wrapper`. No format-1 news exists today, so this is not live.

**Verdict: FAIL** (round 1, `dbb4905`). F1 is a one-line shell fix plus a test; F2 is text.

## Addendum 1: round 2 on `2ac29df` (main with NP2c merged in)

`git diff origin/main 2ac29df -- fno ops .github`:
- the commit guard runs `git add` only when the file exists (`commit_news_record.sh:16`), for every manifest;
- `resolve/wiring.py` hands the pass `wrappers.csv`;
- the S1 news proof also requires the wrapper-index row for a resolvable article (`_indexed`, X8);
- the story is updated.

**F1 fixed: re-run with the real script in a scratch repository.** With `articles.csv` holding a new row and
`wrappers.csv` absent, the script exits 0 and commits and pushes (`0478ff3`).

**F2 fixed:** the resolve pass now reads the index.

**Gates** (in the locked venv): 1636 passed; ruff clean; imports clean (559 files); code size passed; contract plants all
ok.

**My plants (3 of 4 killed):**

| Plant | Tests failed |
|---|---|
| unconditional `git add` | 3 |
| proof without `_indexed` | 2 |
| resolve wiring reading `articles.csv` | 2 |
| staging-cleanup **wiring** not passing the wrapper index | **survived** |

**Should fix (not blocking):** the survivor means `NewsPollProof` is tested with an index, but nothing checks that
`staging_cleanup/wiring.py:82-84` really gives it one. With the index left out, `_indexed` is always True, which is
the round-1 behaviour that judge 86's recommendation was meant to close. One wiring test (the news rule holds a
wrapper index) pins it.

**Verdict: PASS** (`2ac29df`), with the wiring test as a should-fix.
