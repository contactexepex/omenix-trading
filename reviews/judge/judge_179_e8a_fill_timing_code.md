# Judge 179: E8a / FT1 fill-timing study, code, run and results at b4c0ea07

Judge C. Branch `story/e8a-fill-timing`, head `b4c0ea07a8c9dcbfe561a6f271ea60006c18d2d8` (builder
session_01H1CmuWzBtbtjzoQNJUz2Dz). Lane 1 (a study that feeds E4's fill rule and gates the S1 freeze). The story
review was judge 155.

**Verdict: FAIL, one must-fix (a failing gate). Everything about the study itself checks out.**

## Must-fix 1: the full suite fails on the branch

`env -u FNO_SLACK_BOT_TOKEN python -m pytest -q` at b4c0ea07: **1 failed, 5961 passed**.

`tests/research/test_ledger_guard.py::test_the_repository_ledger_counts_experiment_1_and_keeps_history_retrospective`
pins the repository ledger at trials 1-53 (`range(1, 54)`, set by 08901f5b when R2 added trial 53). Commit 245934ab
adds trial 54 to `research/ledger.csv` but leaves the test unchanged, so it fails ("Left contains one more item: '54'").
It fails the same way on the merged tree (main is still at 53). Fix: the test's range to `range(1, 55)` in the same
pattern as 08901f5b (add a line checking row 54's kind and protocol commit 47d15989 if wanted). The test is not in
FREEZE.md's hash list, so the fix does not touch the frozen code or the run.

Would it change a trade? No, but CLAUDE.md makes the full suite a merge gate, so it blocks the merge.

## Gates (PYTHONDONTWRITEBYTECODE=1)

| Gate | Result |
|---|---|
| pytest, full suite | **1 failed**, 5961 passed (above) |
| `ruff check fno tests tools research/2026-10-16-fill-timing` | All checks passed |
| `ruff format --check` (same paths) | 1110 files already formatted |
| `python tools/check_imports.py` | clean: 1147 files, 1 archival skipped |
| merge-tree with origin/main | conflicts only in `reviews/claude/README.md` and `reviews/judge/README.md` (index rows; keep both sides) |
| work register on main | E8a row under the project thread, this session; no other row covers fill timing |
| ledger | main ends at 53; trial 54 free |

## The builder's three checks

### 1. The two hand days, recomputed from the raw Drive copies: match

I loaded the eight legs through `ft1study.wiring.build_archive()` and `ContractArchive.load(row)` (read-only; `load`
checks each file's SHA-256 against its manifest row before reading). Rule in the code: the decision price is the close
of the 15-minute candle that ends at the decision time; a fill at time T is the close of the candle that ends at T.

Day 1, 5 Jun 2024, 15:00 decision, June expiry (SF: sell 22600 CE and PE, buy 22800 CE and 22400 PE):

| Leg (manifest sha prefix) | 14:45 close (decision) | 15:00 close (R5, 15:15) | 6 Jun 09:30 (R30, 09:45) | 6 Jun 10:00 (R60, 10:15) |
|---|---|---|---|---|
| 22600 CE (c6defc9a) | 416.6 | 426.0 | 474.65 | 515.0 |
| 22600 PE (8f5230c1) | 360.85 | 347.2 | 291.75 | 263.0 |
| 22800 CE (9af8d5cf) | 314.0 | 321.5 | 356.7 | 393.2 |
| 22400 PE (399df175) | 283.85 | 273.0 | 222.95 | 201.1 |

SF net credit: 179.6 at the decision; 178.7, 186.75 and 183.7 at the fills, so C = +0.9, -7.15, -4.1 (C positive is
worse for the trader; for a seller, a smaller credit). LC (22600 CE): 426.0-416.6 = 9.4; 474.65-416.6 = 58.05;
515.0-416.6 = 98.4. **All six equal `hand_check`.**

Day 2, 28 Mar 2025, 14:00 decision, April expiry (strikes 23450 / 23650 / 23250): closes 13:45 / 14:00 / 14:30 / 15:00
give SF credits 174.7 / 173.85 / 177.45 / 176.25, so C = +0.85, -2.75, -1.55; LC 362.8 to 372.35 / 426.2 / 408.15,
so C = 9.55, 63.4, 45.35. **All six equal `hand_check`**, and the R mapping (R30 from 14:00 is the 14:45 fill, R60 the
15:15 fill = E4's fill) is the one PROTOCOL.md states.

### 2. Planted bugs: 18 of 18 caught

I ran `mutation_proof.py` in a separate checkout (it edits files in place): 18 of 18 CAUGHT, exit 0. Among them the
four the story names: sign error (`observe.py`), stale-leg substitution, expiry-week entry (`MIN_SESSIONS_TO_EXPIRY`
7 to 6) and wrong R mapping (`LAST_SAME_DAY_MARK`). The checkout was clean after the run.

### 3. Probe and freezes before the fetch: holds

| Step | Commit (UTC) | Checked |
|---|---|---|
| Protocol, idea card, probe | 47d15989 16:23:06 | `probe.csv` columns are expiry, kind, symbol, answered, candles, note: no price. PROTOCOL.md at b4c0ea07 hashes to the FREEZE.md row (0dea9e11...) |
| Ledger 54, freeze record | 245934ab 16:23:54 | names 47d15989 |
| Code and tests | 163cbac1 16:42:47 | `git diff 163cbac1 b4c0ea07` on `ft1study/`, `study.py`, `mutation_proof.py`, `tests/research_ft1/`: empty |
| Dry run (111 windows) | fetched 16:43:25-16:47:49 | after the code commit, before the hash freeze (the stated deviation) |
| Code hashes | 18727bb8 16:55:20 | all 26 FREEZE.md rows match the files at b4c0ea07 (`sha256sum -c`: 0 failures) |
| Full fetch | first new row fetched 16:56:18, manifest 19626105 18:25:53 | after the hash freeze; 2,548 windows (2,549 lines with the header) |
| Run and results | b4c0ea07 18:50:15 | `run_commit` 19626105 |

**Stated deviation accepted:** the dry run came before the hash freeze, but no code changed between 163cbac1 and
the freeze (the diff is empty), and the dry run read only counts and layout. It could not have tuned the analysis.

## PROTOCOL.md section 16 (four differences from the story): all accepted

1. Nights 0, 1, 2, 3+: needed, a midweek holiday would otherwise fall in no group. 2 nights is "too few days" in
   every cell (n about 20), so nothing rests on it.
2. A day whose next session is special or muhurat is left out: stricter than the story, 7 days.
3. Flips leave out the unsettled 27 Oct 2026 expiry: necessary (8 entries "not settled" in the table).
4. Splits print no interval: the story asks for none.

## Headline: matches the table, with two notes

"The overnight 60-minute fill costs about +15 points on single options, about +3 on verticals, under 1 on SF/SC/BF"
is the owner's-choice table (mean D = bad-side C at 15:00 minus at 14:00, R60): LC 15.0 [10.8, 19.2], LP 15.6
[10.6, 21.6]; the four spreads 2.5-3.0; SF 0.1, SC 0.7, BF 0.3. Correct, and correctly labelled exploratory.

- Note (reasoning only): SF and BF, and each debit and credit spread pair, are exact mirrors by construction
  (PROTOCOL.md line 100 says so; the C tables are sign-flipped copies). So "SF/SC/BF" is two independent facts, not
  three, and the four verticals are two.
- Note (some evidence): the risk is in the tails, not the mean. LC 15:00 R60 has mean abs C 55.5 points (Rs 3,608 a
  lot) and 23% of days move more than 10% of the debit; on gap days of 1% or more the mean abs C is 179 points. For SF
  the same cell is 2.9 points. Candle closes are last trades, not the owner's bid or ask; results.md says so, and the
  A16 live check is the planned confirmation.

## Merge notes

- Merge, never squash or rebase: FREEZE.md requires 47d15989 to stay in history for B4's ledger guard.
- If main takes another ledger trial first, trial 54 and the test fix must move together.

## Re-review

Only the test fix needs re-checking: the full suite on the merged tree. The study, run and results stand as judged
here.

## Addendum 1: the must-fix at 1f8ddef5 (branch head 76d73a06): PASS

The builder sent this re-check directly, and I told the orchestrator. The fix is 1f8ddef5, the only change since
b4c0ea07 apart from the merge.
- `tests/research/test_ledger_guard.py` now pins `range(1, 55)` and checks row 54 as prospective, hypothesis "no" and
  protocol commit 47d15989, following the pattern of 08901f5b.
- The study's files are unchanged since b4c0ea07: `research/2026-10-16-fill-timing/`, `tests/research_ft1/` and the
  ledger row.
- Main has added no ledger trial; 54 is still the last row.

**Trial merge with today's main (cbdc3c38):** 76d73a06 merged an older main. Today's main conflicts with it in
`docs/stories/E-paper-desk.md`, where E2c's story section and E8a's were both appended after E7. I resolved it by
keeping both sections and ran the gates on that tree:
- ruff check, ruff format and check_imports are clean.
- The full suite gives **3 failed, 6,219 passed**. All 3 failures are main's own: they fail the same way on
  origin/main cbdc3c38 alone, with no E8a in the tree.
  - `tests/books/test_paper_account.py::test_the_committed_state_is_the_13_oct_rs_5_lakh_opening_topped_up_to_rs_20_lakh_on_15_oct`
    (ValueError, "not enough values to unpack"; the paper accounts left the public record in E2c d9f67c4f)
  - `tests/forecast_v4_rules/test_v4rules_series_and_rules.py::test_committed_closes_reproduce_the_disclosed_v6_counts`
    ((100, 2410) against the pinned (100, 2409); the new 2026-10-16 close, 69af006a)
  - `tests/market_read_models/test_home_blocks.py::test_the_live_wiring_reads_the_repositorys_books_and_their_open_risk_cap`

E8a's must-fix is closed, and E8a adds no failure. The merge itself still needs main green first: the merger takes main
again, keeps both story sections, and runs the full suite. Those 3 tests belong to main's own builders (E2c, G7/v4 and
P6-P9), not E8a.
