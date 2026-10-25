# Judge 553: A17 verify precision (`global-cues verify` at the copy path's second, DRY1 row c4)

**Scope:** story/a17-verify-seconds at 6a279ed9 (builder session_01MBnbVU4sundxNjs5u4xCsP), diff 575a8b90..6a279ed9:
`fno/global_cues/verify.py` (+8 -1), `tests/global_cues/test_verify_precision.py` (new), the story. Judge I
(session_01MvZneCLZqBuiGyNxawdVee). Lane 1 (a record check). Round 1 of 2.

**Verdict: PASS.** No finding; 2 notes.

## The orchestrator's list
| # | Check | Result | Evidence |
|---|---|---|---|
| a | Root cause, and no other compare shares it | MET | See "Root cause" below |
| b | A truly early row still fails; time zones | MET | See "Early rows and time zones" below |
| c | The "equivalent mutant" claim | MET | See "Plants" below |
| d | Real read-only verify runs | MET | See "Real runs" below |
| - | Gates on the branch merged with main | MET | See "Gates" below |

## Root cause (a)
- The collector names a copy `{fetched_at:%H%M%S}_...` from the same `fetched_at` it logs (`collector.py:93,110-113`). So the path's second is always the logged moment rounded down, never rounded up.
- `adopt` parses that second back (`archived_copies.py:37`) and logs it only for a path not yet logged (`:52`).
- For FBIL's copies, which the fill had already logged, `first_seen_at` is therefore the floor of the logged fetch. The old `seen < fetched_at` fails it by the dropped microseconds.
- **No other compare shares the pattern.** `fetched_by_sha256` is read only by `verify.py`. I searched `fno/` for every compare of `first_seen_at`, `fetched_at` or `seen` against a path-parsed time:
  - the rest compare against cutoffs (`table.provenance`, `as_of`, `forecast_v4*`, `preopen/run.py`);
  - `owner_timing/mark_snapshots.py:93` parses a capture name's second but checks the real `started_at` too;
  - `global_cues/preopen.py` logs `seen_at` in full and has no verifier.

## Early rows and time zones (b)
- **Early rows:** 06:16:30 and 06:16:30.999999 against the copy of 06:16:31.010317 both fail. A row 1 s early fails too (my plant "1 s tolerance" is caught).
- **Time zones:** `fromisoformat` keeps the offset, and `replace(microsecond=0)` on an aware datetime keeps it. The compare is between moments. The UTC test (00:46:30 UTC fails, 00:46:31 UTC passes) catches my naive plant.

## Plants (c)
8 planted, 6 caught. The 2 survivors are both equivalent:
- **Only the fetch time cut (`seen < floor(fetched)`): equivalent, as claimed.** For a whole second s, `seen < s` holds exactly when `floor(seen) < s`. If `seen < s`, then `floor(seen) <= seen < s`. If `floor(seen) <= s - 1 s`, then `seen < floor(seen) + 1 s <= s`. IST's offset is whole minutes, so this holds in any zone. The builder reports the same result: 0 tests fail.
- **1 s subtracted on both sides:** equivalent, since the same shift is applied to both sides.
- **Caught:**
  - the strict compare restored;
  - only `seen` cut;
  - `<=`;
  - minutes instead of seconds;
  - a naive compare;
  - a 1 s tolerance.

## Real runs (d)
Read-only, with Drive, 24 Oct (IST); `git status` was clean after each run:
- `global-cues verify --cue usdinr_fbil` at 6a279ed9: exit 0, "every cue row equals the archived copy it names".
- The same with the strict compare planted back: exit 1, with 1,981 lines, every one "first seen 2026-10-15 06:16:31+05:30 before its copy was fetched 2026-10-15 06:16:31.<µs>+05:30". These are DRY1's lines.
- `global-cues verify` on every cue: exit 0.

## Gates (on 6a279ed9 merged with main)
full `pytest -n auto` 14,779 passed, 16 xfailed, 0 failed; ruff check and format, check_imports and check_records clean. The largest changed file is the 51-line test.

## Notes (no action required)
- **[reasoning only] Cutting `seen` is redundant.** By (c), only the fetch time needs the cut. Cutting both is harmless and arguably clearer.
- **The check is now blind within one second.** A row stamped up to 0.999 s before its copy's fetch, within the same second, passes. That is the path's own precision, so nothing finer can be checked for an adopted row.
  - A fill row's `first_seen_at` is the fetch time itself, so it can only be equal.
  - [reasoning only] Rounding down never moves a time across a whole-second cutoff such as 09:15:00, so `provenance` labels are unaffected.
