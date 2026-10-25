# Judge 577: T1e story text, any failed or refused step turns the card's headline into a warning (story/t1e-card-warning at 2fa8f6f6a)

**FAIL, lane 1.** Round 1 of 2. Judge I, in its own session (session_01CHtddAzFcEdQh4HFiz3mqU), 24 Oct 2026.
Judged: `git diff 5cbd3c4c7 2fa8f6f6a`, which changes only `docs/stories/T-cards.md` (a new T1e section). I read it
against DESK_DECISIONS 24 Oct ("The card warns when any step failed"), T1's criteria and T1d's code at 5cbd3c4c7.

## Criteria (text checks)

| Check | Verdict | Evidence |
|---|---|---|
| Matches the owner's decision | MET | It covers every `failed`/`refused` step, a superset of "outside the rule checks"; the code changes too, so the warning is not left to the text alone |
| Trigger is O1's one rule | MET | Scope "Trigger" and criterion 8 name `problem_steps` through `RunLogReader`, as T1d does |
| Severity order | MET | `data_check_failed` > `hard_rule_breach` > `step_problems` > T1's code: a rule result is more specific than "a step failed"; the table and criterion 3 agree |
| Criteria testable | MET | Each criterion has an exact string or code; tests 1-10 and plants W1-W12 map to them |
| Facts cited | PARTLY | Verified: the ⚠️ glyph (`forecast_lab/page/verdict_words.py:24`), that the renderer prints the status lines right after line 1 (`render.py:33`), the `{"marked": False}`, `{"built": False}` and per-book `error` results with no `status` (`trade_marking.py:115`, `daily_steps.py:89,220`). Wrong: "no other module reads the card's code" (finding 1) and "line 1 needs T1's rule changed" (finding 2) |
| Gap list complete | NOT MET | Finding 1 |
| The builder's three open points stated plainly | PARTLY | Point 1 (failures with no status) and point 2 (problems that are not steps) are plain and routed. Point 3 gives a wrong reason (finding 2) |
| Doc-reading tests at 2fa8f6f6a | MET | 829 passed, 15 xfailed; record scan clean |

## Findings

1. **Blocking (rule 2): the dashboard contract rejects `step_problems`, and the text says nothing reads the code.**
   - The delivery file's `reason_code` (`fno/cards/issue.py:79`) is the dashboard card's `reason`
     (`tests/market_read_models/test_p1_t1_card.py:42`).
   - That field is a closed enum in the pinned contract, `contracts/omenix-dashboard/api/schemas/fno-card.yaml:39`:
     `[no_approved_strategy, weather_red, data_check_failed, risk_bucket_full, budget_stop, cost_wall,
     advocate_hard_rule, null]`.
   - `test_every_committed_delivery_record_fits_the_catalogs_card` checks every committed delivery against it, and
     `test_a_delivery_record_with_a_reason_the_catalog_lacks_fails` shows that an unknown code breaks `enum`.
   - So the first live card with `step_problems` turns `main`'s suite red, and the dashboard cannot show that day's
     card. The Scope's grep looked only in `fno/`, so it missed `tests/` and `contracts/`.
   - Fix expected: a criterion and a test for the contract, or an Out item with an owner and a register row. The
     contract is the dashboard's own (pinned from `exepex/omenix-dashboard`), so this means a dashboard contract
     change plus a re-pin before T1e goes live, and T1e's merge waits for it. Correct the "no other module" claim.
2. **Should-fix: the reason for putting the warning on line 2 is wrong, and the owner's real option is hidden.**
   - T1 criterion 1 says only "Every card's first line says PAPER ONLY" (`T-cards.md:82`). It does not say the line
     must start with it.
   - The TEST post's first line already puts text before it ("TEST — PAPER ONLY: ...", `issue.py:21`).
   - A prefix such as "⚠️ WARNING: desk steps failed. PAPER ONLY. ..." keeps PAPER ONLY on line 1 and puts the
     warning in the phone preview, which is what the owner asked for ("headline", "instead of hiding"). It would
     change only T1's tests, which check `startswith("PAPER ONLY.")` (`test_card.py:35`, `test_cli.py:48`).
   - Fix expected: state the constraint correctly, and give the owner the choice: a line-1 prefix, or line 2 with
     the preview limit. Either is fine once the owner picks one.
3. **Minor: say where the `Status:` line goes.** With a warning, the status section's first line becomes the
   warning, so `Status: ...` moves to line 3. Neither criterion 1 nor test 8 says this; add it.

## Plants

None (a text round). Plants W1-W12 are planned for the code.

## Notes (not findings)

- Pre-existing, for T2's owner: `hard_rule_breach` (T2) is not in the contract's enum either, so a day with a C4
  refusal already fails the same test. Finding 1's fix should cover both codes.
- Not checked: the dashboard repository itself (outside this session's scope). I checked only the pinned contract
  here.

## Addendum 1: round 2 at b673e0ddd (diff 2fa8f6f6a..b673e0ddd)

**PASS, lane 1** (Judge I, own session). The diff changes only the T1e section of `docs/stories/T-cards.md`.

| Round-1 finding | Verdict | My evidence |
|---|---|---|
| 1 Blocking: the dashboard contract rejects `step_problems` | FIXED | Criterion 10, test 11 and plant W13 are new: every card code from `fno/constants.py` must be in the pinned `fno-card.yaml` enum, with neither list hard-coded. The merge waits for the contract change and re-pin, now an Out item owned by a dashboard builder, with the re-pin steps from `contracts/omenix-dashboard/README.md:8-9`. The "no other module" claim is corrected. The builder's extra code `trade_fields_not_built` is real (`constants.py:332`) and missing from the enum (`fno-card.yaml:39`) |
| 2 Should-fix: the line-2 reason was wrong | FIXED | T1 criterion 1 is restated correctly, with the right citations. The owner gets options (a) line-1 prefix and (b) line 2, each with its phone-preview effect. The placement is one renderer function on a `CardWarning` value (criterion 11, plant W14), so the owner's choice is a one-place change |
| 3 Minor: where `Status:` goes | FIXED | Criteria 1 and 5: line 3 on a warning day, line 2 otherwise; tests 1 and 7 |

Checked again: the TEST banner stays the post's first line under both options (test 8). The gap list now names all
three findings. Doc-reading tests at b673e0ddd: 829 passed, 15 xfailed; record scan clean.

Minor wording (none blocks; fix in the code round):
- "judge I's recommendation" (twice, Placement (a)): round 1 said (a) fits the owner's word "headline" and that
  either option is fine once the owner picks. Better wording: "fits 'headline' (judge 577)". The owner decides.
- "and the dashboard itself through the read models": no module in `fno/market_read_models/` reads the card's code
  (my grep). It reaches the dashboard through the delivery file and the contract. Drop the clause.

For the code judge: test 11 is red by design until the re-pin. A code PASS needs the re-pin merged first and that
test green on the merged tree.
