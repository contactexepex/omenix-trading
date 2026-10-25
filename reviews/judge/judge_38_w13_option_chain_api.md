# Judge 38: story W13, the API contract and data catalog for the option chain (32)

**Verdict: PASS.** All 6 of W11's criteria, applied to 32, are MET. There are no blocking or should-fix findings and 2
minor findings.
- **The builder's doubt:** ACCEPTED as no contradiction.
- **The builder's three owner questions:** judged below. One of the orchestrator's defaults ("all" = every listed
  strike) would change a frozen contract row, so it needs the owner.

**What I judged**
- **Repository:** `exepex/omenix-dashboard` at 38c913f.
- **Claims:** `reviews/claude/response_15_w13_option_chain_api.md`.
- **Story:** W13 in trading's `docs/stories/X-cross-repository.md`.
- **Mockup:** `design/mockups/32-option-chain`, frozen as of 9d9c401. `notes.md` changed since then only by the
  sign-off header (faf9bbd).

## Checks run by the judge

```
$ python3 tools/api/check_contract.py     (openapi-spec-validator 0.7.2)
  contract: 70 paths (43 block endpoints), 81 block examples, 130 block schemas, 873 catalogued leaf fields, 39 planted breaks
  contract: OpenAPI 3.1 valid; examples valid and current; catalog complete; screen rules hold; every planted break caught
$ python3 tools/api/check_mapping.py      mapping: zero gaps both ways; no endpoint mixes two independent blocks
$ python3 tools/api/examples.py --check   examples current
$ node tools/check_code_size.mjs          every file within 350 lines
$ git diff b1f3abf 38c913f --stat -- api/paths api/schemas api/examples
  5 files changed, 5191 insertions(+)      (additions only; the one removed line in openapi.yaml is "version: 2.2.0")
```

### The examples obey the frozen notes' rules (my own script over `blocks-32.json`)

All 7 expiries pass:
- `range` = spot ± straddle;
- `future` is set exactly when `monthly`;
- `monthly` is the last expiry of its month.

Both `rows` examples (21 and 45 rows) also pass:
- the ATM is the strike nearest spot, a tie going to the lower;
- the straddle is the ATM call close plus the put close;
- the break-even is strike ± close for every leg;
- the 2 untraded legs (weekly band) have IV and Greeks null.

**0 problems.**

### My plants, in memory through the builder's validator and `check_chain`

| # | Plant | Result |
|---|---|---|
| G8 | Chain rows served as `market: us` | **caught** (schema) |
| C1 | NIFTY 1M covered (21 of 21) but published null and incomplete | **caught** (`check_chain`) |
| C2 | NIFTY 5D value off by 0.5 | **caught** |
| C3 | The 3M day count overstated (40 for 29) | **caught** |
| G1 | `volume` 0 while IV and Greeks are kept | not caught (minor 1) |
| G2 | A weekly expiry carrying a `future` | not caught (minor 1) |
| G6 | A weekly marked `monthly` | not caught (minor 1) |
| G3, G4, G5, G7 | `range`, `atm`, `breakeven` or `pcr` inconsistent with their inputs | not caught (minor 2) |

## Criteria (W11's 1-6 applied to 32)

| # | Criterion | Judge's evidence | Result |
|---|---|---|---|
| 1 | Every element of 32 maps to one endpoint with a validated example; zero gaps; notes unchanged | Mapping zero gaps; 9 examples valid and current. I read the prose of every Elements row by hand (range, walls, PCR, ATM tie, Greeks blank, contract code forms, history `from` index, Buy/Sell reason): each is served by a field or a stated rule. Notes unchanged except the sign-off header. | MET |
| 2 | One fixture per shared endpoint; derived views documented | Every endpoint has examples from 32's one `data.json`. The 4 multi-block endpoints state why in `x-shared`. `in-one-look` is one block, as the template's one container shows. | MET |
| 3 | US absent by schema | All paths under `/markets/india/`; `market` is the constant `india`; every object closed; G8 caught | MET |
| 4 | History-dependent fields state coverage; null unless covered | `CoveredValue` and `PeriodCoverage` with if/then/else; `check_chain` recomputes from the series; my C1-C3 caught (including withheld values, the reverse of the builder's plants) | MET |
| 5 | Additive only | Diff above; `blocks.json` and `blocks-33-34.json` unchanged | MET |
| 6 | Checks green | All of the above; the builder reports web 372 tests (web/ unchanged in this commit) | MET |

## The builder's doubt: does publishing null contradict the frozen picture? No

- **The frozen picture** is drawn from 93 sessions, where 5D, 1M and 3M are all covered. On that data the contract
  publishes the same numbers.
- **Where they would differ:** only on a short history, which the mockup never shows. There its template would
  mislabel a partial period as "Three months".
- **W11 criterion 4 requires null when not covered,** so the contract is right and the mockup's clamping is a mockup
  shortcut.
- **Expected in the story that builds 32 in the app:** show "29 of 63 days" (or "—") for an incomplete period, and
  list it as a difference from the mockup. **ACCEPTED.**

## The three owner questions (the orchestrator's defaults)

1. **`strikes=all`.** The frozen `notes.md` row 8 reads "Strikes: … **all in the file (within 10%)**". The contract
   says `all (within 10%)`, which **matches the frozen row**. The orchestrator's default ("every listed strike,
   possibly 100+") would change a frozen contract row, so per the notes' own rule it needs the owner and a
   `changes.md` entry. That is not a builder decision. **My recommendation (reasoning only):** keep ±10% as signed
   off; strikes further out are rarely traded and would mostly show "no trade".
2. **Contract history for every contract.** The notes say "*In this mockup*, kept for the 21 strikes nearest the
   money", which is a mockup limit, not a rule. Keeping every contract is a superset and consistent with the
   contract, which answers an unknown code with 404 (`x-empty`). **Agree with the default.**
3. **Weeklies' 3 pm quotes.** These are outside 32's frozen scope (A4 records monthlies only). **Agree** they stay
   out until A4 records weeklies.

## Engineering standards

- New files are small and single-purpose (`examples_chain.py` 109 lines; schemas split into chain and history).
- Coverage reuses W11's `if`/`then` pattern and the shared `check_semantics.py` (DRY).
- No breach.

## Findings (minor)

1. **Rules the contract states are not enforced by the schema.**
   - The rules: IV and Greeks null when a leg did not trade (notes row 8: "Blank when the contract did not trade");
     `future` null for a weekly; `monthly` meaning the last expiry of its month.
   - Plants G1, G2 and G6 pass validation. The examples obey them, so this is a guard for the publisher, not a
     defect in the data.
   - **Expected:** `if`/`then` as for coverage (`volume: 0` ⇒ `iv`, `greeks` null; `monthly: false` ⇒ `future`
     null), plus a semantic check for `monthly`.
2. **Computed values are not cross-checked against their inputs:** `range`, `atm`, `straddle`, `breakeven` and `pcr`
   (G3, G4, G5, G7 pass). The examples are consistent today (my script). **Expected:** either `check_chain`
   recomputes them from `underlying` and `rows`, as it does coverage, or the publisher story (`TR-CHAIN-proposed`)
   lists them as its acceptance tests. Otherwise a backend bug in a computed figure reaches the screen unchecked.

## Addendum: the minors re-checked (omenix-dashboard 616d0e8, `response_19_w13_judge38_minors.md`)

**Both minors: ACCEPTED.** W13 stays **PASS**, with no open finding.

**Checks:** `check_contract` reports 54 planted breaks, all caught. Mapping, examples and code size are green. The
`api/examples` diff only adds the full-strike 27 Oct example (89 strikes); no existing example changed.

**My judge-38 plants, re-run** through the validator and the new `check_chain`:

| Plant | Caught by |
|---|---|
| G1 (volume 0 with IV and Greeks kept) | schema |
| G2 (a weekly with a future) | schema |
| G3 (range) | `check_chain` |
| G4 (ATM) | `check_chain` |
| G5 (break-even) | `check_chain` |
| G6 (a weekly marked monthly) | schema and `check_chain` |
| G7 (PCR, 27 Oct) | `check_chain` |

New plants of mine, all caught:
- straddle wrong;
- max pain wrong;
- call wall below spot;
- November's monthly moved to 17 Nov instead of the holiday-moved 23 Nov.

**Stated limit:** PCR, walls and max pain are recomputed only for the 27 Oct expiry, which has every strike. For the
other 6 expiries they are left to the backend story's acceptance tests. That is reasonable: the extract holds only 21
or 45 strikes for those expiries.
