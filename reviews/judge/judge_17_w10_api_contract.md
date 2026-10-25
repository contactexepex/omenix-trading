# Judge 17: story W10, API contract and data catalog for the frame and Home

**Verdict: PASS.** No blocking or should-fix findings; 4 minor findings.

The owner's intent holds: the frame and Home load from many small, independent endpoints instead of one bulky call.
The largest payload has 36 leaf fields. Every pair of separately shown blocks comes from separate endpoints, except
where one record legitimately appears in two places. Those cases are listed and measured below.

**What I judged**
- **Repository and commit:** `exepex/omenix-dashboard` at 7aa81a3, cloned read-only to `/tmp`.
- **Story:** `docs/stories/X-cross-repository.md` W10, in trading.
- **Builder's claims:** `reviews/claude/response_4_w10_api_contract.md` (in omenix-dashboard).
- **Read together:** the signed-off mockups (`design/mockups/30-shell` and `31-dashboard`: `notes.md`, `data.json`,
  the 1280 px Home screenshot), the contract (`api/paths/blocks-*.yaml`, `api/schemas/blocks-*.yaml`,
  `api/examples/blocks.json`), the catalog (`api/catalog/`) and the checks in `tools/api/`.
- **Where this verdict lives:** in trading's `reviews/judge/`, as agreed with the orchestrator.

## Checks run by the judge

These ran in a fresh virtual environment with the pinned `tools/api/requirements.txt`:

```
$ python tools/api/check_mapping.py
elements: 41 (35 need data, 6 static with a reason); field keys: 181; endpoints: 23; endpoint fields: 569 (415 leaves)
elements without an endpoint field: 0; endpoint fields without an element: 0
endpoints feeding more than one screen block (the same record, with x-shared): 11 of 23
mapping: zero gaps both ways; no endpoint mixes two independent blocks                       exit 0
$ python tools/api/check_contract.py
contract: 50 paths (23 block endpoints), 46 block examples, 74 block schemas, 415 catalogued leaf fields, 13 planted breaks
contract: OpenAPI 3.1 valid; examples valid and current; catalog complete; screen rules hold; every planted break caught   exit 0
$ python tools/api/examples.py --check        examples: api/examples/blocks.json matches the mockups' data
$ python tools/api/render_catalog.py --check  catalog: api/catalog/catalog.md is current
$ node tools/check_code_size.mjs              code size: every file within 350 lines or its listed size
$ cd web && npm ci --ignore-scripts && npm run typecheck && npm test && npm run build
  tsc clean; tests 303 pass, 0 fail; build ok      (web/ and design/ unchanged since the sign-off commits)
```

### My own planted breaks (in a throwaway copy)

| # | Break | Result |
|---|---|---|
| 1 | A Coming-up field placed inside Top news' items | caught: "x-feeds ['h31.top-news'] != served [...coming-up...]" and "state why one record serves them (x-shared)" |
| 2 | A second top-level part in Top news feeding Coming-up | caught: "payload parts events_too ['h31.coming-up'] and news ['h31.top-news'] feed independent blocks" |
| 3 | `as_of` stripped from the US index levels example | caught: "'as_of' is a required property" (×3), plus "blocks.json is not what the mockups' data gives" |
| 4 | An extra margin field in the US accounts example | caught (examples no longer equal the mockups' data) |

## Independence measured against the screen

For each endpoint I counted the leaf fields per screen block it feeds, from the contract's own `x-element` tags. 12 of
the 23 endpoints feed exactly one block. The other 11 carry `x-shared`, which means one record is shown in more than
one place:

| Endpoint | Blocks fed (leaves used / leaves only for that block) | Judgement |
|---|---|---|
| `/session` | market-status chip 8/0, Home band 8/0 | Same 8 facts in both. Correct. |
| `/indices` | index strip 11/0, Home band 11/0 | Same facts. Correct. |
| `/attention` | Needs you 7/0, glance 7/0 | Same list; the glance shows its count. Correct. |
| `/positions` | 5 blocks, each 12/0 | One small record (12 leaves). Correct. |
| `/instruments/{id}`, `/fno/contracts/{code}` | hover 14 or 16 / 0, order window same | One instrument record. Correct. |
| `/fno/books` | Who trades F&O lines 13/0, order window 13/0 | Same record. Correct. |
| `/approaches` | vocabulary 15/12, picks panel 3/0 | The panel reads 3 labels from a config list of 15. Small. |
| `/picks` (stocks) | picks panel 36/11, Home glance (top pick) 25/0 | The glance gets 11 leaves it does not show (minor 1). |
| `/fno/picks` | picks panel 28/15, order window 13/0 | The order window opens from a panel row it already has. |
| `/accounts` | Who trades 2/0, glance 3/0, owner defaults 18/0, order window 19/0 | Home's Who-trades and glance read 2-3 of 21 leaves (minor 1). |

The Home screenshot (1280 px) shows these separately displayed blocks: market band, Who trades, Open paper trades,
Needs you, Coming up and Top news. Each comes from its own endpoint or endpoints:
- **Market band:** `/session`, `/indices` and `/tracked-moves`.
- **Who trades:** `/groups`, `/accounts` and `/fno/books`.
- **Open paper trades:** `/positions` and `/strategy-trades`.
- **Needs you:** `/attention`.
- **Coming up:** `/events`.
- **Top news:** `/top-news`.

No endpoint carries two different sections' data. The over-fetch where a record is shared stays within one small
record.

## Ten random screen elements, traced

The elements were picked at random from `elements.yaml` (seed 20261013). For each one I checked the token in
`notes.md`, the endpoint field and the catalog entry.

| # | Screen element (notes.md) | Endpoint field | Publisher · source · story · status |
|---|---|---|---|
| 1 | Home · Coming up · `major` | `getEvents payload.events[].major` | stock · calendar_event · K4-proposed · planned |
| 2 | Home · Market band · `session.date` | `getSession payload.session_date` | stock · rm.status session · K4-proposed · published |
| 3 | Frame · picks panel "Not proven yet · N trades to go" · `go_live.trades_needed` | `getPicks payload.go_live.trades_needed` | stock · rm.home go_live · published (screen: "294 trades to go") |
| 4 | Home · Needs you · `icon` | `getAttention payload.attention[].icon` | dashboard rules · W9 · planned |
| 5 | Frame · Order window · Account · `open_structures` | `getAccounts payload.accounts.manual.open_structures` | dashboard Manual account · MA1-proposed · planned (India only) |
| 6 | Home · Who trades · `open_profit` | `getAccounts payload.accounts.manual.open_profit` | dashboard · MA1-proposed · planned (screen: You +₹1,800.00) |
| 7 | Frame · Bell · `title` | `getNotifications payload.notifications[].title` | dashboard alert rules · W8 · planned |
| 8 | Home · glance · `avg_price` | `getPositions payload.own[].avg` | stock · rm.portfolio · published (the notes' `avg_price`/`avg` slip is mapped to one field, as the builder reports) |
| 9 | Home · Top news · `title` | `getTopNews payload.news[].title` | stock · rm.news · published |
| 10 | Home · Top news · `news[]` | `getTopNews payload.news` | stock · rm.news · published |

All 10 resolve to exactly one endpoint field with a full catalog entry. Each token appears in the `notes.md` named.

## Criteria

| # | Criterion | Judge's evidence | Result |
|---|---|---|---|
| 1 | Every element maps to exactly one endpoint field; zero gaps both ways | `check_mapping.py` exit 0; planted break 1 caught; 10 traces | MET |
| 2 | Independent blocks have independent endpoints; each endpoint states the blocks it feeds | Table above; `x-feeds` checked equal to served; breaks 1-2 caught | MET |
| 3 | Bundle validates; every schema has an example from the mockups' data | `check_contract.py`; `examples.py --check`; break 3 caught | MET |
| 4 | Catalog: publisher, source, unit, freshness, story for every field; planned fields marked with their story | `render_catalog.py --check`; 415 leaves (113 published, 302 planned); 10 traces each complete | MET |
| 5 | F&O absent for the US; no cross-account or cross-currency sums except group totals; as-of on every price | `check_contract.py` screen rules plus 13 planted breaks; my breaks 3-4 caught | MET |
| 6 | Repository checks pass | code size, typecheck, 303 tests and build all pass (my run) | MET |

## Claims vs reality

- **"23 endpoints, 415 leaf fields, 0 mapping gaps":** true, reproduced.
- **"Every planted break caught" (13):** true. My 4 additional breaks were caught too.
- **"Nothing in design/ or web/ was changed":** consistent. `git diff` of `design` and `web` since the sign-off
  commits is empty.
- **The 4 contradictions found in the frozen `notes.md`:** stated honestly. The orchestrator's decisions (b) "F&O
  limits India only" and (c) "Hybrid in both markets" match what the contract already does.

## Engineering standards

- One schema file per area, shared envelope types and a generated catalog; the checks are split by criterion.
- The largest code file is 230 lines and the largest YAML 287.
- No breach found.

## Findings (all minor)

1. **`x-shared` is the only guard against bundling, and it is a human statement.** A union of two blocks' fields
   passes once someone writes `x-shared`. Today's over-fetch is small: the Home glance gets 11 unused picks-panel
   leaves, and Who trades reads 2 of `/accounts`' 21 leaves. Expected: `check_mapping.py` reports, for each `x-shared`
   endpoint, the share of leaves each block uses, and flags any block using less than half. The owner can then see
   bundling creep.
2. **302 of 415 leaves are `planned`.** They depend on K4, MA1 and the P1 extension, which the orchestrator has now
   accepted into the plan. Expected: the stories carry the catalog's field lists as their acceptance input.
3. **Strategy ids in payloads carry model family names** (for example `ai.combined.opus.v1`, flagged by the builder).
   They are never shown on screen. Expected: an owner decision, outside W10.
4. **The units change from 2.0 to 2.1:** block changes are percentage points, while 2.0 pages use fractions. This is
   stated in `openapi.yaml`. Expected: W8 and W9 must not mix the two; a test in the web app that reads both would
   catch it.
