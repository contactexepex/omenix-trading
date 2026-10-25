# Judge 260: D4 code, Book 2's authority envelope (story/d4-envelope-code at 2f4c94ef)

Judge B, 16 Oct 2026. Lane 1 (decides trades; C4). Claims: `reviews/claude/response_247_d4-envelope-code.md`. Story
text: D4 in `docs/stories/D-playbook-decisions.md` (judge 207 addenda; ChatGPT 130 answered in response 212). The
owner decided on 16 Oct (DESK_DECISIONS row 239) that the code starts now, switched off until an envelope exists.

**Verdict: FAIL.** One should-fix: C4's "eligible" set is the playbook's approval list, not D2's eligible set, so
`choose_strategy` can trade a version whose own rule did not fire that day.

## What the orchestrator asked

| Question | Result | Evidence |
|---|---|---|
| Book 1 byte-unchanged in behaviour | MET | `PlaybookMode`'s new `lots_rule` defaults to `exact_lots`, the old `==`. No `fno/books/book1*`, `evaluate.py` or `candidates.py` file changes. Book 1's tests are unchanged |
| No path lets Book 2 trade without a valid, hash-matched envelope | MET | `EnvelopeMode.checks`: no file gives "no trade envelope" and returns. The file hash must equal the active D6 row's `trade_envelope:<name>-v<n>` component (missing gives `none`, so False). The verdict must be `allowed`, so shadow-only and forbidden both fail. `ValidityChecker.check` appends the mode's checks to the report, and any False fails it |
| It is off today | MET, twice over | no `playbook/envelopes/` folder exists, and C4's adapter (`validity_adapter.proposal_of`) never sets `rule_default`, so even with an envelope every Book 2 trade fails "no rule default given" |

## Criteria (story D4)

| # | Result | Note |
|---|---|---|
| 1 | MET | table tests; an unlisted action is forbidden (`TradeEnvelope.status`) |
| 2 | MET | lots above the version's, a width outside its set, another structure, a changed fingerprint: refused at `permits` and C4 |
| 3 | MET | `resolve`: shadow-only keeps the account at the rule default and the choice as shadow |
| 4 | MET | hash against the registry row (temporary registry test) |
| 5 | MET | C4 calls `permits` itself |
| 6 | MET | `rule_default is None` with a choice is forbidden ("never creates one") |
| 7 | MET | `NON_EMPTY` for Book 2 in `validate_record` (write-time only; no Book 2 records exist, so no stored record is affected) |
| 8 | MET | the traded version's envelope governs (`_verdict(self.envelopes.get(choice.version), ...)`) |
| **9** | **NOT MET** | see the should-fix |

## Should-fix: "eligible" must be D2's eligible set, not the approval list

`EnvelopeMode` passes `proposal.approved` to `permits` as `eligible`. That is `playbook.approved_on(day)`: versions
whose **status** is `paper` on the day (`validity_adapter.py`, `loader.py:56`). The story says `choose_strategy`
chooses "which of the day's simultaneously eligible `paper` versions trades (**D2's eligible set**)". Criterion 9 says
"C4 verifies, independently of the decider, that the chosen version was in that day's eligible set (D2)". D2's set is
the versions whose rule **fired** and whose candidate survived (D2: "fire when all conditions hold; build the
structure ... run C2 checks").

The difference is concrete:
1. Versions A and B are both `paper`; A's rule fires, B's conditions are unmet that day.
2. The rule default is A. The decider picks B at one of B's widths.
3. C4 then passes: B is `approved`, B's envelope allows `choose_strategy`, the rule default is not None, and B's
   structure, width, lots and shape are B's.

Book 2 then trades B on a day B's own thresholds said no. That is exactly what the envelope's last row forbids ("any
threshold, feature ...: a new playbook version through the research loop"). C4 is meant to block it even when F5's
own check is skipped (criterion 5).

The test for criterion 9 checks an *unapproved* B, not an approved B that did not fire, so it does not catch this. The
fix is the builder's design: C4 must receive the day's D2 eligible set from D2's evaluation and check
`choice.version` against it, plus a test with an approved but not-fired B refused. One option is a proposal field the
adapter builds from the day's outcomes whose rule fired with a built candidate.

**A condition of the same kind, for switching on (recorded, not a should-fix today):** C4's `rule_default` must also
come from D2's own evaluation, never from the decider or its record. The actions are derived from the choice against
the rule default (deviation 2), so a decider-supplied rule default equal to its own choice would always read
`follow_rule`. Today the adapter sets none, so Book 2 fails closed. The story that switches Book 2 on (F5) must fill
both fields in C4's adapter from D2.

## Rulings on the five stated deviations

1. **`playbook/envelopes/` instead of beside the playbook file: ACCEPT.** `loader.py:124` globs `FILE_PATTERN`
   directly in `playbook/`, so an envelope beside it would be read as a strategy and refused. Strong evidence.
2. **Derived actions, no `action` field: ACCEPT.** A derived action cannot disagree with the terms. It is only as
   sound as the rule default, hence the condition above.
3. **Reference terms on a version switch (the widest width and the version's lots): ACCEPT.**
   `structure_spec.py:35, 62` enforces "widest first, no repeats", so `widths[0]` is the widest, and D2 tries widths in
   that order (`candidates.py:64`).
4. **C4 checks the file against D6; D6 checks `served`: ACCEPT.** D6 already unscores any differing served key.
   `served_envelopes` builds those keys from the same hashes. Not repeating it in C4 is DRY, and C4 still fails closed
   on a changed file.
5. **`PlaybookMode` takes a lots rule: ACCEPT.** One copy of the six checks; the default keeps Book 1 exact.

## Changes to other owners' files (C4's and D3's): OK

`validity_modes.py` (the lots parameter), `validity_proposal.py` (one defaulted field), `checks/wiring.py` (Book 2 maps
to `EnvelopeMode`; `validity_modes(root)`) and `decision_record.py` (Book 2's non-empty fields) are each minimal and
in D4's scope. Book 1 and Book 3 behave as before. I agree with them, subject to the should-fix above.

## Mutations (real cases, all caught)

- `envelope_registered` always True: 1 test fails.
- The eligibility test in `permits` removed: 2 tests fail. They catch an unapproved B, not the not-fired case above.
- `at_most_lots` without the upper bound: 1 test fails.
- `_terms_problem`'s lots-above check removed: 2 tests fail.

## Notes only

- A malformed envelope file raises `EnvelopeError` out of `mode.checks` (C4 does not catch it), so Book 2's run stops
  loudly instead of recording a failed check. It is fail-closed either way. A named `CheckResult` would be kinder once
  envelopes exist.
- `ValidityProposal.rule_default: object | None` is untyped. `BookTerms | None` under `TYPE_CHECKING` would say what
  it is.
- The D4 register row's file list still says `playbook/*.envelope.yaml`. Update it to `playbook/envelopes/` and the
  files actually changed.

## Gates (run by me on 2f4c94ef)

`env -u FNO_SLACK_BOT_TOKEN python -m pytest -q -n auto -p no:cacheprovider`: 7,208 passed. `ruff check`: clean.
`ruff format --check`: 1,281 files already formatted. `check_imports`: clean.

## Addendum 1: story/d4-envelope-code at 917ee25a (fix 2cd7df07)

**Verdict: FAIL.** The fix is right in shape, but its eligible set still holds one kind of version D2 refused.

What changed:
- `DayEvaluation.eligible` = the book's versions whose outcome is `CHOSEN` or `NOT_CHOSEN`;
- `validate_chosen` passes it to the validator, and `ValidityProposal.eligible` (empty by default, so fail closed)
  carries it to C4, where `EnvelopeMode` checks against it;
- a test: an approved, not-fired B is refused, then passes once B fires;
- a damaged envelope is now the named `envelope` check;
- `rule_default` is typed `BookTerms | None`, and the switch-on condition is written on the field and in
  `envelope.py`;
- the register paths are corrected.

| Item | Result |
|---|---|
| A not-fired B refused | MET (test; my plant "C4 back to `approved`" fails 1 test) |
| `NO_TRADE` never eligible | MET (my plant adding `NO_TRADE` fails 1 test) |
| Notes of judge 260 | all applied |
| **Eligible = fired with a candidate that survived D2** | **NOT MET**, see below |

### Should-fix: `NOT_CHOSEN` includes a version D2 refused by its own per-strategy rule

`Decision.NOT_CHOSEN` is "a valid candidate that lost its slot, cash or risk check to the ranking". In
`Allocator.allocate` it is also given by `_before_risk` for the **unproven limit**: "an unproven strategy (fewer than
20 completed paper trades) may hold at most 1 open trade" (D2; `allocation.py:75-80`, `refusal[0] = True`). That
refusal has nothing to do with losing to A; B is refused on its own. C4 does not re-check the unproven limit (grep:
nothing in `fno/checks` or `fno/risk`).

Path, once Book 2 is switched on:
1. B is unproven and already holds one open trade.
2. Today A fires and is chosen; B fires and is `NOT_CHOSEN` ("unproven ... at most 1").
3. `eligible` = {A, B}. The decider picks B. F5 computes B's C2 verdicts (B's own outcome has none), and C4 passes:
   B is eligible, permitted, and its envelope allows `choose_strategy`.

Book 2 then holds two open trades of an unproven strategy, which D2's rule (design 3.2) forbids. The other
`NOT_CHOSEN` reasons are covered: a slot lost to A is exactly what `choose_strategy` trades, and a cash or risk refusal
is caught by C4's `risk_verdicts` and limits.

The fix is the builder's. Either leave refusals of a version's own rule out of `eligible` (D2 knows the reason), or
have C4 re-check the unproven limit independently. The second keeps C4 independent of D2's labels. Add a test: an
unproven B holding its one trade, `NOT_CHOSEN` for that reason, is refused as Book 2's choice.

### Gates (run by me on 917ee25a)

7,212 passed (`-n auto`, Slack token unset). `ruff check`: clean. `ruff format --check`: 1,281 files already
formatted. `check_imports`: clean. D5's head d3d31558 carries this fix, but not yet D5's own should-fix (judge 263).

## Addendum 2: story/d4-envelope-code at 35126eb0 (fix 094f7a97)

**PASS.** `DayEvaluation.eligible` now keeps only `CHOSEN` or `NOT_CHOSEN` outcomes that reached C2 (`o.risk is not
None`). A candidate refused by its own version's limits before C2 (the no-trade threshold, the unproven limit:
`allocation._before_risk`, risk `None`) is never eligible. A C2 refusal stays eligible, which is right: a slot lost to
A is what `choose_strategy` trades, and B's own C2 verdicts are then required and re-checked by C4 (`risk_verdicts`,
limits).

- Tests: an unproven B (3 completed, 1 open) is `NOT_CHOSEN` "unproven", so eligible is {A}; a B losing the last
  slot gives {A, B}.
- My plant (drop the reached-C2 condition) fails 1 test.
- The builder proposes option 2 (C4 re-checking the unproven limit from E5's counts) for F5's switch-on. I agree that
  belongs there, as reasoning; record it with the switch-on condition already written on `ValidityProposal`.

**Gates (run by me on 35126eb0):** 7,371 passed. The 3 failures are `tests/risk/test_manager.py` (two) and
`tests/risk/test_stress_factor.py::test_the_repository_seed_row_is_read_by_c2_and_c4`. They fail identically on
main since `df9bfaff` (A14c's stress factor 2.1 against tests pinned to 1.45; judge 268), not D4's. `ruff check`:
clean. `ruff format --check`: 1,317 files already formatted. `check_imports`: clean. D4 goes to ChatGPT next (rule
9).
