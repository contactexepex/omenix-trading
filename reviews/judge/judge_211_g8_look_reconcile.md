# Judge 211: G8 look reconciliation: `story/g8-look-reconcile` 079461ed (lane 1, the looks, before the freeze)

Judge B. A16/G8 builder. It builds the reconciliation agreed in response 213 and G11's text (judge 206 addendum 5).

## What is right
- **`AiSlotDays.unsettled(freeze_day, look_day)`.** For each registered `hybrid` or `ai_team` slot, it lists every
  scored, non-`system_late` session in [max(`effective_start`, freeze + 1), look day] with no row in the forecaster's
  file.
  - "A row of any status settles the day" holds in the code: `ForecastFiles.values` returns every row, with value None
    when the status is not `ok`, so a `not_fired` row settles its day.
  - The rules slot is not checked; its gaps stay misses.
- **`require_reconciled`** names the count and the earliest day, question and slot. A recorded look writes nothing
  when blocked; an exploratory look is unaffected.
- **Wiring.** One `_registry()` feeds both scoring and the reconciliation, so the freeze's adapter replaces one line.
  The sessions come from the A7 calendar minus `system_late` labels.
- **Tests.** ChatGPT's sealed-but-not-collected case, the window bounds (`effective_start`, the freeze floor, the look
  day), the rules slot ignored, `not_fired` settling a day, the recorded look writing nothing, and the live wiring
  (weekend skipped).
  - My plant (the reconciliation never finds a missing day) fails 3 tests.
  - The builder reports 3 more plants caught.
- **Gates.** `-n auto`: **6,820 passed, 0 failed**.

## Blocking 1: the open-audits gate is kept, but G11 no longer writes the file, so every look blocks once AI rows exist
- The branch keeps `build_open_audits()` and `require_settled` in `_look`, with judge 209 addendum 1's rule: a missing
  `open_audits.csv` raises `AuditFileError` once any v4 row has `kind == "ai"` (`has_kind`).
- G11's text, as passed at e1f7ea8c (judge 206 addendum 5; response 202 addendum 6, "agreed with the A16/G8 builder,
  16 Oct"), drops that file: "`open_audits.csv` and its gate are dropped ... so G11 keeps no such file". Your message
  says dropping it is "still open with them". That contradicts G11's addendum 6, which records the agreement.
- **In normal running:** G11's first AI row makes `has_kind(..., "ai")` true. With no file, every recorded look raises
  `AuditFileError`, and no look can run. It is a certain failure, not an edge case.
- **Fix (one of the two, agreed in writing):**
  - (a) remove the open-audits gate, `OpenAuditFile`, `has_kind`, `V4_KIND_AI` (if unused) and their tests. The
    reconciliation covers a strict superset of it (judge 206 addendum 5's coverage check: an open audit is a day
    without a row); or
  - (b) G11 restores the file in its text.

  (a) is the agreed and simpler path, and it is what the orchestrator's message described.
- The coordination rule (owner, 15 Oct) treats a contradiction between two stories as a FAIL.

## Tests to keep or add with the fix
These are judge 206 addendum 5's list. Present now:
- an open audit as a day without a row (the sealed-not-collected case is the same shape);
- `system_late` excepted;
- a day before `effective_start` not required;
- a complete record running.

Add one test where collect never ran for a day (no row and no fire): it must refuse. The shape is the same, but name
it.

**Verdict: FAIL for 079461ed on blocking 1.** The reconciliation itself is correct. A re-check needs only the gate
removal (or G11's written reversal) and the tests.

## Addendum 1 (15 Oct 2026): db1a0e93

**Blocking 1 is MET: the open-audits gate is removed deliberately and completely.**
- Removed: `audits.py` (`OpenAudits`, `OpenAuditFile`, `has_kind`, `require_settled`, `AuditFileError`),
  `V4_KIND_AI`, `OPEN_AUDITS_FILE` and `build_open_audits`, and `test_look_audits.py` (its 8 tests). This explains
  6,813 against 6,820.
- A grep of `fno/` and `tests/` finds no remaining reference.
- `_look` takes only `slot_days`. `LookBlocked` moves into `reconcile.py`. `sessions_not_late(is_session, days)` is
  now a testable function.

**No gap left by the removal.** Each case the old gate guarded, and those it could not see, has a named test in
`test_look_reconcile.py`:

| Case | Test |
|---|---|
| An open audit (a day without a row) | `test_an_open_audit_refuses_the_look` |
| Sealed but never collected | `test_a_sealed_answer_never_collected_refuses_the_look_and_a_written_miss_settles_its_day` |
| Collect never ran (3 sessions) | `test_a_collect_that_never_ran_refuses_the_look` |
| `system_late` never required | `test_a_system_late_day_is_never_required` (the weekend skipped too) |
| Before `effective_start`, and the freeze floor | `test_a_day_before_effective_start_is_never_required` |
| A complete record runs and is recorded, with a `not_fired` miss | `test_a_complete_record_lets_the_look_run_with_its_definitive_misses` |
| The orchestrator's case: AI rows, no `open_audits.csv`, complete record, so the look runs | The same test: no such file exists anywhere now, and the look returns (0, recorded) |
| A blocked look exits 1 and writes nothing | `test_an_unsettled_slot_day_stops_a_recorded_look_and_records_nothing` |

**My plants:**
- the `effective_start` bound dropped (freeze floor only) fails 1 test;
- the `system_late` filter dropped fails 1 test.

The builder's plants (the AI-slot filter, the freeze floor, the skipped check) were caught earlier.

**Gates.** `-n auto`: **6,813 passed, 0 failed**. Ruff and imports are clean.

**PASS for db1a0e93.** Merge it before the freeze. Response 157 is updated (36f87bbe) to drop the gate from the
checklist.

## Addendum 2 (15 Oct 2026): 83a5ee7a (test rename only)

The db1a0e93..83a5ee7a diff renames the complete-record test to
`test_ai_rows_with_no_audit_file_and_a_complete_record_let_the_look_run_with_its_misses` and adds its docstring (2
lines added, 1 removed, test only). It names the orchestrator's case explicitly. The audit-file-required rule
(16e082a7: `has_kind`, `AuditFileError`, `V4_KIND_AI`) is gone: on 83a5ee7a a grep of `fno/` and `tests/` finds only
that docstring's mention of the file. **PASS for 83a5ee7a.**
