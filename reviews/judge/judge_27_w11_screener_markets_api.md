# Judge 27: story W11, the API contract and data catalog for the Screener (33) and Markets (34)

**Verdict: FAIL.** There are 3 should-fix findings and 3 minor findings.

What works:
- OpenAPI 3.1 is valid, and the examples validate.
- The builder's 20 planted breaks are caught.
- The 72-element mapping check passes.
- The web app is untouched: 363 of 363 tests pass, and Home's fixture is byte-identical.
- The W10 changes are additive in the schema sense.

The contract still hides three gaps:
1. **The shared events block contradicts itself** across its own examples, and it would change Home's frozen content.
2. **"F&O absent in the US by schema" holds only for two keys.**
3. **Markets' default flows view cannot be served truthfully,** and nothing in the contract says so.

**What I judged**
- **Repository:** `exepex/omenix-dashboard` at 9f36599, cloned read-only to `/tmp`.
- **Claims:** `reviews/claude/response_10_w11_screener_markets_api.md`.
- **Contracts reviewed together:** the frozen `design/mockups/33-screener/notes.md` and `34-markets/notes.md`, with
  `api/` (paths, schemas, examples) and `api/catalog/`.
- **Criteria:** there is **no written W11 story** in trading's `docs/stories/X-cross-repository.md` (W10 is the last
  section). I judged against the orchestrator's assignment, which the claims quote: every element of 33 and 34 maps
  to a block endpoint with a validated Mock example; the catalog gives source, owner story, freshness and "Published
  today?"; F&O is absent in the US by path and schema; contract changes are additions only, without breaking W9's
  Home fixture.

## Checks run by the judge

```
$ python3 tools/api/check_mapping.py      mapping: zero gaps both ways; no endpoint mixes two independent blocks
$ python3 tools/api/check_contract.py     (openapi-spec-validator 0.7.2 in a scratch venv)
  contract: 64 paths (37 block endpoints), 68 block examples, 112 block schemas, 736 catalogued leaf fields, 20 planted breaks
  contract: OpenAPI 3.1 valid; examples valid and current; catalog complete; screen rules hold; every planted break caught
$ git diff --stat 1c026c4 9f36599 -- api/examples/blocks.json web/      (empty: Home's fixture and web/ unchanged)
$ cd web && npm ci --ignore-scripts && npm run typecheck && npm test     # tests 363 # pass 363 # fail 0
$ node tools/check_code_size.mjs          every file within 350 lines (largest tools/api file: 247)
```

### Additivity of the W10 changes (full diff of W10's files read)

- **`Session.major_event_names`:** new and optional, so it is additive.
- **Enums widened:**
  - `BlockFreshness.rule` gains `nse_calendar`;
  - `BlockMetaFields.publisher` gains `nse_ingest`;
  - `Events.kind` gains `filing`.

  These are additive for the schema, but a widened enum in a *response* can break a client that handles a fixed
  list. I checked the only client: Home renders `KIND[e.kind] ?? e.kind`, so an unknown kind shows its raw code
  ("filing") and does not crash. W9's fixture is unchanged.
- **New `x-feeds` and `x-shared` on `/events` and `/session`:** see finding 1, where the real problem is.

### The mapping check reads backticked tokens only

`tools/api/check_mapping.py:32`: `TOKEN = re.compile(r"`([^`]+)`")`. Prose requirements in a notes row are invisible
to it, so "zero gaps both ways" is a token-level claim. I checked the prose of every 33 and 34 Elements row by hand
against the schemas:

| Prose requirement | Served? |
|---|---|
| The period's change, on the main card, broad indices and sectors | yes: `d1`…`y1` as `PeriodChange` |
| "The closes over the period (chart)" and the spark | yes: `closes` |
| The VIX's 3-month middle | yes: 63+ `closes`, median on screen |
| The equal-weighted average change, best and worst | yes |
| **34 row 8: "the period total" of flows** | **no** (finding 3) |
| **34 row 12: "the 12 nearest" with type "economy"** | **no** (finding 1) |

### My own planted breaks, in memory through the builder's own `errors()` validator

| # | Plant | Result |
|---|---|---|
| J1 | A US screener row carrying F&O fields (`fut`, `oi`, `b`, `lot`) | **NOT caught** |
| J2 | A US screener row with delivery % `dl` (India only in 33 row 6: "delivery at least (`dl`, India)") | **NOT caught** |
| J3 | A US row in the `n500` universe | caught |
| J4 | India stock rows in USD | caught |
| J5 | The US screener summary with an F&O count block (`payload.fno`) | **NOT caught** |
| J6 | India's F&O rows served as `market: us` | caught |
| J8 | An event kind `economy` (34 row 12's word) | caught (not in the enum) |

I also tried two plants outside W11's scope; both passed validation:
- **J7:** an RBI event in the US calendar (the events kind list is W10's).
- **J9:** a currency key on World quotes, which carry their own currencies.

### The events block: one endpoint, four examples that cannot all be true

`/markets/{market}/events` takes only `market`. Its `x-shared` says "one calendar: Home's Coming up and the Markets
overview's What is coming? list the same events". Its examples:

| Example | Dates | Kinds |
|---|---|---|
| `getEvents_us` (Home, as of 6 Oct) | 13 Oct – 17 Nov | earnings, **cpi 14 Oct**, **fomc 28 Oct**, jobs_report |
| `getEvents_us_markets` (34, from 13 Oct) | 13 Oct – 11 Dec, 22 events | earnings, ex_dividend only. **No CPI on 14 Oct, no FOMC on 28 Oct** |
| `getEvents_india` (Home) | 7 Oct – 29 Oct | rbi_policy, earnings, **holiday 20 Oct**, fno_expiry, **fomc 29 Oct** |
| `getEvents_india_markets` (34) | 13 Oct – 6 Nov, 24 events | earnings, ex_dividend, fno_expiry. **No 20 Oct holiday, no 29 Oct FOMC** |

## Criteria

| # | Criterion (from the orchestrator's assignment) | Judge's own evidence | Result |
|---|---|---|---|
| 1 | Every element of 33 and 34 maps to a block endpoint with a validated Mock example | Tokens: zero gaps (check run). Prose: all served except 34 row 8's period total and 34 row 12's economy events. The events examples contradict each other. | **PARTLY** |
| 2 | The catalog gives source, owner story, freshness and "Published today?" | Columns present for every endpoint and leaf; `catalog complete`. "No" and "partly" are honest (114 NSE-ingest leaves with no publisher). | MET |
| 3 | F&O is absent in the US by path and schema | Path: MET (every F&O block under `/markets/india/fno/`; J6 caught). Schema: only `universes.fno` and the `u` tag are rejected. J1 and J5 pass, and so does J2 (India-only `dl`). | **PARTLY** |
| 4 | Changes are additions only and do not break W9's Home fixture | Schema-additive; Home's fixture byte-identical; 363/363; Home falls back on unknown kinds. **But** the shared events block now also has to carry 34's lists, which changes what Home's frozen row 6 receives (finding 1). | **PARTLY** |

## Claims vs reality

- **"72 elements mapped, zero gaps":** true for backticked tokens; false for two prose requirements.
- **"20 planted breaks caught":** true, reproduced. All of them change examples. None adds a forbidden *field* to a
  US payload, which is where the schema is open (J1, J2, J5).
- **"363/363 web tests":** true, reproduced; `web/` and Home's fixture are unchanged.
- **The "Published today?" column:** honest. India's 33 and most of 34 have no publisher today (`nse_ingest`,
  "nothing publishes it yet"). The screens cannot go live in India until the owner answers question 1.
- **"No 34 example for `/session`":** true. The new `major_event_names` field has no example value (minor 2).

## The builder's open owner questions: hidden gap or honest question?

| # | Question | Judge |
|---|---|---|
| 1 | Who publishes NSE's daily files? | An **honest open question, not hidden**: the contract names `nse_ingest`, marks every leaf "not published" and the story `NSE1-proposed`. It blocks India's 33 and most of 34 going live. The owner should decide before W12 builds these screens. |
| 2 | Flows history for 1M, 3M and 1Y | A **gap the contract hides** (finding 3). |
| 3 | One "economy" kind, or the specific kinds | Specific kinds are reasonable: Home already shows them by name. The gap is that 34's examples contain no economy event at all (finding 1). |
| 4 | No "major" flag on 34's events | **Not a gap**: `Events.items.major` is already required (W10). 34 only has to read it. |

## Engineering standards

- **Structure:** the generators and checks are split by concern (`examples_screens.py`, `walk.py`, `render_catalog.py`).
- **DRY:** one schema serves both markets, with the publisher per operation; shared records carry `x-shared`
  rather than being served twice.
- **Sizes:** all files under 350 lines.
- **Breaches:** none found.

## Findings

1. **Should fix: the shared `/events` block cannot serve both screens as written.**
   - **Evidence:** the table above. With only a `market` parameter, one request cannot return both Home's list (CPI,
     FOMC, holidays) and 34's list (results and ex-dividend, no economy events). The examples on overlapping dates
     disagree.
   - **Effect on Home:** if the publisher fills 34's list, Home's Coming up starts showing ex-dividend and filing
     rows, which its frozen row 6 does not list. It shows "filing" as a raw code, because Home's label map has no
     such kind.
   - **Expected:**
     - one calendar with every kind, and a `kinds` and `limit` query (or a documented screen rule) per screen;
     - examples generated from one day's calendar, so both screens' views agree;
     - 34's example containing its economy events;
     - a planted break where the two views disagree.
2. **Should fix: "F&O absent in the US by schema" is enforced for two keys only.**
   - **Evidence:** J1, J2 and J5 pass validation. The rows and summary schemas are open: they do not set
     `additionalProperties`.
   - **Expected:** US variants that reject F&O fields (`fut`, `fc`, `oi`, `oc`, `b`, `iv*`, `pcr`, `mv`, `x`, `lot`,
     and any `fno` key) and India-only fields (`dl`), with planted breaks for each kind. This is the same pattern W10
     used for `open_structures` and `at_risk` in the US account.
3. **Should fix: 34's flows "period total" has no truthful source at the default period.**
   - 34 opens on 1M (notes, "Period switch … 1M as the default"), and row 8 asks for the period total.
   - The flows block carries only the days it is given: 5 days in the data, as the builder says. The schema tells
     the screen to add the days up, but says nothing about coverage.
   - So the screen would either label a 5-day sum as "1M" or have to invent its own rule.
   - **Expected:** one of
     - per-period totals published, with `null` when the days do not cover the period;
     - a stated screen rule ("—" unless the days cover the period), with a planted break;
     - an owner decision to show flows only for 1D and 1W.
4. **Minor: W11 has no written story.** It has no criteria, judge steps or status in `docs/stories/`. Every other W
   story (W1 to W10) has one. Expected: a W11 section with its criteria, so the next judge judges against text, not a chat
   message.
5. **Minor: the new `Session.major_event_names` has no example value anywhere,** so nothing validates a non-empty
   value. Expected: one example with a major event (e.g. US CPI).
6. **Minor: the mapping check reads backticked tokens only.** Expected: either the notes put every required field in
   backticks, or the claims say "token-level". Prose requirements then get a listed manual check, as above.
