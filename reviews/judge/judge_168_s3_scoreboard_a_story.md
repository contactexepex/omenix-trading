# Judge 168: S3 scoreboard A, story text revision 1 (judge G)

- **Judged:** `story/s3-scoreboard-a` at `2b2c41346fd3bef437b03597d9b4a56b25a49857` (builder session
  0185gR5DmoDh2zBAvgRU4CEB), quality rule 1 (story check before code). Only the S3 changes on top of S6's PASSed text
  (judge 158 add. 1, `a18a6bed`): `docs/stories/S-scoreboards.md` S3 section, a WORK_REGISTER row and a plan row. The
  orchestrator gave no number; 168 was the next free one on main.
- **Read:** CLAUDE.md, docs/JUDGE.md (quality rules), DESK_DECISIONS rows 156 (keep it simple), 170 and 177 (miss
  caps), `research/evaluation/PROTOCOL.md` (`scoreboard_a_standardisation`, `uncertainty_criterion`), and every code
  line the text cites.
- **Verdict: FAIL (text):** 1 blocking, 2 should-fix and 4 minor. The design is sound and simple. It reuses S2's
  bound, E4's pricing, E7's settlement and E2c's Drive board, and every code citation is accurate. The fixes are
  wording.

## Citations checked (all accurate)

| Text says | Code |
|---|---|
| Slot and cash rules `max_open_trades`, `margin_room` | `fno/playbook/allocation.py:18` `SLOT_RULES, CASH_RULES` |
| "unproven:" limit | `allocation.py:72-77` |
| C4 block: action "no trade" while outcome "chosen" | `fno/playbook/decision_record.py:76-79` `_action` |
| "refused, input not usable" | `fno/risk/manager.py:66` |
| Time exit: last trading day at least N days before expiry | `fno/playbook/opportunities.py:43-46` `last_on_or_before` |
| Only the time exit is enforced | `fno/playbook/exit_terms.py` docstring |
| Touch, all units or none | `fno/desk/pricing.py:55-64` |
| `NO_TRADE_ID`, `common_pack_sha256` in records | `decision_record.py:19, 22` |
| `worst_rs` negative, at the book's lots | `decision_record.py:55` |
| Board B to Drive under E2c | E2c branch, `E-paper-desk.md:738` |
| S2 bound: n < 20 gives null, 20 gives a bound; risk 1 gives the mean | `fno/scoreboard/uncertainty.py:32-47` (BLOCK_DAYS 20) |

The risk rules are classified completely: all 10 rule names in `fno/risk/profile_settings.py:22-33` appear in the
text.

## Findings

### Blocking

1. **`stress_loss` and `exposure_limit` are account limits, but the text calls them trade-level rules (skip).**
   - `StressLoss` is the "combined stress loss of the book's open trades ... plus the proposal" (`fno/risk/rules.py:45-47`).
   - `ExposureLimit` is "the account's loss ... every position valued from its mark" (`rules.py:82-84`).
   - So a refusal from either can come purely from the book's other open positions: the same account state the text
     already removes for `bucket_cap` and `open_risk_cap`.
   - **Path:** this happens in normal running. A book holding a few positions near its stress limit gets each new
     trade refused, and A scores those as skips (0). That biases A against the books that trade more, the opposite of
     A's purpose (S1: "sizing and account state ... are removed").
   - **Fix:** say which. The simplest is to count both as account limits (take). Keeping the book's own rule means
     re-checking the one-lot trade alone, against an empty book, and counting it a skip only if the trade alone
     breaches the rule. Add a criterion 7 fixture for each case.
   - `max_loss_per_trade` is per trade and correctly a skip. (At more than one lot it could pass at one lot; every
     version is `lots: 1` today, so that is a note only.)

### Should fix

2. **Holm cannot be done with `lower_bound` as written.**
   - `lower_bound` returns a fixed 5th-percentile bound (`uncertainty.py:15, 47`).
   - The protocol says "Holm's correction across them sets each claim's one-sided level" (`PROTOCOL.md:131`). Holm
     needs either per-claim p-values, or bounds at the step-down levels (5%/m, 5%/(m−1), ...).
   - **Path:** at every review where three books and their pairs are tested.
   - **Fix:** state the method. Either `lower_bound` takes a percentile and the claims are checked step-down at the
     Holm levels, or a bootstrap p (the share of resamples at or below 0) goes through Holm. Add a criterion with
     known answers, for example 3 claims where one passes at 5% but fails at 5%/3.
3. **The per-book series' days are not defined.**
   - "Its series puts each action on its decision day."
   - The text does not say whether days with only skips (0, 0), or with no opportunity, are in the series. That
     changes the block bootstrap (which days fall in a block), the "shorter than 20 days" null and the 120-day sample.
   - **Fix:** one line. The suggestion is: every observed session of the book, zeros included, several takes on a
     day summed, as S2's `DailySeries` holds every trading day. Add it to criterion 8.

### Minor

4. Criterion 7 says Book 3's verdict before F7 reads "undecided, operations". But design 6 counts as misses only "no
   run collected" days, and does not list the empty F7 port. Say that a day with no F7 entry counts as a miss, or
   that Book 3 is "not available" until F7 exists.
5. Criterion 6, "exits at the next snapshot, dated that day": say "dated the session it fills", to avoid reading it
   as back-dated.
6. Design 3: a structure without a defined maximum loss would give a division by zero or by infinity. If D1 already
   refuses undefined-risk versions, cite that line; otherwise list such takes apart.
7. Criterion 2 could add one take that is "not filled" (scored 0, listed), so the known-answer example covers that
   path.

## Gap list check

- The builder's gap list covers design 12.5, 13.5, rows 162, 168 and 170, S1's items, E2c's privacy rule and F9's
  sharing. Each row points to a design item or criterion that exists.
- Missing from it: S1's Holm sentence (finding 2) and the account-versus-trade split for the stress and exposure rules
  (finding 1).

## Project rules

- **Reuse:** no duplication. S2's bound, E4 pricing, E7 settlement and S6's functions are reused. F9 is shared
  through one module, and no new composition root is added.
- **Work register:** the S3 row is added by this builder.
- **Order:** code waits for E2c, which is correct, since the board goes to Drive.
- **Simplicity:** six modules' worth of design for an M story is proportionate. Nothing is built for unrealistic
  cases.

## Addendum 1: re-judge of text revision 2 at `1ea46646929803a771e27dda821d7a2b1b1b5fcd` (judge G)

**Verdict: PASS (text).** I judged only the S3 changes (commit `22fd8369`). The rest of the range is main merged in.

| # | Fix | Re-judge |
|---|---|---|
| 1 (blocking) | `stress_loss` and `exposure_limit` become account limits (take), with fixtures for each alone and a skip for `max_loss_per_trade` with `bucket_cap` | **Accepted.** It matches the rules' account-wide inputs (`rules.py:45-47, 82-84`). The claim that neither is in the books' profile today is true: the `config.yaml` `risk.profiles.books.rules` list on the branch has no `stress_loss` or `exposure_limit`. Taking them as account limits rather than re-running the risk check on an empty book is the simpler choice (row 156) |
| 2 (should fix) | `uncertainty.py` is split into the resampler plus two readers (S2's bound unchanged, and a one-sided bootstrap p = share of resampled values at or below 0), with Holm step-down on the p-values | **Accepted.** See the checks below the table |
| 3 (should fix) | Series days: every observed session, skip-only and no-opportunity days as (0, 0), not-observed days left out, up to the last decision day whose actions have all closed; known answer 25 − 3 = 22 days | **Accepted.** It is consistent with S2's every-day series and fixes the 20-day null and the 120-day count |
| minors | Book 3 before F7: "not observed: F7 not built", outside the miss cap, verdict "undecided, F7 not built"; exit "dated the day it fills, never backdated"; a fixed maximum loss cited (`docs/design_v2/03_layers_factory_desk.md:106`, "fixed at entry"), with "maximum loss unknown" listed apart; a not-filled take added to criterion 2 | **All accepted** |

Checks on finding 2:

- **The single-claim equivalence is exact.** With R = 10,000 resamples, the nearest-rank 5th percentile is the 500th
  smallest value. p < 0.05 means at most 499 values are at or below 0, which holds exactly when the 500th smallest
  value is above 0. The strict inequalities match on both sides, including ties at 0.
- **The Holm known answer is right.** For 0.010, 0.030 and 0.040: 0.010 < 0.05/3 = 0.0167 passes; 0.030 ≥ 0.05/2 =
  0.025 fails and stops the test, so 0.040 is never tested.

**On the orchestrator's design point (one Holm implementation in `fno/scoreboard/uncertainty.py`, also used by F9):**
agreed, it is DRY, and owner row 201 gives F9 Holm across roles. Two conditions, notes for the code review:

- **(a)** The Holm step-down takes a plain list of p-values, so F9 can pass its own p-values without the resampler.
- **(b)** S2 is merged code, so the split must leave every existing S2 test in `tests/scoreboard/` unedited and
  passing. The judge checks that at the code review.
