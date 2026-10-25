# Judge 45: story W12, Screener (33) and Markets (34) in the real app

**Verdict: FAIL.** There is 1 should-fix finding and 3 minor findings.

**The work is strong.**
- **Both pages pass the harness.** Every W12 case passes, Home's harness still passes, and both pages also hold at
  1440, 1680 and 360 px.
- **The figure check bites.** My 4 visual plants (breadth, flows, US F&O, Buy/Sell) are each caught with an exact
  message.
- **The 13 uncovered states are not hidden failures.** With data present, all 13 render through the contract and
  pass the same checks.

**The should-fix is a data-integrity defect W12 introduced.** W12 runs W11's blocks through the model-name scrub,
and the scrub rewrites every string, company names included. Two real NSE companies, GPT Healthcare and GPT
Infraprojects, would be shown as "AI team Healthcare Limited" and "AI team Infraprojects Limited".

**What I judged**
- **Repository:** `exepex/omenix-dashboard` at 52a07f6 (W12: 361be46, 0113cdb and 80c9bc2; merged 2637880).
- **Claims:** `reviews/claude/response_14_w12_screener_markets.md`.
- **Story:** trading `docs/stories/X-cross-repository.md`, W12.

## Checks run by the judge

```
$ npm ci; npx tsc --noEmit                        clean
$ npm test                                        387 tests, 387 pass
$ node tools/check_code_size.mjs                  every file within 350 lines or its listed size
$ npm run build                                   ok
$ node tests/ui/harness.mjs --only screener       8 cases, 0 failed
$ node tests/ui/harness.mjs --only markets        10 cases, 0 failed
$ node tests/ui/harness.mjs --only home           13 cases, 0 failed   (W9's Home, including home-open)
$ node tests/ui/harness.mjs --only frame-page     16 cases, 0 failed
```

I could not read the CI run (38399910415) myself: the dashboard repository is outside this session's GitHub scope.
Every CI step above was reproduced locally on 52a07f6. The full-harness result is in the addendum below.

### (a) The 13 states W11's examples do not cover

**Criterion 1's wording ("every gallery state … that the W11 examples cover") excludes them honestly.**
- The fixture adapter answers only the exact query of each example (`STOCK_EXAMPLES`, `FNO_EXAMPLES`).
- Any other view says "no example data for this view yet" instead of showing another query's rows. That is the
  right fail-closed choice.

**Do they render once data exists? Yes (strong evidence).**
- **How I tested:** I temporarily made the fixture answer every query with an example of its block, rebuilt, and ran
  my own harness cases. They carried the same checks (figure sources, Buy/Sell, model names, overflow, console) and
  sat beside the mockup's gallery picture.
- **The states:** `uni=ours`, ours + picks, `per=y1`, `pre=volume`, `pre=oversold`, `pre=picks`, `pre=results`, a
  filter `f=pmin:100,rmax:40&fopen=1`, `fpre=short_buildup`, `fpre=ivhigh`, `fpre=index`, `mov=losers` and
  `mov=active`.
- **Results:** 13 of 13 pass.
- **Screenshots:** the chosen screen is highlighted. With "followed by our tools", the summary switches to that
  universe's counts (3 up, 16 down, of 20).
- **Reverted afterwards.**

The real backend must still answer W11's query semantics. The builder states that limit, and it is correct.

### (b) The hydration fix (useSyncExternalStore server snapshot)

**The mechanism is sound (reasoning, checked in the code).**
- `useFrame()` returns the server's view of the frame while a component hydrates, then the live view.
- It uses `useSyncExternalStore(never, () => true, () => false)`, React's documented "hydrated yet" pattern.
- A client-side navigation mounts directly with the live view.

**With the fix:** I delayed Home's positions and strategy-trades blocks (the sections holding Buy/Sell) by 2.5 s on a
production build. `home-open` passed 3 of 3, with 0 controls locked.

**I could not reproduce the original failure.** With the same delay, the pre-fix frame code passed every run:
- with its `startTransition`: 3 of 3;
- with the transition removed: 3 of 3, delaying the market band;
- with the transition removed: 3 of 3, delaying the trade sections.

So the builder's "12 locked to 0" is **not reproduced by me**. The fix is accepted on its mechanism and on passing
runs, not on a reproduced before-and-after. It replaces a weaker fix and adds no risk I can find.

### (c) Flows

- **1M, 3M and 1Y:** the page shows "Over 1M: — (only 5 days of data for 21 sessions)". This is read from the block's
  `totals`, never summed on screen.
- **1W:** shows "Over these 5 sessions foreign investors sold ₹30,294 crore net …".
- **My plant P2** (show the 5-day sum when the period is incomplete) is caught: "flows:totals.m1.fii: the field is
  empty, the screen shows ₹30,294" and "the m1 flows total is incomplete but the page does not show —".

### (d) US absence

My plant P3 forced the tab group onto the US Screener with "F&O (0)", an empty element. It is caught: "an F&O element
(empty or not) on the US Screener" and "fnoSummary:n: no such field". The US Markets case fails on any flows, VIX or
index-options section, and on "NSE", "Nifty" or "₹".

### My plants (each reverted; `git status` clean)

| # | Plant | Caught by |
|---|---|---|
| P1 | Markets breadth `down` + 1 | **caught**: "summary:universes.all.down: shows 1,477, the field holds 1476" (US: ours 8 vs 7) |
| P2 | Incomplete flows period shows the summed days | **caught** (above) |
| P3 | US Screener shows an empty F&O tab | **caught** (above) |
| P4 | Buy/Sell enabled for every company | **caught**: "MONEYVIEW is not followed but its Buy / Sell are not grey with a reason" (every unfollowed row) |
| P5 | A Screener component statically imports the fixture adapter | **caught**: import-graph test, 3 failing |
| P6 | A Markets component imports the wiring through a computed `import(m)` | **not caught** (minor 2) |
| P7 | "GPT-4o" in a stock's name, in both the contract example and its copy | Not flagged. The adapter **silently rewrote** it to "Moneyview AI team Limited" (my screenshot). That led to the should-fix. |

## Criteria

| # | Criterion | Builder's claim | Judge's evidence | Result |
|---|---|---|---|---|
| 1 | Every gallery state the W11 examples cover renders at 390-1680 px; side by side; differences listed | strong evidence | **Renders:** all 18 cases pass (1280/1024/768/390); my extra cases pass at 1680, 1440 and 360; I read the side-by-side images. **Differences:** the list is incomplete (minor 1). | MET (minor 1) |
| 2 | Components depend only on W11 typed contracts; import-graph test (W8 resolver, transitive) | strong | **Caught:** P5. **Not caught:** a non-literal dynamic import, P6 (minor 2). | MET (minor 2) |
| 3 | DOM assertions against `data-src`, incl. breadth, movers and flows; incomplete flows show "—" with the coverage | strong | P1 and P2 caught; the "—" text is asserted exactly | MET |
| 4 | F&O and India-only elements absent (not empty) in the US; a harness case proves it | strong | P3 caught, including an empty tab | MET |
| 5 | No model or vendor name on any screen; Buy/Sell only for followed companies, grey otherwise with the reason | strong | **Buy/Sell:** P4 caught. **No model name:** holds, but by rewriting real company names (finding 1). | PARTLY |
| 6 | Code size, typecheck, tests, build, UI harness pass in CI | strong once CI green | Every step reproduced green locally (full harness: see the addendum). The CI run itself was not visible to me. | MET locally; CI run unverified by the judge |

## Findings

### 1. Should fix: the model-name scrub rewrites real NSE company names

- **Where:** `exampleReader` (`lib/fixtures/examples.ts`) passes every payload through `applyDisplayNames`, which
  calls `withoutModelNames(t, "AI team")` on **every string** (`lib/ui/strategy-names.ts:76`).
  - W9 used it for strategy blocks.
  - W12 puts W11's Screener and Markets blocks through it, and those blocks carry NSE security names and news text.
- **The detector:** `lib/ui/model-names.ts` counts "gpt" as a brand on its own.
- **My run over all 2,606 names in 33's NSE name list** (`design/mockups/33-screener/source/names.csv`):

  | Symbol | NSE name | Shown |
  |---|---|---|
  | GPTHEALTH | GPT Healthcare Limited | **AI team Healthcare Limited** |
  | GPTINFRA | GPT Infraprojects Limited | **AI team Infraprojects Limited** |

- **Why no test sees it:** neither company is in W11's examples. A real adapter that goes through the same boundary
  rule would show both wrong names.
- **Why it matters:**
  - The page would invent text and misname a listed company, which is wrong data on a trading screen.
  - The owner rule is "no AI model or vendor name". A company that happens to be called GPT is neither.
  - The same rewrite would silently alter any headline or event text that quotes an AI company, instead of keeping
    it off the screen by design.
- **Expected:**
  - Apply the display-name rule only to fields that can carry a strategy or model name (strategy names, and the tools'
    free text), never to security names, symbols or exchange-sourced text.
  - Or exempt fields the contract marks as security identity (`s`, `n`).
  - Keep the harness's page-text gate as the backstop. If it ever flags a real company name, that is an owner
    decision (an allowlist of listed names), not a silent rewrite.
  - Add a test with GPT Healthcare's real name, which must render unchanged.

### Minor findings

1. **The differences list misses visible data differences against the mockup pictures.**
   - **What differs:** W11's examples were regenerated after the mockups' gallery pictures (sessions fix,
     split/bonus fix). So the app shows:
     - Screener near-high 54 against the picture's 50, near-low 247 against 254, volume 63 against 64;
     - KOTAKBANK's 52-week position 91% against 5%;
     - Markets breadth 54 / 247 / 692 against 50 / 234 / 689.
   - **Event titles also differ:** W11 says "HDFC Life results" and "NSE monthly F&O expiry (last Tuesday)", where
     the mockup says "earnings" and "NIFTY monthly expiry".
   - **Why it is minor:** these come from the contract, not the app, and are correct. But the owner reviews side by
     side, so the list should say so: one line naming W11's regenerated examples, with design's changes files.
2. **The import-graph test misses a computed dynamic import.** `import(m)` with `m` built from strings, reaching
   `lib/overview/wiring.ts` from a component, passes all 4 tests. **Expected:** fail on any non-literal `import()` in
   `components/` and the pages' client parts. That is one rule, and the code base has none today.
3. **Neither page is in the frame's every-page list** (`frame.mjs` `inFrame`, 390-1680), and no committed W12 case
   runs above 1280. My 1680 run passes, so this is coverage, not a defect. **Expected:** add `screener-stocks` and
   `markets-india` to the frame's page list.

## Claims vs reality

| Claim | Checked | Result |
|---|---|---|
| 13 uncovered states show "no example data …" and would render from the contract | My any-query probe: 13 of 13 render and pass the checks | **True** |
| Paged blocks answer only their example's query | `answer()` matches `queryKey` exactly | **True** |
| Flows: published totals, "—" with coverage | Read; P2 caught | **True** |
| US absence by element and text | P3 caught | **True** |
| "W9 detector at every adapter (`exampleReader`)" satisfies criterion 5 | It does, by rewriting all text, company names included | **True, with finding 1** |
| The hydration root fix: 12 locked to 0 | Fix passes 3 of 3; the failure did not reproduce for me (9 runs of the old code) | **Mechanism accepted; the failure itself not reproduced** |
| 387 tests, build, code size | My runs | **True** |
| Tooltip layer's `tabindex` mutation (raised, not fixed) | Agreed: outside W12. It should become its own small fix. | noted |

## Project rules

- **Read-only:** I edited nothing in the dashboard repository. Every plant was reverted, and `git status` is clean.
- **Size and design:** new files are small and single-purpose. `lib/fixtures/examples.ts` and `lib/ui/sources.ts` are
  shared readers (DRY). Each page has one wiring line.
- **No order placement:** paper Buy/Sell goes through the frame's single order window.

## Addendum: the full UI harness

```
$ npm run build && node tests/ui/harness.mjs      (clean tree at 52a07f6)
  166 cases, 0 failed
```

**Every page passes**, so the frame change (`useFrame`'s server view) breaks no page. The only open item on
criterion 6 is the CI run itself, which is outside my reach (see above).

## Addendum 2: round 2 (omenix-dashboard e885f17, `response_25`)

**Round 2's own scope is ACCEPTED. W12 stays FAIL:** finding 1 (the scrub rewrites real company names) is not part of
this round and is still in the code (`lib/ui/strategy-names.ts:76`).

**Checks:**
- tsc clean; `npm test` 388 of 388; build ok.
- Harness: **Screener 19 cases and Markets 12 cases, 0 failed**; `home-open` passes.
- CI for e885f17: not visible to me (outside my GitHub scope).

**The 13 states are now covered by real W11 examples.**
- The adapter reads each example's own `x-query`, so the examples are the one source of truth. I confirmed this in
  round 1 with my any-query probe.
- Each state is now a committed case beside its gallery picture. Criterion 1 no longer depends on the "not covered"
  wording.

**The tools order (picks: most buying; results: soonest). My plant reversed `toolsOrder`:**
- **The unit test catches it** (1 failing).
- **`screener-picks` still passes.** `orderProblems` builds its expected order with the app's own `toolsOrder`, so
  the UI check is circular. It proves the page applies the function, not that the order is right.
- **Minor 4 (new):** the UI check should state the order from the tools block's fields directly (most buying first,
  then the route's order), not call the app's function. Correctness is held by the unit test today, so this is
  minor.

**The near-high tie order** (exact position against the rounded percent): agreed. Same set and same count, and it is
listed as a difference.

**Still open from round 1:**

| Finding | Status |
|---|---|
| 1 (should fix) | Open: model-name scrub rewrites "GPT Healthcare/Infraprojects Limited" |
| Minor 1 | Partly: the uncovered list is gone; the regenerated-examples differences are still not listed |
| Minor 2 | Open: computed `import()` |
| Minor 3 | Open: not in the frame's 1680 list |

## Addendum 3: round 3 (omenix-dashboard 758c6d3, 7bc0e0c, 672c9a0; `response_26`)

**Verdict on W12: PASS.** The should-fix and all four minors are fixed, and each is re-checked with my own plants.
There is 1 new minor on the detector's reach.

**Checks:**
- tsc clean; `npm test` 392 of 392; build ok.
- Harness: **Screener 21, Markets 14, frame-page 20 (now including both pages at 390-1680 px), `home-open` 1:
  0 failed.**

| Judge 45 item | My re-check | Decision |
|---|---|---|
| 1 Should fix: the scrub rewrote real company names | My run of the detector over all 2,606 NSE names: **0 hits**. GPT Healthcare and GPT Infraprojects stay as published. W12's blocks skip the strategy rule. **My plant:** "Moneyview GPT-4o Limited" in the contract example and its copy, rebuilt. It is now **flagged**, not rewritten: `screener-stocks` and `frame-page-screener-stocks` fail at every width with "names an AI model: … Moneyview GPT-4o Limited". | ACCEPTED |
| Minor 1 Differences list | The regenerated-example differences are now listed (near-high 56, near-low 247, volume 63; KOTAKBANK 91%; "results" and the expiry title) | ACCEPTED |
| Minor 2 Computed `import()` | My `import(m)` plant in a Markets component: **caught** (1 failing) | ACCEPTED |
| Minor 3 Pages at 1680 | The frame list now runs `screener-stocks`, `screener-us`, `markets-india` and `markets-us` at 390-1680 px; all pass | ACCEPTED |
| Minor 4 Circular order check | My reversed `toolsOrder` plant: `screener-results` **fails** ("the results rows read ULTRACEMCO … not the tools order HDFCLIFE …"). `screener-picks` still passes, because all seven picks tie at 3 buys, so only the symbol tie-break orders them. That is correct and is now unit-tested. | ACCEPTED |
| `home-open` claim | Restated as a mechanism fix, not reproduced on demand ("some evidence"). That matches my finding. | ACCEPTED (honest restatement) |

**Minor (new): what the detector now misses.** Making "GPT" need a version removes the false positives on company
names, at a cost:

| Text | Before | Now |
|---|---|---|
| "uses GPT" (bare, in prose) | flagged | **not flagged** |
| "gpt-oss-120b" (an open model's name) | flagged (brand) | **not flagged**: "-oss" is neither a digit part nor a listed variant |
| "GPT-4o", "gpt4", "GPT 5", "ChatGPT", "OpenAI", "Claude", "(GPT)", "o3" | flagged | flagged |

- **Why it is minor:** none of these appear in any fixture, and the backends' outputs pass through the strategy
  allowlist.
- **Expected:** add "oss" (and the vendor's other open-model suffixes) to the variants, and accept bare "GPT" as a
  known residual risk in the owner's rule text, since it collides with listed company names.
