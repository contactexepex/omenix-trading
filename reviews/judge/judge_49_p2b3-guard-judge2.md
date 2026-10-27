# Judge 49: P2b3 the news manifest commit guard, code (judge #2)

Branch `story/P2b3-commit-guard`, SHA `e41cd1e48e26cec38fda673a5c4a808ce52dbdf0`, lane 1. **FAIL** (round 1) on 3
small should-fix: two tests and one alert. The guard's design meets both of my conditions.

## Gates (`__pycache__` cleared)

767 passed; ruff check and format clean; imports clean; code size passed.

## My two conditions

1. **One definition of "valid": MET.** `news check-manifest` calls `NewsManifest.well_formed()`, which is
   `check_appendable()` (a trailing new line) plus `not skipped` (every row passes the loader's own `_whole`). The
   workflow calls the command, with no copy in shell. Plant G1 (skipped rows ignored) fails 1 test. **But G2 (the
   trailing-new-line half removed) survives: T1.**
2. **Healing is range-bound: MET** in the story ("healing a crashed day needs a later promote whose `--from` covers that
   day"). It also says a skipped commit leaves out both the manifest and the receipts. The repair keeps an existing
   receipt when its digest matches, so that is safe.

## Plants (each restored)

| Plant | Failed |
|---|---|
| G1 `well_formed` ignores skipped rows | 1 |
| G3 the guard removed (`if true`) / G4 the guard keyed on promote's outcome | 1 / 1 |
| C6 the commit step limited to promote success | 2 |
| Carried: C1 wiring onto Staging / C2 the torn-line stop / C3 overwrite / C4 repair with new bytes / C5 reconciliation | 1 / 2 / 5 / 2 / 1 |
| **G2 `well_formed` without `check_appendable`** | **0: survives (T1)** |
| **G5 the skip branch commits anyway** | **0: survives (T2)** |

## Findings

1. **T1 (should fix, test): a torn line that looks whole is not tested.** G2 survives because each test's torn line
   is also a bad row, so `skipped` catches it. A cut that leaves a whole-looking row is possible: a cut inside
   `size_bytes` (`...,29` for `...,292`), or a full row whose new line was lost. I checked the real code on such a
   file: `skipped: 0`, `well_formed: False`, which is correct, and only `check_appendable` catches it. Under G2 the
   guard would pass the file, it would be committed, and every later run would stop on `manifest_broken` until fixed
   by hand. Add that case to the guard test.
2. **T2 (should fix, test): the skip branch is not pinned to commit nothing.** G5 (`git add` and `git commit` in the
   `else` branch) leaves all 767 green. Assert that the `else` branch holds no `git add`, `git commit` or `git push`.
3. **A1 (should fix): the skip should alert.** My ruling on criterion d: a red run alone is not enough.
   - The case the guard exists for, a promote killed by OOM or SIGKILL, is exactly the one where the command's own
     #fno-desk alert never fires.
   - GitHub's failed-run e-mail goes only to the person it notifies (for a manual run, the one who started it; for a
     later cron, the last editor of the schedule).
   - The project rule is that F&O alerts go to #fno-desk. A skipped commit also leaves GitHub behind Drive until a
     run over the same range, which the owner has to know to do.

   Fix: `check-manifest` sends the fixed alert itself when the file is broken, for example "news manifest:
   manifest_broken; commit skipped; re-run the same --from..--to" (no path, no content), through the existing alert
   sender, which prints "alert NOT sent" without the token. Add a test.

## Note (not blocking)

A malformed row that is already on `main` (a hand edit, or a commit from before the guard) makes the guard skip every
later commit until someone fixes it by hand. That is loud, with A1, but it stalls GitHub's record. The alert text
should say "fix the manifest by hand" when `skipped` > 0 and the file does end in a new line.

**Verdict: FAIL** (round 1). Three small items; the guard's design is sound.
