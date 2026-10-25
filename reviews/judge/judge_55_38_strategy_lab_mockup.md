# Judge 55: mockup 38-strategy-lab, focused check (owner signed off at omenix-dashboard 32ad873)

**Verdict: FAIL on 1 should-fix.** The page is clean. The fault is in the frozen contract: the F&O readiness bar and
the F&O profit are defined on market charges, while the desk's own verdict (DESK_DESIGN 12.8, story S2) is net after
execution **and operating** costs, which includes AI and data costs. There is 1 minor finding.

**What I judged:** `design/mockups/38-strategy-lab` at omenix-dashboard main (sign-off recorded in 4f28735). The
orchestrator's five points, kept focused for cost.

| # | Check | Judge's evidence | Result |
|---|---|---|---|
| 1 | Real figures trace to their source; Examples labelled | **Real state:** 39 India trades, net **−₹542.93** (shown −₹543), **18 won = 46%**, all `baseline`, exits on 13 Oct 2026. I recomputed these from `source/settled.json`, and `data.json`'s real state holds the same 39 trades and the same sum. **The source** is the copy made by `fetch_trades.py` from the stock tool's records; the originals are outside my reach and read-only by rule. **Example states** (`ex=early`, `ex=review`) carry visible "EXAMPLE" labels in every state I rendered. | MET (the originals not verified by me) |
| 2 | `check_page.js` clean at 1280 and 390 px | "no console errors, no overflow, no external requests". `check_currency.js`: clean. | MET |
| 3 | No model or vendor names; no strategy internals | All 9 gallery states rendered: the app's model-name detector over text, tooltips, labels and titles gives **0 hits**, and **no internal strategy id** is shown. The "why" is told from outcomes (market, sector, news, calm or stormy), not methods. | MET |
| 4 | The owner's combined rule: only a "both books together" total line in INR, India only; no combined leaderboard, win rate or winner | The block reads "Both books together: total only … in rupees" with one line per family: Stocks + F&O = total. Families are in fixed order (Rule-based, Hybrid, AI team), **not sorted**, e.g. totals of +₹90,618, +₹92,510 and −₹1,84,400 in that order. No win rate and no winner. **Absent in both US states.** | MET (minor 1) |
| 5 | The frozen contract is consistent with the F&O stories it names (S1/S2, E2-E6) | **Families vs books:** 12.1's three books (pure rules, hybrid, fully AI) match the three families. **The gate:** E6's real-money gate (at least 3 months and 20 positions, judged on review dates) and 12.8's first review at 6 months agree with the "6 months" stated. **The cost basis does not agree:** finding 1. | NOT MET |

## Finding 1 (should fix): the F&O verdict is on the wrong cost basis

- **What the contract says:** `notes.md` defines "Profit is after **market** charges", and the F&O readiness row as
  "net profit after charges".
- **What the desk's rules say:**
  - DESK_DESIGN 12.8: "Primary verdict: net account result after execution **and operating costs**".
  - S2 (scoreboard B) reports gross, execution costs, "AI and data costs (13.6 labels)" and net, per book.
- **Why it matters:**
  - For the Hybrid and AI books, operating (AI) costs are part of whether the system pays.
  - A screen that tells the owner "ready for real money" on market charges alone could pass a book that loses money
    once its AI costs are counted.
  - That is exactly the decision this screen exists to support.
- **Expected:** a `changes.md` entry to the frozen contract.
  - The F&O readiness check and the F&O "profit" use S2's net after execution and operating costs.
  - Market-charges-only profit, if shown at all, is labelled as such.
  - The contract names S2's fields (gross, execution costs, AI and data costs, net) as the F&O source.
- **The stock side** already distinguishes market cost and "your cost" (notes, last bullet). The F&O side needs the
  same care.

## Minor 1: a combined total that does not add up as shown

- In the `review` example, AI team shows "Stocks −₹1,24,474 + F&O −₹59,925 = total −₹1,84,400".
- The two shown parts add up to **−₹1,84,399**. The total is summed before rounding.
- A beginner adding the two numbers will find a ₹1 gap.
- **Expected:** compute the total from the rounded parts shown, or show the parts to the paisa.
