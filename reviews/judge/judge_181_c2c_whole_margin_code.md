# Judge 181: C2c code, the stressed margin multiplies the whole margin (judge G)

- **Judged:** `story/c2c-whole-margin-stress` at `01d39e4d51368f2bcae44ae728983077e10bf636` (builder session
  01Vm1WnH8i9waM8EJG8zwWqg). Lane 1, money and risk. The text was PASSed in judge 174 addendum 1; ChatGPT review 117
  accepted it (response 169). The claims are in `reviews/claude/response_173_c2c-whole-margin-code.md`, which is being
  renamed to 175 because the number collides; the code was judged as it is.
- **Verdict: FAIL**, on one process should-fix: the claims file lacks the builder self-review that quality rule 3
  requires. The code itself is correct. Every criterion is MET on my own evidence, and all six mutations I planted are
  caught. Once the self-review is stated, I expect a PASS with no code change.

## The diff

There is one term in each copy, and nothing else in `fno/`:

- `fno/risk/margins.py`: `stressed` and `at_entry` add `factor * self.exposure`. `_span` and the STR1 cap are
  untouched.
- `fno/checks/validity_margin.py`: `stressed_per_lot` adds `factor * exposure` after the cap.
- `fno/constants.py`: the record label `STRESSED_MARGIN_STRESSES`.
- `fno/risk/capital.py`: the module text only.
- `initial()` is still `stressed(1.0)`, so the broker's figure is unchanged.

## Criteria

| # | Criterion | Builder's claim | Judge's own evidence | Result |
|---|---|---|---|---|
| 1 | Five rows to the paisa, C2 and C4, real 14 Oct rows, lot 65 | Five rows, including CCS 300 at 52,260.42 | `tests/risk/test_whole_margin_stress.py` checks broker, stressed (C2 and C4) and at-entry figures with `round(·, 2) ==`. The values equal my own recomputation from the fixture in judge 174 and its addendum. It passes on the commit | MET |
| 2 | SF and SC = k × initial; BF ≥; CCS and PCS between; all ≥ broker | All 47 real rows | The parametrized test over every fixture row has those exact branches. It passes | MET |
| 3 | C2 = C4; mutations in both copies caught | k 1.0 and 2.0 (new) plus 1.45 (STR1b's existing test); six mutations caught | I planted each mutation alone, ran `tests/risk tests/checks` and reverted. All six were caught. Clean tree: 744 passed. Details below | MET |
| 4 | Cap bounds the SPAN part; never below broker; LC and LP unchanged | Yes | The credit-spread cap test still applies the cap only to the SPAN part. LC and LP are 0 at entry. Criterion 2's test covers "never below broker" | MET |
| 5 | Record label pinned | Exact string | `test_manager.py:55` pins "scan and exposure (owner, 15 Oct 2026; story C2c)" exactly | MET |
| 6 | Every changed pinned figure listed with its recompute | 12 rows | I checked each by hand. 107,300 = 1.45 × 9,000 + 1.45 × 65,000. 105,125 = 1.45 × 72,500. 174,000 = (12,000 + 75,000) × 2 and 162,000 = (6,000 + 75,000) × 2. CCS 100: 6,893.25 + 42,830.87. Every assertion stays an exact or `approx` equality, so none is loosened | MET |
| 7 | Gates | 6,153 passed, ruff and imports clean | ruff check, ruff format and `check_imports` are clean on the commit. The full suite gives 6,144 passed, 8 failed and 1 error. **The same 9 tests fail on main (`bc5796c1`)** in this session, because this clone is shallow (`git rev-parse --is-shallow-repository` = true) and the freeze and back-fill tests read git history. The branch adds no new failure and 161 new passes | MET (the 9 are environmental) |

The six mutations, each planted alone and caught:

| Copy | Mutation | Failing tests |
|---|---|---|
| C2 | exposure not stressed in `stressed` | 118 |
| C2 | exposure not stressed in `at_entry` | 28 |
| C2 | premium stressed | 67 |
| C2 | cap applied to the exposure | 52 |
| C4 | exposure not stressed | 77 |
| C4 | premium stressed | 46 |
| C4 | cap applied to the exposure | 41 |

## The orchestrator's point: CDS and PDS now carry k on their exposure

**Confirmed.** For CDS and PDS the STR1 cap is 0 (debit row) and the broker's span is `max(0, scan − NOV)` = 0 (NOV
equals the scan on the real rows), so the capped span is 0. At entry the figure is therefore `1.45 × 29,538.53` =
42,830.87, up from 29,538.53.

That follows directly from the passed text: "The exposure is outside the cap: it is charged on the short legs'
notional". C2c criterion 2's debit clause holds too: 42,830.87 = k × initial(). The renamed test ("no stress reserve
on its premium") is accurate, and its arithmetic identity still checks that the premium is not stressed.

## Findings

### Should fix (process, quality rule 3)

1. **The claims file does not report the builder's self-review.**
   - Rule 3: "Before reporting, the builder runs independent code-review agents (correctness and silent failures) on
     its diff and states in its claims file what they found and what it fixed or why not."
   - `response_173` has no such section.
   - **Fix:** run them and add the section to the claims file (renamed 175). No code change is expected. The diff is
     small enough that I found nothing such a review would.

### Notes

- Rule 6 (real output sample): the five-row test runs the committed code on NSE's real 14 Oct rows and prints the
  figures in the claims table. That serves as the sample; no live output is involved.
- Rule 8 after the merge: the orchestrator's end-to-end dry run should show one decision record with the new label and
  a stressed margin about 45% higher than before.

## Project rules

- **Money safety:** every stressed figure rises or stays the same, and none falls below the broker's (`k ≥ 1` is
  enforced by the settings). No order path is involved.
- **Engineering rules:** the files are under 350 lines, the constant lives in `fno/constants.py`, and the duplication
  between C2 and C4 is intended (C4's independence) and pinned by the agreement test.
- **Register:** this builder owns the C2c row.

## Addendum 1: re-judge at `6353bf68565cafd0204a2c4a133e8e2fc289ab86` (judge G)

**Verdict: PASS.** The fix reached me from the builder. I re-judged it as part of the judge and builder loop and report
the verdict to the orchestrator.

- **Should-fix 1 (rule 3 self-review) is accepted.** The claims (renamed `response_175_c2c-whole-margin-code.md`) now
  carry the section: one independent agent, given only the diff, the passed text and the claims.
- **The self-review caught something I missed.** STR1b's written `stress_reserve` contradicted the new code, so my
  statement above that "I found nothing such a review would" was wrong:
  - **STR1b's text:** "LC, LP, CDS and PDS have stress_reserve 0", and CCS/PCS "at most width − credit".
  - **After C2c:** the reserve includes `(k − 1) × exposure`.
  - **My recomputation:** 0.45 × 29,538.53 = 13,292.34 for CDS 200, PDS 300 and CCS 100. For CCS 100 the SPAN
    extra stays capped to the broker's 6,893.25, because the cap of 2,564.25 is below it. LC and LP remain 0.
- **The fix is correct and within scope.**
  - A new test pins each reserve, and CDS and PDS at entry are pinned as a number (42,830.87).
  - The rule documents get accurate "superseded by C2c/C2d" notes, with no criterion rewritten:
    - STR1b's reserve paragraph and criterion 1;
    - C2's judge-75 sentence;
    - A14's judge-75 bullet.
  - These are lane-1 rule-document edits, judged here. They match C2c's passed text: the exposure is outside the cap.
- **No `fno/` file changed** (`git diff 01d39e4d 6353bf68 --stat -- fno` is empty).
  - On the fix tree, `tests/risk tests/checks tests/scoreboard` give 782 passed, and ruff is clean.
  - `capital_tied` (S2's capital figure) is unchanged; only the reported `stress_reserve` and scoreboard B's
    `stress_reserve_days_rs` rise, as the claims state.
- **For the merge:** C2d's branch is built on `01d39e4d`, so it needs `6353bf68` merged in. That fix is docs and tests
  only.
