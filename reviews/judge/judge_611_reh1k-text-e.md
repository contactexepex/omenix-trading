# Judge 611: REH1k story text, the lab's editions in a rehearsal of a day before their live date (story/reh1k-lab-editions @ 10f6f520e), judge E

**PASS (round 1 of 2, text; 2 minor). Lane 1** (what a rehearsal posts to #fno-forecast and #fno-desk). Judge E, own
session. Text only: one file, `docs/stories/REH1-rehearsal-mode.md`, +72. Judged by reading. Doc-reading tests with
the token kept: 864 passed, 14 xfailed.

## Facts checked

| Claim | Result | My evidence |
|---|---|---|
| `EditionRun.run` checks the edition's live date first | True | `forecast_lab/edition_run.py:92-94` |
| Both editions live from 23 Oct | True | `config.yaml:231-233` |
| The lab's own live dates, read in `build_composer` | True | `forecast_lab/wiring.py:50-53,101`; `CloseReport(..., live[EVENING])` at `:106` |
| REH1c covers only the daily run's steps | True | `rehearsed_live` is called only in `fno/daily/wiring.py` |
| A routine's line is "failed: ..." or "<n> commands done" | True | `rehearsal/rehearse.py:108` |
| The morning and evening routines | True | `rehearsal/routines.py:36-47` |

## Criteria (rule 1: the text against the orchestrator's gap and the owner's rows 322 and 329)

| # | Check | Result |
|---|---|---|
| K1 | Live dates under the mode; boundary on the live day; none without the mode; null date | MET: testable, with a boundary plant |
| K2 | The note in every post | MET: REH1a's `labelled()` reads `FNO_REHEARSAL_NOT_LIVE` |
| K3 | Exercised, not a routine failure; a live failure stays a failure | MET, with good, bad and empty cases |
| K4 | One line, once | MET: REH1j's `report_exercised` reused |
| K5 | Real runs unchanged | MET: behind `rehearsal()`; `live_key` is outside a command's words, so `test_routines.py` still holds |
| Gap list | release-check, preview, the other commands | MET: each reason true (none reads `forecast_lab.live_from`) |

## Findings

None blocking, none should-fix.

## Minor

1. **A rehearsed evening before the live date has no morning record of its own.** Each rehearsal is its own
   `run_id`, with its own `dryrun/` and checkout. A 22 Oct evening rehearsal reads the record's 22 Oct morning, which
   does not exist (the morning was not live), not the morning rehearsal's `dryrun/` output. So `lab close` on 22 Oct
   will likely report no forecast to check. That is honest, and it lands in the exercised line. Say so in the gap
   list, so the owner's weekend dry run of 22 Oct is not read as a fault.
2. **Design 2 sets the environment variable "in the lab's root".** Say that it is set only under the mode (no mode,
   no variable), for that child process alone, and never left set for a later edition in the same process (the CLI
   runs one edition per process today). Add a K5 case: without the mode the variable is never set.

## Plants

None (text round). The planned plants cover the root, the boundary, the note, the live key, the counted failure and
the once-only post.
