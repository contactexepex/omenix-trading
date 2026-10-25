# Judge 662: F5 code, Book 2's decider (story/f5-code at da5808026; F5's code as at 6e5c882da)

**FAIL, lane 1.** Round 1 of 2. Judge I (1 of 2; B is the other, not consulted), own session
(session_01CHtddAzFcEdQh4HFiz3mqU), 25 Oct 2026. Judged against the passed text (judge 631.1 at 27aa46107) on a
trial merge of the stack (F1t, F6, F5) with `main`. Both AI books' `daily.live_from` keys are null.

## Checks

| Check | Verdict | My evidence |
|---|---|---|
| `book2_tradable` | MET | `Book2Playbook.approved_on` = D2's `approved_on` + `shadow_on` still `research` through the day − Book 2's pauses; `shadow_on` empty (`fno/playbook/book2_playbook.py`). F1, F2, F3 caught |
| Research pauses | MET | catastrophic: one closed Book 2 trade ≤ −cap; cumulative ≤ −`CUMULATIVE_CAPS` × cap (E6's constant, imported); Book 2's account only; `research_pauses.csv` refuses an edited, shortened or back-dated file and writes one row per version (`fno/book2/pauses.py`). F8-F12 caught |
| C4 `unproven` | MET | `unproven_check` in `EnvelopeMode` only, separate from D2; `version_counts` None fails closed. F4, F7 caught |
| 1-open-trade limit | MET | below 20 completed: open trades + same-day C4 passes < 1. F5 (`<=`) and F6 (same-day passes dropped) caught |
| Book 1 unchanged | MET | `CandidateBuilder.build` keeps the same checks, order and texts through `at_terms`. `RecordBuilder`, `DayInputs` and `PlaybookSnapshot` add keys only for Book 2's values. The allocator's plain `True`/`False` threshold path is unchanged. F13, F14 caught; Book 1's suites green |
| Label | MET | a chosen record without `served.strategy_status` is refused by F5 before F1t; a research pick labels the run `research`. G1, G5 caught |
| Judge-blocked day | MET | no slots kept; unpicked read "no trade, judge failed" or "no trade, judge unavailable" from the verdict file. G2, G4 caught |
| `rule_trade` in the day log | MET | every slot and every blocked default (`fno/book2/day_log.py`). G3 caught |
| Merge resolution | MET | against `main`, `config.yaml` keeps `recommend` and adds the null AI book keys and F1t's timetable. `reason_codes.py` adds the AI steps; `wiring.py` adds Book 2's review only while Book 2 is live |
| Size | MET | no new file over 300 lines |

## Findings

1. **Should-fix (quality rules 4 and 6): the code round's Claims have no plant list and no real output sample.**
   - "Mutation checks on ..." is in the text's test plan only (line 299).
   - The Claims name the self-review, deviations and gates, but no plant per criterion with its result, and no output
     made by the committed code: for example the day log of the recorded 16 Oct replay, or a judge-blocked day's
     records.
   - Fix expected: add both. Docs only; round 2 is judged by reading.

## Plants

19 on F5's head 6e5c882da (the same F5 code as da5808026; I checked that `fno/book2`, `fno/playbook`, `fno/checks`,
`fno/judge` and `tests/book2` have no diff), one at a time, each restored, tree clean after. F1-F14 cover the
research filter, the pauses filter, an empty `shadow_on`, fails-closed, `<` changed to `<=`, same-day passes, the
check removed, both pause thresholds, both append-only guards, the account filter, the rule defaults and Book 1's
bytes. G1-G5 cover the label refusal, the judge wording, `rule_trade`, the judge block and the status.
**19 caught.**

## Gates (da5808026 merged with origin/main 30f1e6839 as 50f82c2d3, clean; FNO_SLACK_BOT_TOKEN kept)

- `ruff check` clean; `ruff format --check` clean; `check_imports` clean (2989); `check_records` clean (9582).
- `python -m pytest -q -p no:cacheprovider -n auto`: **18100 passed, 12 xfailed, 0 failed** (617 s). No post on
  #fno-desk in the window.

## Notes (not findings)

- The defect the builder reports outside F5 is real by its description: E3's `fills` run-log result is keyed by trade
  ID alone (`fno/desk/daily_steps.py:185`), so Book 1 and Book 2 on the same opportunity log one fill. It is for E3's
  owner, lane 1.
- Until F4 lands, `NoJudge` blocks Book 2 every day ("judge unavailable"), as the Claims say. F4 must merge before
  Book 2's live date.
- The run-level label is conservative: a paper pick in a run that also picks research reads "strategy not yet passed".

## Addendum 1: round 2 at bc146b720 (the last round)

**PASS, lane 1**, merge on condition (below). Judge I, own session. F5's change since da5808026 is `pauses.py` and
`decision_wiring.py` (the full history check), two tests, and the Claims.

| Item | Verdict | My evidence |
|---|---|---|
| 662.1 plant list and output sample | FIXED | 26 plants, one row per criterion with its result; real samples of the 16 Oct replay's day log and records, and of a judge-blocked day |
| B's 661 m1, full-history pause check | MET | every committed version must be a prefix of the next and of the file now; the history is `commits_touching` (oldest first, `git log --reverse`, `ledger.py:104-106`); a real-git test. R1 (last version only) and R2 (wiring to the last commit) caught |
| B's 661.1 S1, the stops in the real daily run | MET | `build_day_runner` with `book2_hybrid` set holds `Book2ResearchPauses` and commits `research_pauses.csv`. R3 and R4 (each wiring function returning nothing) caught |

**Condition for the merge.** bc146b720 does not merge cleanly with `main` 2331b7a93. The conflict is one line in
`config.yaml`: `main` set `daily.live_from.recommend: "2026-10-26"`, while the branch keeps `null` beside its new AI
keys. For my gates I resolved it in a scratch tree only: `main`'s date plus the branch's null `book2_hybrid` and
`book3_ai` keys and its `ai_books` block. That commit was made with the hook off, was never pushed, and the worktree
was removed. The builder makes that same merge on the branch; the orchestrator checks the merged `config.yaml` keeps
`recommend: "2026-10-26"` and both AI books null.

Gates on that trial tree (fda97ab30; FNO_SLACK_BOT_TOKEN kept): ruff, format, `check_imports` (3001) and
`check_records` (9598) clean; pytest -n auto **18191 passed, 12 xfailed, 0 failed** (622 s). No post on #fno-desk in
the window.
