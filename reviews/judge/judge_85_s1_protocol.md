# Judge 85: story S1, the evaluation protocol: tooling and draft (branch, before merge)

Date: 14 Oct 2026 (UTC). Branch `story/s1-protocol` at ceb20eb. Claims: `reviews/claude/response_86_s1-protocol.md`.
Story: `docs/stories/S-scoreboards.md` S1.

Scope, as asked:
- the tooling as built;
- the draft protocol for completeness and honesty only.

The values are the owner's to decide. The protocol is **not frozen**, by design.

## Verdict: FAIL, one must-fix (criterion 3 is not enforced), shown by probe

## Gates (my runs, `python -B`, caches cleared)

- Full suite: 2,843 passed.
- `ruff check`: clean. `ruff format --check`: 633 files. Imports: clean (640).
- `git merge-tree` with current `main` (f684a87): clean.
- `python -m fno evaluation check`: "version 1: complete" (exit 0). With `--decided`: "not decided by the owner (18)",
  exit 2. As claimed.

## Must-fix: a change after the freeze is detected by nothing

`changed_targets` exists but is called only by a test. No command, no suite test and no counting rule uses it.
`version_of` and `order_problems` look at commit ancestry only.

**My probe** uses the branch's own fixtures (`protocol_repo`, `freeze`, `decide`):
1. Freeze v1 and commit.
2. Edit `PROTOCOL.md`: the uncertainty criterion's "one-sided 95%" becomes "one-sided 80%".
3. Change the frozen `fno/scoring.py`, and commit both under the same version number.
4. Commit a Book 1 decision.

Results:
- `version_of(decision)` = **1**;
- the completeness check finds nothing;
- no test fails.

The loosened criterion would be reported as protocol v1. That is exactly what criterion 3 exists to stop: "a change
after the freeze is only possible as a new protocol version".

**Fix:**
- `python -m fno evaluation verify`: for every committed `FREEZE_v<n>.md`, the targets of the **latest** version are
  unchanged. A change to an older version's target is allowed only once a newer version is frozen.
- A **suite test** that runs the same check on the repository, so CI fails on any edit to a frozen target (as
  `tests/test_code_size.py` guards size).
- `version_of` refuses to count a decision whose commit holds a frozen target that differs from its freeze record:
  "the protocol changed without a new version".
- Tests: my probe's sequence fails; the same edit with `Protocol version: 2` and a new freeze passes.

## Per criterion

| # | Criterion | Check | Result |
|---|---|---|---|
| 1 | The freeze commit precedes each book's first counted decision | Strict ancestor: my plant reducing it to "ancestor or equal" is caught. Pilot exclusion: my plant counting pilot runs is caught. The tooling is right; the real order can only be checked after a freeze | MET (tooling) |
| 2 | Every item has a value or rule; "to be decided" rejected | 18 items; my plants switching off the open-words check (6 failed), the evidence-label check and the decided-only freeze are caught | MET |
| 3 | A change after the freeze is a new version; results per version | Per-version lookup and "never freeze a version twice" work. But an edit under the same version is not caught (must-fix) | NOT MET |

## The two points the orchestrator asked me to check

- **Canonical-JSON config hashing:** I tested it myself on `config.yaml:desk.timetable`.
  - Comments, key order and flow style give the **same** hash.
  - A changed value gives a different one.
  - Unquoted `14:58`, which YAML 1.1 reads as the number 898, gives a different one. That is correct: the value
    really changed.
  - MET.
- **Strict-ancestor order:** a decision committed **together with** the freeze is not after it (the builder's test).
  My plant removing "strict" is caught. MET.

## My plants (8, `tests/evaluation`)

| Plant | Result |
|---|---|
| Strict ancestor relaxed to "ancestor or equal" | caught |
| `version_of`: the earliest version wins | caught |
| Pilot runs counted | caught |
| Open-words check off | caught (6) |
| Undecided protocol allowed to freeze | caught |
| Config hash over the whole file | caught |
| **The protocol no longer always a target** | **not caught** (should-fix: one test; the draft lists it explicitly, so no harm today) |
| Evidence label unchecked | caught |

## Should-fix (tooling)

- **The freeze hashes the working tree.** It checks only that `PROTOCOL.md` is unchanged since HEAD. An uncommitted
  edit to `fno/scorecard/review.py` or `config.yaml` at freeze time is hashed into a record that matches no commit.
  Require every target to be unchanged since HEAD.
- **One test for "the protocol is always a target"** (the plant above).

## The draft: completeness and honesty (not its values)

The draft is complete by its own check: 18 items, each with a status, a reason and an evidence label, all "reasoning
only". Section 4 of the claims is candid: six months will very likely be inconclusive, and the AI-cost choice and the
timetable are untested.

Two points the owner should see before deciding:

1. **The "version 2 adds hashes only" plan contradicts the draft's own reporting rule.** `frozen_files` says the
   S2/S3/F8/F9 code, if not built at the freeze, is hashed by a v2 "frozen before any result is reported".
   - But `reporting_per_version` counts each decision under the latest version frozen **before that decision**, and
     never recomputes it under a later one.
   - So every decision before the v2 freeze stays under v1, whose scoring code was never hashed.
   - That code would also be written after decisions were seen, the kind of reinterpretation S1 forbids.
   - The draft must choose:
     - (a) freeze only once the scoring code exists; or
     - (b) state that a hash-only v2 covers all earlier v1 decisions, frozen before **any** result, and that the code
       must implement v1's text exactly.
   - Reasoning only; the choice is the owner's.
2. **Statistician's note on the bootstrap (reasoning only).** At 120 trading days with a 20-day block there are only
   about 6 blocks.
   - A percentile bootstrap with so few blocks tends to give a lower bound that is **too high** (it under-covers). So
     "lower bound above zero" can be claimed too early.
   - The draft's minimum sample (paper gate plus 120 days) does not guard against that.
   - Options for the owner:
     - a minimum number of blocks (for example 12, so 240 days);
     - or a second, conservative bound as a cross-check (a t-based bound on block means), with the claim made only if
       both clear zero.

## Claims vs reality

| Claim | Reality |
|---|---|
| "A change after the freeze is a new version" (criterion 3) | Only the freezer's refusal to re-freeze is enforced; an edit under the same version passes silently (probe) |
| "28 of 28 mutations caught" | Not re-run; 7 of my 8 caught |
| The config hash ignores layout, not values | Confirmed by my own test |
| NOT frozen; values are the owner's | True; `--decided` lists all 18 |

## Project rules

- New package `fno/evaluation/` with its own wiring, and a CLI entry.
- Files are within 350 lines. The ledger row goes through B4's `Ledger`.
- No orders and no secrets.

## Addendum 1 (round 2, b1a609243cd55f961ce104b427d8ebf3e2ae3c68 = fix 04bbff2 plus a merge of main): PASS

**The must-fix is met.** Criterion 3 is now enforced three ways:
- `python -m fno evaluation verify` reports every target of the latest freeze that differs in the working tree.
- A suite test (`test_the_repository_holds_no_edit_to_a_frozen_target`) runs it on the repository, so CI fails on any
  edit to a frozen target.
- `version_of` reads the version's targets **as the decision's own commit holds them**, and raises
  `ChangedAfterFreeze` if any differ.

My exact probe sequence is now a test, and it fails as it should. The same edit as v2 with its own freeze is counted.

**Should-fixes met:**
- the freeze requires every target committed and unchanged since HEAD, and hashes it as HEAD holds it;
- a test that the protocol is always a target.

I accept the builder's equivalent-mutant note: with the committed-and-unchanged refusal, hashing the working tree or
HEAD gives the same bytes.

**Gates (my runs, `python -B`, caches cleared):**
- full suite: 2,849 passed;
- ruff, format (633 files) and imports (640): clean;
- `fno evaluation verify`: "unchanged (or nothing is frozen yet)";
- `check`: complete.
- **`git merge-tree` with current `main` (400699a): CONFLICT in `CLAUDE.md` only** (E5 merged meanwhile). The merge
  must keep both composition-root lines and change nothing else.

**My plants on the freeze guard (8, `tests/evaluation`):**

| Plant | Result |
|---|---|
| `version_of` ignores changes | caught |
| `version_of` checks the working tree instead of the decision's commit | caught (2) |
| `verify` checks the oldest version | caught |
| `verify` never reports | caught |
| The freeze accepts an uncommitted target | caught (3) |
| Strict ancestor relaxed | caught |
| The protocol not always a target | caught |
| **A deleted (or renamed) frozen target not counted as changed** | **not caught** |

**Should-fix (test only, not blocking).** The code is right today: `changed_targets` counts a missing target as
changed, by my reading. But no test covers it. A refactor that moves a frozen file is likely, because the 350-line
rule splits files. Without a test, a later edit could let a moved and changed scoring file pass `verify`. Add one test:
a frozen file deleted, then `verify` and `version_of` both refuse.

**Process note (reasoning only).** Once v1 is frozen, a v2 **draft** of `PROTOCOL.md` committed to `main` turns the
suite red: the guard sees v1's target changed. Decisions committed while that draft stands are refused by
`version_of`.
- So draft and freeze v2 on a branch, and merge them together as one merge.
- Every decision then sits either before the draft or after the v2 freeze.
- That fits the owner's branch rule. It is worth one line in the protocol's `reporting_per_version`.

**The draft:** the two owner questions from judge 85 (the hash-only v2, and about 6 bootstrap blocks) are now in
`PROTOCOL.md` with options. The builder recommends "freeze once the code exists", and both "≥12 blocks" and "a t-based
bound". These are the owner's to decide.

**Verdict: PASS** for b1a609243cd55f961ce104b427d8ebf3e2ae3c68, merged outside 09:25-09:50 UTC, with the `CLAUDE.md`
conflict resolved as text only. After the merge I check `main` against it and CI.

## Addendum 2 (merge check bdd46ff, and `story/s1-missing-target-test` 9e21d87)

**Merge: MET.**
- bdd46ff has parents 483fd7c (`main`) and b1a6092 (the passed SHA).
- It differs from my recomputed merge only in `CLAUDE.md`. That is the expected conflict resolution as text: it keeps
  the E5 root and adds `fno/evaluation/wiring.py`.
- d7d3418 equals its recomputed merge.
- CI `checks` is green on d7d3418 (run 38546425533).

**`story/s1-missing-target-test` 9e21d87: PASS** (tests only; my addendum 1 should-fix). Three tests: a frozen file
deleted, a frozen file renamed, and a frozen config section removed. In each case `verify` names the target and
`version_of` raises `ChangedAfterFreeze`.
- My plant (a missing target not counted as changed): **3 failed**.
- Full suite (token unset): 2,853 passed. Ruff, format (634 files) and imports (641): clean.
- `git merge-tree` with current `main`: clean.

## Addendum 3 (merge check, 35f6f46: `s1-missing-target-test`)

**MET.**
- 35f6f46 has parents c8ab4f3 (`main`) and 9e21d87 (the passed tip), and it equals my recomputed merge. 898f1af
  equals its recomputed merge too.
- The only code change since my last check is `tests/evaluation/test_missing_target.py`.
- CI on 898f1af (run 38549236262) was in progress when I wrote this; I confirm it at my next check.

**Confirmed:** CI is green on 898f1af (run 38549236262).
