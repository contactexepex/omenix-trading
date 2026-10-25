# Judge 43: story C2, risk manager

**Verdict: PASS.** All 7 criteria are MET.
- **Your limits are applied exactly as you decided** (`docs/DESK_DECISIONS.md`).
- **My own crafted proposals:** inside, outside and borderline. Their numbers equal my independent arithmetic to the
  paisa.
- **Fail closed:** the manager refuses every trade until you enter margins and a stressed-margin factor. That is the
  right default.

There is 1 item to fix **before paper trading** and 2 minor findings.
- **The item:** stress repricing uses Black-Scholes on spot, which the story text prescribes, while the project's IVs
  come from B1's Black-76 on the future. I measured a ₹1,000+ a lot error per leg in a no-move scenario. It is a
  design inconsistency for the orchestrator, not a builder defect.

**What I judged**
- **Repository:** trading `main` at be500e0, which contains C2 code fe77d79 (merged 6c8b959).
- **Claims:** `reviews/claude/response_51_2026-10-13-c2-risk-manager.md`.
- **Story:** `docs/stories/C-code-roles.md`, C2.

## Checks run by the judge

```
$ python -m pytest -q tests/risk                                94 passed
$ pip install -r requirements.txt; python -m pytest -q          1083 passed
  (before installing: 1 collection error, psycopg missing for P6's tests; it is declared in requirements.txt, so this
   was my environment, not a defect)
$ ruff check fno tests tools; python tools/check_imports.py     clean (237 files)
```

### Your limits in `config.yaml` `risk`, against `DESK_DECISIONS.md`

| Decision | Config | Rule |
|---|---|---|
| ₹10,000 maximum loss per trade, charges included | `max_loss_per_trade_rs: 10000` | B2's `PositionCosts.max_loss` (pads, every charge, worst-case exit) |
| At most 3 open trades | `max_open_trades: 3` | a 4th is refused |
| Brake: ₹30,000 below the closed-equity high, new trades only, you restart | `drawdown_brake_rs: 30000` | blocks entries; never closes a trade; restart only by a row in `journal/<book>/owner_overrides.csv` |
| Available cash = the lower of cash and marked equity, minus margin, minus premium reserved | E1's `fno/books/equity.py`, reused unchanged | `MarginRoom` checks against the cash **after** the proposal's entry |

Stress limit ₹30,000; exposure ₹15,000 for a 2% move and for +5 IV points (design 8.1's proposed values, labelled
"reasoning only").

### My crafted proposals, through `build_risk_manager` exactly as the app wires it

My own condors, with my own max-loss arithmetic (B2's formula: (width − credit) × units, plus entry charges at padded
fills, plus worst-case exit charges, plus all pads; charges typed from `config.yaml`):

| Case | Manager | Judge | Verdict |
|---|---|---|---|
| **Inside:** SC 25500/24500, 150-point wings, 1 lot | ₹6,256.20 | ₹6,256.20 | all 7 rules pass (stress worst: the 23 Mar 2020 replay ₹5,873.91; exposure ₹1,131 and ₹1,201; stressed margin ₹45,000 within cash ₹4,99,627.66 after entry) |
| **Outside:** the same condor with 300-point wings, 1 lot | ₹15,035.15 | ₹15,035.15 | refused by `max_loss_per_trade` only |
| **Outside:** 300-point wings, 2 lots | ₹29,881.51 | ₹29,881.51 | refused |
| **Borderline:** limit = ₹29,881.51 / limit − ₹0.01 | – | – | passes / refused |

**The brake:** high ₹5,20,000. Closed equity ₹4,90,000.00 gives "Rs 30,000.00 below its high … new trades wait"
(refused); ₹4,90,000.01 passes.

**Open trades:** with 3 open, a 4th gives "3 open; this trade would make 4 of at most 3" (refused).

### The fly-plus-condor hand case (criterion 4), recomputed

- **Fly marked value:** (−60 − 55 + 5 + 4) × 65 = −₹6,890.
- **At −8% (NIFTY 23,000):**
  - the fly's value at expiry is −200 × 65 = −₹13,000, so its loss from marks is **₹6,110**;
  - the condor's credit is 31 × 65 = ₹2,015, and its value is −₹13,000, so its loss from entry is **₹10,985**;
  - combined **₹17,095**. With 3 condor lots: 6,110 + 3 × 10,985 = **₹39,065**, above ₹30,000, so refused.
- **All equal the builder's values.**
- **`fno.analytics.bs_price` against my own Black-Scholes** at three points (ATM call and put, and an
  out-of-the-money put): equal to 6 decimals.

### Breaks (reverted; `git status` clean)

| # | Break | Risk tests failing |
|---|---|---|
| M1 | The brake uses marked equity instead of closed equity | 6 |
| M2 | Stress counts the proposal from its mark instead of its entry | **0** (minor 1) |
| M3 | Margin room leaves out the proposal's own stressed margin | 2 |

## Criteria

| # | Criterion | Judge's evidence | Result |
|---|---|---|---|
| 1 | Max loss 9,999 passes; 10,001 blocked with reason and numbers | Tests; my borderline at ₹0.01 | MET |
| 2 | A 4th trade blocked | My run | MET |
| 3 | The brake blocks entries, never closes trades, and re-arms 30,000 below the restart day | My run (just inside and just outside); `test_drawdown.py` (7 tests); M1 caught | MET |
| 4 | The fly plus condor stress equals the hand computation; blocked above 30,000 | Recomputed above | MET (see the pre-paper item for real expiries) |
| 5 | Exposure: a 2%-move loss above the setting is blocked | Test passes; numbers reported in my inside case | MET |
| 6 | Every rule has a just-inside and a just-outside test | Read in the tests; my own for max loss and the brake | MET |
| 7 | Two books are independent | `test_books.py` on real E1 accounts; `stress_positions` takes one book only | MET |

## The third composition root (`fno/risk/wiring.py`): justified?

**Yes.** It is a per-area root, like `fno/storage/wiring.py`. It holds only the risk wiring (the rules, B2's cost
model and the stressed-margin method), and CLAUDE.md now lists it. Splitting composition by area is design, not
squeezing: no long lines, no joined statements. The trigger was `composition.py` nearing 350 lines, but the result is
the right shape. `composition.py` is at 309 lines; the next story that adds to it should split it by area (the builder
says so too).

## To fix before paper trading (design inconsistency, routed to the orchestrator)

**Stress repricing must use the same model that produced the IVs.**
- **The two models:** the story's stress text says "reprices every leg … with `fno.analytics.bs_price` (Black-Scholes
  on spot)". But the project's IV model is B1's Black-76 on the same-expiry future (judge 26), adopted because
  spot-BS split call and put IVs by about 2 points.
- **The measurement:** on 12 Oct 2026, ATM 22350, Oct expiry, I fed B1's Black-76 IVs (14.51% / 14.47%) into
  `bs_price` on spot with **no move**:
  - the call reprices to 300.01 against its market close of 280.30: **+₹1,281 a lot**;
  - the put reprices to 226.40 against 243.25: **−₹1,096 a lot**.
- **The effect:** a zero-move scenario then shows a loss or gain of about ₹1,000 a lot per leg. For a short call
  spread or a condor side, that bias is about 10% of the ₹10,000 limit, and it is the stress rule that decides
  refusals.
- **The builder states the limit** ("C3/E4 should supply consistent IVs"), but the pricing model is C2's.
- **Expected:**
  - the stress engine prices through B1's `ImpliedVolModel` (Black-76 on the leg's future, rate only to discount),
    swappable in the composition root;
  - a test that a zero-move, zero-day scenario gives a loss of about 0 on real quotes;
  - the story text amended to match.

## Findings (minor)

1. **The proposal's pads and charges are not proven to count in the stress loss.** M2 (count the proposal from its
   mark) passes all 94 tests. The hand case enters at mids with zero charges and pads, so the entry and the mark
   coincide. Expected: one test with real charges and pads, where counting from the mark would pass but counting
   from the entry refuses.
2. **Owner inputs, so no trade can open yet** (fail closed, as designed):
   - margins per lot in `research/data/margins/margins.csv`, from Groww's calculator or NSE SPAN, with source and
     date;
   - a stressed-margin factor with its source and date.

   The builder's suggested factor of 1.5 is reasoning only. Check it on the calculator under a ±8% move before
   entering it.

## Notes (stated by the builder; agreed)

- Stale marks are recorded but do not block. That is C3's check. **If C3 is not built before paper trading, this is a
  gap.**
- Exit charges are left out of the stress losses but included in the per-trade maximum loss.
- Pending orders are not counted until E4.

## Addendum: the fix re-checked (trading c61fbbd, which merges ae113ec; `response_51` addendum)

**The before-paper-trading item: ACCEPTED. Minor 1: ACCEPTED.** C2 stays **PASS**. The only open item is minor 2,
the owner's margin inputs (fail closed, as designed).

**Checks:** `python -m pytest -q tests/risk` gives 99 passed.

**The model.** `StressEngine` now takes B1's `ImpliedVolModel`. `fno/risk/wiring.py` wires `Black76()`, so swapping
the model is one line in the composition root. Each leg is priced on its same-expiry future, moved by the
scenario. If that future is missing, the trade is refused.

**My own Black-76** (written independently of `fno`), on real 12 Oct 2026 quotes. The ATM strike is 22,350 and the
October future closed at 22,386.50. My implied volatilities, 14.51% for the call and 14.47% for the put, equal B1's.

| Scenario | Call: engine / mine | Put: engine / mine |
|---|---|---|
| No move, no days | 280.30 / 280.30 (its mark) | 243.25 / 243.25 (its mark) |
| +2% | 573.0434 / 573.0434 | 89.6035 / 89.6035 |
| −2%, +5 IV points | 181.0271 / 181.0271 | 590.5854 / 590.5854 |
| −8%, IV × 1.5, 3 days | 5.8974 / 5.8974 | 1,756.4752 / 1,756.4752 |

- **The ₹1,000-a-lot error is gone.** A zero-move scenario now values each leg at its mark. My own run gave an error
  of 0.0000.
- **The builder's test** `tests/risk/test_stress_real.py` checks the same thing on at least 20 real legs. It also
  keeps a guard: spot Black-Scholes with these volatilities is off by more than ₹1,000 a lot.
- **My no-future plant:** a market with no future is refused with "no usable NIFTY future for expiry 2026-10-27: the
  option cannot be priced". **Fail closed.**
- **The story text** (`docs/stories/C-code-roles.md`, lines 78 and 101-103) now says Black-76 on the same-expiry
  future and gives the reason.

**Minor 1: M2 is now caught.** I re-ran M2, which counts the proposal from its mark, by changing
`fno/risk/stress.py` to return `loss_from_marks`. The risk tests then give 1 failed, 98 passed. The failing test is
`test_the_proposals_pads_and_charges_count_in_the_stress_loss`. I reverted the change, and `git status` is clean.

**Limit (reasoning only).** The zero-move test is consistent by construction: the volatilities are inverted and then
repriced with the same model. That consistency is exactly the property required. My independent Black-76 table above
shows the pricing itself is right, not only consistent.
