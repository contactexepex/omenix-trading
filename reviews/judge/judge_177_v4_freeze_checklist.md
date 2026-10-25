# Judge 177: protocol v4 freeze checklist (plan only): `freeze/v4-checklist` c84d3554 (lane 1)

Judge B. Plan: `reviews/claude/response_157_v4-freeze-checklist.md` (A16/G8 builder, who now owns the freeze), merged
with `main` 55726493. The commit adds only the response and its README row: no protocol text, code or record changes.
I checked it against PROTOCOL_v4.md sections 4, 6, 10 and 11, G7, G8, M1 and A16's code at c84d3554, and
`docs/WORK_REGISTER.md`.

## (1) Does the byte-check list miss a file that decides a v4 baseline, outcome or score?
I listed every `fno` import of the planned byte-checked set myself: `fno/forecast_v4/`, `fno/forecast_v4_rules/`,
`fno/forecast_scoring/v4/`, `tools/v4_*.py` and M1's six `METHOD_FILES`. Outside the set they reach `fno.constants`,
`fno.models`, `fno.config`, `fno.storage.*` (plumbing), `fno.desk.settlement` and `fno.research_data.calendar`
(recorded, as section 10 says), `fno.global_cues.*` (the US flag, free by the owner), `fno.weather.model` (an abstract
interface only), `fno.weather.drivers` and `fno.weather.records` (the card's drivers, not the probability), and two
real gaps:

**Should-fix 1: V1's outcome and its HAR baseline depend on A16's RV method, which is neither byte-checked nor pinned.**
- V1's outcome is intraday `RV_s`, and its trailing and HAR baselines are built from the same rows. The figure and its
  void status come from A16's code: `fno/intraday/realised_vol.py` (the arithmetic), `session_rv.py`, `status.py`
  (`index_check`, the void rule) and `slots.py`.
- `fno/intraday/rv_table.py` stores the rows written once, with a `method` column. Checked:
  `forecast_v4_rules/series.live_intraday_rv` reads `status` and `rv_session` and ignores `method`.
- **The normal-running path:** A16's design 5.2 and protocol 1.x plan for it. Above 5% void sessions in a quarter, "a
  new version is proposed", and `realised_vol.py` says "a new sampling rule is a new class with its own method name".
  After the freeze, such a version's rows would feed V1's outcomes and baselines silently, against the protocol's
  "series never pooled".
- **Fix (either is enough):**
  - (a) byte-check `fno/intraday/realised_vol.py`, `session_rv.py`, `status.py` and `slots.py`; or
  - (b) record A16's current `method` value in FREEZE_v4 and make V1 count only rows of that method, as a G7 change
    before the freeze, with a test.

  (b) leaves A16 free to add versions. `rv_table.py` stays recorded as planned.

**Should-fix 2: `fno/forecast_scoring/scores.py` (G4) decides v4's log score and calibration table but is in no
list.**
- `fno/forecast_scoring/v4/scores.py` imports `log_score`, `calibration_table` and `CalibrationBin` from it: the
  clipping 0.01-0.99 and the 10 bins.
- No FREEZE_v1 to v3 lists it (checked), so nothing stops an edit for another protocol from changing v4's reported
  scores.
- Section 10 asks for "every G7 and G8 file that decides a v4 ... score". The verdicts use `forecast_v4/loss.py`
  (byte-checked), so this affects reported scores only.
- Fix: add it to the byte-checked list (one line).

Not gaps: the committed data (NIFTY closes, VIX history, `rv/` rows) is data, not code, and the rows are written once.
M1's `METHOD_FILES` already includes G7's `series.py` and `baselines.py` and v4's `terms.py` and `sessions.py`, all
byte-checked anyway.

## (2) Does any protocol text edit change a rule rather than state the code?
| Edit | Code checked | Result |
|---|---|---|
| 11 E decided, option 2 | `confirmatory.crash_dominated`: `event_days > CRASH_SHARE * n` (strict). At n = 125, 12 days pass and 13 fail; 13 passes first at n = 130 | states the code |
| V6b scored, no edit | only V7 is in `DESCRIPTIVE_ONLY` | correct |
| HAR (intraday) skips void sessions | `forecast_v4_rules/capture.py:79-86`: `usable` drops `value is None` before `Har(...)`; `Har`'s docstring says the same | states the code |
| Freeze start, "not started" | `scoring._miss_start` (judge 156) | states the code |
| Back-fills disclosed | `f891d9b` "G7 back-fill ... V6 (2017-01-03 to 2026-10-14)" and `6b7eaba` "M1 weather back-fill, labelled backfill_exploratory", both exist | correct |
| Long line | cosmetic | none |

The G10 edits are judged with G10's build, not here.

## Coordination (owner's rule of 15 Oct)
**Should-fix 3: `docs/WORK_REGISTER.md` still gives the freeze to the G6 session.**
- Row 27, "G6 freeze", names `01MgTu3L1T3y6R18ATTwbFub` and "waits for the G6 session". The plan says the A16/G8
  builder owns it now (orchestrator, 15 Oct).
- CLAUDE.md: "add or update your own row in your first commit". Update the row's owner and status in this branch.
- G10's row is the same builder's, and the plan orders G10 first, so there is no overlap.

## Notes (one line each, not blocking)
1. **Later registrations.** V1's `rules` ("once V1 starts") and the AI slots (G11) are registered after the freeze.
   Protocol section 6 allows a registration made before a slot's first counted forecast. Say that each such
   registration is an appended ledger row, and that G8's adapter reads every row, not only the freeze's.
2. **Golden fixture.** The plan names `tests/fixtures/forecast_v4/v4_golden.json`; keep its hash in the freeze test,
   as v2 does.
3. **The owner's confirmations.** Each quote needs its source row and date in `DESK_DECISIONS.md`, as judge 149 M4
   asked for both 10% caps.

## Gates
Docs only; no gate applies beyond `git diff --check`, which is clean. Nothing here is frozen, so the freeze commit
gets its own lane-1 verdict (and rule 9).

**Verdict: FAIL for c84d3554 on should-fixes 1-3.** Each is a plan edit of one or two lines, plus, if option (b) is
chosen, one G7 change before the freeze. A re-check needs only the revised response 157 and the register row.

## Addendum 1 (15 Oct 2026): revision 1 at 3e3fd302

The revision changes `response_157_v4-freeze-checklist.md` (adding a "Revision 1" section) and the
`docs/WORK_REGISTER.md` row. The rest of the branch diff is the `main` merge.

| Finding | Status | Evidence |
|---|---|---|
| Should-fix 1: V1's RV method | MET | Both options are taken. (b): the record pins `rv-quote-15m-v1` (checked: `fno/intraday/realised_vol.py:49`), and G7's `series.live_intraday_rv` will read only that method's rows, with a test, before the freeze. (a): `realised_vol.py`, `session_rv.py`, `status.py` and `slots.py` are byte-checked. The builder's reason for taking both is right (reasoning): (b) stops a new class, and (a) stops an edit in place |
| Should-fix 2: `fno/forecast_scoring/scores.py` | MET | Added to the byte-checked list, with what it decides |
| Should-fix 3: register row | MET | "G6 freeze" names the A16/G8 builder, its branch, the freeze test and the status |
| Notes 1-3 | MET | Later registrations are appended ledger rows that G8 reads in full. The golden fixture's hash is in the freeze test. Each owner quote carries its `DESK_DECISIONS.md` line and the row's text. I checked lines 121, 123, 157, 177, 181, 182, 184, 185, 186 and 194 on 3e3fd302: each is the row named |

**Verdict: PASS for 3e3fd302** (plan only). Next, in order: ChatGPT, the owner, G10's build, then the protocol-edit
commit and the freeze commit, each with its own lane-1 verdict. The G7 method filter must land, judged with its test,
before the freeze commit.

## Addendum 2 (15 Oct 2026): revision 2 (ChatGPT review 119) at 10fa113c

The delta is the "Revision 2" section of response 157.

| Item | Status | Evidence |
|---|---|---|
| 1. IV30 and Black-76 are not in v4's live path | MET (claim verified) | I imported all 48 modules of `fno/forecast_v4/`, `fno/forecast_v4_rules/`, `fno/forecast_scoring/v4/` and `fno/weather/` myself. `fno.forecast.iv30` is never loaded. `fno.research_engine.implied_vol` is loaded, through the import chain the builder names. A grep finds no call: `forecast_v4/units.py` uses only its own arithmetic and a parameter named `implied_vol`. The planned patched-to-raise run is the right proof. Saying that V2-V5 count only under a later record that byte-checks their IV code is correct and honest |
| 2. Prospective `effective_start` for a registered slot | Sound as a rule; **not carried into the plan's own edit table** (should-fix 4) | From the slot's registered start, every baseline-observable day counts. A registered family therefore cannot dodge misses by submitting late, which is the owner's own aim for the miss rule ("cannot gain by missing hard days"). It is stricter, never looser. Unregistered slots stay `not_started` |
| 3. V1's method filter | Planned (not built), as stated | Built and judged with its test before the freeze commit |

**Should-fix 4: the protocol-edit table still writes the rule Revision 2 replaces.**
- Line 22 of response 157 still tells step 2 to add "a forecaster that starts only after the freeze counts misses from
  its first live forecast; the days before it are not started".
- For registered slots, Revision 2 replaces this with "from its `effective_start`". A protocol commit that follows the
  table would freeze the old rule.
- Fix: rewrite that row. A registered slot counts from its `effective_start`, a session on or after the freeze and
  before its first eligible session. An unregistered slot is `not_started`. Name review 119 as the source, beside
  judge 156.
- Because this changes the start of the owner's miss rule (G9, the 15 Oct row on `DESK_DECISIONS.md` line 177), the
  owner should see it as a change when they decide the checklist, not only as an edit. Add it to the list of what the
  owner confirms.

**Verdict: FAIL for 10fa113c on should-fix 4** (one table row plus one owner-confirmation line). Items 1-3 are
accepted. A re-check needs only those lines.

## Addendum 3 (15 Oct 2026): 03586b07

There is one commit, and it changes only response 157 (4 lines added, 2 removed).

| Finding | Status | Evidence |
|---|---|---|
| Should-fix 4 | MET | The edit-table row now replaces section 4's start rule. A registered slot counts from its `effective_start` (a session on or after the freeze, before its first eligible session, named in its registration row). An unregistered slot is `not_started`. Its sources are review 119 and judge 156 notes 1 and 3. The owner-confirmation list carries the change as "one change for the owner to confirm before the freeze" (line 177's start moves to `effective_start`) |

**Verdict: PASS for 03586b07** (plan only). The open steps are unchanged: ChatGPT, the owner (including this change),
G10's build, the V1 method filter, then the protocol-edit and freeze commits, each with its own verdict.

## Addendum 4 (15 Oct 2026): the V1 method filter, `story/v1-method-filter` 732db7e7 (code, lane 1)

This is option (b) of should-fix 1. Four files change: `fno/forecast_v4/terms.py`, `fno/forecast_v4_rules/series.py`
and two test files.

- **The code.**
  - `terms.V1_INTRADAY_METHOD = "rv-quote-15m-v1"`.
  - `series.live_intraday_rv` skips every row whose `method` is not the pinned one, including a missing method.
  - It is the only path: G7's capture (`forecast_v4_rules/wiring.py:37`) and G8's outcomes (`g7_series.py:31`) both
    read A16 rows through `live_intraday_rv`. Checked by grep. So V1's outcomes, its trailing baseline and its HAR
    baseline are all filtered by one line.
- **Tests.**
  - One test feeds the same date with a v1 row, an `rv-quote-5m-v2` row and an empty-method row: only the v1 row is
    read.
  - `test_the_pinned_method_is_a16s_live_method` ties the pin to `QuoteSnapshotRv15m.method`, so the two cannot drift.
  - My plant: removing the filter's two lines fails 1 test.
  - `tests/forecast_v4` + `forecast_v4_rules` + `forecast_scoring_v4` + `weather`: 304 passed.
- **Gates.**
  - Trial merge with `main` 2281a679: ruff, format and imports clean; **6,120 passed, 3 failed**.
  - **All 3 also fail on `main` 2281a679 alone**, so they are not this branch's:
    - `tests/books/test_paper_account.py::test_the_committed_state_is_the_13_oct_rs_5_lakh_opening_topped_up_to_rs_20_lakh_on_15_oct`
      and `tests/market_read_models/test_home_blocks.py::test_the_live_wiring_reads_the_repositorys_books_and_their_open_risk_cap`
      expect committed account files, which E2c's merge step 3 removed (`journal/<book>/` now holds only
      `daily_totals.csv`);
    - `tests/forecast_v4_rules/test_v4rules_series_and_rules.py::test_committed_closes_reproduce_the_disclosed_v6_counts`
      expects 2,409 V6a outcomes and the committed closes now give 2,410 (one more day of data).
  - This is a red `main`, reported to the orchestrator. It is a fix for E2c's owner and G7's owner, not for this
    branch.
- **Note (not blocking).** A skipped row leaves its session unresolved for V1, so it is not counted as void. If A16
  ever writes a new method, V1 simply stops resolving. That is intended ("a new version"), but the look's count line
  should then show it. The freeze record can say so in one line.

**Verdict: PASS for 732db7e7.** Merge it before the freeze commit, after `main`'s 3 failures are fixed (the full suite
on the merged tree must pass).
