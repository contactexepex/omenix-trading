# Judge 166: P1 trim in exepex/omenix-dashboard (lane 1: removes tests; judge E)

Date: 15 Oct 2026 (UTC). Dashboard branch `story/p1-trim` at **171e6129ee6230112b67f925a101d35c61007262**, parent
`a696b4d` (dashboard `main`, checked equal). 5 files, +3/-88. Owner approval: typed in the P1 builder's session
(`docs/DESK_DECISIONS.md` "clean-ups approved", "P1 test trim"); the trim is decision 67 of response 113 (simplicity
rule), held back by decision 68 until the owner approved. Read-only clone; nothing pushed to the dashboard.

## Verdict: PASS; 3 notes

| Check | Status | Evidence (mine) |
|---|---|---|
| Removed exactly what was approved | MET | Diff: `tools/api/fno_planted.py` (28 plants) deleted; 4 id-keyed `allOf` rules in `api/schemas/fno-forecast-lab.yaml`; 2 probes in `fno_rules.py` (null family, mislabelled as baseline); `check_fno_screens.py` no longer calls `planted`; README and docstring wording. Matches decision 67: "P1's planted-mutation tool and its id-keyed AI rules (one simpler rule instead)" plus their two probes |
| Real rule kept | MET | `fno-forecast-lab.yaml:70-71`: family hybrid or ai must be `sealed_same_day` or `full_f1`; its probes (`fno_rules.py`, "AI book ... isolated", "declared code with no isolation label") remain; 10 probes run |
| Nothing still needed is weakened today | MET | I ran the deleted file's 28 plants (from `a696b4d`) against the trimmed checker and schema: **28 of 28 still caught**, baseline 0 problems. Every rule they guarded (privacy keys, owner-only, PAPER ONLY, Mock labels, records, mockup drift, hashes, caps, the AI isolation rule) still bites. Strong |
| What is lost | stated | (1) Future-regression proof only: a later edit that silently stops one of `check_fno_screens.py`'s rules is no longer caught by a planted break. Every such edit is lane 1 and judged with its own mutations, and trading's `tests/market_read_models/test_p1_data_catalog.py:250` still checks the pinned examples for strategy-internal names and PAPER ONLY. (2) The schema now accepts an AI book with a null family or a "baseline" kind. Its labels come from trading's fixed wiring (`AI_BOOKS` constant, `fno/forecast_scoring/score_report.py:77`; the forecast-lab publisher is not built yet), not from data, so this needs a code bug, not normal running (reasoning only; owner's simplicity rule) |
| Contract version 2.7.0 | MET | `api/openapi.yaml:4` unchanged. The README's rule covers additions (minor) and majors (owner); a removed constraint is neither, and producers are unaffected |
| Examples unchanged | MET | `git diff a696b4d 171e6129 -- api/examples design api/openapi.yaml`: empty |
| API gates | MET | `check_mapping` zero gaps; `check_contract` OpenAPI 3.1 valid, 66 of 66 planted breaks caught; `render_catalog --check` current; `check_fno_screens` "every rule holds" (5 pages, 17 examples); `render_fno_catalog --check` current |
| Code size | MET | `node tools/check_code_size.mjs`: every file within its limit |
| Web gates (Node 22.22) | MET | `npm ci`, `npm run typecheck` clean, `npm test` 465 of 465 pass, `npm run build` done |
| Duplicates or contradictions | none | No register row besides P1 touches these files |

## Notes

1. **Trading re-pin right after the merge.** `contracts/omenix-dashboard/pin.json:27` pins
   `api/schemas/fno-forecast-lab.yaml` (bd3eb1bf...). The dashboard merge changes that file, so the drift check reads
   red until the one-file re-pin lands; do it in the same sitting.
2. Stale docs: none found. `api/README.md:25`'s remaining "planted breaks caught" belongs to `check_contract.py`,
   which still has its 66.
3. If an AI book's family ever comes from data (for example a book list read from a file), the id-keyed rules should
   return. Today it does not.

**Verdict: PASS for 171e6129ee6230112b67f925a101d35c61007262** (dashboard). Merge, then re-pin trading.

## Addendum 1: trading re-pin to dashboard f617139 (story/p1-trim-repin at 2ebd62aa)

**Verdict: PASS.** Merge it.

| Check | Evidence (mine) | Result |
|---|---|---|
| f617139 is the judged trim | Dashboard `git diff 171e612 f617139` is empty: the merge commit's tree is the tree judged above | MET |
| yaml byte for byte | All 33 files in `pin.json`: the trading copy at 2ebd62aa equals `git show f617139:<file>` byte for byte, and its SHA-256 equals the pinned hash. 0 mismatches | MET |
| Other 32 pins unchanged | Same 33 keys as on main. Only `api/schemas/fno-forecast-lab.yaml` changed its hash. The only other pin.json change is `commit` (a696b4d to f617139); `contract_version` stays 2.7.0 | MET |
| contract-check | `python -m fno market contract-check`: "pinned W11 contract 2.7.0 (commit f617139491cd): same as the dashboard's", exit 0 | MET |
| Gates | pytest 5,861 passed; ruff check and format clean; import check clean | MET |
| Docs | The P-publishing test-plan line and response 102 addendum 7 say the planted breaks were removed (the "28 of 28" line no longer holds). This matches the dashboard diff | MET |

The branch diff is the 4 files named, and nothing else.

Note (no action): the trim removes schema rules but no field, and the version stays 2.7.0. That is consistent with the
compatibility rule, which covers field removals and retypes. The family-keyed isolation rule stays in the yaml.
