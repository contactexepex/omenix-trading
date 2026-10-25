# Judge 19: story W8, the signed-off app frame in the real app

**Verdict: FAIL.** There is 1 should-fix finding: the import-graph test, which enforces criterion 5, can be bypassed
in two ways. There are also 3 minor findings and no blocking ones.

Everything else checks out:
- the frame matches the signed-off mockup;
- every page runs inside the frame;
- the closed-market lock works;
- the order window cannot submit anything.

**What I judged**
- **Repository:** `exepex/omenix-dashboard` at 068f774, cloned read-only to `/tmp`.
- **Story:** W8 in trading's `docs/stories/X-cross-repository.md`, with criterion 1 corrected to use the running-app
  harness.
- **Claims:** `reviews/claude/response_3_w8_app_frame.md`, with its images in `reviews/claude/w8/`.
- **Verdict location:** trading's `reviews/judge/`, as agreed with the orchestrator.

## Checks run by the judge

```
$ node tools/check_code_size.mjs                code size: every file within 350 lines or its listed size
$ cd web && node tools/sync-design.mjs --check  design copies current
$ npm ci --ignore-scripts && npm run typecheck && npm test && npm run build
  tsc exit 0; # tests 346 # pass 346 # fail 0; build exit 0
$ node tests/ui/harness.mjs --out /tmp/w8ui     (next start; Playwright 1.56.1 on the preinstalled Chromium)
  147 cases, 0 failed
```

**Story's "judge verifies" step: running the app and looking at real pages.** These are the harness's own screenshots
of the running app, not the builder's images. I looked at:

- **Rule vs AI** at 1280 px;
- **Paper portfolios** at 1280 px;
- **Company / RELIANCE** at 390 px;
- **the default frame** next to the mockup (`compare-default-1280`);
- **the closed-market order sheet** next to the mockup (`compare-closed-order-390`).

What I saw:

- **Frame:** at 1280 px the frame (top bar, market switch, closed chip, index strip, rail, picks panel) matches the
  mockup element by element.
- **Order sheet at 390 px:** matches the mockup, including the estimate labels and the disabled "Market closed" foot
  button.
- **Old pages:** they render inside the frame without overflow, and the harness checks this at 390, 768, 1280 and
  1680 px.

### Planted imports (criterion 5)

Run with `node --test lib/shell/tests/import-graph.test.ts`:

| # | Plant | Result |
|---|---|---|
| 1 | `components/frame/parts.tsx` imports `../../lib/shell/fixture-source.ts` | **caught** (2 tests fail) |
| 2 | The same component imports the JSON fixture `../../lib/shell/fixture/shell.generated.json` | **caught** |
| 3 | A page (`app/(cockpit)/[market]/companies/page.tsx`) imports `../../../../lib/shell/wiring.ts` | **caught** |
| 4 | A component calls `fetch("/api/v1/orders", {method: "POST"})` | **caught** (criterion 6 test fails) |
| 5 | **`components/frame/parts.tsx` imports `@/lib/shell/fixture-source`** (tsconfig has `"paths": {"@/*": ["./*"]}`) | **NOT caught**: 6 of 6 pass, and `tsc --noEmit` accepts it |
| 6 | **A new `lib/shell/helpers-x.ts` re-exports the fixture adapter, and a frame component imports that helper** | **NOT caught**: 6 of 6 pass (the check is not transitive) |

All plants were reverted; `git status` is clean.

### Lot change, 75 to 65 (the builder's doubt c)

- `30-shell/changes.md` records it.
- The data commit changes only values: `lot` and the `name` strings.
- `notes.md`, the signed-off contract, is unchanged since the sign-off commit 82b60bd.
- I checked NSE's live file `BhavCopy_NSE_FO_0_0_0_20261009_F_0000.csv.zip`: all 1,891 NIFTY rows have
  `NewBrdLotQty = 65`.

So this is a **data correction, not a contract change**. Accepted.

## Criteria

| # | Criterion | Judge's own evidence | Result |
|---|---|---|---|
| 1 | Every page inside the frame at 390, 768, 1280 and 1680 px; no console errors, external requests or overflow | Harness: 147 cases, 0 failed (16 page cases × 4 widths); screenshots read | MET |
| 2 | Side-by-side comparison at 1280 and 390 px for the default, dark, US and closed states, differences listed | 14 comparison images committed, 2 reviewed. The 7 differences listed are honest. One unlisted visible defect remains (minor 2). | MET |
| 3 | Search: a stock by name and by ticker, an option by its NSE code; no F&O in the US | 9 search tests pass, plus the UI cases `frame-search-india` and `frame-us` | MET |
| 4 | Market closed: every manual Buy and Sell disabled with the reason, by one rule | `market.ts` rule; `trade.tsx` is the only place Buy and Sell are drawn; `frame-lock` passes; the 390 px sheet shows "Market closed" | MET |
| 5 | Components import only `ShellData`, never the adapter or a data client; **an import-graph test enforces it** | The rule holds in today's code: plants 1-3 are caught. **The test misses the `@/` path alias and imports through a re-export** (plants 5 and 6). | PARTLY |
| 6 | Order window: estimates labelled, the fill basis named, no submit path | Labels seen at 390 px; plant 4 caught; the harness sends no non-GET request, even on a forced click | MET |
| 7 | Code size, typecheck, at least 303 existing tests, build; no regression | 346/346, typecheck, build and code size all pass; all earlier harness cases pass | MET |

## Claims vs reality

- **"Planted imports are caught (static, dynamic, JSON)":** true for relative paths. False for the `@/` alias and for
  re-exports (plants 5 and 6).
- **"147 cases, 0 failed" and "346 tests":** true, reproduced.
- **Doubt (a), the locked-button colour:** settled by the orchestrator (grey is the signed-off rule) and not judged
  here. The default comparison image matches.
- **Doubt (f), the UI harness is not in CI:** true; weighed in minor finding 1.

## Engineering standards

- The 17 frame components are small, under 350 lines each.
- Pure logic sits in `lib/shell/*.ts` with unit tests.
- The adapter is chosen in one line in `wiring.ts`.
- Old defects were fixed at their cause (container queries).
- No breach found.

## Findings

1. **Should fix: the criterion 5 enforcement can be bypassed.**
   - Evidence: plants 5 and 6 above. The `@/` alias compiles and passes. A re-export through any `lib/` module
     passes.
   - Expected:
     - `importsOf` resolves `@/` to the web root, exactly as tsconfig does.
     - The check follows imports transitively from each component, or forbids any module except `wiring.ts` from
       importing `fixture-source.ts` and the fixture folder.
     - Add tests for both plants.
2. **Minor: the UI harness is not in CI** (builder's doubt f). Criterion 1's evidence exists only when someone runs it
   by hand, so a later change could break a page inside the frame and CI would stay green. Expected: a CI job with the
   same Playwright 1.56.1 on Chromium. The harness header already says CI installs it the same way.
3. **Minor: one visible defect is not in the differences list.** On the Watchlist page at 1280 px inside the frame,
   the "Most strategies like" card breaks the ticker mid-word ("RELIAN / CE", `compare-default-1280.jpg`). The card is
   narrower now that the picks panel takes width. Expected: fix the card (no break inside a ticker) or list it.
4. **Minor, an observation for the owner (not W8's code):** the existing Rule vs AI page shows "AI combined (Opus)" on
   screen. W10's contract says model ids are never shown and the screen shows "AI team". When W9 or a later story
   rebuilds that page, it should follow the new rule.
