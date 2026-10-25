# Judge 188: C2d code, C2 and C4 read the stress factor from A14c's file (judge G)

- **Judged:** `story/c2d-stress-factor-file` at `8c0c9fdcfef1c5cf7df44f5db53afd0f9bca01fb`, built on C2c `01d39e4d`.
  The C2d diff is `git diff 01d39e4d 8c0c9fdc`. Lane 1. The text was PASSed in judge 176 addendum 2 (`da699ce8`), and
  ChatGPT 117 accepted it (response 169). The claims were `response_175`, now renamed `response_178`; the code was
  judged as it is.
- The branch head `1fbcb2ff` merges in C2c's fix `6353bf68` and the two claims renames. I checked that this adds no
  `fno/` change.
- **Number:** first written as 187; renumbered 188 because another judge took 187 at the same moment.
- **Verdict: FAIL**, on the same process should-fix as C2c (judge 181): the claims have no quality rule 3 self-review.
  The code is correct. Every criterion is MET on my own evidence, and all 13 mutations I planted are caught.

## The diff

- **Config:** `risk.stressed_margin` is now only `method`, `factor_file` and `max_age_days`. If `multiplier`, `source`
  or `as_of` appears there, `risk_settings` refuses it at start-up.
- **The seed file:** `research/data/margins/stress_factor.csv` has A14c's 8-column header plus the seed row, byte for
  byte as the text gives it.
- **C2's reader:** `fno/risk/stress_factor.py` (52 lines) takes the latest row with `as_of < day` and fails closed by
  name (`RiskInputError`) in each of these cases:
  - no file;
  - a wrong header;
  - no row before the day;
  - a factor below 1;
  - an unknown status;
  - an age above 30 days.
- **C4's reader:** `fno/checks/validity_factor.py` (37 lines) applies the same rule. It is written apart because story
  C4 bans C2 code in `validity*.py`, which justifies two readers. I had said one shared reader was acceptable; two is
  stricter, also fine, and costs 37 lines.
- **The record:** `record(day)` adds the row used (`as_of`, `multiplier`, `status`, `evidence_sha256`) to the
  margin-room verdict. The static block names the method, what is stressed and the file.
- **Dead code removed:** `_optional_date` (C2) and `_date` (C4).

## Criteria

| # | Criterion | Judge's own evidence | Result |
|---|---|---|---|
| 1 | Point in time, with a same-day row never used | `test_the_factor_in_force_is_the_latest_row_before_the_day`, for C2 and C4: 6 Nov and Sunday 8 Nov give 1.45, Monday 9 Nov gives 1.50. Mutations `<=` for `<`, and ignoring the day, are each caught in both readers | MET |
| 2 | Fail closed by name; 13 Nov passes, 14 Nov refuses; a held row uses the old factor | Six named refusals for each reader. The boundary test covers both days. The held-row test reads 1.45 from a held row. Mutations caught: no age check, `>=` for `>` (C2), no factor < 1 check, no status check, no header check, first row instead of latest | MET |
| 3 | The real seed row parses, quoted `peak` | The test compares the file's bytes to the text's row and reads it with both readers on 15 Oct | MET |
| 4 | Single source | `multiplier`, `source` or `as_of` each gives `RiskSettingsError ... not allowed` | MET |
| 5 | The switch changes no figure | C2 and C4 at the seed on 15 Oct equal C2c's SF 100, SC 300, BF 300 and CCS 300 to the paisa. The other rows follow from C2c's 47-row tests at 1.45 (note 2) | MET |
| 6 | The decision record names the row | `test_manager` pins `multiplier`, `as_of`, `status` and `evidence_sha256` in the margin-room verdict | MET |
| 7 | Gates | ruff check, ruff format and `check_imports` are clean. Full suite: 6,177 passed, 8 failed, 1 error. **The failures are exactly the same set as main's** (`diff` empty): the shallow clone's history-based freeze and back-fill tests | MET |

**Mutations planted (each alone, then reverted).** All 13 were caught; the clean tree gives 887 passed.

| Reader | Mutations caught |
|---|---|
| C2 | `<=` for `<`; no age check; `>=` for `>`; day ignored; first row instead of latest; no factor < 1 check; no status check |
| C4 | `<=` for `<`; no age check; day ignored; first row instead of latest; no factor < 1 check; no header check |

**Test changes are not loosened.** Fixtures that put `k` in config now write a one-row factor file dated the day
before the decision. That follows from `as_of < d` and is stated in the claims. The repository-factor test moves its
first day from 14 to 15 Oct for the same reason. Every assertion is still exact.

## Findings

### Should fix (process, quality rule 3)

1. **The claims (`response_178`) have no builder self-review section.** Rule 3 requires one. For C2c that review found
   a real contradiction I had missed (judge 181 addendum 1), so it is worth running here too. **Fix:** run the
   independent review on `01d39e4d..8c0c9fdc` and add the section. Any code change it leads to comes back here.

### Notes (no fix required)

1. **Two rows with the same `as_of`:** both readers take the first in file order (`max` keeps the first of equal
   keys). A14c's weekly job writes one row per Sunday, so this does not arise in normal running. If it ever matters,
   the last appended row should win.
2. Criterion 5's test checks 4 rows. The other 43 follow because both readers return exactly 1.45 from the seed, and
   C2c's tests cover every row at 1.45.
3. A malformed date or number in a row raises `ValueError`. C2 turns it into a named refusal ("input not usable",
   `manager.py:66`). C4 only catches `MarginProblem`, so C4's check would stop with an error rather than a named
   refusal. That is the same as C4's existing margin-row parsing, so it is not new here, and only a broken writer
   would produce it.

## Addendum 1: re-judge at `793e03c415a32e23e84555b216532f1038ae0ecd` (judge G)

**Verdict: PASS.** The fix reached me from the builder. I re-judged it as part of the judge and builder loop and report
the verdict to the orchestrator.

- **Should-fix 1 (rule 3 self-review) is accepted.** The claims (`response_178`) carry the section. As with C2c, the
  review found something the mutations missed: an unreadable row (an empty factor, a bad date, a short row) raised a
  raw `ValueError` or `TypeError`. In C4 that escaped the check, which is my note 3. It is now refused by name:
  "stress_factor.csv row N is unreadable".
- **Note 1 is fixed.** A stable sort on the parsed date makes the later same-date row in the file win, in both readers.
- **Also fixed:** NaN and infinite factors are refused, only YYYY-MM-DD dates are accepted, and the record nests the
  row under `stress_factor_row` with the story's field names.
- **My checks on the fix tree:**
  - ruff, format and imports are clean;
  - `tests/risk tests/checks tests/test_code_size.py` gives 1,936 passed;
  - `fno/constants.py` is exactly 350 lines, which is allowed ("no file over 350") and passes the size test.
- **My new mutations (each alone, then reverted).** All 7 were caught; the clean tree gives 794 passed:
  - `max` restored instead of the stable sort, in C2 and in C4;
  - `isfinite` removed, in C2 and in C4;
  - the bad-row guard narrowed to `KeyError`, in C2 and in C4;
  - `date.fromisoformat` back in C2.
- **Behaviour now:** one unreadable row anywhere in the file refuses every trade until it is corrected. That is
  stricter than before. It is the right side to err on for an append-only file that a job writes unattended, and A14c
  alerts on its own failures.
- **Owner-visible fact (stated in the claims):** a decision dated 14 Oct has no factor, because the seed is dated
  14 Oct and only rows strictly before the day count. There is no record for that day, and the merge comes later.
- `constants.py` has no room left: the next constant must go into a split module.
