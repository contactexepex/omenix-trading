# Judge 423: G13/G13b daily score steps (story/g13-score-steps at b8d90d57; the change is 57daa431)

**Verdict: PASS (lane 1), with one merge condition and 2 minor findings.** It adds two O1 steps:
- `price_distribution_scores` runs `pricedist score`, right after `price_distribution`;
- `price_range_scores` runs `pricerange score` (seals first, then the scores file), right after `price_ranges`.

Each is `Alerted(LiveFrom(CommandStep))` with O2's locks and its own story's receipts as its only pathspecs. Each has
its own `daily.live_from` key, null today. This closes FL1's open point 3 (judge 422): without it, nothing refreshed
G13b's scores file.

## Merge condition: a conflict with today's `main` (strong evidence)
Merging b8d90d57 with `main` (62baa86c) conflicts in `tests/daily/test_day_run.py`. O1's F1 fix (48822a54, the 3 pm
parts' resume) rewrote the same rerun test. The right resolution is `main`'s version, with `new_calls` extended by the
two new names. I resolved it that way locally (not pushed) to run the gates; the builder must do the same at merge
time, then run the full suite on the merged tree.

## Gates (on that locally resolved merge)
- 8,830 passed, 16 xfailed;
- `ruff check` clean; 1,627 files formatted;
- imports clean; record scan clean (7,264 files).

Strong evidence. My first run on the conflicted tree (7 failed, 1 error) is discarded: the file still held conflict
markers.

## Checked by reading (strong evidence)
- **Rerun safety.** Both commands rescan every record and write a file named by content hash. G13's file is named by
  date plus SHA, G13b's by IST time plus SHA. O9's `DataStore.put` treats the same bytes as a no-op, so a same-day
  rerun cannot conflict.
- **A missed day loses nothing.** The scorers rescan everything, so a missed run only delays rows.
- **Seals.** `pricerange score` stores final seals through `seal_lines(..., today + 1)`. An issue whose push time is
  not yet known stays pending, inside GitHub's 8-day log, and is never stored as sealed.
- **Order.** `price_range_scores` comes before `candles`, and so before FL1's `lab_close`, which reads the latest
  scores file (sorted by name, and so by time).
- **Lag stated.** Both story texts state the one-session outcome lag. NSE's index-close file lands about 23:00-02:13
  IST, so day d scores targets up to d-1, and an N1 range issued on d is scored in d+2's run.

## Mutations (each restored)
- Caught (4):
  - G13's pathspecs given to the range step;
  - `LiveFrom` removed;
  - wrong command;
  - the step moved after `candles`.
- Survived (1): each step reads another step's `live_from` key (minor 1).

## Minor
1. **Live-key mix-up is untested.** The test checks `live_from is None`, and every key is null, so a step reading
   another step's live date passes. Set the two keys to different dates in a test config and assert each step uses
   its own.
2. **Runtime on a cold cache is unmeasured.** Reasoning only. The routine runs in a fresh container each day, so the
   verified Drive cache starts empty. Each score step syncs its story's whole Drive folder, including every back-fill
   file, and FL1 syncs G13b's live and scores folders again. Before either `live_from` is set, record one measured
   duration of each score step on an empty cache against O1's 600 s step limit.

## Note: d456c735 (two docs-only commits)
b8d90d57..d456c735 changes only `docs/stories/G13b-price-ranges.md` (7 lines in A4), adding two rules:
- BANKNIFTY's close table reads the first archived index-close file, never a later A11 revision;
- never run `pricerange closes --to <today>` the same evening, because NSE's first file can be partial.

I checked the text against the code. The live issue step updates the table only up to
`previous_regular_session(calendar, day)` (`fno/price_ranges/wiring.py:92`), as the text says. No code or test
changed. **The PASS and the merge condition stand.**
