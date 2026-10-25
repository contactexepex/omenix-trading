# Judge 354: O12, one central place to claim file numbers (story/o12-number-claims @ ac1e52c5)

Judge F (independent). Story `docs/stories/O12-number-claims.md` (text pushed alone at 3a4684aa), claims
`reviews/claude/response_268_o12-number-claims.md`. The builder sent a4ed62fd; the head is now ac1e52c5, which merges
main again, re-seeds, and adds reservation rows for responses 260-270 and judges 300-399. I judged ac1e52c5. Lane 1
(tools, CI, rule documents). Labels: **strong**, **some**, **reasoning only**.

## Verdict: FAIL (1 should fix, 3 minor). The fix is a few lines of documentation; the code may stay as it is.

The design is the simplest that removes the clash:
- one CSV per series;
- git's refusal of the second push decides each race;
- a check in CI catches what slips past;
- the seed is pinned by SHA-256, so history cannot later hide a new clash.

Small, standard library only, no service or lock server. The one problem is the manual path, which tells other
agents to run a destructive git command in their own checkout.

## Gates and runs (mine)

| Check | Result |
|---|---|
| pytest `-n auto`, full history | **7790 passed** |
| ruff, ruff format (1405 files), `check_imports.py` (1495), `check_records.py` (6726), `check_numbers.py` | all clean |
| `tests/numbering` and `tests/test_ci_scope.py` five times in a row (the race tests depend on timing) | 61 passed each time |
| Trial merge with origin/main (16 Oct, about 12:00 UTC) | `check_numbers.py` FAILED with 17 lines: files and addenda landed after the seed (judges 276-307 addenda, my 350.1, responses 250 and 258). `--seed` added 17 rows and the check was clean after, exactly as the merge note says. One text conflict in `reviews/claude/README.md` (the merger's) |
| File size | largest 106 lines (`check.py`) |

## Planted mutations (mine, reverted)

| # | Plant | Caught |
|---|---|---|
| 1 | every push refusal containing "rejected" counts as a lost race (a hook's `[remote rejected]` included) | yes |
| 2 | taken numbers = registry rows only (files on main ignored) | yes |
| 3 | a number with one seeded row may be used any number of times | **no** (minor 1) |
| 4 | no re-read of main after a lost race | yes (2 failed) |
| 5 | the session name `existing` accepted | yes |
| 6 | the worktree not removed | no, but the `rmtree` plus `worktree prune` that follow make this mutant behave the same |

Code read: `[rejected]` in `RACE_LOST` does not match `[remote rejected]`, so a server hook or protected-branch
refusal stops at once, as claimed. The claim happens in a detached temporary worktree, so the caller's branch and
index are untouched. The record-scan hook runs there, because it is on the repository's `core.hooksPath`.

## Criteria

| # | Evidence | Status |
|---|---|---|
| 1 Registry seeded, duplicates kept | check clean at head; duplicates 66, 233-235, 98.3, 122.4, 233.1 as `existing` rows (test); re-seed on the merged tree works | MET |
| 2 Claim next or exact, refusals | tests plus plants 2 and 5 | MET |
| 3 Races: two and four clients; bounded; other refusals stop | tests (5 of 5 runs green) plus plants 1 and 4 | MET |
| 4 Caller untouched, worktree removed | test plus code read | MET |
| 5 Check fails on each case, passes on the pinned seed | 17 cases tested; plant 3 survives on one path (minor 1) | MET |
| 6 CI last with `if: always()`; `ci_scope.sh` lane 3; JUDGE.md | `checks.yml` last step `if: always()`; `LANE3` includes `numbers/`; JUDGE.md lane table and merge gates updated | MET |
| 7 Docs say how to claim; judge convention ended | AGENTS.md, CLAUDE.md, three READMEs, `numbers/README.md`, JUDGE.md "Several judges" | PARTLY (SF1) |

## Should fix

**SF1. The manual path tells ChatGPT and any agent to run `git reset --hard origin/main` in their own checkout
[strong: git's documented behaviour].** `numbers/README.md` step 1, "Without the tool, commit nothing else first,
then: `git fetch origin main && git reset --hard origin/main`". AGENTS.md:51, CLAUDE.md:29 and
`reviews/chatgpt/README.md`:13 say the same ("reset to `origin/main`").

`reset --hard` throws away every uncommitted change in the working tree. It also moves the branch off any commits not
yet pushed, which are then reachable only through the reflog. The agents who use this path (ChatGPT, anyone without
the tool) are the ones most likely to be mid-work in that checkout. "Commit nothing else first" does not protect
uncommitted files. The tool itself avoids exactly this with a temporary worktree.

Fix expected: the manual path works in a separate place. For example, `git fetch origin main && git worktree add
--detach ../claim origin/main`, append, commit and push from there, then remove it. Or a fresh clone. Same change in
the four documents. No code change.

## Minor

1. Plant 3 survives. `_shared_numbers` is right, but no test covers a hand-claimed row that reuses a number seeded
   once (for example a new `250` row and file). Add that case.
2. `numbers/` is lane 3 and only the seeded rows are pinned, so someone can delete or edit a claimed row whose file is
   not yet written, and the number is handed out again. That is low risk, and `numbers/README.md` already says "never
   edit or delete someone else's row". Say in the check's docs that unwritten claims are not protected.
3. A note on code not changed by O12: in `checks.yml` the record-scan steps have `if:` with no status function, so
   when pytest fails the full record scan is skipped. O12 put its own step last with `always()`; the record scan
   deserves the same, in a separate change.

## Merge note

- At the merge, run `python tools/check_numbers.py --seed` on the merged tree.
- Read every added row (my trial gave 17; there will be more). Every added row must be a file that is really on
  `main`, and any number that appears twice must be checked by hand before it is seeded as history.
- The judges' reserved rows 300-399 carry wildcard names (`judge_352_*.md`). I checked that the files I wrote, 350
  and 351 (now seeded) and 352-353 (reserved rows), pass the check on the trial merge.

## Addendum 1: re-judge at 43af4b82 (one commit after ac1e52c5; documents and one test, nothing under `fno/` changed)

**Verdict: PASS. O12 may merge, with the merge note above (re-seed on the merged tree, read every added row).**

| Finding | Builder's answer | My check | Result |
|---|---|---|---|
| SF1: the manual path resets the agent's own checkout | all four documents and the story now claim from a separate copy (`git worktree add --detach ../claim origin/main`, a fresh clone, or GitHub's editor); the reset happens only inside that copy, which is then removed | I grepped for `reset --hard`: the only two hits are `numbers/README.md`:28 ("in `../claim` only") and the story, line 71 ("there only"). AGENTS.md, CLAUDE.md and `reviews/chatgpt/README.md` say "a separate copy of `main`, never your own checkout". GitHub's contents API refuses a save made against an old file version, so "a refused save means someone claimed first" holds | **Accepted** |
| Minor 1: no test for a claim reusing a number seeded once | `test_a_claimed_row_reusing_a_number_seeded_once_fails` | My `< 1` plant now fails 1 test (56 passed); reverted, `tests/numbering` and `test_ci_scope.py` give 62 passed | **Accepted** |
| Minor 2: unwritten claims are unprotected | stated in `numbers/README.md` and the story | read | **Accepted** |
| Minor 3: record-scan steps skipped after a pytest failure | left for a separate change | as I said | **Accepted** (open, outside O12) |

ruff, ruff format and `check_numbers.py` are clean at 43af4b82. I did not re-run the full suite: since ac1e52c5 (7790
passed) only documents and one test changed. The merger runs it on the merged tree, per the new merge rule.
