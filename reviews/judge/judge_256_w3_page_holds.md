# Judge 256: W3, the page-holds notice on the F&O screens (contract 2.13.0 `page_holds`)

Dashboard `story/w3-page-holds` at b71da36 (W3 builder 0134MoC6f7aAJVcHRBiyATo6; claims: response_44). It is built on
2.13's earlier head a0a355d, on main c2589b6, and on W3f-withheld 9f027cc. Lane 1. Judge D, 16 Oct 2026.

**FAIL: two should-fixes.**

**Met:**
- **One reader:** `fnoPageHolds()` in `lib/fno/wiring.ts`. With no database it returns no holds. A publication
  without the page reads as unknown (null), and no notice is invented.
- **One pure view and one notice:** the pure view is `lib/fno-holds/holds.ts`, outside `lib/fno/` because
  components may not reach it. The shared red `HeldNotice` is also used by the card's `withheld` notice.
- **`HeldBlock`:** it shows the notice above the dated previous page, or the notice and "Not published". Eight W3
  loaders wrap their main block with their own page key (weather, weather history, Forecast lab, Strategy lab F&O,
  paper books, data health, budget, scoreboards). The card keeps only `withheld`. A structure test checks every W3
  loader except the card's.
- **Import-graph change accepted:** `_fno/held-block.tsx` joins the readers of `lib/fno/wiring` in the same role as
  `freshness-block.tsx`, a shared server loader part. Data health reads through `HoldsBlock`, not the wiring.
- **Gates on b71da36 alone:** the builder reports `npm test` 583/583. On my trial merge, `check_contract`,
  `check_fno_screens` and `tsc` pass.

## Should-fix 1: Home's two held pages get no notice

P11 drops the row (`shows: nothing`) for exactly two pages: `today` (Home's picks, `APPROVED_PICKS`) and `risk`
(Home's books, `OPEN_TRADE_RISK`). They are read by Home (`lib/home/azure-source.ts:15`, `fnoBooks`, and the picks
read beside it), not by any W3 loader. On this head nothing on Home reads `page_holds`. So on the first approval, or
while a trade is open, Home's F&O panels show plain "no publication" with no notice. That breaks P11's criterion 9
("per user, the held screen says it is held") and the owner's "say so on screen" (row 236), for the two cases the
generic notice was mainly built for.

**Fix:** Home's picks and books panels use `HeldBlock` (or `holdOf`) with their page keys `today` and `risk`, with
a test. Extend the structure rule, or add one, so that every reader of a holdable page key shows the notice: by
endpoint or page key, not only W3 loaders.

## Should-fix 2: rebase on 2.13.0's final head

b71da36 is built on 2.13's a0a355d, whose examples have since changed (70f705c, judge 255 addendum 1, PASS). **My
trial merge** of b71da36 with 70f705c and dashboard main a812fee has no conflicts, but **3 tests fail**
(`holds.test.ts` "a page held with its previous page", "a page held with nothing", and "data health's table"). They
pin a0a355d's example holds (the calendar reason, and paper books as `nothing`). Rebase on 70f705c, update the
expected values to P11's four sentences, and run the suite.

## Addendum 1: head 0979176 (both should-fixes fixed)

**PASS.**
- **Should-fix 1, Home:** one shared read, `lib/fno/page-holds.ts` `readPageHolds(reader)`, is used by the F&O wiring,
  the frame (shell) adapter and Home's adapter (`HomeData.fnoHolds`).
  - Picks (`today`): the frame's picks show `HeldNotice`, and "Not published" replaces them when the hold shows
    nothing.
  - Books (`risk`): the notice sits above the Who-trades cards, and each card's F&O line says not published.
  - `every-reader.test.ts`: every `FNO_PAGES` key sits in one closed list of how its hold is shown. The readers of
    `getFnoPicks` and `getFnoBooks` are pinned and checked for the notice, and a planted reader is caught.
  - A failed holds read invents no notice (test).
  - **My mutation** turning off the books notice in `who-trades.tsx` fails 1 test.
- **Should-fix 2:** the branch merges dashboard main a812fee and 2.13 final 9fc97d0, and `holds.test.ts` expects P11's
  four sentences.
- **Gates:** a trial merge with current main d53cefe (2.13.0 merged) is clean. `check_contract` and
  `check_fno_screens` exit 0, `tsc` passes, and `npm test` gives 587/587.

**Note:** the 10 market pages listed "not held" match P11 today (it raises `PageHeld` only for its named users). The
closed list makes a new hold choose a notice first. The regex checks pin source text, which is brittle but adequate
for a structure rule.
