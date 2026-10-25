# Judge 660: REC1c code, the recommender's evening check, `story/rec1c-evening-check` at ae07ae8d8 (round 1 of 2, judge K, judge 2 of 2)

**FAIL, lane 1** (evaluation records). 1 should-fix, 1 minor. I did not read judge J's verdict.

**Gates.** A trial merge of ae07ae8d8810755f57604186ec852ffe2128e061 into origin/main 9b511a706 is clean (91456ea8e). On it,
with the Slack token set:
- `pytest -n auto`: 17,243 passed, 1 skipped, 13 xfailed, exit 0.
- ruff check and format are clean. `check_imports` (2,856 files), `check_records` (9,443 files) and `check_numbers` are clean.
- **No test posted to Slack** (02:20:56-02:30:53 UTC): #fno-intraday and #fno-forecast are empty. #fno-desk holds two
  "DRY RUN, <day> replay" lines, the orchestrator's rehearsal series, which posts all night; REC1c touches no rehearsal code.

## Checks (the orchestrator's seven)

| Asked | Verdict | Own evidence |
|---|---|---|
| Reads only the record's listed candidates | MET | `check()` iterates `record.candidates` and nothing else. Plant "only traded candidates": caught |
| Corrections resolve to one live outcome | MET | `_live`: a record named in a later `corrects` drops out, and a chain resolves to its last link. An orphan correction or two live records is `InputFailed`. Plants caught: last record taken without resolving; two live allowed; orphan allowed |
| Tickets never counted as trades | MET | a ticket outcome is `TICKET` with its own net, outside `closed_so_far`; an open ticket keeps the day `open`. Plants caught: ticket as `CLOSED`; open ticket ignored |
| "Closed so far" in no line until final | MET | `CheckRun._check` sends a line only for a final verdict; the non-final print gives the open count only; `answer_text` gives no total for `incomplete` or `data_check_failed`. Plant "line before final": caught |
| The 60-session end is a final `data_check_failed` | MET **only if that evening's check runs** (SF1) | `last` with an open position gives `never closed in 60 sessions`, and an unreadable day at its last check is written final. Plant "no never-closed problem": caught |
| A check error never touches the evening edition | MET | CLAUDE.md step 3b runs after step 3's commit; `recommend check` is its own command, exits 1 and alerts itself; nothing in `fno/` reads a check file yet |
| Point in time | MET | outcomes are read from `sessions(session, until=checked_on)` only. Plant "a year ahead": caught. My first look-ahead plant was caught only by a `NameError`, so I redid it |

## Findings

1. **Should fix: a day whose 60th evening is missed leaves the window silently, never final.**
   - `_recorded_days` keeps only the last 60 sessions up to `on`, and `last` is `len(sessions(day, on)) >= 60`. So each day gets its last check on exactly one evening, its 60th session, and the next evening it is gone.
   - If that one evening's check does not run (the evening routine fails, the container dies, or a crash that is not `InputFailed`), the day ends on a `not_known_yet` file with no alert.
   - **Proved:** a scratch test, built from the branch's own harness (`traded_day`, the 120-day session list), runs 59 sessions, skips the 60th, runs the 61st. Result: "no recorded day waits for a check", the only check file is `not_known_yet`, and no alert was sent. That breaks the step's stated rule that no day leaves the window silently.
   - **Fix:** select every receipted day not yet final within `LOOKBACK_DAYS`, and let `last` be `>= 60`, which already holds for overdue days. A day past its 60th session is then finished on the next evening that runs. Add the case "60th evening missed, the next one finishes it final and alerted".

## Minor

- **m1:** `_final` and `_recorded` read today's receipts. A `--on <past day>` catch-up therefore sees check files and receipts made after that day. The outcome reads stay point in time, but which days are skipped as already final does not. Either say `--on` is today's evening only, or filter check files by their `on` date.

## Plants

**Mine: 11 caught**, counting the redone look-ahead: only traded candidates; last not resolved; two live allowed; orphan allowed; ticket as a trade; line before final; no never-closed problem; look-ahead (redone); open ticket ignored; one failed day stops the run.
- **SF1's case is not a plant.** It is a missing behaviour, shown by my scratch test (kept in my scratchpad, not in the repository).

## Addendum 1: round 2 (the last), `story/rec1c-evening-check` at 33f0252db (judge K)

**PASS, lane 1.** 1 minor. I did not read judge J's verdict.

**Gates.** A trial merge of 33f0252db5c933ded100f25c35b7b861a5cce6af into origin/main 48acc7d37 is clean (e45744f44). On it,
with the Slack token set:
- `pytest -n auto`: 17,431 passed, 1 skipped, 13 xfailed, exit 0.
- ruff check and format are clean. `check_imports` (2,884 files), `check_records` (9,473 files) and `check_numbers` are clean.
- No test posted to Slack. The window's #fno-desk and #fno-forecast posts are all "DRY RUN, <day> replay" lines of the
  orchestrator's rehearsal series; #fno-intraday is empty.

| Item | Verdict | Own evidence |
|---|---|---|
| SF1: a missed 60th evening | fixed | `_recorded_days` now lists every receipted recommendation up to `on`, with no fixed window, and `last` (`>= 60` sessions) finishes an overdue day. My 660 scratch test (sessions 1-59, the 60th skipped, the 61st run) now ends with the day written final ("never closed in 60 sessions"), a second check file and the alert. My test fails as intended, because the gap is closed. Plant "window back on": caught |
| m1: a past-day `--on` | fixed | `_final` counts only check files whose `on` is on or before `on`. Plant "every check file counts": caught |
| J's m1: data-reason failures final at once | correct | `DataDisagrees` (two live outcomes, an orphan correction, an untraded decision with an outcome) is caught before `InputFailed` and written final with `last=True`. A plain read error is still retried. Plant "disagreement retried": caught |
| The seven checks of 660 | still met | `check.py`, `outcomes.py`'s matching, `check_record.py`, `check_text.py` and the line-only-when-final logic are unchanged apart from the exception class |

**m2 (minor):** a survivor. Dropping `d <= on` from `_recorded_days` is caught by no test. A past-day catch-up would then also pick days after `on`. Their checks are refused by the record ("a check before its day") and alerted, so the failure is loud, never a wrong total, but the point-in-time rule deserves its test.

**Plants:** 4 of mine, 3 caught (m2 survives).
