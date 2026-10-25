# Judge 430: G6 piece 1b, the rest of the v4 protocol text (story/g6-protocol-rest at 8a539705)

Judge B, 22 Oct 2026 (IST). Lane 1 (a rule document). Builder: R2/G7 (session_0185gR5DmoDh2zBAvgRU4CEB).
- Plan: response 287, and the open items from judge 409.
- Unpaused by the owner: DESK_DECISIONS 2f1e3b63, 21 Oct, "v4 freeze and switch-on".
- One commit on main 1bef2f33.
- Number claimed with `tools/claim_number.py`.
- Coordination: G10's edits (judge 411.1 and 411.2) are untouched. The register row is updated, and there is no
  second builder on `PROTOCOL_v4.md`.

## Verdict: PASS (notes only)

## Criteria

| Claim | Result | Evidence |
|---|---|---|
| 1. Section 4: misses from a registered slot's `effective_start` | MET | see "Section 4" below |
| 2. Section 5.3: item E's share cut | MET | see "Section 5.3" below |
| 3. Section 11 E: "Decided: option 2" | MET | one line pointing to 5.3; the options text is kept |
| 4. Section 3.1: intraday HAR over usable sessions | MET | `forecast_v4_rules/baselines.py`, the `Har` docstring: "`rv` holds only usable sessions (void ones dropped by the caller)" |
| 5. Section 8: the back-fills named | MET | every named folder exists on the branch: `base_rate`, `trailing`, `ewma_094`, `har_daily`, `v6_ewma_t4`, `v2_close_blend`, `v3_close_blend`, `v7_vix_vs_mean20`, `weather`, `weather_vix_v1`, `weather_checklist_v0`, and `v4_scores`. No V1 folder exists, as claimed |
| 6. Line length | MET | no added line is over 120 characters; the old 135-character line in section 4 is rewrapped |
| Test | MET, note 1 | `test_the_freeze_plan_rules_are_written_as_the_code_runs_them` pins the wording |

### Section 4
- "A session **after** the freeze and no later than the slot's first eligible session": this is judge 409 should-fix
  1.
- It matches `scoring._miss_start` = `max(effective_start, freeze + 1 day)` and `SlotFile`'s refusal of a start after
  the first eligible session.
- The first eligible session is described as `wiring._first_eligible` computes it: the first live day after the
  freeze with a primary-baseline value.
- An unregistered slot gets p = 1: `look.run_look` defaults every family member to `NOT_JUDGED`, and
  `member_comparisons` covers registered slots only.
- Before the freeze, misses count from the first forecast (`_miss_start` returns None).
- Owner row: 16 Oct, "from the declared start".

### Section 5.3
- "More than 10% of its scored outcomes, for every member" is `confirmatory.crash_dominated`
  (`event_days > CRASH_SHARE * n` with `CRASH_SHARE = 0.10`), applied in `look.member_result` with n equal to the
  scored differences.
- 0.1 x 125 = 12.5, so at most 12 days; 13 days needs n >= 130 (checked).

## Planted mutations

| Plant | Result |
|---|---|
| text "after" -> "on or after the freeze" | caught by the new test |
| code `CRASH_SHARE` -> 0.15 | 5 failed in `tests/forecast_v4` and `tests/forecast_scoring_v4` |
| code `_miss_start` -> the freeze day itself | 1 failed |
| text "10%" -> "15%" | survived (note 1) |
| text "n = 130" -> "n = 125" | survived (note 1) |

The code side cannot drift without a test failing. The text numbers can, but a text-only edit is visible to the judge,
and `PROTOCOL_v4.md` is byte-checked from the freeze on.

## Notes (one line each)

1. The new test pins the share-cut wording but not its numbers. Asserting `f"more than {CRASH_SHARE:.0%}"` and n = 130
   against `CRASH_SHARE` would tie them, the same way 411.1 tied the clock.
2. The text requires `effective_start` to be after the freeze. `SlotFile` does not refuse an earlier date; the code
   clamps it to the day after the freeze, which is the same result. Piece 4's slot rows are checked by hand.

## Gates (run by me on 8a539705)

| Gate | Result |
|---|---|
| `pytest -q -n auto` | 8,942 passed, 17 xfailed, **no failures** |
| `ruff check fno tests tools` | clean |
| `ruff format --check` | 1,658 files formatted |
| `check_imports` | clean |

Main's two known red tests are fixed on this base.

## Still for piece 4
- `FREEZE_v4.md`, the slot rows, the ledger row and the "DRAFT" line.
- My conditions carried from judges 409 and 414: G11's files go on the list if G11 is unparked; `fno/v4_pack/` joins
  it when V2-V5's implied baselines come under their own record.
