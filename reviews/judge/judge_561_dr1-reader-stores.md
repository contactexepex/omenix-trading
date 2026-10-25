# Judge 561: DR1-1c, the certifier on O9's one reader builder; an unreadable source fails loudly

Judge B, 24 Oct 2026. Commit 9959ae9db on story/dr1-reader-stores (built on main plus O9's
story/o9-readonly-index-close fb1a4bd7d, judged by judge F); lane 1. Story: `docs/stories/DR1-design-staging.md`
section 10. I judged DR1's commit alone, as asked.

**Verdict: PASS.** No blocking or should-fix finding. It merges after O9's branch.

## Claims vs reality

| Claim | Reality |
|---|---|
| The certifier takes its official files from O9's `build_stored_index_close_files()`; DR1's `stored_index_closes()` is deleted | True (`wiring.py`). O9's builder reads the service account's stores plus the owner's Drive raw area, through `StoredFilesLibrary`, so it never fetches or writes |
| Any read failure becomes "NOT recorded: a source could not be read: ...", with `alert=True` (posted, exit 1) | True. `_agreement` turns any exception into `SourceUnreadable`, which `Certifier.certify` catches into `UNREADABLE_LINE` with `alert=True`. `NoReadableStore` is raised at read time (`raw_library.py:40`), not when the builder runs, so it reaches that path rather than crashing `build_certifier` |
| A file not archived yet stays the quiet "no official index-close file in Drive yet" | True: `values()` returning None is still an ordinary failed check |
| Judge 554's note: a missing previous close names the previous session's file | True (`previous_name`); tested |

**My plants (`tests/record_store`):**

| Plant | Result |
|---|---|
| no alert on an unreadable source | 2 failed |
| the exception narrowed to `OSError` (`NoReadableStore` escapes) | caught |
| `SourceUnreadable` not caught | 2 failed |
| an unreadable source counted as recorded | 2 failed |

**Gates on 9959ae9db (run by me):** 14,899 passed, 1 skipped, 15 xfailed; ruff, format and check_imports clean. It
merges cleanly with current main.

## Notes (not findings)

- `choose()` for the certified level reads `official.values(day)` again, outside `_agreement`'s guard. A read that
  failed only on that second call would raise unguarded. The same read has just succeeded, so this is reasoning only.
- With `--since`, an unreadable store gives one alert per session in the window (up to about five on a morning). That
  is loud but repetitive.

## Addendum 1

**Verdict: PASS** on story/dr1-1d-one-read-one-alert at 9f068cee7 (from main 8214a5d5). It closes both of my notes.

- **One guarded read:** `ClosesRules._official(day)` reads each official file once per run. A file not yet archived is
  cached as None; a failure is never cached and raises `SourceUnreadable`. `_agreement` and the certified `choose()`
  both go through it, so `choose()` no longer reads outside the guard.
- **One alert per run:** `cmd_certify` collects every alerting line and announces once, with the lines joined. The
  exit code is unchanged.
- **My plants (`tests/record_store`):**

  | Plant | Result |
  |---|---|
  | `choose()` re-reading unguarded | caught |
  | no cache | caught |
  | one alert per session | caught |
  | no alert at all | 3 failed |

- **Gates on 9f068cee7 (run by me):** 14,908 passed, 1 skipped, 15 xfailed; ruff, format and check_imports clean. It
  merges cleanly with current main.
