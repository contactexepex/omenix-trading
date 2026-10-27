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

## Addendum 1: round 2, 55eea4b (FAIL on one test gap; A1 and T2 fixed)

SHA `55eea4b46526fc1d90a8a1134e36820f79ce4ff2`, which replaces `e41cd1e`. **Gates** (`__pycache__` cleared): 769
passed; ruff, format, imports and size clean.

**What changed.** `check-manifest` now alerts when the manifest is broken, so A1 is fixed. The alert reads "...NOT
committed. Re-run the same --from..--to range ... a later run heals only the days its range covers", which covers my
condition 2, and a test pins the wording. On a broken manifest the guard restores the committed manifest
(`git checkout -- "$MANIFEST"`), commits the receipts only, pushes, and exits 1. Committing the receipts is right: they
keep the true evidence time, and the repair keeps a receipt whose digest matches.

**My ruling on the OOM-kill alert:** it is now sufficient. `check-manifest` runs as its own process after the dead
promote and sends the #fno-desk alert itself.

| Plant | Failed |
|---|---|
| G3 the guard removed / G5 the skip branch stages the manifest / G6 no restore of the manifest | 2 / 1 / 1 |
| G7 the skip branch exits 0 / G8 no guard alert / G9 the receipts dropped on a skip | 2 / 1 / 1 |
| Carried: C1 wiring / C2 the torn-line stop / C3 overwrite / C6 commit only on success | 1 / 2 / 5 / 1 |
| **G1 `well_formed` ignores skipped rows** | **0: survives (it failed 1 on e41cd1e; that test was removed)** |
| **G2 `well_formed` without `check_appendable`** | **0: survives (T1, still open)** |

**T1, widened (should fix, tests only): neither half of "well formed" is pinned on its own.** The new guard tests use
one torn file that both halves catch, so removing either half leaves everything green. Two cases are needed:
- (a) a whole-looking last row with **no** trailing new line, which only `check_appendable` catches;
- (b) a malformed row that **does** end in a new line (for example from `main`), which only the skipped count
  catches.

Each must make the guard refuse.

T2 (the skip branch commits nothing of the manifest) is fixed by G5 and G6.

**Note (not blocking), carried:** when `main` already holds a malformed row, the alert says "re-run the same range",
but a re-run cannot fix it; only a hand fix can. Say "or fix the manifest by hand" when the file ends in a new line.

**Verdict: FAIL** (round 2), on T1 only: two test cases, no code change.

## Addendum 2: 227f668 (PASS)

SHA `227f6689bbb10e77e44a5540590d4b45fa820520`, which replaces `55eea4b`. `well_formed` is now `problem() is None`. Its
two halves each return their own code: `manifest_broken` for no trailing new line, and `manifest_row_skipped` for a
row that is not whole. The alert text follows the code: "re-run the same --from..--to range" for a torn file, "fix by
hand" for a bad row in a complete file. That closes my note. **Gates** (`__pycache__` cleared): 772 passed; ruff,
format, imports and size clean.

| Plant | Failed |
|---|---|
| **G1 the not-whole-rows half removed / G2 the trailing-new-line half removed** | **1 / 4: T1 fixed** |
| G2b the two codes swapped (wrong alert text) | 4 |
| G3 guard removed / G5 manifest staged on a skip / G6 no restore / G7 skip exits 0 / G8 no alert / G9 receipts dropped | 2 / 2 / 1 / 2 / 2 / 2 |
| Carried: C1 wiring / C2 torn-line stop / C3 overwrite / C4 repair with new bytes / C5 reconciliation / C6 commit only on success | 1 / 2 / 5 / 2 / 1 / 1 |

The OOM-kill alert is sufficient, as ruled in Addendum 1. The one case nothing can alert on is the runner itself being
lost, so the commit step never runs; then the red job is the signal, and Drive files without receipts are healed by
the next run over the same range.

**Verdict: PASS** (lane 1, judge #2). Merging needs judge #1's PASS too.

## Addendum 3: 08a55f5, the newest SHA (PASS stands; one note on news-fetch)

SHA `08a55f5ebfa940335d7d6af6395ba6a6b8068862`, which carries `60d3f1b` (judge #1's judge_50 items). Compared with
`227f668` it adds:
- an `if: failure() && !inputs.dry_run` step at the end of `news-promote.yml` that posts a fixed text and the run's
  URL through `build_alert_sender`, the repo's usual pattern;
- a test for a row torn inside the size field.

**Gates** (`__pycache__` cleared): 775 passed; ruff, format, imports and size clean.

| Plant | Failed |
|---|---|
| F1 the failure-alert step disabled | 1 |
| G1 the not-whole-rows half removed / G2 the new-line half removed | 1 / 6 |
| G5 manifest staged on a skip / G7 skip exits 0 / G8 the guard alert removed | 2 / 2 / 3 |
| C3 overwrite (carried) | 5 |

The failure step's text carries only the promote outcome and the public run URL: no feed, URL or title.
- It also fires after an ordinary rejection, which the command has already alerted, so that alerts twice. That is
  noise, not a risk, and it is the repo's usual pattern.
- The promote step's own failure does not trigger it, because `continue-on-error` gives that step a success
  conclusion.
- The commit step's `exit 1` and the final `exit 1` do trigger it, so every red run alerts.

**Note for the orchestrator (not P2b3's scope):** the orchestrator expected the same `failure()` step in
`news-fetch.yml`. It is not there (`grep failure() .github/workflows/news-fetch.yml`: nothing). A fetch killed by OOM
or SIGKILL gets no #fno-desk alert, for the same reason as promote. `news-fetch.yml` is merged P2a code, so this is a
small follow-up of its own.

**Verdict: PASS** on `08a55f5` (lane 1, judge #2).
