# Judge 255: dashboard contract 2.13.0 (nullable `answer_on`; `FnoPageHolds`)

Dashboard `story/fno-contract-2-13` at a0a355d (screens lead 01XFXpbkyixX7SuXeQCp5EnX), on main 47d0328. Lane 1
(contract). Judge D, 16 Oct 2026.

**FAIL: one should-fix.** Both additions are right in shape. The page-holds reason rule contradicts P11's own passed
text.

**Met:**
- **`today.answer_on` is nullable:** null when the answer session falls in a year whose NSE calendar is not
  published. This is option (b) of judge 244, and every 2.12 payload stays valid. The waiting example is dated
  2026-12-04 with Q1's `answer_on` null, and mockup 37 says "Not known yet".
- **`FnoPageHolds` (judge 251 option (b)):** `{page_key, since, reason, shows: previous_page | nothing}`, closed,
  public, with x-never-sent covering the figures and the value that broke the rule. `shows` carries P11's "shown"
  and "dropped" cases. There are three examples (none, held, first), and the mockup 44 drawing goes through
  MOCKUPS_ALSO.
- **Gates:** `check_contract` and `check_fno_screens` exit 0 on a0a355d. The digits probe ("Max loss Rs 10,500 above
  the cap") is refused.

## Finding (should-fix)

**The reason pattern `^[^0-9]*$` refuses P11's own card rule, which would stop every page.**
- P11's passed text (judge 251, design item 3) fixes the card's rule as "risk-rule breach: C2 sizing or C4 validity let
  a trade past its book's per-trade cap". It holds the digits 2 and 4. **My planted run:** that sentence in
  `getFnoPageHolds_india_held` is refused (`payload/holds/0/reason`).
- P11 says `page_holds` itself is never held, so a refused `page_holds` is `ContractBroken`, a whole-run stop, on
  the very day of the over-cap card the hold exists for.
- The examples' reasons ("A trade broke a risk rule: its maximum loss is above its book's cap" and the others) are also
  not P11's sentences. Two lists of the same fixed sentences will drift.

**Fix:** one list of hold sentences, owned by P11's code (each user's story fixes its own), and a pattern that
admits them. Either:
- P11's sentences avoid digits (for example "the risk sizing or the validity check let a trade past its book's
  per-trade cap"), with the P11 text updated to say so; or
- the pattern forbids amounts but admits story ids such as `C2`. That is harder to make value-proof, so I prefer the
  first.

The examples should use P11's sentences, and P11's code round should test that every sentence passes the pinned
pattern.

**Note:** P11's text calls the field `rule`. The contract names it `reason` (the privacy check refuses rule-like
keys), and adds `shows`. P11's code must use the contract's names; record that in P11's text at its code round.

## Addendum 1: head b8399c7 (the should-fix fixed)

**PASS.**
- **Pattern and examples:** the pattern `^[^0-9]*$` stays. The examples now use P11's three digit-free hold
  sentences, for picks (`today`, shows nothing), risk (shows nothing) and the card (shows previous_page). The invented
  calendar reason is gone. Mockup 44's bad case draws Home's two (nothing) and the card (previous page). The reason's
  description names P11's code as the sentences' owner: no value, no story code.
- **Gates on b8399c7:** `check_contract`, `check_fno_screens`, `examples` and `render_catalog` exit 0, and `npm test`
  gives 572/572.
- **Merge with main:** b8399c7 does not contain dashboard main c2589b6 (W3b). A trial merge auto-merges
  `web/lib/fno-forecast-lab/view.ts` cleanly, and then `npm test` gives 574/574. Merge it with a real merge.

**Note (wording, not blocking: the examples are Mock data, and both texts pass the pattern):** the examples are not
yet word for word the sentences on P11's head d2190217.
- picks: example "cannot build its picks yet", code "does not build its picks yet";
- risk: example "an open trade whose risk this page cannot compute yet", code "an open trade, and this page does not
  compute its risk used yet";
- card: example "the sizing or validity checks let", P11 text "the risk sizing or the validity check let".
The lead undertook to copy P11's final wording before 2.13 merges. Copy it from the code, so there is one list.
- **Re-head 70f705c (the wording note acted on):** the held example now has four sentences. I checked each against
  the pushed sources, word for word:
  - `today` (picks, nothing) and `risk` (nothing) equal `home_blocks.py` `APPROVED_PICKS` and `OPEN_TRADE_RISK` on
    P11's head d2190217;
  - `card` (previous_page) equals P11's text, line 459. The card's hold lives in P2f's code, not P11's;
  - `paper_trades` (previous_page), "A book holds an open trade, and this page cannot mark it for the session yet", is
    on **no pushed branch** yet. P2c's rebase must use it word for word, or the example is re-copied.

  `check_contract`, `check_fno_screens`, `examples` and `render_catalog` exit 0. A trial merge with dashboard main is
  clean (view.ts auto-merged), and then `npm test` gives 578/578. The PASS stands on 70f705c.
- **Final head 9fc97d0:** it contains dashboard main a812fee (W3b and W3f-withheld, a real merge in 1ac8f9c). The
  held example's sentences equal P11's head abef96fd (response 244 addendum 7) word for word: `today` and `risk` are
  `home_blocks.py`'s `APPROVED_PICKS` and `OPEN_TRADE_RISK`, `card` is P-publishing.md line 459, and `paper_trades`
  is the P2 builder's agreed P2c sentence (scripted comparison). `check_contract`, `check_fno_screens`, `examples` and
  `render_catalog` exit 0, `sync-design` is clean, and `npm test` gives 578/578. **PASS on 9fc97d0; merge this head.**
