# Judge 42: W11 item 3, the examples after the Sunday 1 Feb 2026 session fix

**Verdict: PASS for item 3.** The session fix is correct, every changed value is listed, and the new calendar check
bites. The orchestrator's question is answered separately below: yes, unadjusted prices make W11 examples wrong today,
and the contract does not say they must be adjusted. That is a should-fix for the separate corporate-action fix, not
for item 3.

**What I judged**
- **Repository:** `exepex/omenix-dashboard` at 996e764 (after design's 3a12c6c, merged as 348fe34).
- **Claims:** `reviews/claude/response_21_w11_item3_sessions_examples.md`.

## Checks run by the judge

```
$ python3 tools/api/check_contract.py     (openapi-spec-validator 0.7.2)
  contract: 70 paths (43 block endpoints), 82 block examples, 137 block schemas, 873 catalogued leaf fields, 58 planted breaks, 5 daily series on NSE's sessions
  contract: OpenAPI 3.1 valid; examples valid and current; catalog complete; screen rules hold; every planted break caught
$ python3 tools/api/examples.py --check   examples current
$ git diff --stat f3e7f5f 996e764 -- api/paths api/schemas api/examples/blocks.json api/examples/blocks-32.json
  (empty: no served schema changed; the frame, Home and chain examples are unchanged)
$ diff design/mockups/_platform/nse_sessions.csv exepex/trading research/data/calendar/nse_sessions.csv
  identical (one calendar; design's copy equals trading's)
```

### Against NSE's own files (fetched by me)

| Claim | NSE file | Value | Result |
|---|---|---|---|
| Nifty Pharma's 52-week low becomes its 1 Feb close, 21,535.30 | `ind_close_all_01022026.csv` | Nifty Pharma 21,535.3 (Nifty 50 24,825.45) | **confirmed** |
| The 1 Feb session exists | A1 calendar `2026-02-01,special` (FAOP/72352), and NSE's index file for that Sunday exists | – | confirmed |

## Item 3: decision

| Part | Judge's evidence | Decision |
|---|---|---|
| The examples regenerated from the session-fixed data | Checks green; the changed values match design's change list (the builder's script); the Pharma low verified against NSE | ACCEPTED |
| `check_calendar.py` (as_of on a session; daily series equal NSE's run of sessions) with 3 plants | Runs inside `check_contract` ("5 daily series on NSE's sessions"); 58 plants caught. It reuses the single vendored calendar, which equals trading's. | ACCEPTED |
| Stated limit: 34's `closes` and 33's 1Y figures carry no dates, so the example check cannot see their days | True. Those are guarded in design's fetch scripts (`sessions()`, `nse_calendar.py --check`) | ACCEPTED as a limit |

## The orchestrator's question: do the unadjusted prices make W11 examples wrong, and should the contract guard it?

**Yes, examples are wrong today (strong evidence for KOTAKBANK).** NSE's own equity files give:

| Date | KOTAKBANK close |
|---|---|
| 13 Oct 2025 | ₹2,152.10 |
| 1 Apr 2026 | ₹356.05 |
| 1 Jul 2026 | ₹400.45 |
| 12 Oct 2026 | ₹443.40 |

A large bank moving from about ₹2,150 to about ₹356 inside six months fits a 5:1 split, not an 80% fall. Adjusted, the
year-ago close is about ₹430, so the true 1Y change is about **+3%**. The served example `getScreenerStocksIndia_india`
shows **−79.15%** on its first page, with a 52-week high of 2,266. I did not check NSE's corporate-actions file
itself, so the split is inferred from the price path. The builder's other 87 rows are its pattern, unverified by me.

**Does the contract guard it? No.**
- The W11 screener and Markets schemas never say whether prices, period changes (`d1`…`y1`) and 52-week `h`/`l` are
  adjusted for splits and bonuses.
- The older company contract does say so (`api/schemas/company.yaml`: "split-adjusted sessions", plus an `adjusted`
  flag per bar).
- So a publisher can serve unadjusted figures and still pass every check, and the frozen notes (33 row 5: "% change on
  the close 1, 5, 21, 63 and 250 sessions back") do not settle it either.

**Expected, for the separate corporate-action fix (should fix there, reasoning only on the form):**
1. **The contract states the rule.** Every period change, 52-week high and low, and 1Y close series is adjusted for
   splits and bonuses as of the close, as in `company.yaml`.
2. **The publisher is guarded.** The publishing story (`TR-NSE-proposed`) adjusts using NSE's corporate-actions file,
   and its acceptance test includes a known split (KOTAKBANK: 1Y change about +3%, not −79%).
3. **No heuristic in the contract** (such as "h above 3 × p"). A real crash would trip it, and a small split would
   pass it. The definition and the publisher's test are the right guard.
4. **33 is rebuilt and the examples regenerated,** with the changed values listed, as was done for item 3.

## Addendum: the contract-side fix (omenix-dashboard c48860a, `response_22_w11_split_adjusted.md`)

**Points 1 to 3: ACCEPTED. Point 4: pending.** The builder's pushback (no per-row `adjusted` flag) is **ACCEPTED**.

**Checks:** `check_contract` and `check_mapping` are green.

**What the diff says now:**
- **`PeriodChange`:** "% change on the close … back, that past close adjusted for every split and bonus since (NSE's
  corporate-actions file …), so a 5:1 split is not a −80% year".
- **`ScreenerStock`:** `h`, `l` and RSI are computed from adjusted closes; `p` and `v` are as traded.
- **`OverviewQuote`:** `closes`, `hi52` and `lo52` are adjusted (index levels have none).
- **The catalog sources** are updated.
- **`TR-NSE-proposed`** names the KOTAKBANK case (about +3%) as an acceptance test.

**Decisions on my four expected points:**

| # | Expected | Decision |
|---|---|---|
| 1 | The rule stated in the contract | ACCEPTED |
| 2 | The publisher adjusts from NSE's corporate-actions file, with KOTAKBANK as a named test | ACCEPTED, as story text. It is built in design's new `_platform/nse_actions.py` and in `fetch_nse.py`; the backend comes later. |
| 3 | No heuristic | ACCEPTED |
| 4 | Rebuild 33, regenerate the examples, list the changes | **Pending.** Today the served example still shows KOTAKBANK `y1` −79.15% and `h` 2,266, which now **contradicts the contract's own definition**. It must close with design's rebuild (the builder says so). Until then, W11's examples carry a known wrong value. |

**The pushback: no per-row `adjusted` flag. ACCEPTED** (reasoning, checked).
- Frozen 33 and 34 have no element that shows adjustment.
- `check_mapping` requires every field to serve an element, so a flag would be a field with no screen.
- `company.yaml` has an `adjusted` flag because its bars are raw sessions that a reader may re-adjust. Here the served
  figures are already derived, so the definition plus the publisher's test is the right guard.
- A visible "adjusted for a 5:1 split" marker would be a design change for the owner, as the orchestrator says.

## Addendum 2: point 4 re-checked (omenix-dashboard 000df7a, verified at 1dc47e3; `response_23`)

**Point 4: ACCEPTED.** Judge 42's should-fix is closed. There is 1 new minor finding, demergers, which my own point
1 left out.

**Checks:** `check_contract` reports 58 planted breaks, all caught, and 5 daily series on NSE's sessions.
`check_mapping` and `examples.py --check` are green.

**The served example now matches the contract's adjusted definition.** `getScreenerStocksIndia_india` serves
KOTAKBANK with `y1` +4.24, `h` 453.2 and `m3` 15.27 (443.40 / 384.65 = +15.27%).

**Actions against NSE's corporate-actions API** (fetched by me), and prices against NSE's equity bhavcopies:

| Symbol | NSE action | NSE closes (bhavcopy) | Served (adjusted) | Check |
|---|---|---|---|---|
| KOTAKBANK | 14 Jan 2026, split ₹5 to ₹1 | 13 Jan 2,132.60, then 14 Jan 421.00. 250 sessions back (7 Oct 2025): 2,126.90 | 1Y close 425.38, so `y1` = 443.40 / 425.38 − 1 = **+4.24%**. `h` = 2,266 × 0.2 = 453.20. | equal |
| ANGELONE | 26 Feb 2026, split ₹10 to ₹1 | 25 Feb 2,489.90, then 26 Feb 246.50. 7 Oct 2025: 2,250.50 | 225.05, so **+34.30%** | equal |
| BHARATRAS | 12 Dec 2025, split ₹10 to ₹5 **and** bonus 1:1 | 11 Dec 9,900, then 12 Dec 2,657. 7 Oct 2025: 9,936 | 9,936 × 0.5 × 0.5 = 2,484.00 | equal |
| BESTAGRO | 16 Jan 2026, split ₹10 to ₹1 **and** bonus 1:2 | 7 Oct 2025: 354.25 | 354.25 × 0.1 × 2/3 = 23.62 | equal |
| DELPHIFX | 13 Feb 2026, split ₹10 to ₹2 **and** bonus 2:1 | 12 Feb 228.13, then 13 Feb 16.70. 7 Oct 2025: 239.91 | 239.91 × 0.2 × 1/3 = 15.99 | equal |
| BANKNIFTY1, AASTHA, CUB, BEML, MOLDTKPAC | Ex-date and ratio as in `actions.csv` | – | – | equal |

**Notes on the checks:**
- **Bonus factors are right in every form present:** 1:1 = 1/2, 1:2 = 2/3, 1:3 = 3/4, 2:1 = 1/3, 4:1 = 1/5.
- **Same-day split and bonus are compounded,** not just one applied.
- **The change list** has 317 values on 99 stocks, as claimed.

**My judge-42 estimate of "about +3%" was the wrong base, not a data error.**
- It used a calendar year back (13 Oct 2025).
- The contract's `y1` is 250 sessions back. Counting the 21 Oct 2025 muhurat session (NSE published an equity
  bhavcopy for it), that is 7 Oct 2025. The exact adjusted figure is +4.24%.

### Minor (new): demergers are not adjusted, so two stocks still show a corporate action as a crash

- **The contract's rule** (and my own expected point 1) covers splits and bonuses only. NSE lists demergers as
  corporate actions too.

| Symbol | Demerger (NSE) | Closes either side (bhavcopy) | Served 1Y |
|---|---|---|---|
| INDIAGLYCO | 2 Sep 2026 | 1,111.70 the day before, 236.20 on the ex-date | **−64.5%** (3M from 1,088.20) |
| DCMSRIND | 26 Dec 2025 | 172.16 on 24 Dec, 54.52 on the ex-date | **−76.3%** |

- **Why it matters:** a holder of these shares also received shares of the demerged company, so most of each "fall"
  is value moved, not lost.
- **Why it is not a simple fix:** a demerger has no fixed ratio in NSE's action record, so it cannot be scaled like
  a split.
- **Expected (reasoning only; owner or design decision):**
  - **Either** adjust demergers by the standard price factor: the ex-date's price-discovery base divided by the
    previous close.
  - **Or** state in the contract that demergers are not adjusted, and mark such rows (a design change).
- **Not blocking:** the contract as written is met.

**Also seen:** INDOTHAI shows −89.3% with no split, bonus or demerger on NSE since July 2025. That looks like a
genuine fall, and the contract is correct to show it.

**Not judged:** the same commit carries unrelated changes (Google Search Console's ownership file and the 36 home
page). I judged only the data fix.

## Addendum 3: demergers adjusted (omenix-dashboard 00abb11)

**ACCEPTED.** Addendum 2's minor is closed. There are 2 new minor findings on the edge cases.

**The method:** factor = the ex-date's opening price ÷ the previous close, from NSE's equity bhavcopies.

**Three cases against NSE's files** (`OpnPric` on the ex-date, `PrvsClsgPric` = the previous close):

| Symbol | Ex-date | NSE open / previous close | Factor | Builder's factor | Served now |
|---|---|---|---|---|---|
| INDIAGLYCO | 2 Sep 2026 | 225.00 / 1,111.70 | 0.202393 | 0.202393 | 1Y close 182.41 → `y1` +75.32% |
| DCMSRIND | 26 Dec 2025 | 51.00 / 172.16 | 0.296236 | 0.296236 | 1Y close 51.32 → −20.05% |
| VEDL | 30 Apr 2026 | 289.50 / 773.60 | 0.374224 | 0.374224 | 1Y close 176.58 → +50.02% |

All three factors equal NSE's numbers exactly.

**The "special pre-open" claim (some evidence; partly true).**
- **Where it is true:** NSE's own page on special pre-open sessions and its FAQ cover stocks **with derivatives
  contracts** on the ex-date after a corporate restructuring such as a demerger. There, the session's discovered
  price is the price NSE itself uses for index adjustment (the demerged entity enters at the T−1 close minus that
  price). For F&O stocks (VEDL; Tata Motors, HUL), the open is that discovered price.
- **Where it is not:** INDIAGLYCO and DCMSRIND have no derivatives, so their open comes from the normal pre-open call
  auction. It is still an exchange-discovered price, but noisier. DCMSRIND opened at 51.00 and closed at 54.52 (+7%)
  on its ex-date.
- **Why the method is still right:** it is the only price-based factor NSE's files allow, and better than no
  adjustment. The README should say "pre-open price (special session for F&O stocks)".

**Minor findings:**
1. **TMPV's recorded reason is wrong.** `actions.csv` says "not adjusted: no trade on the ex-date". NSE's
   bhavcopy for 14 Oct 2025 shows the stock **did** trade, under its old symbol TATAMOTORS: open 400.00, previous
   close 660.75, factor 0.6054.
   - **No wrong figure is served:** the TMPV series starts after the symbol change (239 sessions), so its 1Y is
     null.
   - **But** its 52-week high and low (419.00 / 272.20) cover only 239 sessions, without saying so.
   - **Expected:** follow NSE's symbol-change file into the old symbol's history, or record the reason as "symbol
     changed" and treat a 52-week window shorter than 250 sessions like the 1Y.
2. **The pre-open wording** (above): name the special session only for F&O stocks.

HEGAM (14 sessions, a new listing) is correctly left unadjusted.

Sources: [NSE: special pre-open session](https://www.nseindia.com/products-services/equity-market-special-pre-open-session),
[NSE FAQ on the special pre-open session](https://nsearchives.nseindia.com/web/sites/default/files/inline-files/FAQs%20on%20Special%20Pre-Open%20Session.pdf).
