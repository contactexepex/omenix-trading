# Judge 32: story W11 re-judged (round 2)

**Verdict: FAIL.** There is 1 should-fix finding, a regression this round introduced.

What is fixed:
- **Judge 27 findings 2 and 3:** ACCEPTED, with my own plants.
- **Finding 1:** the design is ACCEPTED (one calendar per market, a documented query per screen, a disagreement
  check).
- **Minors 4, 5 and 6:** closed.

The regression: Home's documented query ("the 6 nearest of 7 kinds") does not reproduce the signed-off Home on a
real calendar. Resyncing Home's fixture to that calendar removed the holiday, the monthly F&O expiry and the FOMC that
the signed-off Home shows, and no test noticed.

**What I judged**
- **Repository:** `exepex/omenix-dashboard`, b23daca (merged into main at ef9bd9a), cloned read-only.
- **Answers:** `reviews/claude/response_11_w11_screener_markets_api.md`.
- **Story:** W11, now written in trading's `docs/stories/X-cross-repository.md` (minor 4 closed).

## Checks run by the judge

```
$ python3 tools/api/check_contract.py      (openapi-spec-validator 0.7.2)
  contract: 64 paths (37 block endpoints), 70 block examples, 113 block schemas, 753 catalogued leaf fields, 31 planted breaks
  contract: OpenAPI 3.1 valid; examples valid and current; catalog complete; screen rules hold; every planted break caught
$ python3 tools/api/check_mapping.py       mapping: zero gaps both ways; no endpoint mixes two independent blocks
$ python3 tools/api/examples.py --check    examples: api/examples/*.json match the mockups' data
$ cd web && npm test                       # tests 363 # pass 363 # fail 0      (at ef9bd9a)
$ npm run build && node tests/ui/harness.mjs      148 cases, 0 failed                  (at ef9bd9a)
```

### My round-1 plants, in memory through the builder's validator

| # | Plant | Round 1 | Round 2 |
|---|---|---|---|
| J1 | A US row with `fut`, `oi`, `b`, `lot` | not caught | **caught** |
| J2 | A US row with `dl` | not caught | **caught** |
| J5 | The US summary with an `fno` block | not caught | **caught** |
| J7 | An RBI decision in the US calendar | not caught | **caught** |
| J9 | A currency on a world quote | not caught | **caught** |
| J10 (new) | A nested extra object on a US row | – | **caught** |

### Flows totals: my plants through the schema and `check_flows`

| Plant | Schema | `check_flows` |
|---|---|---|
| 1M marked complete, carrying the 5-day sums | passes | **caught** |
| The 1W FII total off by Rs 100 crore | passes | **caught** |
| FII and DII added into `fii` | passes | **caught** |
| 1M incomplete but carrying a number | **caught** | **caught** |

### Home's "Coming up": the signed-off picture against the resynced fixture

| | India (from 7 Oct) | US (from 7 Oct) |
|---|---|---|
| **Signed-off Home** (31 gallery; Home fixture at 1c026c4) | RBI 7 Oct, Reliance 16, HDFC Bank 17, **NSE closed 20**, **monthly F&O expiry 27**, **FOMC 29** | JPM 13, CPI 14, **FOMC 28**, Apple 29, **jobs report 6 Nov**, Nvidia 17 Nov |
| **Now** (`kinds=…&limit=6` on the 12 Oct calendar, ef9bd9a) | RBI 7, HDFC Life 15, Reliance 16, HDFC Bank 17, ICICI Bank 17, UltraTech 19 | JPM 13, CPI 14, Bank of America 14, Progressive 14, GM 20, United 20 |

- **The harness does not see it:** 148/0. Its comparisons are images for a person, not assertions. My own run's
  `home-india/compare-1280.png` shows "NSE closed 20 Oct" in the mockup and "HDFC Life results 15 Oct" in the app.
- **The same query on Home's own signed-off events reproduces both pictures exactly** (my script: India True, US
  True). So the query only works in the mockup's 3-company world.
- **The stock tool follows 20 companies per market, so production Home would behave like the new fixture.**
  Results crowd out the market-wide events the signed-off screen shows. For a trader, the 20 Oct NSE holiday and the
  27 Oct monthly expiry matter most.

**A rule that reproduces the signed-off design on both worlds (my script, some evidence):** take the market-wide
kinds in date order, then fill with the nearest results up to 6, and show them by date.
- **On Home's signed-off events:** identical to both pictures (True, True).
- **On the real 12 Oct calendar:** India gives RBI 7, HDFC Life 15, Reliance 16, NSE closed 20, F&O expiry 27,
  FOMC 29. US gives JPM 13, CPI 14, BofA 14, Progressive 14, FOMC 28, jobs report 6 Nov.

## Judge 27's findings: decisions

| # | Finding | Builder's fix | Judge's evidence | Decision |
|---|---|---|---|---|
| 1 | Should fix: one `/events` block, contradictory examples | One calendar per market (`getEvents_<m>_calendar`); `/events?kinds=&from=&limit=`; each screen's example is its documented `x-query` applied to the calendar; `check_views` recomputes them, with a disagreement plant | Design and check confirmed; Markets now lists US CPI on 14 Oct and FOMC on 28 Oct. **But Home's query does not reproduce the signed-off Home on the real calendar** (above). | ACCEPTED for the design; **new should-fix** below |
| 2 | Should fix: F&O and India-only fields open in the US | All 25 W11 objects closed; `dl` and `screens.delivery` India only by rule; 8 plants | J1, J2, J5, J7, J9 and J10 caught | ACCEPTED |
| 3 | Should fix: flows period total | `Flows.totals` per period with `days`, `complete`, null unless covered (`if`/`then`); `check_flows` recomputes from the days | 4 plants caught (above) | ACCEPTED |
| 4 | Minor: no written story | Written by the orchestrator | W11 is in `X-cross-repository.md` with 6 criteria | ACCEPTED |
| 5 | Minor: no `major_event_names` example | Home's `/session` examples carry it (India "RBI policy decision"; US empty) | Present and validated | ACCEPTED |
| 6 | Minor: token-level mapping | Stated as a limit; prose table done by hand | The builder's table agrees with my judge-27 hand check | ACCEPTED |

**The owner's answer to question 1** (exepex/trading publishes the NSE-file blocks) is applied: publisher `fno`,
story `TR-NSE-proposed`, India-only paths, and "Published today?" still says no. Correct.

## Criteria (story W11 as written)

| # | Criterion | Result |
|---|---|---|
| 1 | Every 33/34 element maps to one endpoint with a validated example; zero gaps; notes unchanged | MET |
| 2 | One source fixture per shared endpoint; each screen's example derived by a documented query; a test fails on disagreement | MET in form. The derived Home view no longer matches the signed-off Home (see criterion 6). |
| 3 | F&O and India-only fields absent in the US by schema, with plants | MET |
| 4 | Coverage stated; uncovered totals null; 1M-from-5-days plant fails | MET |
| 5 | Catalog: source, owner story, freshness, "Published today?" | MET |
| 6 | Contract changes additive only (Home's fixture unchanged, or regenerated by sync with tests green); size, typecheck, tests, build, CI | **PARTLY.** The wording is met (resynced, 363/363, 148/0). "Additive only" is not: the change altered what the signed-off Home shows, and the tests cannot see it. |

## Finding (should fix)

1. **Home's documented events query must reproduce the signed-off Home on a real calendar.**
   - Today `kinds=…&limit=6` reproduces it only in the mockup's 3-company world. On the 12 Oct calendar it drops the
     holiday, the monthly expiry and the FOMC (India) and the FOMC and jobs report (US).
   - **Expected:**
     - a selection rule that keeps 31's design on real data, for example market-wide kinds first and then the nearest
       results, up to 6 (it reproduces both signed-off pictures exactly);
     - the rule written into `x-query` and `check_views`;
     - a check that Home's query applied to 31's own events equals the signed-off "Coming up";
     - the difference stated in `response_9`'s differences list if any remains.

   If the owner prefers results to crowd out market events, that is a change to a signed-off screen and needs the
   owner's sign-off, not a fixture resync.
