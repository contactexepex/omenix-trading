# Judge 83: story C4, hard-validity checks (branch, before merge)

Date: 14 Oct 2026 (UTC). Branch `story/c4-hard-validity` at 3f311f8 (7e1bc8c merged with main; draft PR #96). Claims:
`reviews/claude/response_83_c4-hard-validity.md`. Story: `docs/stories/C-code-roles.md` C4.

## Verdict: FAIL, three must-fixes

The independent arithmetic is good:
- a payoff grid in place of the proposer's formula;
- charges read from the table directly;
- 12 reference vectors;
- the override always refused;
- books 2 and 3 failing closed.

But:
- **my own wrong proposal passes**: a wrong lot size with a consistent claim;
- three of C2's limits are trusted, not recomputed;
- tampering with the snapshot's sidecar is untested.

## Gates (my runs, `python -B`, caches cleared)

- Full suite: 2,649 passed. Ruff and imports: clean.
- `git merge-tree` with `main`: clean.

## The story's own check: my new wrong proposal

**Wrong lot size, consistently claimed.**
- The proposer prices a correct SF for NIFTY's old lot of **75 units** (the current lot is 65), and its claimed
  maximum loss is consistent with 75 units: Rs 4,056.23 against the correct trade's Rs 3,540.57.
- **C4 passes it.** `ValidityProposal.lot_size` comes from the proposal, and C4 recomputes the loss with the same
  number of units, so a wrong lot size is never seen.
- A wrong lot size scales every rupee of risk, margin and P&L, and lot sizes change (NSE revises them).

**Must-fix 1:** check the lot size against an independent source: NSE's own contract data for the day, or the
committed `config.yaml` `lot_sizes` with its date and source. Add a seeded wrong proposal with a lot of 75.

## My plants (`tests/checks` and `tests/decisions`, 129 tests)

| Plant | Result |
|---|---|
| The loss tolerance at Rs 5 | caught (4 failed) |
| The legs' cutoff not checked | caught (1 failed) |
| STT charged on purchases too | caught (33 failed) |
| Exit charges left out of the maximum loss | caught (34 failed) |
| The "permitted on the day" check off | caught (2 failed) |
| The date check off | caught (3 failed) |
| **The sidecar (meta) hash not compared** | **not caught** |

**Must-fix 2 (criterion 4):** the sidecar holds the capture's start time, which the date and cutoff checks use. A
sidecar rewritten to move a late capture before the cutoff must fail. Add a test with a tampered sidecar and the quote
file intact.

## The orchestrator's points: rulings

1. **"All C2 limits": must-fix 3, for all three trusted limits, not only margin and stress.**
   - Today C4 recomputes the maximum loss per trade and the open-trade count. It takes the drawdown brake, the stress
     limits and the margin room from C2's recorded verdicts (`risk_verdicts_ok`, a boolean).
   - That is not independent: a C2 bug that passes a trade passes C4 too. Criterion 1 ("a limit breach is blocked")
     and the story's "all C2 limits" are not met.
   - C4 must recompute each from raw inputs with its own arithmetic:
     - the drawdown brake from the book's committed ledger;
     - the stress losses from the legs, on its own pricing grid;
     - the margin room from the margins file and the account.
   - Margin is where today's A14 work found real errors. Write it on A14's three-part format (scan, NOV, exposure;
     judge 75) once A14 merges, or now on the current format with the test updated when A14 lands.
   - One seeded breach per limit.
2. **The contract with E3: they fit, on one condition.**
   - C4 runs inside D3's decision run, on the common pack's A4 snapshot (`PackCaptures` with
     `PackSnapshotSchedule`). Those are the mids D2 priced with, and C4's verdict is stored in the record
     (`validity.c4`).
   - E3 fills at the 15:15 execution capture, whose mids differ from the 15:00 ones. **E3's `ValidityGate` must read
     the committed decision record's completed C4 pass.** It must never re-run C4 against the execution capture: that
     would fail every leg's "price equals the mid" check and block every trade.
   - Say this in both stories. E3's next round must implement the gate that way, with a test.
3. **The monthly expiry as the latest listed expiry of its month in the snapshot: accepted for now, as a stated
   limit.**
   - A4 records only the monthly chains it chose, so the rule agrees with A4. But it is not independent of A4's
     expiry choice: if A4 picked a wrong expiry as "monthly", C4 would accept it.
   - Should fix: check against NSE's own listing (A5's listed expiries from the F&O file).
4. **My new wrong proposal:** the lot size of 75, above. Not caught; must-fix 1.

## Per criterion

| # | Criterion | Result |
|---|---|---|
| 1 | Seeded wrong proposals blocked, a limit breach included | **PARTLY**: 17 seeded ones are caught, but the trusted limits and the lot size are not checked (must-fixes 1 and 3) |
| 2 | A correct proposal passes with every check's numbers | MET (3 structures) |
| 3 | No path turns a failure into a pass | MET (`override` raises for owner, desk and judge) |
| 4 | Tampered and absent evidence fail | **PARTLY**: the quote file's hash and a missing file are tested; the sidecar is not (must-fix 2) |
| 5 | At least 10 reference vectors, to Rs 0.01 | MET (12; I did not recompute them by hand) |
| 6 | Constitution mode | Fails closed until D5 (`WaitsFor`); not checkable yet, as stated |
| 7 | Book 2 envelope | Fails closed until D4; as stated |

**Independence:** `validity_money.py` imports nothing from `fno.costs`, `fno.research_engine` or `fno.risk` (test, plus
the builder's fresh-interpreter check). My plants on the charge formula are caught by the reference vectors.

## Project rules

- New modules in `fno/checks/`, wired in `fno/checks/wiring.py` (listed in CLAUDE.md).
- D3's `validity.c4` is filled.
- No orders and no secrets.

## Addendum 1 (round 2, branch b446d09): the three must-fixes MET; not yet PASS (one new wrong proposal of mine passes)

**Must-fix 1, lot size: met.**
- The lot size and the monthly expiries now come from NSE's own F&O file of the previous session (`NewBrdLotQty` per
  expiry; the newest file within 7 days, else the check fails closed). The proposer's settings and A4's chain choice
  play no part.
- **My round-1 probe re-run:** the lot-75 case now fails `lot_size`, and the correct trade passes.
- The monthly-expiry should-fix is done by the same file.

**Must-fix 2, sidecar: met.** A sidecar whose `started_at` is rewritten after the commit fails on its SHA-256 (test).

**Must-fix 3, every owner limit recomputed: met.** Each is computed from raw inputs:
- **drawdown brake:** from the E1 ledger and overrides, with C4's own high-water mark; an owner restart when the brake
  was not in force fails closed;
- **stress and exposure:** with C4's own Black-76 on the committed snapshot;
- **margin room:** on A14's three-part file, with the dated multiplier applied to the scan only (judge 75).

The independence guard is extended. My plants:

| Plant | Result |
|---|---|
| The multiplier applied to the netted figure | caught (2 failed) |
| Drawdown `<` relaxed to `<=` | caught |
| Stress ignoring the held trades | caught |
| The restart guard off | caught |
| **The margin room's own-liability term dropped** (judge 77's "never looser" case) | **not caught** |
| The listing lookback widened to 30 days | not caught (minor) |

**Stated limits, accepted:**
- **Stress disagreeing with C2 near a limit:** C4's stress can disagree with C2's there, and then C4 blocks. That is
  the safe direction.
- **Every trade blocked on margin until A14 merges:** `main`'s `margins.csv` still has the pre-A14 header and no
  multiplier, so `margin_room` blocks every trade until A14 merges. That fails closed, but **no Book 1 trade can pass
  C4 until A14 does.** A14 is still FAIL (judge 77).
- **Open trades' terms from the D2 book:** these terms decide each trade's margin row, and C4 does not re-derive them.

**My new wrong proposal for this round: not caught (must-fix).**
- A correct SF whose first leg carries the contract name `NIFTY26102725100CE` while its strike is 25,000 passes C4.
- C4 looks quotes up by (expiry, strike, type) and never checks that the contract name the desk fills and marks by is
  that contract.
- E4 prices by strike but records and later marks by the contract name, so the book would hold one contract and mark
  another.
- **Fix:** each leg's contract name must match its expiry, strike and type, checked against the snapshot's own
  contract identifier or NSE's symbol format. One seeded case.

**Should fix:**
- one test that drops the margin room's own-liability term (it must fail);
- the lookback bound;
- the merge with `main` now conflicts in CLAUDE.md, because E3 changed the same composition-root line. Resolve it at
  the merge.

**Gates:**
- full suite: 2,709 passed;
- ruff and imports: clean.

One small round for the contract-name check and its test.

## Addendum 2 (round 3, branch bf0d4af = fix 3764572 plus a merge of main): PASS

**The must-fix is met.** Each leg's name must now equal the snapshot's `contract_id` for its (expiry, strike, type).
Seeded case 18 is my wrong proposal (`NIFTY26102725100CE` on the 25,000 CE leg). It fails exactly that leg: the test
asserts the failure set equals `{"leg 2026-10-27 25000 CE"}`.

The builder's extra finding is correct and serious: the misnamed leg was checked at 25,000 but priced by name at
25,100 in stress and margin. Requiring the names to match closes both.

**Should-fixes met:**
- the own-liability mirror test (open BF, new SF);
- the lookback bound (8 days refused, 7 used);
- CLAUDE.md keeps both composition-root lines (`fno/checks/wiring.py` for C3 and C4, `fno/desk/daily_wiring.py` for
  E3).

**Gates (my runs, `python -B`, caches cleared):**
- full suite: 2,778 passed;
- ruff, format (618 files) and imports (625): clean;
- `git merge-tree` with current `main` (e41d988): clean.

**My plants (9, `tests/checks` and `tests/decisions`): all caught.**

| Plant | Result |
|---|---|
| Name check off | 1 failed |
| Name compared on its first 5 characters only | 1 failed |
| Own liability dropped from the margin term | 1 failed |
| Lookback widened to 30 days | 1 failed |
| Regression from round 2: stress multiplier on NOV too | 2 failed |
| Regression: liabilities term dropped | 1 failed |
| Regression: drawdown `<` to `<=` | 1 failed |
| Regression: stress ignores held trades | 1 failed |
| Regression: restart guard off | 1 failed |

**One should-fix for a later round (reasoning only, not blocking).**
- `Evidence.mids()` takes every two-sided quote. It ignores A4's validity (no same-day trade, a crossed book, a zero
  bid). `parity_forward` then takes the forward from the single strike whose call and put mids are closest.
- One bad quote at that strike moves every stress figure on that expiry, in either direction.
- At-the-money quotes at 3 pm are almost always valid, and C3's per-leg rule still gates the fill. So the risk is
  small, but a looser stress could pass a trade.
- Read `valid` and use only A4-valid quotes for the forward. Book 1's market (E5) already does.

**Accepted limit (unchanged):** `margin_room` blocks every trade until A14's rows exist.

**Verdict: PASS.** After the merge I check `main` against bf0d4af and CI.

## Addendum 3 (merge check, dafbebe)

**MET.**
- dafbebe has parents f67c090 (`main`) and bf0d4af (the passed tip).
- It equals my recomputed merge of the two (`git diff` empty).
- CI `checks` is green on dafbebe (run 38529262438).

## Addendum 4 (should-fix, branch `story/c4-a4-valid-quotes` e01a939): PASS

My addendum 2 should-fix is met, with one rule in one place.
- C4 reads every quote row through E4's `quote_from_row`. Its `a4_problem` is A4's rule: two-sided, not crossed,
  sizes on both sides, and the recorder's `valid` (a trade today).
- An unusable quote has no mid. So it never feeds the parity forward, marks or stress, and a proposed leg on it fails
  ("quote not usable by A4's rule").
- I read the rule: it is consistent with Book 1's market (E5 also requires `valid`, `bid > 0` and `ask >= bid`).

**My plants (4, `tests/checks`, `desk`, `decisions`): all caught.**

| Plant | Result |
|---|---|
| The mid ignores `a4_problem` | 6 failed |
| The leg's A4 check off | 4 failed |
| `a4_problem` not read from the row | 7 failed |
| The recorder's `valid` ignored in A4's rule | 8 failed |

**Gates (my runs, `python -B`, caches cleared):**
- full suite: 2,788 passed;
- ruff, format (619 files) and imports (626): clean;
- `git merge-tree` with current `main` (f6e4b9d): clean.

**Consequence (agreed, risk manager, reasoning only).** If an open trade's leg has no A4-usable quote at 15:00, C4
cannot mark the book, so there is no new entry that day. Exits are unaffected. Failing closed is the right default.

The builder's fallback (the previous session's NSE settlement as the mark) is reasonable but unmeasured. Decide it only
after real captures show how often it happens. I will count it on the first weeks of real 3 pm captures: legs of open
trades with `valid = false`.

**Verdict: PASS.** After the merge I check `main` against e01a939 and CI.

## Addendum 5 (merge check, b03c4ef)

**MET.** b03c4ef has parents 2602bda (`main`) and e01a939 (the passed tip), and it equals my recomputed merge.
81c9c86 joins it with 9811203 (E3's gate tests) and equals its recomputed merge too.

CI on 81c9c86 (run 38533124620) was in progress when I wrote this; I confirm it at my next check-in.

**Confirmed (addendum 5 follow-up):** CI is green on 81c9c86 (run 38533124620). My own full-suite run on 81c9c86 gives 2,792 passed.
