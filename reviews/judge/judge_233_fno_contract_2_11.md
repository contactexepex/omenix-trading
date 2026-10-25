# Judge 233: dashboard contract 2.11.0, the card's per-trade loss cap (`trade.max_loss_cap`)

Dashboard `story/fno-contract-2-11` at f94f3bf (screens lead 01XFXpbkyixX7SuXeQCp5EnX), on main f4f7f40. Lane 1
(contract). Judge D, 16 Oct 2026.

**FAIL: one should-fix.** Everything else is met.

| Claim | Result | Evidence |
|---|---|---|
| 1. `FnoCardTrade.max_loss_cap` is new, required, INR Paper, from C5's `max_loss_per_trade_rs`; mockup 39 reads it | PARTLY | The field is required in `fno-card.yaml`. Trading's `config.yaml` sets `max_loss_per_trade_rs: 10000` for both `books` and `manual`. `const CAP = 10000` is gone, and the bar width and visible words read `T.max_loss_cap`. But the bar's `aria-label` in `39-trade-card/js/3-position.js:50` still says `of the Rs 10,000 cap`. See the finding. |
| 2. `maximum: 10000` stays the owner's ceiling, and the probe still bites | MET | Both `max_loss` and `max_loss_cap` keep `maximum: 10000`, and `exclusiveMinimum: 0` is on the cap. My planted breaks on `getFnoCard_india_trade` were each rejected by `check_fno_screens` (exit 1, the `payload/trade` problem): cap removed, cap 10001, cap 0. A config above Rs 10,000 fails validation and the page stays unpublished, which is a closed failure. The description says raising it is a contract change. |
| 3. Version 2.11.0; a 2.10 card with a trade is rejected; examples and regenerated files at 2.11.0 | MET | `openapi.yaml` 2.11.0 has its note. The other changes are version strings plus the new field in two examples (TRADE, WATCH). These all exit 0: `check_contract`, `check_fno_screens`, `examples`, `render_catalog` and `render_fno_catalog`. The card page is not published (P2f), so no live payload breaks. |
| 4. Menu groups: 39 `strategies`, 40 and 46 `markets` | MET | `PF.mount` `group` changes only in `9-mount.js` of 39, 40 and 46. This matches story W3 answer (a) (card in Strategies, weather in Markets). |
| Gates | MET | `sync-design` clean, `tsc` OK, `npm test` 520/520 (0 skipped). |

## Finding (should-fix)

**The cap bar's screen-reader label still copies Rs 10,000.** `3-position.js:50` reads
`'aria-label': \`${Math.round(share * 100)}% of the Rs 10,000 cap\``. The visible line beside it uses
`rs(c, T.max_loss_cap)`.

- **Path:** the owner lowers `max_loss_per_trade_rs` (allowed: the schema only caps it at 10,000), for example to
  Rs 5,000. The card then sends 5000. The bar and the visible words say "of the ₹5,000 a trade may lose", but a
  screen reader says "of the Rs 10,000 cap".
- **Why it matters:** this silent copy of the owner's number is exactly what the field was added to remove (claim 1;
  judge 224 addendum 3). W3f will build the screen from this mockup.
- **Fix:** use `rs(c, T.max_loss_cap)` in the label. The header comment's "against the Rs 10,000 cap" (line 1) may
  stay as description, or say "against the book's per-trade cap".

## Note

- The schema cannot check `max_loss <= max_loss_cap`. C2 sizing enforces it on trading's side. P2f's build should
  refuse a card whose `max_loss` is above `max_loss_cap`, since both come from the same records.

## Addendum 1: head e3829c2 (BG1's budget shares added)

**FAIL still: the should-fix above is not addressed.** `git show e3829c2:design/mockups/39-trade-card/js/3-position.js`
line 50 still reads `% of the Rs 10,000 cap`. 39's files are unchanged in `git diff f94f3bf e3829c2`.

What e3829c2 adds is met:
- **Three required FnoBudget fields:** `share_pct` (exclusiveMinimum 0, maximum 100), `alert_pct` and `stop_pct`,
  from trading `config.yaml` `budget:` (`books_and_roles_share_pct: 50`, `alert_pct: 80`, `stop_pct: 100`, lines
  172-174). The level and cap descriptions name the fields instead of 80, 100 and 50.
- **Planted breaks:** removing each field from `getFnoBudget_india_ok` was rejected by `check_fno_screens` ("'<field>'
  is a required property").
- **Mockup 43:** the alert tick is at `left:${min(100, alert_pct)}%`. The facts, aria label, sentence and how-to read
  the three fields, and none of 80, 100 or "half" remains.
- **Gates:** `check_contract` and `check_fno_screens` exit 0.
- **The sweep:** the lead's sweep of 37 and 39-46 for copied owner limits missed exactly the label I raised. The fix
  is still one line: `rs(c, T.max_loss_cap)` in the aria label.

## Addendum 2: head a570f0d (the should-fix fixed)

**PASS.** a570f0d contains main f4f7f40, and its diff from e3829c2 touches four files.
- **The finding is fixed:** `39/js/3-position.js:50` now reads `% of the ${rs(c, T.max_loss_cap)} cap`, and line 1
  says "the book's per-trade cap". A grep of 39's js finds no 10,000 or 10000.
- **44's how-to:** "Runs every morning at 07:10 IST" becomes "Runs every session morning, before the market opens".
- **Gates on a570f0d:** `check_contract`, `check_fno_screens`, `examples` and `render_catalog` exit 0, `sync-design`
  is clean, and `npm test` gives 520/520.

**Notes (not blocking):**
- Mockup 39's lede (`2-top.js:8`) still says "at about 15:08". That sentence predates 2.11 and is judge 234's finding
  on W3f; fix it here or with W3f, so the screen and mockup agree.
- 44's "before the market opens" describes the 07:10 IST schedule, but GitHub's schedule is best effort and has run
  hours late. It is true of the schedule, not a promise; "every session morning" alone would be safer. W3e's screen
  keeps "07:10 IST", which matches the cron (judge 232).

## Addendum 3: head c4ba78d (copied-figure check; the two wording notes)

**PASS.** It contains main f4f7f40; `git diff a570f0d c4ba78d` touches 8 files.

- **New check:**
  - `config_figures` collects the example values of 1,000 and up of every field whose `x-catalog.source` names the
    config. Today these are `max_loss_cap`, `open_risk_cap` and `pause_at`, which now has its source line: C5's
    `drawdown_brake_rs`. It writes each value three ways: 10000, 10,000 and 1,50,000. `_indian` groups correctly,
    for example 150000 becomes 1,50,000.
  - `check_copied_figures` fails a catalog mockup's js line that contains one of them. The list comes from the
    contract, so there is no second copy.
- **My planted breaks:** `cap = 150000` and `cap = 1,50,000` in `41/js/2-books.js:13` were each reported ("writes the
  config figure …"). The restored tree passes.
- **Wording:**
  - 39's lede is now "after the 3 pm quotes". That is true (O1 posts after `quotes_done`) and has no fixed time.
  - 44 is now "Runs every session morning".
- **Gates on c4ba78d:** `check_contract`, `check_fno_screens`, `examples` and `render_catalog` exit 0. Code size is
  OK, `sync-design` is clean, and `npm test` gives 520/520.

**Notes:**
- The check covers mockup js only. The screens in `web/` rely on their own tests (W3f's fixed-time test; W3c, W3f and
  W3g grep tests). A `web/` copy of a config figure is not caught by this check.
- Shares under 1,000 (BG1's 50, 80 and 100) are left out by design; W3g's test covers them on its screen.
