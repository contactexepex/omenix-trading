# Judge 50: mockup 35-stock, focused check (owner signed off at omenix-dashboard 7b10cc0)

**Verdict: FAIL on 1 should-fix.**
- **The defect:** the US stock page shows its price forecast in rupees. Every other check passes.
- **The F&O block is exact:** all 3 futures and all 114 option legs equal NSE's 12 Oct file, with NSE's own contract
  codes.
- **The page is clean:** `check_page.js` is clean, and no model or vendor name or internal id appears in any of the 21
  gallery states.

**What I judged:** `design/mockups/35-stock` at omenix-dashboard 9585c3e (sign-off recorded; page as of 7b10cc0). The
focused check asked by the orchestrator, kept short for cost.

| # | Check | Judge's evidence | Result |
|---|---|---|---|
| 1 | Figures trace to the stock tool's records or NSE files; examples labelled | **NSE-sourced figures, checked against NSE's own files:** RELIANCE close 1,158.90, change −11.40 (previous 1,170.30); the F&O block below. **Stock-tool figures:** compared only with the copied `source/stock.json`. The stock tool's own repository and database are outside my reach and read-only by rule. **Example labels:** the hand-made states carry visible "EXAMPLE" labels (example marks, F&O picks, win/lose families, the AI plain summary). | MET for the NSE figures and labels; **not verified by me** against the stock tool's originals |
| 2 | `check_page.js` clean at 1280 and 390 px | `node design/system/check_page.js …/35-stock/page.html`: "no console errors, no overflow, no external requests" | MET |
| 3 | No model or vendor names; no strategy internals | I rendered all 21 gallery states and ran the app's own model-name detector over the visible text, tooltips, labels and titles: **0 hits**, and no internal strategy id shown. | MET (note below) |
| 4 | F&O block: NSE contract codes and real 12 Oct data | I fetched NSE's `BhavCopy_NSE_FO_0_0_0_20261012_F_0000.csv.zip`. **Futures:** RELIANCE26OCTFUT 1,160.20 (OI 144,250,500), NOVFUT 1,166.20 (OI 21,534,000), DECFUT 1,173.10 (OI 2,220,500), lot 500, all equal. **Options:** all **114 legs** in the chain, close and open interest, equal NSE by `FinInstrmNm` (0 mismatches). **US:** `fno` is null. | MET |

## Finding (should fix): the US forecast line is in rupees

- **What the page shows:** on NVDA (`#m=us`, and every US state), the line under the chart reads "Our forecast for
  Mon 19 Oct (in 5 sessions): middle **₹**229.09 · 1 in 2 chance between **₹**222 and **₹**239 · 4 in 5 chance
  between **₹**215 and **₹**248".
- **The cause:** `design/mockups/35-stock/js/3-chart.js:116` writes "₹" literally instead of using the market's
  currency.
- **Why it matters:** this is a wrong unit on a price for a US stock, on a signed-off screen that the app will copy.
- **Expected:**
  - Use the market's money format, as the rest of the page does. That is a design fix recorded in `changes.md`, so
    no re-sign-off is needed for a unit correction.
  - The app story building 35 adds a US harness case that fails on "₹" (W12's US checks already do this for
    Markets).

## Note (not a finding)

- `data.json` maps internal strategy ids to display names (`"ai.combined.sonnet.v1": "AI team"`), so a model name
  sits in the page's embedded data, never on screen (checked on all 21 states).
- The owner's rule is about screens, so this is acceptable in a mockup.
- The served contract for 35 should carry display names only, as W9's adapter rule does, so the id never leaves the
  backend.
