# Judge 567: T1d story text, the card names the steps that failed or were refused today

**Scope:** story/t1d-failed-steps at 73c1f201 (builder session_0145TfSwzmpk6MBrH92f5h4G): `docs/stories/T-cards.md`
section T1d and its Claims, plus a `docs/WORK_REGISTER.md` row. Docs only. Judge I (session_01MvZneCLZqBuiGyNxawdVee).
Lane 1. Round 1 of 2. I read R2 at story/o1-r1r2-step-safety e8dc9498.

**Verdict: FAIL.** 1 should-fix. The rest of the text is right.

## Claims checked
| Claim | Result | Evidence |
|---|---|---|
| The problem rule exists once, inline in `fno/daily/runner.py:61` with `PROBLEMS` at `:19` | MET | Both lines read as cited |
| R2's failed and refused are run-log statuses, committed after each step before the card | MET | See "Claim 2" below |
| The card's `RunLogReader` reads that same log, so nothing new reads git | MET | See "Claim 3" below |
| `fills` is the step that is refused | MET | R2's `NEEDS = {"fills": ("snapshot", "decisions")}` (`daily_run.py:75`); no other step can be refused today |
| Steps after the card are Out | MET, correctly | `DAILY_RUN_STEPS` puts `price_distribution` and later steps after `card` |
| Import direction | MET | `fno/cards` already imports `fno.desk.run_log` (`rule_checks.py:25`) |
| Gates (text-only rule, my run) | MET | Doc-reading tests 829 passed, 15 xfailed; record scan clean |

**Claim 2.**
- R2's `_run_step` logs `{"status": "failed", "reason": ...}`, and `_refused` logs `refused`.
- `DailyRun._step` records and commits the run log after every step, O1's day steps (the card among them) included. All of them go through `_step` in `run()`.
- The public form keeps `failed` and `refused` (`public_log.WORDS`) and turns the reason into a code such as `raised:KeyError`.

**Claim 3.** `RunLogReader` reads the same `journal/runs/<date>.json` (`rule_checks.py:45-68`). Its step order is the insertion order, which is the run order.

## Finding
1. **Should-fix: with R2, the card's T2 decisions line misreads a failed `decisions` step, and T1d does not cover it.**
   - **The cause:** T2's `DecisionOutcome` (`fno/cards/rule_checks.py`) treats every key of the `decisions` step's result as a book: `late = [b for b, r in result.items() if "run_id" not in r]`.
   - Before R2 a `decisions` step either held the books or did not exist (the run stopped). With R2, a `decisions` step that raises is logged, and committed, as `{"status": "failed", "reason": "raised:<Type>"}`.
   - **The effect:** the status section then shows "late or not committed: status, reason" as a final outcome. That line names two non-books and hides that the step failed. I checked the expression on that result: it gives `['status', 'reason']`.
   - The `snapshot` rule reads a failed step as "no valid execution snapshot (raised:...)" with `data_check_failed`, which fails closed. Only `decisions` misreads.
   - **Why it belongs here:** T1d is the story for "the card after R2", and its Context says R2 is why the card must change. R2 changes no card file, and no other story or register row covers this. T1d's new line would sit right under a wrong decisions line on the same card.
   - **Fix expected:**
     - T1d's scope gains a rule: when the `decisions` step's status is `failed` or `refused`, T2's decisions line says the step failed (for example "decisions step failed") with `data_check_failed`, never listing result keys as books. It uses the same `problem_steps` statuses.
     - Add a criterion and a test: a planted failed `decisions` result gives that line, never "status, reason".
     - Or name it Out with an owner and a register row, and say why the card may go live without it. I recommend in scope: it is the same reader in the same section, a few lines of code.

## Notes (no action required)
- `problem_steps` returns `(name, status)` pairs, while the runner prints names only. That is fine as long as its line is unchanged, as criterion 4 says.
- A failed step is "done" for `RunLog.done`, so a same-day rerun never reruns it. The card's line stays true for the day.

## Addendum 1: the new head b10c9c2d (diff 73c1f201..b10c9c2d), still round 1

**Verdict: FAIL** (unchanged). This head was pushed before the builder had read this verdict. It changes two things, and neither touches finding 1:
- **The line now uses the orchestrator's wording,** "Steps with problems today: ...". Accepted.
- **The Claims cite the orchestrator for refused steps and state the after-the-card limit.** Accepted; this is the same limit the Out section names.

Finding 1 (T2's decisions line misreading a failed `decisions` step under R2) stands for b10c9c2d. Doc-reading tests at b10c9c2d: 829 passed, 15 xfailed.

Minor (text): the changed line in the card-line bullet now runs past the file's usual width. Rewrap it.

## Addendum 2: round 2 at 9a6ba1c3 (diff b10c9c2d..9a6ba1c3)

**Verdict: PASS** (Judge I).

- **Finding 1: FIXED in scope.**
  - The new scope bullet, criterion 6 and test 5 make a `decisions` result whose `status` is a problem under O1's rule (the `problem_steps` set) give "decisions step <status> today" with `CARD_DATA_CHECK_FAILED`. Such a result is never read as books.
  - The planted R2 result `{"status": "failed", "reason": "raised:NotImplementedError"}` is the exact case I found.
  - The plant list adds "removing the decisions status check fails test 5".
  - Checking `status` is safe: a normal decisions result is keyed by book ids, and a book's own value (for example `NO_DECISION_LATE`) sits one level down, so a real result never carries a top-level `status`. T2's per-book tests stay as they are.
  - `refused` cannot happen for `decisions` today, since R2's `NEEDS` refuses only `fills`. Covering it costs nothing and keeps the one status set.
  - The snapshot check stays unchanged, correctly.
- **My minor (line width): withdrawn.** `T-cards.md` already has many lines over 120 characters, and no doc test enforces a width.
- **Gates (text-only rule, my run at 9a6ba1c3):** doc-reading tests 829 passed, 15 xfailed; the diff is Markdown only (`T-cards.md`, `WORK_REGISTER.md`).
- **For the code judge:** check that criterion 6's status test reads the same status set as `problem_steps` (one rule, not a second copy).
