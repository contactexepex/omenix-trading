# Judge 40: W11 follow-ups (stored parts, stored tables, the NSE Sunday session)

**Verdict: FAIL.** There is 1 should-fix finding and 2 minor findings.
- **Additive and correct:** the served contract is truly unchanged; my round-1 US plants still bite; the 6 new plants
  are caught; and every field has exactly one publisher.
- **The should-fix:** the split hands the stock tool a field it cannot compute from its own data. That repeats, one
  level down, the problem P6 found.
- **Item 3** (the Sunday session): the root cause is confirmed. It needs a decision on who edits `design/`, and I
  give a recommendation.

**What I judged**
- **Repository:** `exepex/omenix-dashboard` at 6ef9fd1 (merge of bc8c75f).
- **Claims:** `reviews/claude/response_17_w11_followups_stored_parts.md`.
- **Contract:** 2.3.0 → 2.4.0.

## Checks run by the judge

```
$ python3 tools/api/check_contract.py     (openapi-spec-validator 0.7.2)
  contract: 70 paths (43 block endpoints), 81 block examples, 138 block schemas, 873 catalogued leaf fields, 45 planted breaks
  contract: OpenAPI 3.1 valid; examples valid and current; catalog complete; screen rules hold; every planted break caught
$ python3 tools/api/check_mapping.py      zero gaps both ways
$ python3 tools/api/examples.py --check   examples current
$ node tools/check_code_size.mjs          within limits
$ git diff --stat 241242a 6ef9fd1 -- api/examples      (empty: no example changed)
```

### Is the served contract truly unchanged?

I read the full diff of the served files:
- **The US and India row rules** moved from inline objects into `UsStockRows` and `IndiaStockRows`. The properties
  are identical (`u` items `const: ours`, `dl: false`; `required: [dl]`), now behind a `$ref` so the stored tables
  reuse them.
- **The other changes:** the `ours` property gained only an `x-catalog` and a description (catalog metadata, no
  validation change); the operations gained `x-stored`; and the version line changed.
- **My W11 round-2 plants** against the refactored rules are all still caught: J1 F&O fields on a US row, J2 `dl` on
  a US row, J5 `fno` in the US summary, J7, J9 and J10. **Unchanged in behaviour.**

### One publisher per field

- `ScreenerSummaryNsePart` (exepex/trading) holds `as_of` and `universes.{all, n500, fno}`, and is closed.
- `ScreenerSummaryOursPart` (the stock tool) holds `as_of` and `ours`, and is closed.
- `merge_summary` takes `all`, `n500` and `fno` from the first and `ours` from the second. `as_of` must be equal,
  otherwise the route answers 503.
- The merged object equals the served example and validates against the served schema (`check_stored`).
- The builder's plants for ours-in-the-NSE-part and fno-in-the-ours-part are caught.

**Each served leaf has exactly one publisher.**

## Finding (should fix)

1. **The stock tool's part requires a count it has no data for.**
   - `ScreenerSummaryOursPart.ours` is a `UniverseCounts`, and the served India rule (`IndiaScreenerSummaryRule`)
     requires `screens.delivery` for **every** universe, `ours` included (the example has `"delivery": 3`).
   - Delivery % (`dl`) is, per the contract itself, from the "NSE security-wise file". That is an NSE file published
     by exepex/trading (`TR-NSE-proposed`), not something the stock tool records.
   - The same holds for the counts the screener derives from NSE's rows (52-week `high`/`low` from NSE's `h`/`l`,
     `volume` against `va`). The example computes `ours` from 33's **NSE rows** filtered to the 20 companies
     (`examples_screens.py`).
   - So the part assigned to the stock tool can only be produced from exepex/trading's data. Either the stock tool
     must ingest NSE's delivery file, which duplicates a publisher, or its part cannot meet the schema.
   - **Expected:** the field's publisher must own its inputs. The cleanest fix (reasoning only): the stock tool
     publishes only **which companies it follows** (a list it truly owns), and exepex/trading computes `ours` counts
     over its own NSE rows for that list. That gives one publisher per figure, one source per input, and no merge.
     Otherwise, document how the stock tool obtains delivery % and from whom.
   - Also: **"owner decision (a)"** in `blocks-stored.yaml` is recorded only as an **orchestrator** line in
     `conversations/2026-10-13.md`; I find no owner record in `docs/DESK_DECISIONS.md`. It must not be called an owner
     decision unless the owner made it.

## Item 3: the Sunday 1 Feb 2026 session (not fixed; decision needed)

**Root cause confirmed:**
- `design/mockups/33-screener/fetch_nse.py:53`, `34-markets/fetch_nse_indices.py:40` and
  `32-option-chain/fetch_nse.py:32` all walk `weekday() < 5`.
- The A1 calendar lists `2026-02-01,special,"Sun Union Budget live session …" (NSE/FAOP/72352)`.
- So every 1Y series in 33 and 34 lacks that session.

I did not re-check the builder's Nifty Pharma figure.

**My recommendation (reasoning only):** treat it as a **data correction, not a contract change**. That is the same
precedent as judge 19's lot-size correction (75 to 65), which changed values, not the contract.
- The fetch scripts read the A1 session calendar, the two `data.json` files are rebuilt, and `changes.md` records
  every changed number with the reason.
- The owner is informed but need not re-sign, because the fields and the screen stay the same.
- Who edits `design/` is for the orchestrator to assign.

## Findings (minor)

2. **The per-leaf catalog shows `UniverseCounts`' leaves with the first universe's publisher** (exepex/trading), so
   the stock tool's ownership of `ours` leaves appears only on the property, the endpoint row and the Stored parts
   table (the builder states this). If finding 1 is fixed the cleanest way, this goes away.
3. **Stored tables are built in memory and not kept as example files** (2,924 India rows, about 640 KB). That is
   reasonable. A backend testing its own table must then use `check_stored.py`'s builder, so the publishing stories
   should name that tool as their acceptance check.
