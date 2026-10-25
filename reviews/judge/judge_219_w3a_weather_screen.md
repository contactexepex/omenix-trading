# Judge 219: W3a part 1, the market weather screen (exepex/omenix-dashboard story/w3a-weather at 5cbbaa44)

**Verdict: PASS.** I checked a read-only clone at 5cbbaa44: `npm ci`, then `npm run typecheck` (clean) and `npm test`
(**483 passed, 0 failed, 0 skipped**; the builder claimed 483). The orchestrator's checks:

1. **The no-threshold test with a pinned copy of M1's levels: acceptable.**
   - `tests/m1-levels.ts` matches trading exactly: `WEATHER_RED_FLOORS (0.10, 0.35)`, `WEATHER_AMBER_FLOORS
     (0.06, 0.20)` and the multiples 2.5 and 1.5 (`fno/weather/constants.py:23-24`); `RED_LIMITS (1.30, 0.20, 0.020,
     0.25)` and `AMBER_LIMITS (1.10, 0.10, 0.0125, 0.18)` (`checklist_v0.py:22-23`).
   - It is test input only, so it adds no exposure: the dashboard repository is public, but so are these values in
     trading (judge 216).
   - It cuts both ways: the screen's code and its rendered output are scanned for the levels and for threshold
     wording, with planted breaks.
   - The one stated exception, "2% move", names the question, not a level.
   - The drift risk (a new weather version with new levels) is stated in the file. A new M1 version is lane 1 and
     judged, so the copy's update can be required there.
2. **`/us/weather` is a real 404: verified in code.** `app/(cockpit)/[market]/weather/page.tsx` has
   `generateStaticParams` with India only, `dynamicParams = false` and `notFound()` for any other market. The route
   test shows the nav item only in India's Markets group. The builder's `next start` check (200 for India, 404 for
   the US) is consistent with that code.
3. **Gateway rule: met.** `gateway-imports.test.ts` takes its roots from `gatewayDecision` itself (served routes plus
   rewrite targets, `OAUTH_ROUTES` now exported rather than copied, "/" as `/about`). It fails if any reaches
   `lib/fno-*`, `components/fno-*` or a W3 page, and it catches planted direct and chained imports.
4. **Changes to existing files: each is a no-op or additive.**
   - `OAUTH_ROUTES` gains `export` only, with the same object and no behaviour change.
   - `ExampleTag`'s prop narrows to `Pick<Instrument, "live">`, the one field `exampleTagShown` reads, so every
     existing caller still type-checks (typecheck is clean).
   - `.mb-howto` is added, three lines, to `design/system/components.css`, its README and the web copy. It is a new
     class replacing a page-local duplicate the duplicates test refused, and no existing class changes. As a
     design-system change it is additive and documented; the owner may still review the look.

**Notes (not should-fix):**
- **After contract 2.8.0 merges (judge 217):** re-check `contract.ts` against 2.8.0's `FnoWeather`. Its new required
  `recent[].label`, `red_share.basis` and `scores[].exploratory` should then be shown, with back-fill labelled
  exploratory, per story W3 answer (d).
- **The icon:** the nav uses `sensors` because the sprite has no weather glyph, as stated. Adding one is the owner's
  call.
