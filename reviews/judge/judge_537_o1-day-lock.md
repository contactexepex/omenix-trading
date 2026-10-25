# Judge 537: O1-day-lock, one daily run per day per container (story/o1-day-lock at 02d0fe24)

**Verdict: PASS. Lane 1 (the scheduled routine and its Drive writes). Round 1 of 2.** Merge go, never
14:00-16:15 IST. No should-fix. Two notes.

## Criteria
| Criterion | Result | Evidence |
|---|---|---|
| A second `daily run` of a day beside a living one does nothing, prints one line and exits 1 | MET | `cmd_daily_run` takes `DayLock.taken` before `load_app_config`/`build_day_runner`. The lock is an exclusive non-blocking `flock` on git-ignored `journal/runs/.parts/<day>_run.lock`. The test holds the lock in a real other process: refused, no log written |
| A crash or kill frees the lock, so the rerun goes on | MET | the kernel frees a `flock` when its descriptor closes or the process dies; the descriptor is closed in `finally` |
| No child keeps the lock | MET | `os.open` descriptors are not inheritable, and every `Popen` in `fno/` keeps the default `close_fds=True` (`daily/processes.py:113`, `desk/git_limit.py:78`). The child test checks a living child leaves the lock free |
| Every wait of a minute or more prints "waiting until HH:MM IST"; polls and repeats print nothing | MET | `AnnouncedWaiter` wraps the run's one waiter. That waiter is used by the desk timetable, `NotBefore` (A4h's 15:40 close_read: the 23 Oct case) and the catch-up, while the quote parts' 5 s polls stay under the 1-minute threshold |
| The routine knows what both lines mean | MET | CLAUDE.md daily routine step 2: one added sentence |
| Separate from the part locks | MET | `<day>_run.lock` vs `PartLocks`' `<day>_<part>.lock`; no part is named `run` |

## Plants: 7 planted, 7 caught
| Plant | Caught |
|---|---|
| The second run not refused | yes |
| A shared lock in place of an exclusive one | yes |
| Only waits of 10 min or more announced | yes |
| A repeated moment announced again | yes |
| The run's waiter not wrapped | yes |
| The lock released before the run | yes |
| A held lock treated as free | yes (2 failed) |

## Gates
Trial merge with main at 4f05c63e (removed):
- 14,590 passed, 16 xfailed;
- ruff check and format clean;
- check_imports clean, check_records clean (8,818 files), check_numbers clean.

## Notes (not blocking)
1. **The lock is per container, as the story says.** Two containers (say, a routine and a hand rerun in another
   session) can still race. Only the write-once checks in A4h's and O9's Drive store stop a double write across
   containers.
   - 23 Oct's stray Drive copy (two uploads 0.8 s apart) is for the owner to keep or remove.
   - Whether those stores really refuse a second create is not part of this story and not verified here.
2. **"Never stop the run while it waits" leans on O2's limits.** A truly hung git call or child command is stopped by
   O2's hard limits (judges 204 and 412), so a routine that never stops the run cannot hang past them. Keep that
   pairing if either changes.
