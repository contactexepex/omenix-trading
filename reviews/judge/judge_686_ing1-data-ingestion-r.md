# Judge 686: ING1 data ingestion as a separate part (design), Judge R

Branch `story/ing1-data-ingestion`, SHA 6988fc3e291b49d7e6c2d8554b3883d3e75031c3, `docs/stories/ING1-data-ingestion.md`
(479 lines). Judge R (session_01KR5SiKNBq2bYMHtd8GbdN6), judge 1 of 2; Judge S's verdict not read. **FAIL** (1
blocking, 3 should fix, 2 minor). Lane 1, design only.

## Criteria

| # | Criterion | Result | Evidence |
|---|---|---|---|
| 1 | Capture inventory matches the code | PARTLY | C1-C21 checked: `quote_parts.py:80-84`, `v4_part.py:27-35`, `quote-recorder-nse.yml:11` (14:20), `execution_capture.py:37`, `DAILY_RUN_STEPS` (`constants_operations.py:69-97`), `runner.py:58-60` all as stated; every workflow file is named. Mixing list misses the shared composition root (finding 1) |
| 2 | Migration never loses a session's data | PARTLY | class G single writer, key flips 16:40-08:00, rollback, 5 clean sessions: sound; I6 drops a live fallback before I9 replaces it (finding 2) |
| 3 | Reuses O14's retry | MET | classes, 30 s/8 min/5 and "not wrapped" match `O14-retry-policy.md:35-39, 99-102`; the deadline change is an ask to O14's owner, not a redesign |
| 4 | Reuses GW1's Groww limits | PARTLY | limits and quiet windows reused; budget arithmetic wrong and the 130 cap is already nearly full (finding 4) |
| 5 | Two judges for every removal | MET | 6.2 right column and the paragraph under it; nothing removed in I0-I3 |
| 6 | Evidence levels honest | PARTLY | claim 14 and summary item 4 rest on readings the code contradicts (findings 1, 4) |
| 7 | Size, one owning document | MET | 479 lines; links O14, DR1, GW1, O9 rather than restating |

## Findings

1. **Blocking: capture code loads the whole system through `fno/composition.py`.** Summary item 4 and M5 say capture
   imports system code in three places. But `fno/quotes/cli.py:53`, `fno/intraday/wiring.py:13`,
   `fno/preopen/wiring.py:10`, `fno/close_read/wiring.py`, `fno/intraday/cli.py` and `global_cues/preopen_cli.py` import
   the app root. `python -I -c "import fno.composition"` loads `books`, `accounting`, `research_engine`,
   `nse_margins`, `market_read_models`, `analytics`, `costs`. So a broken import in desk or research code stops the
   3 pm recorders, A16 and A22: a shared failure domain at load time. K1 as written (AST of direct imports) passes
   it. Fix: add it to section 3.2; define the allowed shared layer (models, constants, config, storage, providers,
   alerts...); make K1 a transitive import walk from each ingestion entry point (like `test_freeze_walk.py`); and
   plan a capture-side composition root as a step.
2. **Should fix: I6 removes the closes fallback before I9 gives it a host.** Section 7 item 3 removes evening step 1c,
   which holds `closes read --commit`, A4h's fallback. Until I9, C11's main host is the daily run, which skips
   `close_read` and `close_recheck` on any desk stop (`RunStopped`, `runner.py:58-60`). On such a day between I6 and
   I9 the 15:40 live read is lost and cannot be replayed. Fix: keep the evening `closes read` until `post-close` has
   run 5 clean sessions (move it to I9's removals), or do I9 before I6.
3. **Should fix: the v4 freeze reaches much more than I11.** Q3 and R9 treat only I11 as touching frozen files.
   `fno/forecast_scoring/v4/freeze_classes.py` lists `fno/quotes/recorder.py`, `slot.py`, `weekly.py` and other
   capture modules as RECORDED (lines 97-102), `quotes/v4_extras.py` as byte-checked (line 31), and
   `daily/wiring.py`, `constants_operations.py`, `intraday/wiring.py`, `quotes/window.py` as walked roots (lines
   112-141). The K3 refusal "at the start of every capture path" edits recorded code. New modules that v4 code
   reaches (`fno/ingest/`, `fno/alerts/reported.py`) must be classed for the walk test. Fix: add a per-step
   freeze-impact column (byte-checked, recorded or walked) and put the Q3 question for every affected step, not only
   I11.
4. **Should fix: the Groww budget is miscounted and leaves no room.** Section 4.6 adds 21 + 5 + 1 + 4 + 2, which is
   33, not 38: `groww_sign_in.py:11-12` reaches 38 with 10 daily-run children (a rerun). The "school's 4 slots" match
   MS-P0b's capture probes (C20, "4 slots a session"), so claim 14's "conservative" is doubtful (some evidence). 114 + 12
   (O14) = 126 against the proposed 130 cap: C9 (3) plus a feed recorder (3) exceed it, so K7 fails at I10 by
   design. Fix: correct the tally, show the budget with every planned job, and say what gives (fewer A16 reruns, a
   per-account counter, or an owner question).
5. **Minor:** I3's missing health rows omit C6 (`CanonicalCheck` reads NIFTY's `DATASET` only,
   `health/expectations.py:71`), C8, C12, C16 `fo-masters` and C17. Fix: criterion "every job in 4.2 has a row",
   tested.
6. **Minor:** C14 should say `panel-days.yml:58-62` also archives the F&O bhavcopy, which is what covers C13's
   evening download.

## Plants

1: imported `fno.composition` as every capture CLI does. 10 system packages loaded; K1 as specified would not catch
it (finding 1).

## Notes

- The C5 double writer (M15) and the C8 move (I8) are well framed; I8 needs E3's owner and two judges, as written.
- Q1 (b) would put the Groww key on a new host: a secrets question the owner must decide with that risk stated. It is stated.

## Addendum 1

Round 2 at c9e988f7681cd358131f8ce777a4687a017b27eb (story text 637d9555; 499 lines), judged by reading. **PASS**,
lane 1, judge 1 of 2: no blocking or should-fix finding left from my round 1. I did not judge Judge S's findings;
the merge also needs S's PASS.

| # | Finding | Result | Evidence |
|---|---|---|---|
| 1 | Shared composition root (blocking) | Accepted | M16 states it; 4.0 item 3 is now a transitive rule; 4.1 adds `fno/ingest/composition.py` and a shared layer that itself imports no system package; K1 is an import walk plus a `python -I` `sys.modules` check; I2 builds the root |
| 2 | I6 before I9 | Accepted | now I9b, after `post-close` has 5 clean sessions, with the `runner.py:58-60` reason; section 7 item 3 matches |
| 3 | v4 freeze scope | Accepted | freeze-impact paragraph matches `freeze_classes.py` (recorder and A4 files RECORDED 97-102, `composition.py` line 111, walked roots); Q3 asked for every step except I1 and I3 |
| 4 | Groww budget | Accepted | 33 normal, 38 with the rerun, 114 worst, 126 with O14, 132 with C9 and a feed recorder; K7 limits 60 and 140 (margin labelled reasoning only); MS-P0b's 4 slots confirmed at `capture_probes/constants.py:41` |
| 5 | Health gaps | Accepted | I3 and 4.7 now list C6, C7, C8, C10, C11, C12, C16, C17, C18, C19 |
| 6 | Bhavcopy in panel-days | Accepted | C14 row names `panel-days.yml:58-62` |

Notes: with K7's worst case at 132 of 140, any further Groww job after I10 needs a budget decision first. I3's claim
of no freeze impact should be rechecked by I3's judges against the files it actually edits.
