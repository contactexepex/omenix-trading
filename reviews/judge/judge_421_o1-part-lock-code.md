# Judge 421: O1 F1 code, a rerun resumes the 3 pm parts (story/o1-part-lock at 48822a54)

**Verdict: PASS at 48822a54 (on main 8ced7208). Lane 1. Condition before merge:** G4 (judge 420) is now on main and
conflicts with this branch in `fno/daily/quote_parts.py` (`_finish`, the commit alert), `fno/daily/wiring.py` (the
committer line), `tests/daily/fakes.py`, `.gitignore`, the O1 story and the claims. Those are judged lines, so the
builder merges main, re-runs the full gates and sends me the merged head. I check only the conflict resolution:
- G4's `_commit_alert` (NOT_PUSHED / NOT_COMMITTED) is kept beside F1's `_earlier_commit`;
- the run still builds ONE `GitCommitter(git, OwnUnpushed(...))`, shared by `QuoteParts` (now with `PartLocks` and
  `PartMarkers`) and the desk;
- `.gitignore` keeps both `journal/runs/.own/` and `journal/runs/.parts/`.

## Criteria (judge 417 addenda 1-2, the passed text)
| Criterion | Result | Evidence |
|---|---|---|
| An OS lock per part and day, held by the recorder for its life | MET | `PartLocks.taken`: `flock(LOCK_EX\|LOCK_NB)`, the start time written in, the fd handed to the child through `pass_fds`, the run's copy closed; git-ignored `journal/runs/.parts/` (no `.json` there, so no run-log glob sees it) |
| Resume order: adopted, then earlier run, then restarted inside the window, then `NOT_IN_THIS_RUN` with one alert | MET | `QuoteParts.resume`; windows from A4's `WINDOW_END` and `INDEX_WINDOW_END` |
| An adopted part's status comes from its markers; never stopped by the run | MET | `EarlierRun`: `poll` stays None while the lock is held, then `ok` "recorded earlier (commit <sha>)" or `failed` with the missing markers; `stop()` is a no-op |
| Bounded: past `FINISH_LIMIT` (not before `fills_by`), `failed` with the hand fix, no commit | MET | the existing `finish` loop; `_still_running` gives `STILL_HELD` for an adopted part |
| NIFTY first, the indices after NIFTY | MET | unchanged `service` logic; earlier-run parts pass through it |
| `how` and `started_at` per part; "nifty, nse from 14:38" | MET | `_logged`; `started_at` read from the lock file, so an adopted part shows the earlier run's start (closes judge 178 add. 19's note) |
| Runner | MET | `DayRunner` resumes when the log holds `quotes` but not `quotes_done` |
| Code size | MET | `quote_parts.py` 237 lines; the new modules 62 and 63 |

**The builder's addition, which I accept:** `_start` also adopts when the lock is already held, so a routine started twice
in one container never runs two recorders. A second *live* daily run in the same checkout remains a wider problem than
F1, outside this change.

## Planted mutations (all caught)
| Mutation | Failed |
|---|---|
| No `pass_fds` (the child does not hold the lock) | 2 |
| No adoption in `resume` | 1 |
| Restart even after the window | 2 |
| No `STILL_HELD` reason | 1 |
| No "earlier run" from the markers | 2 |
| `_start` starting a second recorder when the lock is held | 1 |

**Gates at 48822a54:** 8817 passed, 17 xfailed, 0 failed; ruff and check_imports clean.

O2's strict xfails for F1 and G4 flip after both land, as the builder says.

## Addendum 1: the merged head 00e9da61 (48822a54 plus main, G4 included)
**Verdict: PASS. The condition is met; it may merge after the full gates pass on the exact pushed tree.**

I checked only the conflict resolution:
- `QuoteParts._finish` uses G4's `_commit_alert` (NOT_PUSHED / NOT_COMMITTED) and F1's `_earlier_commit` and
  `_logged`, and both helpers are kept;
- `fno/daily/wiring.py` builds ONE `GitCommitter(git, OwnUnpushed(...))` and gives it to `QuoteParts` (now with
  `PartLocks` and `PartMarkers`) and to `build_daily_run(git_committer=committer)`;
- `.gitignore` keeps both `journal/runs/.parts/` and `journal/runs/.own/`.

**Gates on a trial merge of 00e9da61 with today's main:** no conflict; 8826 passed, 16 xfailed, 0 failed; ruff clean.

## Addendum 2: F1 follow-up, a `none` marker is never "recorded earlier" (story/o1-none-marker at 25ded294)
**Verdict: PASS. Lane 1. Merge before tomorrow's go-live.**

**The gap (strong evidence; I confirmed it on main):** A4 writes the canonical marker as `none` when the window ends
with no complete attempt (`NONE_MARKER`, `fno/quotes/recorder.py` 56 and 170). F1's `PartMarkers.recorded` checked only
that the marker file exists. So a rerun on such a day reported the part `ok` "recorded earlier", and the run log
claimed data that does not exist (against O10's "no ok without data"). My judge 421 missed this.

**The fix:**
- `PartMarkers.ended_none` reads each marker's content;
- `EarlierRun._outcome` gives `failed` "the day ended none, no complete attempt (recorded earlier, commit <sha>):
  <markers>";
- a `none` part is never restarted: its marker exists and its window is over.

**Alerting, which I accept:** the rerun alerts the `none` part once more (`alerted()` stays False). The builder checked
that `record_today` (`fno/quotes/cli.py` 101-125) does not alert for itself on every path to `none`. Incomplete
captures to 15:10 exit 1 silently, and O1's `PART_NOT_OK` is the only alert. A run killed between the marker and that
alert would otherwise leave a silent day. A possible duplicate is better than silence (the owner's 16 Oct rule).

**Checks:**
- a unit case (fake markers; NSE still `ok`, no restart, one alert) and an e2e case (real markers; Groww down all day,
  killed after `reviews`, rerun: `failed`, `how` "earlier run", exactly one new NIFTY alert with the exact text);
- planted mutation: the `ended_none` branch disabled fails both (2 failed);
- trial merge with main: 8944 passed, 17 xfailed, 0 failed; ruff and check_imports clean.
