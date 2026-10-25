# Judge 595: BG1-u story text "no monthly AI cap", story/bg1u-no-cap at 2befcafc1 (judge J, round 1 of 2)

**PASS** (text), lane 1. Diff: only `docs/stories/BG-budget.md` (+99), on main a38dad1b3. Doc-reading tests with
`FNO_SLACK_BOT_TOKEN` set: 853 passed, 15 xfailed.

## Criteria
| Item | Verdict | My evidence |
|---|---|---|
| Owner's words | MET | DESK_DECISIONS line 339 quoted exactly; it replaces the 15 Oct cap |
| Every reader of the level and the stop | MET | grep of main and G11's branch for BUDGET_STOP/ALERT/UNKNOWN, stop_ai_roles, cap_minutes, pct_of_cap, cap.level, signal_path. Readers: `budget/cap.py`, `report.py:93`, `signal.py:53`, `learning/writer.py:49`, G11's `budget_stop.py:49-50`. `role_value` reads only the allocation; `ai/usage_*` only the ledger |
| G11's stop under `no_cap` | MET | `reading.cap.level == BUDGET_STOP and books >= cap` short-circuits, so `books >= None` is never evaluated |
| Signal file | MET | no workflow writes `accounting/budget/` (grep), and the folder does not exist; the writer treats a missing file as no stop |
| Dashboard contract | MET | `fno-budget.yaml` is `x-fill: not_built`, and nothing in fno or tools publishes it (grep): nothing breaks. Its `level` enum and required cap numbers need the dashboard owner's change when it is built (handed off, gap list) |
| Nothing lost | MET | the `share` path, its settings and checks, the stop fields and `AI_ROLE_STOP_ORDER` are kept (C6, tested at 80% and 100%) |
| Facts | MET | `budget meter --month 2026-10` on main: 34.46 minutes, "level unknown" (C2's G case) |
| Criteria testable, G/B/Bd/E and plants | MET | C1-C6 each have cases and a plant |

## Findings (minor only)
**m1 The missing-key refusal must stay safe for its two callers.**
- `build_month_meter` is called by G11's v4 fire (`MeterBudgetStop`) and by role_value's weekly cost
  (`role_value/wiring.py:65`).
- G11 fails open only on ValueError, OSError and KeyError (`budget_stop.py:44`). Any other refusal type would crash the
  fire, and role_value would crash on any refusal.
- The owner never edits the config, so the risk is only a code change landing without the key.
- Fix in C1: `budget.cap: none` lands in the same commit as the code, and the refusal is a ValueError, with a test.

**m2** `fno/ai/usage_gaps.py:3` says a not-captured run makes "its level shows unknown". Under `no_cap` that is
false. It is a G11/F8c docstring; name it in the gap list for its owner.

## Plants
0 (text round). C1-C6's plants are noted for the code round.

## Notes
- Under `no_cap`, G11's C8 owner choices ("forecasters last", fail open) become moot but stay in its code. A later
  `share` decision restores them with no code change.
- The BG1 one-line note above BG1-w ("criteria 2, 3, 4 and 7's levels hold only under `cap: share`") is accurate.
