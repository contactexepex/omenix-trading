# Judge 74: D2 start-of-day playbook (branch, before merge)

Date: 14 Oct 2026 (UTC). Branch `story/d2-start-of-day` at d22e134. Claims: `reviews/claude/response_72_d2-rule-evaluation.md`
addendum 2. Cross-checked with E6 (judge 73, c264ccd).

## Verdict: FAIL, one must-fix. Approvals from the next session are right; pauses from the next session are not

**Gates:** `tests/playbook` 246 passed (my run, `python -B`). The loader change and both new tests read correctly.

### What is right

`status_on(day)` takes each version's latest registry change dated before the day. So:
- `approved_on(day)` gives a version approved during the session to Book 1 only from the next session, and it stays
  in shadow that day;
- `shadow_on(day)` takes candidates registered before the day.

This matches E2's common opportunity set and makes a day rebuildable. My agreement with the approval half is reasoning
only (same rule as E2, judge 72).

### Must-fix: a pause must stop new entries at once

`test_a_pause_on_the_day_takes_effect_from_the_next_session` asserts that a version paused by `hard_loss_rule` on the
day is still in `approved_on(day)`. That means Book 1 may open a new trade in a version the hard-loss rule stopped that
morning.

The builder's reason is "the same day had only one decision at about 15:00, so no new trade is lost". It does not hold.
A pause dated today can come before that 15:00 decision:
- E6's scorecard runs whenever it is called (the claims' own limit 4). A morning run after yesterday's loss writes a
  pause dated today.
- The owner can pause a version at 10:00 after finding a defect.
- After E6 merges, a drifted version (judge 67) is removed only by `approved()`, which D2 no longer calls. It stays
  tradable until the scorecard pauses it, and even then for the rest of that day (judge 73, must-fix 4).

Nothing downstream stops it either. E4's `EntryDesk` does not check the playbook status (I read `fno/desk/entries.py`).
D2 is the only gate.

**Risk manager's rule (the fix, reasoning only):**
- A version may trade on day D only if it was `paper` at the start of D **and** is still `paper` now **and** is not
  drifted.
- Approvals wait for the next session; every stop (paused, retired, drift) is immediate.
- In code: `approved_on(day)` must also require that the current status (file and latest row) is `paper` and that the
  version is not in E6's `drifted`. The existing test changes to: a pause on the day leaves `approved_on(day)` empty.
  Add one more test: an evaluation on the day of a pause chooses nothing for that version.
- Rebuilds stay stable for audit: the registry row and its date record when the stop happened.

**Which branch changes:** this one. E6 then adds one end-to-end test through D2's evaluator (judge 73, must-fix 4).
Merge order: this fix first, then E6 after `main` is merged into it and the full suite runs on the merged tree. The
`loader.py` conflict between the two is real: `git merge-tree` reports it. Both add fields to `Playbook`.

### Shadow side

A candidate retired on the day stays in shadow for that day. That is harmless: there is no book money in it, and it
is at most one more forward-test entry. I accept that as built.

## Claims vs reality

| Claim | Reality |
|---|---|
| "a hard-loss pause made during a session also takes effect from the next session ... no new trade is lost" | False when the pause is written before 15:00 (above) |
| "E6 must still stop new entries at once if it pauses before that day's decision; that is E6's design point" | E6 cannot. It writes the pause, and only D2 reads it. So the fix belongs here |
| Mutations `<=` and the evaluator reading `approved()` are caught | Consistent with the tests I read; not re-run |
| E2's `approved_on` should call `Playbook.approved_on` (one rule) | Agreed (DRY). E2's set may keep a version paused today, as I said in judge 72; it is Book 1's gate that must drop it |

## Project rules

Small change in place. The story text is amended with the date and source. No new composition root.

## Addendum 1 (round 2, branch 93efd01 = fix e23a92c plus a merge of main with no code): PASS

**The must-fix is met.** `approved_on(day)` now requires `paper` at the start of the day (latest row dated before it)
**and** `paper` after every row dated on or before it (`status_through`). So:
- an approval or resumption on the day waits for the next session;
- a pause or retirement on the day stops new entries at once.

The tests cover a hard-loss pause, an owner pause and a retirement on the day. Each makes the evaluation on that day
choose nothing, and the day before is unchanged. A same-day resumption waits.

**Gates (my runs, `python -B`, caches cleared):**
- full suite: 2,258 passed;
- ruff, format (489 files) and imports: clean;
- `git merge-tree` with current `main`: clean.

**My plants (5, `tests/playbook`): all caught.**

| Plant | Result |
|---|---|
| The start-of-day half dropped | 2 failed |
| The "through the day" half dropped | 3 failed |
| "Through" reading `<` instead of `<=` | 3 failed |
| The evaluator reading `approved()` again | 1 failed |
| The shadow test reading "through the day" | 1 failed |

**Two notes (information, reasoning only; not blocking):**
1. **A rebuild can disagree with the live day.** "A rebuild of the day gives the same set" holds unless a stop is
   written later on that same day: after the 15:00 decision, but dated the day. The live run traded, and a later
   rebuild of the day says "stopped". The recorded decision (D3) is the truth for that day. Audits that replay a day
   should know that a same-day stop after 15:00 shows as a difference. Only a time on registry rows would remove it.
2. **The drift exclusion is not here yet**, as the builder says. After E6 merges, a drifted version must also be
   dropped from `approved_on` (judge 73 must-fix 4). That is E6's condition, not this branch's.

**Verdict: PASS.** After the merge I check `main` against 93efd01 and CI.

## Addendum 2 (merge check, a0a8eef)

**MET.** a0a8eef has parents d88d2c7 (main) and 93efd01 (the passed tip), and it equals my recomputed merge of the
two. CI `checks` is green on a0a8eef (run 38504327736).
