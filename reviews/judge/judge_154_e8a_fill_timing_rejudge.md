# Judge 154: E8a fill-timing study, story text re-judge (revision 2)

**Story:** `docs/stories/E-paper-desk.md:713-860`, branch `story/e8a-fill-timing`, commit `0cc98798`. Builder's
answers: `reviews/claude/response_149_e8a-judge-153-answer.md`.

## Verdict: FAIL (0 blocking, 3 should fix, 5 minor)

All 3 blocking and all 9 should-fix findings of judge 153 are fixed in the text. Revision 2 adds three new gaps, all in
the parts it added: the flip share, the theta part and the width share for single options.

## Judge 153 findings, checked one by one

| 153 | Fix in revision 2 | Result |
|---|---|---|
| B1 mean is drift | Lines 735-742: mirror identity stated; headline is the size of the move, `|C|` and the bad-side tail; theta shown separately; 1 vs 3+ nights split; signal decay "not measured" | Fixed |
| B2 win at both | Lines 798-800 flip share; threshold shares named as stand-ins for "missed, price moved" (757) | Fixed (new issue N1) |
| B3 gap list | Lines 753-761 Out list with a reason for each; R = 5/30/60 and E4's 15:15 baseline in scope (747-748, 781-784) | Fixed |
| S1 ledger kind | 765-766: prospective, hypothesis no | Fixed |
| S2 data spend | 812-814 spent, rows written with the ledger row | Fixed (minor M1) |
| S3 paired difference | 795-797 | Fixed (minor M3) |
| S4 14:00 mapping | 783: 14:15, 14:45, 15:15. I recomputed every mapping from E8's rule (card at T+8, first 15-minute mark at or after T+8+R, after 15:25 the next session at 09:15+R): 15:15, 09:45, 10:15 and 14:15, 14:45, 15:15. All correct | Fixed |
| S5 stale/missing cap, probe | 768-771 probe with no price; 802-804 10% cell rule | Fixed (minor M2) |
| S6 spread caveat | 805-807 "not measured" | Fixed |
| S7 live rule | 815-818 paired mid and bid/ask, "not confirmed" rule | Fixed |
| S8 expiry and units | 774-775 split by sessions to expiry; points, share of width and rupees at today's lot | Fixed (new issue N3) |
| S9 criteria | Criteria 4-6 and a hand-checked 14:00 day (823-834) | Fixed |
| M1-M5 | Blocks 10/20; gap from the same window; VIX at the decision day's open; call estimate; line 709 fixed | Fixed |
| M5 "owner row appears twice" | Builder's pushback **accepted**: there is one row (`DESK_DECISIONS.md:179`) on 13e1f090, 0cc98798 and origin/main. My error: the `tail -5` I ran in judge 153 included line 179, which my `grep -n` had already printed | Withdrawn |

## New findings

### Should fix

**N1. The flip share has no valid interval, its direction is not fixed, and it can leak strategy results.** Lines
798-800.
- Entries held to expiry from almost every session overlap heavily: all entries into one expiry share one settlement
  price. So the independent unit is the expiry, about 33 of them, not the session. Five-session blocks (801) would
  give an interval far too narrow. *Fix:* resample whole expiries for the flip share's interval, or print no interval
  and state "about 33 independent expiries".
- The Description (719) asks how often a trade that wins at the decision price loses at E8's price. The design (799)
  measures "sign differs", which counts both directions. *Fix:* print bad flips (win to loss) as a share of the trades
  that win at the decision price, and good flips separately.
- Gross or net of C1 costs is not stated, and a P&L of exactly zero is not handled. *Fix:* net of C1 costs at both
  fills; state which side zero counts on.
- To count flips, the code computes every structure's P&L held to expiry. *Fix:* add to criterion 7 that the report
  and `results.json` print only the flip shares, never a win rate or the mean or total P&L (scope 760: no edge).

**N2. The theta part is defined for the wrong time span, and it has no forward price.** Lines 791-792 define it as "one
night's decay from the decision-day close to the fill's open". That fits none of the paths:
- the 14:00 path, R = 5 and R = 30 fills, and 15:15 fills have no night;
- an R = 60 fill is at 10:15, not at the open;
- a gap of 3 or more nights is not one night.

Black-76 also needs the same-expiry future at the decision time (`implied_vol.py:4`), and the story fetches no futures
candles. *Fix:* the theta part is the model value change when only time moves, from the decision time to the fill time,
with the forward and IV held at the decision. Name the forward source (15-minute futures candles, or put-call parity
from the same candles). State the time convention (calendar days / 365, as `implied_vol.py:37`). Add a unit test
against a hand Black-76 value.

**N3. "Share of width" means nothing for LC and LP.** Lines 785-786 and 790. For LC and LP, `width` is the distance
out of the money (STR1, `B-research-engine.md:369`), not the risk. So the 5/10/20% thresholds and the live 2% tolerance
(818) are not comparable with the other families. *Fix:* for LC and LP, use the share of the decision debit (their
maximum loss).

### Minor

- **M1. Data-spend wording.** Line 812 says "fresh to spent", but the update rule needs a `registered` row at
  registration first. The flip share reads NSE's final settlement price (E7's `SttlmPric`), not "monthly closes"
  (813). Add that 2019-2023 intraday option candles stay fresh.
- **M2. The probe can quietly shorten the window.** A month that fails is dropped (771). Require each failed month to
  be diagnosed, for example by trying the panel's expiry date, before the freeze, and state the count in the protocol.
- **M3. Terms and cells.** "Bad-side `|C|`" (795) should be defined as max(C, 0). There is no minimum n per cell: gap
  of 1% or more is about 5% of sessions, about 11 per sessions-to-expiry band. Print "too few" below a frozen n.
- **M4. The E4 baseline adds no new figure.** E4's 15:15 equals R = 5 for a 15:00 decision and R = 60 for a 14:00
  decision (784). Say so rather than print it twice.
- **M5. Theta and band splits have no test** in the test plan (842-845); add them.

## Re-judge needs

N1-N3 fixed in the text; the minors fixed or answered; a new SHA.

---

## Addendum 1: revision 3 at 3a833565 (narrow re-check of N1-N3 and the five minors)

**Verdict: PASS (0 blocking, 0 should fix, 3 minor).** The builder may fold the minors into the protocol; they need no
new re-check.

| Finding | Fix in revision 3 (`docs/stories/E-paper-desk.md`) | Result |
|---|---|---|
| N1 flip share | 805-811: expiry is the unit (about 33) and the interval resamples whole expiries; bad flips as a share of wins and good flips as a share of losses, printed apart; net of C1 charges; zero counts as not a win; only the two shares are printed. Criteria 6 and 9 cover these | Fixed (minor A1) |
| N2 time part | 795-798: only time moves, from decision to fill; forward = same-expiry future's 15-minute close, fetched read-only; IV per leg; calendar minutes / (365 x 1440); hand Black-76 test (criterion 8). Fits every path and gap | Fixed (minor A2) |
| N3 risk scale | 787-790: decision debit for LC and LP (their maximum loss), width for the rest; thresholds and the live tolerance (832) use it | Fixed |
| M1 data spend | 823-827: `registered`, then `spent`; NSE final settlement; 2019-23 `fresh` | Fixed |
| M2 probe | 771-773: an unanswered month is investigated, its cause recorded before the freeze | Fixed |
| M3 terms and cells | 786 bad side means C > 0; fewer than 30 days prints "too few days" (criterion 8) | Fixed |
| M4 E4 baseline | 748-749: labelled on the R = 5 and R = 60 rows | Fixed |
| M5 tests | Criterion 8 | Fixed |

**New minor findings**

- **A1.** Line 806 says C1 charges are "the same at both fills". They are not: STT (`stt_sell_pct` 0.15) and the exchange
  charge (`exchange_txn_pct`) are percentages of premium (`config.yaml:25-27`, `fno/costs`). *Fix:* charge each fill at
  its own price. The amounts are small, but they can flip trades whose P&L is near zero.
- **A2.** Line 797 has no rule for a leg whose IV cannot be solved (`implied_vol` returns None, for example a price
  below intrinsic value). *Fix:* that structure's time part is "not computed" and counted, never filled in.
- **A3.** Lines 740 and 850 still say "theta part", but the design now says "time part". Use one name.
