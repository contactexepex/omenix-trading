# Judge 213: BR1a code round: studies, breadth protocol and freezer (judge A)

**Checked:** `story/br1a-protocol` at `a2e4adf9ee3da5834739940adca0202ba751678e` (main merged in), against the passed
text (judge 186 addendum 1) and the builder's claims (response 201). The builder sent it to me directly, and I told
the orchestrator.

**Verdict: FAIL, 1 should-fix (one word in `PROTOCOL.md`), no blocking.** The studies reproduce exactly from the
Drive archive, and the freezer leaves S1 unchanged. The outcome, claims postponed, is the pre-registered rule
working as written.

## My independent re-run of the studies (the "judge verifies" list)

- **Data:** I copied 1,366 legacy and 693 UDiFF bhavcopies from the Drive raw archive (read only), with
  `research/2026-10-15-breadth-sizing/fetch.py`. `run.py panel` checked every SHA-256 against the manifests. The
  UDiFF manifest has one more day than the builder's run (16 Oct), outside the 2024-25 window.
- **`run.py panel` then `run.py studies`:** `study1.json`, `study2.json` and `study3.json` are **identical** to the
  committed files (sorted-key JSON diff: no line differs). That covers:
  - study 1: agreement 96.0%, 22,364 of 23,296 pairs equal;
  - the fallback window 2024-25;
  - primary `trail60`, mean Brier 0.19241, against `cal60` 0.19307 and `market` 0.19409;
  - δ = 0.0038482;
  - the excluded counts;
  - the study 2 table;
  - the whole study 3 loop.
- **One year's SD, lag-1 and look counts, by hand:** 2024's `market`/`trail60` pair has SD 0.0199109 and lag-1
  0.253757, so the inflated variance is 0.000666064, the same as `study2.json`. With z = Φ⁻¹(1 − rate/3) + Φ⁻¹(0.8)
  and look 2 = ⌈z² × v / δ²⌉, I get 248/495, 263/526, 285/569 and 321/642 at 0.02, 0.015, 0.01 and 0.005. These are
  exactly the committed looks.
- **Study 3 at another seed (777 instead of 20261016):**
  - The decision is the same: no rate passes, so claims are postponed.
  - The −d failures repeat at every rate. At 0.02, whole window, −d: 0.0915 against 0.0835 at look 1, 0.082 against
    0.079 at look 2, and 0.1355 against 0.130 at either.
  - Every cell agrees within 2 SE except one, at about 2.0 SE (0.005, whole, −d, either: 0.0705 against 0.088),
    which changes no decision.
- **The outcome screen sees only t+1:** `daily.outcomes` excludes a (u, t) when `sizing.adjusted(a, b)` is true for
  t+1's row. The flag never enters the forecasts (`sizing.forecasts(series)` takes the outcomes only), and it applies
  to every baseline alike.

## The deviations in response 201 (asked to accept or reject)

1. **Item key `target`, not `target_t1`: accepted.** S1's parser takes `[a-z_]+` only. Widening it would edit
   `protocol.py`, which S1's `frozen_files` lists. The title still says "T1 target".
2. **v4's sign of d: accepted.** `batch_means_p` is one-sided for P(T ≤ t), so a negative mean favours the second
   series. `study2.differences` is second minus first, and the claim's meaning is unchanged.
3. **The fallback cuts the inputs too: accepted.** The story's "use 2024-2025 alone" after the proxy failed its gate
   is best read as no old-format row anywhere, so 2024's first 60 sessions are history only (189 + 248 = 437 scored
   sessions). The other reading would feed the failed proxy into `trail60` and `cal60`. The choice was written in
   `primary_baseline_rule` and runner.py's order before the run, and the run reproduces.
4. **The window (437) is shorter than look 2 (495-642): accepted as disclosed.** The circular bootstrap wraps. The
   300-day diagnostic, outside the frozen procedure, shows the failure is not that artefact.
5. **No rolling real windows: accepted.** It follows from 4 (`windows: 0`).

## Freezer (scope 3): S1 unchanged

- **No S1 test was edited.** The only test changes are two new files.
- `EVALUATION` carries the exact S1 strings, so the record and the ledger are byte-identical: "Evaluation protocol
  freeze record", "story S1, criterion 3", "Evaluation protocol v{n}: the three books' comparison rules (story S1)",
  "evaluation-protocol-v{n}", and `requires_gate=True`.
- `protocol.py`, `completeness.py`, `gate.py` and `review_dates.py` are untouched, and `parse_protocol` and
  `PROTOCOL_FILE` keep their names (the F9 agreement).
- Only `wiring.py` maps the names to definitions.
- `python -m fno evaluation check` prints S1 and the gate as before, and `--protocol breadth` prints "complete".
- **RM1's gate is kept:** plant P1 (S1's definition with `requires_gate=False`) fails 3 tests. BR1 has
  `requires_gate=False`, and plant P2 (forcing it True) fails 3 tests.

**My plants** (`tests/evaluation` and the study tests; 81 pass unplanted):

| Plant | Result |
|---|---|
| P1 S1 drops the gate | 3 fail |
| P2 breadth requires the gate | 3 fail |
| P3 the freeze checks S1's items for any protocol | 3 fail |
| P5 Holm without the division by K | 2 fail |
| P6 no centring of the null | 2 fail |
| P4 the CLI's `verify` ignores `--protocol` | 0 fail (note) |
| P7 every bootstrap path starts at 0 | 0 fail (note) |

The study code's other check is my byte-identical re-run.

## Should-fix

**SF1. `PROTOCOL.md` `looks` states the opposite of the result.**
- **Evidence:** it reads "at every rate the sign-flipped null (-d) on the whole window **passed** the limits of 0.025
  per look and 0.045 at either (at 0.02: 0.092, 0.082, 0.136 …)". The numbers are above the limits: −d **failed**.
  `null_size_check`, `DIAGNOSTICS.md` and the README all say "no rate passes".
- **Path:** the owner decides `PROTOCOL.md` item by item, and this item tells them the opposite of what happened, in
  the one item that explains why claims are postponed.
- **Fix:** "passed" becomes "exceeded" (or "failed").

## Notes (one line each, no fix asked)

- **P4:** the CLI's `verify --protocol breadth` is untested. CI uses the `verify(root, definition)` function, through
  `test_the_suite_fails_when_a_frozen_breadth_target_changes`. A one-line CLI test would close it.
- **P7:** no test catches study 3's block starts collapsing. The study was run once and committed, and my re-run is
  the check. A test that path starts vary would guard a rerun.
- **For S1's text owner (the builder's own note, agreed):** S1's `frozen_files` lists `protocol.py` and
  `completeness.py` but not `freeze.py` or `definition.py`, where `requires_gate=True` now lives. This is no weaker
  than before (the gate call was in the unfrozen `freeze.py`), but both belong on the list before S1's freeze.
- **Merge:** the branch conflicts with main in `reviews/claude/README.md`, rows only. Unresolved conflict markers
  fail 4 tests, so keep both sides.
- **What the result means, for the desk (some evidence):** on 2024-25 the daily cross-sectional Brier differences are
  so crash-skewed that `confirmatory_test` over-rejects under −d (0.064-0.088 per `market` member against 0.0067).
  A breadth claim is therefore not available under v1. A new version (a crash-day gate, a rank test, or a calibrated
  threshold) is the owner's decision.

## Gates

- On the trial merge with origin/main f10735e7 (tree 7b958d0, README rows resolved by keeping both sides), `-n auto`:
  pytest 6852 passed; `ruff check` clean; `ruff format --check` 1214 files formatted; `check_imports` clean.
- On the branch itself: 81 of 81 evaluation and study tests pass.

**A re-check needs only the one word in `looks`.**

## Addendum 1: the head named by the orchestrator (90fe09be)

The orchestrator's message, queued at 21:58 UTC and received at 23:14, named head 90fe09be. a2e4adf9..90fe09be
renames the claims file (response 201 to 197) and changes one line each in `BR-breadth.md`, `WORK_REGISTER.md` and
the claims index. There is no code, study or `PROTOCOL.md` change, so judge 213 applies to 90fe09be unchanged (FAIL,
SF1 "passed" → "exceeded").

The orchestrator's two questions, answered above:
- **What I re-ran:** all three studies, from the Drive files, byte-identical, plus study 3 at a second seed. Nothing
  was checked from the committed results alone.
- **S1:** S1's freeze is byte-for-byte unchanged, and nothing is weaker than before. `requires_gate=True` moved from
  the unfrozen `freeze.py` call to the unfrozen `definition.py`. Both files should join S1's `frozen_files` before
  S1's freeze.

## Addendum 2: aeea15d5 (the fix, two optional tests, response 198): PASS

The fix and the tests sit in merge commit aeea15d5. I read its diff against 90fe09be for the BR1 files.

- **SF1: MET.** `PROTOCOL.md` `looks` now reads "the sign-flipped null (-d) on the whole window **exceeded** the
  limits". This is its only change.
- **The optional tests:**
  - `test_block_starts_vary_across_paths_and_populations` is real: my plant P7 (every path starts at 0) now fails 1
    test.
  - `test_the_verify_command_takes_protocol_breadth` runs `evaluation verify --protocol breadth` and expects
    "unchanged". In a repository with no breadth freeze that is true whichever definition the command passes, so my
    plant P4 (the CLI's `verify` ignores `--protocol`) still passes all 21 tests. A note only: it was optional, CI
    checks `verify(root, definition)` through the function, and a test with a planted breadth `FREEZE_v1.md` and an
    edited target would close it.
- **No other change** to `fno/evaluation/`, the studies or their results since 90fe09be. Everything else in the diff
  comes from main, which the merge brings in.

**Response 198 (the candidate comparison), a sanity read as asked, not a verdict:**
- **Order:**
  - Part 1, the pre-declaration, is commit 0fd0c2de at 21:54 UTC.
  - The code (`research/breadth/candidates/`) is 76952bf2 at 22:08.
  - The results (`results.json`, `run.log`, Part 2) arrive only in aeea15d5 at 23:19.
  - Part 1 is unchanged, with 85 lines added after the "Part 2" heading and 0 removed.
- **The declared pass rule is applied as written:** ≤ 0.025 at each look and ≤ 0.045 at either, both signs, the whole
  window and the worst year; B also on the mean-centred null; C also on the 2025 hold-out.
  - **A fails on its own reported numbers:** whole −d at 0.005 is 0.065 at either.
  - **B fails on its own null** (0.168 at 0.005), and so cannot win.
  - **C's α* = 0.0055 fails the declared hold-out** (2025 −d 0.072).
  - "No candidate passes, no winner" follows.
- **Power** was declared "for information only" for a failing candidate, and it is reported that way.
- **Fair:** the diagnosis (dependence beyond 5-session blocks; variance ratios 1.43 and 2.08 for the `market` pairs
  against 0.62) and the D proposal are labelled reasoning only and "not run here". I did not re-run response 198's
  numbers.

**Gates on the trial merge with origin/main 350de5df, `-n auto`:**
- The merge conflicts in `docs/WORK_REGISTER.md`: main's side holds the "G8 look reconciliation" and "BR1 breadth
  track" rows, and the branch's side is empty. With the markers left in, 4 record-scan tests fail.
- With main's side kept (tree 8fa9fe9): 6864 passed. `ruff check` is clean, `ruff format --check` shows 1215 files
  formatted, and `check_imports` is clean.
- The merger should check that the BR1 row on main says what the branch intended.

**Verdict: PASS.** Protocol v1's claims stay postponed, as its pre-registered rule says. A v2 is the owner's
decision, through its own story text, judge and ChatGPT round.

## Addendum 3: f6239740 (the owner's "descriptive only" written in): PASS

The builder sent this directly, and I reported it to the orchestrator. The delta aeea15d5..f6239740 on BR1's files is
86b3a60c plus a merge of main. Against main, `fno/` holds the same seven `fno/evaluation` files judged above.

- **Matches the owner's row** (DESK_DECISIONS, 16 Oct, "BR1: descriptive only; no skill claim; the null size check
  re-measured each year", in ce150a37 on main).
  - `looks` and `null_size_check` read "decided by the owner on 2026-10-16".
  - `null_size_check` adds the yearly re-measure on the latest two full years, labelled exploratory: "a pass is never
    a claim by itself; it can only start a new protocol version".
  - The status header, `claim_meaning` ("under version 1 it is never made"), `descriptive_reports` and `reporting`
    ("each labelled descriptive") say the same.
  - No other item changed status. `check --protocol breadth --decided` lists the other 16 as undecided, which is
    right.
- **The one test change** is in BR1a's own new test file. It pins the decided set to exactly {looks,
  null_size_check}, which is correct.
- **No code or config change** on the branch since aeea15d5.

**Gates:**
- The merge conflicts in `reviews/claude/README.md`, rows only. With the markers left in, 4 record-scan tests fail.
- With both sides kept (tree f9cd8ab, origin/main 71bed543), `-n auto`: pytest 6864 passed. `ruff check` is clean,
  `ruff format --check` shows 1215 files formatted, and `check_imports` is clean.

**Verdict: PASS.**
