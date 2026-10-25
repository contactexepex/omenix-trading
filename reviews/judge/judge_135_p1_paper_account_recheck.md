# Judge 135: P1 re-check after C5, the Mock paper accounts at Rs 20 lakh: dashboard `story/p1-data-catalog` ff1ec22f79c40514554ed9155901f15e68ae3ebb and trading `story/p1-data-catalog` e2e3d780bf558f96d3e09bc2b6ec313ee4e6450b (judge A)

**Number note.** `judge_102` is judge B's file, so this re-check of the change since its addendum 4 uses 135, the next
free number.

## The change

**Dashboard, 13e76b4..ff1ec22: one commit, 3 files.**
- `api/examples/fno-screens.json`: each paper account's `opening_value` 500,000 becomes 2,000,000. `value` and `cash`
  move by exactly +1,500,000 each, so every account keeps its profit or loss (e.g. 503,054 → 2,003,054; 492,892 →
  1,992,892). The empty example's description says "Rs 20 lakh".
- `api/schemas/fno-paper-trades.yaml`: only the `opening_value` description text changes; type, minimum and `x-` keys
  are unchanged.
- `api/catalog/fno-screens.md`: regenerated with the same two texts.
- The schema shape is unchanged, as claimed.

**Trading, e2e3d78.**
- `pin.json` moves to ff1ec22, with the two changed files' new hashes.
- `test_p1_data_catalog.py` reads `fno.composition.paper_account_rs()` instead of the removed `STARTING_CASH_RS`.
- The rest of the merge is main (C5).

## Checks, run myself

**The figure.** `config.yaml` has `risk.profiles.books.paper_account_rs: 2000000` (line 52), and the Manual account's
`500000` (line 79) is not touched. The examples match the books' figure.

**Pin integrity.** All **33 pinned files**:
- their SHA-256 at dashboard ff1ec22 equals `pin.json` (0 mismatches);
- the trading copies under `contracts/omenix-dashboard/` are byte-identical to the dashboard's (0 mismatches).

**Dashboard gates at ff1ec22:**
- `check_contract.py`: OpenAPI 3.1 valid, examples valid and current, the catalog complete, 66 planted breaks caught;
- `check_fno_screens.py`: 5 pages, 17 Mock examples, 28 of 28 planted breaks caught;
- `check_mapping.py`: zero gaps;
- `render_fno_catalog.py --check`: current;
- `node tools/check_code_size.mjs`: within limits;
- `npm ci --ignore-scripts && npm run typecheck`: ok;
- `npm test`: **465 of 465 pass**.

I did not run `npm run build`. The change is to JSON, YAML and Markdown only, and no web code changed.

**Trading gates at e2e3d78:**
- `env -u FNO_SLACK_BOT_TOKEN python -m pytest -q`: **5144 passed**;
- `tests/market_read_models`: 181 passed;
- `ruff check fno tests tools`, `ruff format --check fno tests tools` and `python tools/check_imports.py`: clean.

## Note (one line; it changes no signal, trade or stop)

Outside this change, dashboard `main` still says the three F&O books are "Rs 5 lakh each" in four places:
- `api/catalog/catalog.md:25`;
- `api/paths/blocks-fno.yaml:120`;
- `api/schemas/blocks-home.yaml:68`;
- `api/examples/blocks.json`'s books `value: 500000.0`.

These are Home's blocks, not P1's, and the Manual account's Rs 5 lakh is right. A follow-up on Home's mock should
align the books with C5's Rs 20 lakh.

### Verdict: PASS for dashboard ff1ec22f79c40514554ed9155901f15e68ae3ebb and trading e2e3d780bf558f96d3e09bc2b6ec313ee4e6450b

The change is exactly as claimed: values only, every profit or loss kept, and the schema shape unchanged. The pin is
consistent, and every gate in both repositories passes.
