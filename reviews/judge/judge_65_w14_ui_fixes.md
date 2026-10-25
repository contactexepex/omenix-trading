# Judge 65: W14 (dashboard), UI interaction fixes

Date: 14 Oct 2026 (IST). Repository: exepex/omenix-dashboard at 6cc6b7a (claims: `reviews/claude/response_30*.md`, d18a489).
Story: trading `docs/stories/X-cross-repository.md` W14.

## Verdict: criteria 1-4 MET; criterion 5 PARTLY (the builder says so); one rule breach found outside W14's scope

## Gates (my runs)

- `npm ci`, `npm run build`: pass.
- `npm test`: 444 pass, 0 fail (more than the claimed 435 because main moved on).
- `node tools/check_code_size.mjs`: pass.
- UI harness `--only w14`: 24 cases, 0 failed. I did not re-run all 207 cases (cost).

**Planted breaks (one build, four plants):** 21 of 24 W14 cases failed, each on its own plant. All restored afterwards.

| Plant | Caught by |
|---|---|
| The flyout's route-change close removed (`use-flyouts.ts`) | `w14-flyout`: "stayed open after the move", "reopened by itself" |
| The 250 ms loader delay overridden (`.mb-delayed` always visible) | `w14-block-loader` at 1280 and 390: "showed before the delay (flicker)" |
| Disabled controls' border removed | `w14-disabled` ("border is none, not dashed") and every `w14-look-*` case |
| Links un-underlined on the News page | `w14-look-news-india`: each link named |

## Per criterion

| # | Criterion | Check | Result |
|---|---|---|---|
| 1 | Page loader on load and route change; block loader only in the triggering block; `aria-busy` | Harness `w14-page-loader` and `w14-block-loader` pass; the delay plant caught | MET |
| 2 | Clickable things look clickable; disabled ones visible, distinct from labels, never clickable | `w14-look-*` (18) and `w14-disabled` pass; two plants caught; disabled Buy/Sell are native `disabled` with the reason on the wrapper | MET |
| 3 | Flyout closes on navigation, Escape, outside click | `w14-flyout` covers all three plus keyboard reopening; plant caught | MET |
| 4 | Every price chart on signed-off pages zooms, pans, resets, crosshair, one shared component | `w14-chart-stock` and `w14-chart-markets` pass; one shared `zoom.tsx` with `chart-view.ts`. Not planted by me. Non-price charts excluded, stated | MET (not planted) |
| 5 | Every signed-off page audited and fixed; shared parts replace page-local styles and duplicated markup; 350-line limit and design rules hold | Audit table of 17 pages: 808 findings to 0 (the builder's tool; my plants show the tool detects these classes). **Partly modular:** three duplicate `.go` rules, three sort-header rules and a second `useWidth` remain (builder lists them). The size check passes only through `tools/code_size_allowlist.txt`: 10 older files over 350 lines, the largest `strategy-lab-page.tsx` at 607. W14 added none, but the limit does not "hold" for those files | PARTLY |

## Claims vs reality

| Claim | Reality |
|---|---|
| "808 findings to 0" | Not re-run by me; the per-page cases pass and catch my plants, so the claim is consistent |
| Rule breach on the app's Strategy lab page (strategy internals shown) | **Confirmed.** `strategy-lab-page.tsx` line 341 shows "buys when the chance of a rise is at least …" as a chip, with signal, news weight and regime filter beside it. This is against the 13 Oct rule "strategy internals stay private". Not W14's scope, but it is live on the deployed app: it needs its own story, soon |
| Plain mouse wheel scrolls the page, not the chart | A sound choice (reasoning): it avoids trapping page scroll. The owner may disagree; it is one line |
| Mockups' own charts do not zoom | Stated; they are static references |

## Follow-ups

1. The Strategy lab internals breach (owner rule): its own story. This is the most important follow-up.
2. W14's criterion 5 remainder: merge the duplicate `.go` and sort-header rules and the second `useWidth`.
3. The size allowlist (10 files, up to 607 lines): a cleanup story, so the 350-line rule holds without exceptions.

## Addendum 1 (W14 round 2, omenix-dashboard 375ceee; X1 restore check e20cc12)

**Verdict: PASS on criterion 5 and the internals breach on the Strategy lab and Help. One should-fix: the API
projection is a deny-list whose test is circular.**

**Duplicates and the guard: MET.**
- `lib/ui/tests/duplicates.test.ts` fails on my plant (a `.sec-head` rule block re-added to `markets.css`: 1 failed).
- `check_code_size.mjs` passes. `strategy-lab-page.tsx` is off the allowlist; the largest part is 143 lines.
- 38 older duplicate blocks are listed in a shrink-only allowlist. Stated, and not hidden.

**Internals on the pages: MET.** I planted a tooltip with each strategy's description back into `lab-detail.tsx` and
rebuilt. `w14-no-internals-lab` fails, naming four strategies' descriptions (the fixture still carries them, as
claimed). `w14-no-internals-help` passes.

**Internals in the API, partly:**
- **Removing the projection step from the page spec is caught:** 1 failed.
- **Should fix: removing `threshold` from `INTERNAL_KEYS` is not caught.** All 450 tests pass, and the stored registry
  entry does carry `threshold: 0.55`, so the API would send it again. The cause: both projection tests loop over
  `INTERNAL_KEYS` itself, so they can never notice a key leaving that list. A future registry field (another setting)
  would also pass straight through, because the projection is a deny-list.
- **Fix (reasoning only):** project to an allow-list of the public fields (`id`, `family`, `name`, `horizons`, `live`,
  `live_from`, `settled_trades`), and make the test name the forbidden keys literally, not through the module's own
  constant.
- I could not call the real route: it answers 503 without the data service, and the harness serves fixtures in the
  browser. The route check rests on the handler test.

**Still open (the builder listed these; I agree they matter):**
- Display names and ids carry how a strategy decides ("60% bar", "calm markets only"; ids like `rule.model_news.v1`).
- The stock-strategies, lifecycle and track-record endpoints still carry thresholds.
- The payload's `backtest_run.note` still says the model-only strategy needs "walk-forward probabilities". That is
  method, not a decision rule, but worth the same review.
- These are the owner's call and a follow-up story.

**X1 restore marker (e20cc12): MET, verified by running it.** I started Docker and ran
`platform/tests/restore_marker_check.sh` in `bash:3.2` (3.2.57) with stubbed `psql` and `az` (no Azure). All 4
endings send `DROP TABLE` and write the evidence line.

On `restore_test.sh` as it was before a0bb4bb, the same check fails two endings:
- "normal": the marker written, no drop;
- "ctrl-c-in-wait": the evidence line missing.

So the check really catches the bash 3.2 trap bug. Note: e20cc12 adds the check only. The script's fix is a0bb4bb,
and this commit proves that fix.

## Addendum 2 (8893f17: the Strategy lab API projection is now an allow-list)

**MET; the should-fix is closed.** The projection now keeps only `PUBLIC_KEYS` (`id`, `family`, `name`, `horizons`,
`live`, `live_from`, `settled_trades`). The tests name the forbidden keys literally and plant an unknown field
(`planted_secret_setting`). My plants, run on the strategy-pages and data-handler tests (109 pass at baseline):

| Plant | Result |
|---|---|
| `threshold` added to the public list (the old plant, the other way round under an allow-list) | caught (2 failed) |
| `parameters` added to the public list | caught (2 failed) |
| No projection at all (entry returned as is) | caught (2 failed) |

A new registry setting now stays private unless someone adds it to the list on purpose. The test's planted field
shows that.
