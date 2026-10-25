# Judge 78: story D6, version registry and evaluation segments (branch, before merge)

Date: 14 Oct 2026 (UTC). Branch `story/d6-version-registry` at 20f62ed (code 04fc20a). Claims:
`reviews/claude/response_76_d6-version-registry.md`. Story: `docs/stories/D-playbook-decisions.md` D6.

## Verdict: FAIL, two must-fixes (both small, both found by probe)

The ancestry rule and the pause logic are right, and my plants on them are caught. But a decision can still be scored
when it does not say which model served it, and a version may be registered in the very commit that holds the
decision.

## Gates (my runs, `python -B`, caches cleared)

- Full suite: 2,278 passed. Ruff and imports: clean.
- `git merge-tree` with current `main`: clean.

## My plants (`tests/versions`, 15 tests): all 6 caught

| Plant | Result |
|---|---|
| The row's own commit no longer has to be an ancestor | caught (1 failed) |
| `registered_in_commit` no longer has to be an ancestor | caught (1 failed) |
| A mismatch never pauses | caught (1 failed) |
| `starts_on < day` instead of `<=` | caught (3 failed) |
| The registry's order check off | caught (2 failed) |
| Decisions not sorted (arrival order) | caught (2 failed) |

## Per criterion

| # | Criterion | Check | Result |
|---|---|---|---|
| 1 | A version registered in a commit after a decision cannot be its version (git ancestry) | Met for "after": both the row's adding commit (read from git with `log -S`, never from the file) and `registered_in_commit` must be ancestors of the decision's commit, so back-dating `starts_on` does not help. **But "before" is not enforced: `git merge-base --is-ancestor X X` is true.** My probe: a version row and a decision record in **one** commit, and that decision is scored as `book2_hybrid/v1`. Design 13.5 says a version is "registered and committed **before** its first counted decision" | **PARTLY** (must-fix 1) |
| 2 | A different served model is `unscored`, and later decisions stay unscored until a new version | Met when the decision reports the model. **My probe: a decision with `served = {}` (D3 filled nothing) is scored `book2_hybrid/v1`, and so is one that reports only the prompt.** The check compares only the keys the decision sends, so a fallback is hidden by leaving the model out | **PARTLY** (must-fix 2) |
| 3 | Deterministic segments; scoreboards group by them | Sorted by (book, day, decision ID). Plant V6 is caught; the test gives the decisions in reverse order | MET |
| 4 | Registry rows never edited | `append` keeps the old bytes. The repository test `test_the_repository_registry_was_only_ever_appended_to` fails on any rewrite in git history (CI) | MET |

## Must-fix

1. **Strictly before.** A version counts for a decision only if the row's commit is an ancestor of the decision's
   commit **and is not that commit** (likewise `registered_in_commit`). Add one test with both in one commit.
2. **The served set must cover the version.** Every key in the active version's `components` must be present in
   `DecisionFacts.served` and equal to it. A missing key is `unscored` with the reason "served <key> not reported",
   and it pauses scoring like a mismatch. Add one test with `served = {}` and one with the model missing.

## The orchestrator's points

- **The append-only refusals:** met (criterion 4).
- **Ancestry with back-dating:** met for later commits; the same-commit case is open (must-fix 1).
- **The per-book pause until a new version, independent of arrival order:** met. A pause in one book leaves the
  others scored (test).
- **`DecisionFacts` as D3's contract:** it is the right shape (book, day, decision ID, commit, served). Must-fix 2
  makes it safe against an incomplete D3. D3's story should state that `served` carries every component of the
  version, the served model taken from the API's answer and not from config.

## Claims vs reality

| Claim | Reality |
|---|---|
| "2278 tests pass" | Confirmed |
| "10 of 10 mutations caught" | Not re-run; my 6 are caught. My two probes found what no mutation covered |
| "Back-dating doesn't help" | True across commits; a same-commit registration still counts |

## Project rules

- New modules behind a `GitHistory` protocol, wired in `fno/composition.py`; `journal/versions.csv` starts with its
  header only.
- No orders, secrets or Slack.

## Addendum 1 (round 2, branch e239ba1): PASS

**Both must-fixes are met.** I re-ran my two probes on a temporary git repository:
- a version row committed in the same commit as the decision: now `unscored`;
- a decision with `served = {}`: `unscored`. One reporting only the prompt: `unscored`.

The code requires both the row's commit and `registered_in_commit` to be ancestors **and** different from the
decision's commit. It compares the union of the version's and the decision's keys, so a missing component is a
mismatch and pauses scoring.

**My plants (`tests/versions`, 18 tests): all 7 caught.**

| Plant | Result |
|---|---|
| The same commit allowed again | 1 failed |
| Only the served keys compared | 2 failed |
| `registered_in_commit` ignored | 1 failed |
| A mismatch never pauses | 3 failed |
| `starts_on < day` | 3 failed |
| The order check off | 2 failed |
| Decisions not sorted | 2 failed |

**Gates:**
- full suite: 2,289 passed;
- ruff, format (496 files) and imports: clean;
- `git merge-tree` with current `main`: clean.

**Verdict: PASS for e239ba1.** D3 must fill `served` with every component of the version, with the model taken from
the API's answer.

## Addendum 2 (merge check, c12137e)

**MET.** c12137e = 6f8c859 + e239ba1. It differs from a plain merge only in the conflict resolutions:
- `fno/cli.py` keeps both the `desk` and `versions` parsers;
- the README index.

CI `checks` is green on 0f4e888 (run 38510606597), which contains it. My full suite on 0f4e888: 2,368 passed.
