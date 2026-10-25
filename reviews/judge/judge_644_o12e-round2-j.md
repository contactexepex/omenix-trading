# Judge 644: O12e ledger-trial blocks, text and code, story/o12e-ledger-trials at cb6ceb79b (judge J, 2 of 2, round 2)

**FAIL**, lane 1: 1 should-fix, 1 minor. Judge 636's four round-1 points are fixed. Trial merge with main (ca4b6502):
16,639 passed, 1 skipped, 13 xfailed; ruff, format, check_imports (2,766 files), check_records (9,304) and
check_numbers clean.

## Criteria
| # | Verdict | My evidence |
|---|---|---|
| 1 findings | MET | Plants U2 (overlap), U3 (uncovered), U4 (outside), U5 (bad id flag) and U8 (`5-3` accepted) are each caught |
| 2 main clean, pins | MET | check_numbers is clean on the trial merge. The 16 seeded rows equal their pin; 101-108 sit in `forecasts-v4`. EDGE2's real ledger (a5cc130f, 120 rows) against this registry gives `block_findings` = [] |
| 3 claim, race, exact | MET | Tests for the race, an exact block overlapping a block or a ledger id, and a ledger id typed past every block. Plants U11 and U12 are caught |
| 4 register | MET | My probe: unclaimed 5 is refused; `book3:x` is refused under `exp` and accepted under `book3_ai strategies`; `' 3'`, `'3 '` and `book3:` are refused. U1 (`edge2-f60`), U6, U7 (`07`), U9 and U13 are caught. Book 3 names are slugs (`NAME_PATTERN`), so `book3:\S+` never refuses a real one |
| 5 freeze | MET | The id is chosen before `FREEZE_v<n>.md` is written. U15 (id after the write) is caught, and so is U10 (an id from another block) |
| 6 docs | MET | `numbers/README.md:11,14` and `research/LEDGER.md:10` name it; the claim tool's help lists `ledger-trial` |
| 7 factory | MET | `_next_claimed`; U16 (highest plus one restored) is caught |
| 8 require_committed | PARTLY | S1; U14 (the check removed) is caught |
| Judge 636's four | MET | A refused freeze writes nothing (U15); the exemption covers Book 3's experiment only (U6); the check runs in `require_committed` (U14); prefix plus `-` (U1) |

## Findings
**S1 (should fix) The claim check reads the registry from the working tree, so a block never committed lets a trial
run.**
- `TrialClaims` reads `root/numbers/ledger-trial.csv` as it is on disk. `require_committed` insists only that the
  ledger is committed and unchanged.
- My probe, in a temporary repository whose block is `1-3`:
  1. commit a hand-typed ledger row 5: `require_committed("5")` refuses, correctly;
  2. add `4-6,exp,...` to the registry, uncommitted: `require_committed("5")` is accepted, and so is
     `register("6", "exp-b")`.
- That breaks the story's own rule, "an unclaimed trial never runs, even before CI sees the push". A claim is a row
  pushed to `main`; a local edit is not one.
- Fix, the ledger's rule applied to the registry (DRY):
  - in `require_committed`, read the registry at HEAD and refuse while it has uncommitted changes;
  - add a test with a working-tree-only block.
- Keep `register` reading what is committed too, or say why not.
- Plant for round 3: the check reading the working tree again.

**m1 (minor) Known limits miss one case.** A block committed only on a branch, never pushed to `main`, also passes
`require_committed` and the branch's own checks. Only `main`'s check_numbers sees an overlap, at merge. That is O12's
design, but say it in Known limits next to "the session column is what the claimant typed".

## Plants (mine): 16 of 16 caught
U1 prefix without `-`; U2 overlap; U3 uncovered; U4 outside; U5 bad ids not flagged; U6 Book 3 under any experiment;
U7 leading zero; U8 `5-3`; U9 `problem` accepting another block; U10 `next_free` from any block; U11 the next block
ignoring ledger ids; U12 an exact block ignoring ledger ids; U13 `register`'s guard; U14 `require_committed`'s guard;
U15 the freeze id after the write; U16 the factory's highest plus one. Targeted tests: numbering, research,
research_engine, evaluation and factory. Run with PYTHONDONTWRITEBYTECODE=1 in a separate worktree.

## Notes
- Slack, with FNO_SLACK_BOT_TOKEN set (1792888068-1792888643): nothing in any of the three channels.
- EDGE2's S1 (judge 642) changes trials 109-120's `protocol_path` or B4. Whichever way it is fixed, those rows still
  sit in this story's blocks `edge2-f1-weekly-vrp-gate` and `edge2-f6`: the experiment column needs no change.
- I did not coordinate with judge 636.

## Addendum 1: round 3 (granted by the owner, 25 Oct), story/o12e-ledger-trials at 1f680b2c1
**PASS**, lane 1: S1 and m1 closed. Trial merge with main e3f975d6 (a95db046): 17,624 passed, 1 skipped, 13 xfailed;
ruff, format, check_imports (2,912 files), check_records (9,546) and check_numbers clean.
- **S1 closed.** `TrialClaims` now reads `numbers/ledger-trial.csv` through `Git.committed_text` (HEAD). `problem` and
  `next_free` refuse while `git status --porcelain` shows any local change to it, so `register`, `require_committed`,
  the factory and the freeze all refuse.
  - My round-2 probe, re-run unchanged on the branch: the uncommitted block 4-6 now gives "numbers/ledger-trial.csv
    has uncommitted changes" for both `require_committed("5")` and `register("6")`. Every other case answers as in
    round 2.
  - My plants are caught: V1 (refusal removed), V3 (`git diff` only: it misses a registry never committed, caught by
    `test_a_registry_that_exists_only_in_the_working_tree_is_refused`) and V4 (`next_free` unchecked). U1, U10, U13
    and U14 are caught again.
  - V2 (reading the working tree instead of HEAD) survives as an equivalent mutant: the clean-tree guard makes the
    two identical whenever reading is allowed.
- **m1 closed.** Known limits now say a block committed only on a branch passes that branch's guard, and that
  `main`'s `check_numbers` sees it only at the merge. They name the claim tool (it pushes to `main` first) as the one
  safe way to get a block.
- **Seeds:** `edge2-f8` 121-123 and `edge2-f9` 124-127. On the trial merge, `check_numbers` is clean against main's
  ledger, which now runs to 127.
- **Document rules:** `numbers/README.md` gives the command and links the O12e section instead of restating its rules
  (45 lines); `O12-number-claims.md` is 281 lines.
- Slack, with the token set (1792917290-1792917911): nothing in any channel. I did not coordinate with judge 636.
