# Judge 225: W3c, the paper books screen (exepex/omenix-dashboard story/w3c-paper-books at 5e648af, from main 1972241)

**Verdict: PASS.** `npm test` gives **511 passed, 0 failed, 0 skipped** in a read-only clone (the claimed figure).

| Check | Result | Evidence |
|---|---|---|
| One card per book, never summed | MET | `view.ts` maps each account alone ("the screen sums nothing"). There is no `reduce` or total in the screen's views or components, and a test checks that no three-book total appears |
| Shadows apart; B0 is "Measurement" | MET | A separate shadows section from `shadows[]` (2.8.0), using its `label` (`measurement` for B0) |
| Legs and alerts owner-only; gateway test | MET | Legs and today's alerts are shown only on the dashboard, which is behind Vercel Authentication. The contract marks them `x-visibility: owner`, enforced by `OWNER_PATHS` on the contract side. The gateway import test covers every `lib/fno-*`, `components/fno-*` and W3 page by pattern, so it covers this screen, and it passes |
| Costs before and after; no made-up fills | MET | Closed trades show gross, costs, net, result and how each closed, plus the 5/30/60-minute fills. A missed fill says why, and a trade from before E8 says "Before owner-timing fills", never a number |
| Judge 222's tightening | MET | `screens-import-graph.test.ts` now requires every reader of a screen's wiring to be a loader of that screen's own routes, matched by endpoint `fno/<screen>` or `fno/<screen>-<part>` in that loader's own folder, and each screen to have such a route. New planted cases: another screen's loader reading the weather wiring is caught; the weather history's loader passes |
| No cap bar (deviation) | Accepted | The contract does not send the Rs 1,50,000 open-risk cap. Writing it into the screen would be a second copy of a C5 config value, which silently goes stale when the cap changes. Showing open risk alone, with a request for an `open_max_loss_cap` contract field, is the right call |
| India only | MET (code) | The same static-params, `dynamicParams = false` and `notFound` pattern; the nav item sits in India's Portfolio group only |

**Notes (not should-fix):**
- **`fno-screen.css` gets a third edit** (the bar track moved from the weather). W3d also edits this file. Whichever of
  W3c and W3d merges second gets its resolution re-checked, as for W3a part 2.
- **The tightened import test matches by endpoint,** so W3d's route must carry `endpoint: fno/strategy-lab` for
  `fno-strategy-lab`, or this test fails when both are on main. The failure would be loud, not silent: it is a check,
  not a risk.

## Addendum 1: head a2efbb3 (main ea75be3 merged in; the open-risk cap bar drawn)

**PASS.**

- **Shape:** a2efbb3 contains dashboard main ea75be3 (W3d, plus 07c8683 merged as 7731d0e). Its only commits beyond
  main are 5e648af (the main verdict) and a2efbb3.
- **CSS resolution:**
  - `fno-screen.css` differs from main only by three added lines, the shared `.cap` track (`.cap`, `.cap .bar` and
    `.cap .bar i`). Main's `.strip` (W3a) and W3d's rules are untouched.
  - `weather.css` keeps only `:where(.weather) .cap{margin-top:4px}`. Weather's bar is unchanged, because its root is
    `fno-screen weather` (it gets the grid and gap from the shared track, and the margin from its own rule).
  - The paper books' root is `fno-screen paper-books`. Its unused `.risk` rule is removed.
- **Cap bar:**
  - `view.ts` draws the bar as `width(open_max_loss, open_risk_cap)`, capped at 100%. The schema's
    `exclusiveMinimum: 0` rules out a divide by zero.
  - The words and aria label are identical to mockup 41's `2-books.js:19-20`.
  - There is no 150000 in the screen's code. The new test with a Rs 60,000 cap and Rs 30,000 open risk gives a 50%
    bar and the words follow it.
  - This closes judge 225's accepted deviation (no cap bar).
- **Import graph:**
  - Readers of a screen's wiring are matched to that screen's own routes by endpoint (`fno/paper-books`, and W3d's
    `fno/strategy-lab`).
  - My planted break was caught: the weather loader folder reading `fno-paper-books/wiring` failed "fno-paper-books:
    only its own pages' loaders read its wiring". It was removed afterwards.
- **notRead:** `getFnoPaperTrades` is now read and removed from notRead; 2.9's `getFnoForecastHistory` is kept.
- **Gates on a2efbb3:** `check_contract` and `check_fno_screens` exit 0, code size is OK, and `sync-design` leaves the
  tree clean. `tsc` passes. `npm test` gives 520/520 (0 skipped). `next build` exits 0, with `/india/paper-books` and
  `/india/strategy-lab/fno` built.
