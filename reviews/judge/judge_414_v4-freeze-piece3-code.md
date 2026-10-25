# Judge 414: v4 freeze piece 3, the freeze code (story/g6-freeze-code at 76174a7c)

Judge B, 21 Oct 2026. Lane 1. Builder: R2/G7 (session_0185gR5DmoDh2zBAvgRU4CEB), owner of the G6 freeze. Plan: response
287, step 3. Number claimed with `tools/claim_number.py`.

Scope and coordination:
- The orchestrator asked me on 21 Oct to judge this as work submitted before the scope freeze.
- Piece 1 (judge 409) is withdrawn. Piece 3 is cherry-picked onto main 35acffa7 with nothing of piece 1 under it.
- It touches only G8's wiring, two new G8 modules, a tool, tests and M1's back-fill files. There is no overlap with
  another open row.

## Verdict: PASS (notes only)

## Criteria

| Claim | Result | Evidence |
|---|---|---|
| 1. `SlotFile` reads `v4_slots.csv` | MET | see "SlotFile" below |
| 2. The freeze check and the table tool | MET | see "Freeze check" below |
| 3. No implied volatility on v4's live path (ChatGPT 119 point 1) | MET, strong | see "No implied volatility" below |
| 4. M1's back-fill regenerated, values unchanged, plus a gate | MET, with note 4 | see "M1's back-fill" below |
| Not in this piece: G11's files, `FREEZE_v4.md`, the slot rows, B4 | as stated | G11 parked: AI slots unregistered, so `not_started` and p = 1 |

### SlotFile (`fno/forecast_scoring/v4/slot_file.py`)
- It replaces `NoRegistrations` in `wiring._registry`, so scoring and the reconciliation use one registry.
- It refuses, each with its own test:
  - a question outside `FAMILY_QUESTIONS` (V3 is reported only);
  - a slot outside `V4_SLOTS`;
  - a second row for a slot;
  - `registered_on` after `effective_start`;
  - `effective_start` after the first eligible session.
- With no file it returns none. On this repository, before the freeze, it registers nothing.

### Freeze check (`freeze_check.py`, `tools/v4_freeze_table.py`)
- The list matches response 287:
  - the protocol and calibration;
  - every file of `fno/forecast_v4`;
  - `tools/v4_*.py` and their `research/forecasts/v4_*` tables;
  - the golden fixture;
  - every file of G7 and G8;
  - G4's `scores.py`;
  - A16's `realised_vol`, `session_rv`, `status` and `slots`;
  - M1's `METHOD_FILES`, including `weather/constants.py`.
- Recorded, not checked: the six shared files.
- The three packages have no subfolders, so the non-recursive globs are complete. No scheduled job writes a top-level
  `research/forecasts/v4_*` file, because only the calibration tools do. So after the freeze, "added after the freeze"
  cannot go red on its own.
- `table()` and `problems()` agree, and they find a changed, a removed and an added file.
- A record whose rows fail to parse makes every file "added", which is loud, never silent.

### No implied volatility (claim 3)
- The static proof: G7 (`fno/forecast_v4_rules`), M1 (`fno/weather`), G8 (`fno/forecast_scoring/v4`) and
  `fno/forecast_v4` import nothing about implied volatility (`implied_vol`, `Black76`, `iv30`, `live_features`,
  `interpolate_30d` or `v4_pack`). My grep finds only a mention in a docstring.
- The run test: one real day (15 Oct) of all three, with the IV methods raising, gives equal outputs, and a second test
  shows the patch fires.

### M1's back-fill (claim 4)
I compared every changed file with the merge base:
- **CSVs:** all 9,636 rows are equal except `method_sha256` and the new empty `pack_sha256` column, plus 3 new days
  (15, 16 and 19 Oct) in each of the four CSVs.
- **Day files:** all 2,409 are equal except `method_sha256` and one new key, `v0_status` (note 4). There are 3 new day
  files.
- **Gate:** `test_method_hash_gate.py` holds every M1 record to the tree's hash, as G7's gate does.

### Gates
My gates ran on 76174a7c merged with main ebef0db1, which includes main's G10 part 2b A2 drop:

| Gate | Result |
|---|---|
| `pytest -q -n auto` | 8,156 passed, 18 xfailed, 2 failed |
| `ruff check fno tests tools` | clean |
| `ruff format --check` | 1,472 files formatted |
| `check_imports` | clean |

The 2 failures are main's known red tests: `test_g7_series` (V1 rows) and `test_forecast_history_page`. The main
steward owns them (story/main-green). Since 35acffa7, main has changed none of M1's or G7's method files, so the hash
gates hold after the merge.

## Planted mutations (14)

`test_g7_series` was deselected, because it is red on main.

| Plant | Result |
|---|---|
| no second-row check | caught |
| no `registered_on` check | caught |
| no late-start check | caught |
| late start `>` -> `>=` | caught |
| no family check | caught |
| M1's files dropped from the list | caught |
| no "added after the freeze" | caught |
| `session_rv.py` dropped from the list | caught |
| `status.py` dropped from the list | survived (note 1) |
| G4's `scores.py` dropped from the list | survived (note 1) |
| `PROTOCOL_v4_calibration.md` dropped from the list | survived (note 1) |
| `_first_eligible`: `d > after` -> `d >= after` | survived (note 2) |
| `_first_eligible`: live filter removed | survived (note 2) |
| `_registry` back to `NoRegistrations` | survived (note 3) |

None of the six survivors is a fault in the code. I read each line and it is right. None has a normal-running path
before piece 4:
- The list and `wiring.py` are themselves byte-checked from the freeze on.
- Piece 4's judge checks the record's table file by file.

## Notes (one line each; the last two are for piece 4)

1. The list test pins 10 of its paths. Comparing `byte_checked()` with response 287's list in full would catch a
   dropped line before the freeze.
2. `_first_eligible` after the freeze (strictly after `Frozen on`, live rows only) has no test. One with fake frozen
   records would pin the rule that hides no misses.
3. No test shows the wiring reads `SlotFile`. Before the freeze, both return none.
4. The day files also gained `v0_status`, which main's a7a91d65 (response 245) added to M1's records. The claim
   ("differ only in method_sha256 and the new empty pack_sha256 column") leaves it out. The values are unchanged.
5. `SlotFile` does not check the `forecaster` name against decision 70 or the slot. Piece 4's rows are judged by hand.
6. Carried to piece 4:
   - the protocol's "on or after the freeze" wording (judge 409 should-fix 1; the code clamps to the day after);
   - `fno/ai/v4_rows.py` and the other G11 files go on the list if G11 is unparked before the freeze;
   - `fno/v4_pack/` is not byte-checked, which is right while no member reads the pack (V6 and V7 read closes); it
     must join the list when V2-V5's implied baselines come under their own record.
