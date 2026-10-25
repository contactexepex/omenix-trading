# Judge 605: T1f code, the card in a rehearsal and every stage after the post guarded (story/t1f-card-rehearsal-clock at f84c08a18)

**PASS, lane 1.** Round 1 of 2. Judge I, own session (session_01CHtddAzFcEdQh4HFiz3mqU), 24 Oct 2026. Judged against
the passed text (judge 592.1). The code is at 8f4a1e540. 0855b04c8, 754be3446 and f84c08a18 change only
`T-cards.md` (verified). `git diff origin/main f84c08a18 -- fno/desk fno/daily` is empty.

## Criteria

| # | Verdict | My evidence |
|---|---|---|
| 1 | MET | `rehearsed_card_clocks(real, env)` (`card_label.py`) calls `real()` only outside the mode; `HttpDateClock` is built only inside `wiring.build_card_clocks.real`. Probe test: spy counts 0 in the mode, 1 outside; both entries carry REH1c's imported `NOT_CHECKED`. M1 (real form in the mode) and M11 (Slack's entry dropped) caught |
| 2 | MET | In the mode: 1 post, the Drive record saved, metadata written, `complete` (probe test). A rehearsal commits only to `rehearsal/<day>-<run_id>` (REH1, unchanged) |
| 3 | MET | `card_clocks.guarded` catches any error per server, and `CardIssuer._clocks` catches a raising clock form; both stored as unchecked by type, `complete` false. M2 (`ValueError` only) and M12 caught |
| 4 | MET | Stages after `poster.post`, each guarded, in order: clocks, `_facts` (falls back to `minimal_facts` with `failure`), `_save` (record build inside the guard), `_write` (any error; `_printable` falls back to the minimal facts). Posted once, first. M3, M4, M5, M7 (minimal facts without `clock`), M10, M14 caught; M8b (JSON built after the open, leaving an empty attempt file) caught |
| 5 | MET | `issue` never raises, so `cli.py:52` prints the result lines last; exit `sent and complete`. M6 and M13 caught |
| 6 | MET | Without the hook, GitHub's entry is "clock NOT CHECKED: host vs GitHub (RehearsalCallRefused)" and the issue is not complete (probe, real guard in a subprocess) |
| 7 | MET | `guard.builders()` has "the card's clocks": `build_card_clocks` with `RehearsalCardClocks` (`guard.py:45`); `test_guard.py` map and count updated. M9 caught |

**The stated deviation (a non-JSON receipt value is a stage 3/4 case, not a facts failure): accepted.**
- Stage 2's trigger in the passed text is "if building them raises". Building a dictionary that holds a non-JSON
  value does not raise; only `_json` does, in stages 3 and 4.
- Stage 4's text already says that metadata which is not JSON prints the minimal facts. So the code follows the
  passed stages, and test 3b's example in the text was the inaccurate part.
- The outcome is "record not built (TypeError)" plus the printed minimal facts, with exit 1. The real receipt values
  come from Slack's JSON answer, so this path is hypothetical.

## Plants

15 planted (M1-M14, M8b), one at a time on `tests/cards`, `tests/rehearsal` and `tests/market_read_models`; each
restored with `git checkout --` and `__pycache__` cleared; tree clean after. **14 caught.** M8's first form was
equivalent, because the early `body = json.dumps(...)` still ran before the open; this is the builder's own P12
note. M8b removes it and is caught.

## Gates (f84c08a18 merged with origin/main b18507b6d as 2cc32e332, clean; FNO_SLACK_BOT_TOKEN kept)

- `ruff check` clean; `ruff format --check` 2566 files formatted; `check_imports` clean (2695); `check_records`
  clean (9166).
- `python -m pytest -q -p no:cacheprovider -n auto`: **16091 passed, 1 skipped, 14 xfailed, 0 failed** (726 s).
- Sizes: `issue.py` 136 lines, the new modules 53 each; no class near 350.
- Slack during the full run (16:14:16-16:26:24 UTC):
  - #fno-forecast and #fno-intraday are empty.
  - #fno-desk has one labelled "DRY RUN, 2026-10-23 replay" A22 line ("banknifty late: seen 09:11:01"). No test
    holds that text, and a rehearsal of 23 Oct was running (branch `…T154101Z-fa52d2`). So it is a rehearsal's post,
    not a test's (some evidence).

## Notes (not findings)

- Earlier, a cold first run on the narrower set (before the container had warmed) failed 1 of 534. I did not capture
  its name. It did not recur in 4 reruns or in the full run.
- `minimal_facts` repeats `card_sha256`'s one line, so that `issue.py` and `minimal_facts.py` do not import each other
  in a cycle. Moving `card_sha256` out of `issue.py` would remove the copy.
- When the metadata is not JSON, nothing is written to the file; only the minimal facts are printed. That is the passed
  text's stage 4. Writing those always-JSON facts to the attempt file would leave a committed trace too.
