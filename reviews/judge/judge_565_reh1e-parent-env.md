# Judge 565: REH1e, the rehearsing parent's mode and today's tracked paths (judge B's part)

Judge B, 24 Oct 2026. Story/reh1e-parent-env at 8246ddcfe (from main); lane 1, two judges (judge E the rest). Story:
`docs/stories/REH1-rehearsal-mode.md`, "REH1e". My focus: (b) the restore's correctness and the environment's
restoration. I did not read judge E's verdict.

**Verdict: PASS for my part.** No blocking or should-fix finding.

## (b) The restore

- **Faithful for every path main tracks, with no look-ahead:**
  - `git restore --source=<before> --staged --worktree -- <data folders>` runs in its default no-overlay mode. So a
    file added after the routine's start (tracked today, absent then) is removed, and every path the day had comes
    back with its bytes as of `before`.
  - My plant forcing `--overlay` (later files kept) fails 7 tests.
- **What `_drop_moved_since` drops:** only paths tracked at `before` and not tracked at today's HEAD, inside the data
  folders, with `git rm`. The scan then runs on the commit; it is never bypassed.
  - On the real history: since 22 and 23 Oct (08:36 and 14:05 IST), the only such paths are O9b's four VIX files.
    There are no renames inside the data folders.
  - **Nothing a step needs is lost:** the VIX table's Drive copy has a receipt dated 22 Oct 11:03 UTC, before any 23 Oct
    replay time, so REH1a's visibility rule serves it. Its only reader is `vix_history`'s own command, not a routine
    step.
- **My plants:**

  | Plant | Result |
  |---|---|
  | the drop call removed | caught |
  | dropping everything the day had (the HEAD set ignored) | 2 failed |

## The environment

- `in_this_process` sets `FNO_REHEARSAL` for the parent from `Rehearsal.new` to its last line, and restores the
  previous value (or removes it) in a `finally`, so every path out, an exception included, restores it.
- **My plants:** the variable not removed afterwards (caught); the `with` dropped, so the parent has no mode (caught).

## Gates (run by me on 8246ddcfe)

15,108 passed, 1 skipped, 15 xfailed; ruff, format and check_imports clean. It merges cleanly with current main.

## Notes (not findings)

- **A file moved to Drive later than the replay time:** the general case would leave a file the real day read from
  the repository absent in a rehearsal, because its Drive copy's receipt is later than the replay clock and so is not
  visible. It does not happen for 23 Oct, but the story says "its data comes from Drive" without that condition.
- **The drop is silent:** naming dropped paths in the rehearsal's started line (or in the data commit's message) would
  make a missing input traceable in DRY runs (reasoning only).
- **A rename inside the data folders** would also be dropped at its old path with nothing restored at the new one.
  None exists today.
