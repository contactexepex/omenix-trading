# Judge 234: W3f, today's card screen

Dashboard `story/w3f-trade-card` at 0060182 (W3 builder 0134MoC6f7aAJVcHRBiyATo6; claims: response_40). It is built
from main f4f7f40, on contract 2.10.0, with mockup 39. Story W3, build step 6: "T1's delivery records; the full card
from Drive, owner-only fields behind sign-in". Lane 1. Judge D, 16 Oct 2026.

**FAIL: one should-fix.** Everything else is met.

| Criterion | Result | Evidence |
|---|---|---|
| W12 pattern | MET | `lib/fno-card/` has types, one interface (`CardData.card()`), the Azure adapter (page `card`), the fixture adapter loaded only without a database, one wiring and four pure views split by purpose. Every file is within 350 lines (code size check). |
| India only | MET | The build has only `/india/card`. The route test shows the item in India's Strategies group and absent in the US. |
| Owner-only fields | MET | The position, the stress line and the objections carry the Owner only mark. As in judge 225, they show only on the dashboard behind Vercel Authentication, with `x-visibility: owner` and `OWNER_PATHS` on the contract side. The gateway import test covers `lib/fno-*`, `components/fno-*` and W3 pages by pattern, and it passes. |
| No copied per-trade cap | MET | `position-view.ts` shows "The most it can lose: ₹…, charges included" with no bar and no 10000 (grep of `lib/fno-card`, `components/fno-card` and the page). The bar waits for `trade.max_loss_cap` (contract 2.11, judge 233, unmerged). |
| Live and back-fill apart; no invented objection; real money not eligible | MET | `trackText` is used twice per forecast ("Live: … Back-fill (made after the fact, not live): …"). `advocateOf` shows the payload's objections only, and on `advocate_unavailable` it says "no objection is ever invented". `evidenceOf` always returns "Real money: not eligible". |
| Times from the payload | MET | `ist()` renders the payload's UTC times at +05:30 (India keeps no daylight saving), and a missing time is "not sent". |
| Shared CSS | MET | `.facts3`, `.chance` and the code chip move to `fno-screen.css` with the same declarations; weather keeps `.chance .base`. `.muted` is new in `fno-screen.css`; the mockups' `_shared/shell.css:5` already has the same rule, so the screens now match their mockups. |
| Gates on 0060182 | MET | `check_contract` and `check_fno_screens` 0, code size OK, `sync-design` clean, `tsc` OK, `npm test` 539/539 (0 skipped), `next build` 0. |
| Merge with W3e | Note | A trial merge with `story/w3e-data-health` conflicts in `routes.ts`, `fno-screen.css` and reviews README. These are additive lists: keep both sides (W3e's `.cards3` and W3f's rules), then re-run `npm test`. |

## Finding (should-fix)

**The page states a card time the system does not have.** The lede (`card-page.tsx:20`) says "Every trading day at
about 15:08 the desk sends one card". The source tip (`card-page.tsx:54`) says "Once a session day at about 15:08 IST".

- **What trading says (strong evidence):** T2 (`docs/stories/T-cards.md:179`) says "Design 4.1's card at about 15:08
  is earlier than both [decisions final at 15:12, C3 final at 15:15] … So T2 never assumes a time". E8's "Card time"
  (`docs/stories/E8-owner-timing-fills.md:52-56`) says O1 posts the card after `quotes_done`, "so T is 15:15 or later
  on a normal day".
- **Path:** once O1 runs daily, the card arrives at 15:15 or later. It is valid until 15:25 (`CARD_VALID_UNTIL`). The
  owner reads "about 15:08" and expects about 17 minutes to act, when there are about 10 or fewer. A wrong time on a
  time-limited card is the kind of fact this project must not get wrong.
- **Fix:** state no fixed time, for example "Every trading day, after the day's decisions are final, the desk sends one
  card". The card's own three times, already shown from the payload, carry the real time. Mockup 39's
  `2-top.js:8` has the same sentence; the screens lead's 2.11 branch already touches 39 and can fix it there.

## Notes

- "Prices from the 15:00 bid and ask" (`position-view.ts`, from mockup 39) matches the desk's 15:00 decision quotes
  (E-paper-desk), so it stays.
- When 2.11 merges, the cap bar should read `trade.max_loss_cap`, both the width and the aria label.

## Addendum 1: head 2d2a723 (the should-fix fixed)

**PASS.** It adds one commit on 0060182.

- **The fix:** the lede and the source tip now say "after the day's decisions are final", and the card's own times
  from the payload carry the real time. This matches T2 ("never assumes a time") and E8 (15:15 or later).
- **The guard:** the new `no-fixed-time.test.ts` scans the screen's code (comments stripped) for "at, by, around or
  about HH:MM", and a planted "at about 15:08" is caught. A grep of `lib/fno-card`, `components/fno-card` and the page
  finds no "15:08" or "about 15".
- **Times left on the screen:** the "15:00 bid and ask" and the forecast capture's deadline are contract facts, not
  the send time.
- **Gates on 2d2a723:** `check_contract` and `check_fno_screens` 0, `tsc` OK, `npm test` 541/541 (0 skipped).

**Merge:** W3f must merge W3e, W3g and W3h and keep both sides of the additive lists. After 2.11 merges, draw the cap
bar from `trade.max_loss_cap` (width and aria label).

## Addendum 2: the held-back card, `story/w3f-withheld` at 5680fe6 (contract 2.12.0 `FnoCard.withheld`)

**PASS.** 5680fe6 is built on 2.12.0 at 7db3830 (judge 239 addendum 1).
- **Held-back state:** the screen shows a red `role="alert"` notice with the owner's sentence (DESK_DECISIONS row
  236), today's date and "Below is the card of <its session>, not today's", placed after the TEST note and before the
  verdict, as in mockup 39. The verdict sub-line reads "Previous session's card", and the old card's own reason is
  dated ("On Fri 13 Nov 2026: …"), so its "today" words are never the screen's.
- **Contract error:** a card whose session is not earlier than `withheld.session` shows only the notice and no card.
  This covers judge 239's note on the check the schema cannot make. **My mutation** `<=` instead of `<` fails 1 test.
- `withheld.test.ts` covers the notice, the verdict line, a normal day, and an equal and a later date.
- **Gates:** a trial merge with dashboard main 47d0328 (2.12.0 merged) is clean. `check_contract` and
  `check_fno_screens` exit 0, `tsc` passes, and `npm test` gives 575/575.

**Note:** the block's heading still reads "Today's card" above a held previous card. The notice directly under it
says otherwise, so this is not a finding; "Card" would be cleaner.
- **Re-head dac843e (5680fe6 plus main 47d0328):** the `web/` change is the same withheld change. Dashboard main has
  since moved to c2589b6 (W3b merged). A trial merge of dac843e into c2589b6 is clean and keeps W3b's "Baseline"
  wording: the merged diff from main is the 7 withheld files only. `npm test` gives 577/577. The PASS stands.
