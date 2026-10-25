# Judge 100: A15 India VIX full history: `story/a15-vix-history` 514d43ba7bfe18d99f71dae9dd9205b01d584f98 (lane 1, response 100)

Fresh judge session for orchestrator session_01VG1RqxLFUVdvvPuMRYZtDH. Shares no context with the builder.

**What I did:**
- read the story text (`docs/stories/A-data-foundation.md` A15) at this SHA, design v2 2.1's A15 row and REPLAN's A15
  paragraph, response 100 and every new file under `fno/vix_history/` and `tests/vix_history/`;
- ran the full gates on the exact SHA and on a trial merge with `origin/main` (e4882cf);
- ran `python -m fno vix-history verify` against the owner's Drive (read-only; it reads files, writes nothing);
- probed NSE myself, with my own script and plain `requests`, not the repository's code;
- planted 11 code mutations and 3 data/flow scenarios of my own.

I did not run `fill` or `sweep`: both write (Drive files, manifest rows, the revision index).

## Gates

- Exact SHA 514d43b, full history (not shallow), Slack token unset: **3,232 passed** (7 min 55 s). `ruff check` clean,
  `ruff format --check` clean (725 files), `check_imports` clean (735 files). This matches the builder's 3,232.
- Trial merge with `origin/main` e4882cf (merges cleanly): **3,232 passed** (main adds no tests since the branch base), `ruff check`, `ruff format --check` and `check_imports` clean.
- Largest new file: `librarian.py`, 108 lines. Every file is far under 350 lines.

## The story text (checked first, as the owner's quality rule 1 asks for stories already in build)

The story matches design v2 2.1's row ("India VIX daily open, high, low, close back to its start ... A15"), REPLAN's
paragraph (raw in Drive, derived table, A11's revision rule) and the judge-verifies list. Two design items are out of
scope, each with a reason:
- **"daily":** the story leaves schedules out; daily VIX comes from the index-close files (O6). Those give the close
  only, not open, high and low. So a daily OHLC series exists only up to the last month someone runs `fill` for.
- **"back to its start" (2008):** NSE does not serve it. The story says so, names the alternatives tried and leaves
  it open. This is honest, but the design's first reason for A15 (the 2008 crash) is **not delivered**. The weather
  and crash replays get five stress episodes (2011, 2013, 2016, 2020, 2024), not six.

## Per criterion

| # | Criterion | Builder's claim | My own evidence | Result |
|---|---|---|---|---|
| 1 | Source and terms named | README names publisher, URL pattern, terms (reasoning only), pace | README "Source and terms": NSE, `/api/historicalOR/vixhistory?from=DD-MM-YYYY&to=DD-MM-YYYY`, terms "not re-read ... reasoning only", one request a second through `fno/http_pacing.py`, one per month. The terms position is labelled honestly; the story asks only that it is named with its label | MET |
| 2 | Full range from NSE's first served day; earlier gap stated with the probe range | 19 Jul 2010 to 30 Sep 2026, 4,019 days; nothing before 19 Jul 2010 | My own probes (15 Oct 2026): 1 Jan-31 Mar 2009, 1 Sep-31 Oct 2008 and 1 Jun-18 Jul 2010 answer `{"data":[]}`; 1 Jun-31 Jul 2010 answers 10 rows, the first 19-JUL-2010. The table holds 4,019 rows, first 2010-07-19, last 2026-09-30, and the manifest 195 months (Jul 2010 to Sep 2026). The 2008-Jul 2010 gap is stated in the story, the README and response 100, with niftyindices.com tried | MET |
| 3 | Derived rows equal the raw files; command lists every difference; planted value and SHA named; committed SHA = manifest | `vix-history verify`: all 4,019 equal; tests | Real run against Drive: **"India VIX table: all 4019 days equal their archived month files"** (2 min 7 s). It reads every month the table holds and checks each file's SHA-256 against the manifest, so all 195 Drive files equal their manifest rows. Independently, I fetched 8 months from NSE myself (2010-09, 2013-08, 2014-09, 2015-01, 2019-11, 2020-10, 2021-02, 2024-03): **8 of 8 byte-identical to the manifest SHA-256 and size**. Tests name a planted value and a wrong SHA (my M7 caught). **But my plant P1 shows a hole `verify` cannot see:** with all of August 2010 deleted from the table, `verify` reports nothing, and `fill` adds nothing back. See should-fix 1 | PARTLY |
| 4 | Point in time: `first_seen_at`, append-only, no rewrite, no hole filled, running month never fetched, revisions via A11 | tests; real sweep 0 new versions | Append-only, no rewrite and no hole filled: code `table.py:57-72`, my M2 and M11 caught. Revisions: my plant P2 with the real manifest keying stores the revision beside the original, raw bytes unchanged, the change named day by day, and a second sweep adds nothing. Error page never kept: my M6 caught. **Running month never fetched: not tested.** The only guard is `cli.py:42` (`min(args.end or last_ended, last_ended)`); my M5 replaced it with "today" and all 39 A15 tests and the suite still pass. The test the builder cites (`test_month_file.py:24`) tests `last_complete_month`, not that the CLI uses it. See should-fix 2. `first_seen_at` labelling: see should-fix 3 | PARTLY |
| 5 | Overlap check with the 2017+ closes, rounding apart, never fixed | 0 differs, 1,488 rounded, 2 Mar 2024 only in index-close | Recounted from `overlap_index_close.csv`: 1,488 `rounded`, 1 `only_in_index_close` (2024-03-02), 0 `differs`. NSE's own Mar 2024 file (my fetch) has 1 and 4 Mar but no 2 Mar; `warmup_closes.csv` has 2 Mar 2024 = 14.99, kind `special`. My M8 (rounding always true) caught. Nothing is changed in `warmup_closes.csv` | MET |
| 6 | Gaps recorded, never filled; doubtful levels kept and listed | gaps 1, unverified 90, weekend_row 9; 3 level flags | Counts recomputed from `gaps.csv`. NSE's own files (my fetch) confirm 12 Feb 2021 open, high, low 0 with close 23.045, and 22 Aug 2013 close 27.68 below low 27.99; the table keeps both as published. My M10 (zero not flagged) caught. **The 9 muhurat rows (2017-2025) are in the table but listed nowhere**; see should-fix 3 | MET |
| 7 | Failed download writes nothing and is named; stored file never replaced; rerun fetches only what is missing | tests incl. 9 bad shapes | Reader (`month_file.py`): non-JSON (HTML with HTTP 200), no `data` list, empty list, 70 rows or more, another index, day outside the month or twice, a non-number: all refused before `put`. My probe confirms the 70-row cut is real: 1 Jan-30 Apr 2020 answers exactly 70 rows ending 13 Apr. A truncated body fails JSON parsing. A stored file failing its check or manifest SHA is reported, never replaced (my M4 caught). My M1 (cap `>=` to `>`) and M9 (day outside month) caught | MET |
| 8 | No frozen file changes; gates | new package only | `git diff --name-only origin/main...514d43b`: no FREEZE record, no file under `research/forecasts/`, `research/data/nifty-panel/`, `fno/forecast*`, `fno/research_data/`, `fno/constants.py` or `fno/composition.py`. Outside the new package: `fno/cli.py` (+2 lines, the parser), `CLAUDE.md` (+1 composition-root line), `fno/storage/README.md` (+1 row). Gates above | MET |

## Claims vs reality

| Builder's claim (response 100) | Reality |
|---|---|
| "4,019 days, 19 Jul 2010 to 30 Sep 2026, from 195 NSE month files archived in the owner's Drive" | True: table rows, manifest rows and the Drive read-back all agree |
| "The 2008 crash is NOT covered ... probed back to Nov 2007" | True for the windows I probed (2008, 2009, Jun-18 Jul 2010) |
| "0 real differences, 1,488 rounding-only, 1 day missing (2 Mar 2024)" | True (recounted) |
| "NSE cuts answers at 70 rows silently" | True (my 4-month 2020 window: exactly 70 rows) |
| "The same month read twice: identical SHA-256" | True: my 8 fresh reads equal the archived bytes |
| "`warmup_closes.csv`'s VIX is rounded to 0.01 on 1,488 days" | True; largest gap 0.005 (from the file). A useful desk finding |
| "open equals the previous close on 3,519 of 3,584 days before 2025" | True: my own count is 3,519 of 3,584 (20 Jul 2010 to 31 Dec 2024) |
| "VIX peaks ... 2020-03-24 83.6075" | True (table maximum close) |
| "test_month_file.py:24 (last complete month)" proves "a month still running is never fetched" | Not as claimed: the helper is tested, the CLI's use of it is not (M5 survived) |
| "behaviour is the same" for A11's SHA lookup | True. The manifest's "file name" for this dataset is the URL tail (`vixhistory?from=01-07-2010&to=31-07-2010`), so A11's lookup by `india-vix_201007.json` misses and reads the original from Drive. My plant P2 shows the result is still right |
| "Terms: not re-read (reasoning only)" | Honest; stays an open owner item |
| "`first_seen_at` ... for backtests a day's value is taken as known at its close" | Only in response 100; the README does not say it, and "at its close" is the wrong rule for a 15:00 decision (should-fix 3) |

## Findings

### Should-fix

1. **`verify` misses rows that are missing.** `VixTableVerifier.problems` walks only the months the table already holds
   (`verify.py:33-36`). My plant P1 deleted every August 2010 row from a table built by the real builder. `verify`
   returned no problems, and `extend` added 0 rows (correct, since a hole is never filled). The same blindness covers a
   table cut short at the end. The criterion asks for "every difference". Fix: also walk every month in the manifest
   (from the first served month to the table's last month) and name each archived day the table lacks. Add a test with
   a whole month removed.
2. **"A month still running is never fetched" has no test.** The story asks for tests on this rule. The guard is
   `cli.py:42`. My mutation M5 (`end = args.end or now_ist().date()`) fetches the running month, and no test fails.
   A running month's file would grow, which the archive's "never overwritten" rule cannot then hold. Fix: a test of
   `_months` (or of `fill` with fakes) on a mid-month clock and with `--to` set to the current month: the running month
   is absent.
3. **Point-in-time and session labels for the table's users are missing from the README.** The orchestrator asked
   specifically whether back-filled rows can be mistaken for known-at-the-time data. Read literally, they cannot:
   `first_seen_at` is 15 Oct 2026 for all history, and the README calls it "an upper bound on when we knew it". But
   every backtest must ignore that column and use `date`, and the README never says what rule then applies. Response
   100's "known at its close" is wrong for this desk:
   - Day d's close is set at 15:30 IST, after the 15:00 cutoff. So a 15:00 decision or forecast may use day d-1 at the
     latest, never day d.
   - The table holds 9 muhurat sessions (19 Oct 2017 to 21 Oct 2025, one-hour evening sessions, found by matching the
     A7 calendar's muhurat dates against the table). It also holds special sessions (budget Saturdays, 20 Jan and
     18 May 2024) and 9 pre-2017 weekend rows. There is no session-kind column, and the README mentions only "weekend
     rows". A user computing daily VIX changes, or the weather's 5-session windows, would count a one-hour muhurat
     session as a full day. G6 and design v2 use regular sessions only.

   Fix (README text, no data change): state the known-at rule (end of day, after the session's close; usable from
   the next session's 15:00 decision); say that `first_seen_at` is archive time and is not usable as a known-at time
   for history; and say that muhurat and special-session rows are included and must be selected through the A7
   calendar. Optionally list them in `gaps.csv` as a kind, which `check` already has the calendar for.

### Minor

1. **A sweep is silent when the archived original is missing.** In my plant P3 the August raw file was missing from the
   store and NSE had other bytes. A11's `capture` records the path in `not_archived` and returns None. The sweep then
   prints "0 with a new NSE version" and exits 0, and `not_archived` is never shown. Print it, and exit 1, because a
   missing original is a broken archive.
2. **A11's manifest lookup never matches this dataset.** `Fingerprint.filename` is the URL tail, so every new-bytes
   answer costs one Drive read, and `RawFileConflict`'s message would name `vixhistory?from=...`. The result is
   correct; it is disclosed in response 100. Leave it, or key the lookup by archive path in A11's own story.
3. **Not scheduled.** Nobody runs the monthly `fill`, so OHLC stops at 30 Sep 2026. Disclosed; it needs an owner or
   orchestrator decision (an Action, as O6).

## The orchestrator's questions

- **(a) Back-filled `first_seen_at`.** Honest, but not enough on its own: should-fix 3.
- **(b) A11 lookup.** Planted with the real manifest keying (P2): the revision is stored beside the original, the
  change is named, the raw file and table are unchanged, and a repeat adds nothing. The pre-check by manifest SHA in
  `sweep.py` only saves Drive reads. The silent case is minor 1.
- **(c) HTML page or a cut answer as a stored month.** It cannot happen through `fill`: the reader refuses it before
  `put` (M1, M9 caught; the 70-row cut and HTML with 200 shown real). Through `sweep`, an invalid answer is listed and
  never captured (M6 caught).
- **(d) Drive uploads vs the manifest.** Checked read-only from this session with the owner's Drive settings: `verify`
  read all 195 month files, each SHA-256 equal to its manifest row. Independently, 8 of the same months fetched by me
  from NSE are byte-identical to the manifest. I did not list the Drive folder for extra files outside the 195 paths.
- **(e) 350 lines and constants.** All files are under 110 lines. URL, field names and kinds are named constants at
  the top of their modules, and the dataset name is a class attribute, as for every other `NseArchiveSource`. This
  follows CLAUDE.md ("module-specific URLs ... named constants at the top of their module"). No environment-variable
  names are introduced.
- **(f) Lanes.** These rows are made by story code run by hand, not by a scheduled job, so they are not lane 3
  (refinement 3). They are judged here as lane 1, which is right. **Every later monthly `fill` commit is also lane 1**
  until the fill becomes a scheduled job's own output path. Record this, or schedule it.

## Project rules

- Interfaces: `VixMonthReader`, `RawFileSource`, `RawFileStore`. Concrete parts are chosen only in
  `fno/vix_history/wiring.py`; `cli.py` imports the concrete source only for `first_day`, which the builder discloses.
  `CLAUDE.md` lists the new composition root.
- No secrets in files or output; no Slack; no orders. Tests use fakes and local stores; my suite ran with the Slack
  token unset.
- Mutations: 11 planted, **10 caught** (M5 survived; should-fix 2). Plants: P1 shows should-fix 1, P2 is correct, P3
  shows minor 1.

## Verdict: FAIL for 514d43ba7bfe18d99f71dae9dd9205b01d584f98

Three should-fixes: `verify` misses missing rows, the running-month rule has no test, and the README lacks the
point-in-time and session-set labels. The data itself is sound: all 4,019 rows equal Drive and the manifest, 8 months
are byte-identical to NSE today, and every number in response 100 reproduces. A re-check needs `verify.py`, one test
each for should-fixes 1 and 2, and the README; the data files should not change.

## Addendum 1 (15 Oct 2026): b377af2f676a94582596819d414c47c0163cd357 (514d43b..b377af2, response 100 addendum 1)

Two commits on top of 514d43b. They touch only `fno/vix_history/`, its tests, the story text, the README, response 100
and `checks/gaps.csv`.

### Gates

- **Exact SHA:** full history, Slack token unset: **3,251 passed**. `ruff check`, `ruff format --check` (726 files)
  and `check_imports` (736 files) are clean.
  - My first full run showed 1 error in `test_table.py`. That was my own mutation script editing the same worktree
    during the run. A clean rerun passed, and `tests/vix_history` passed alone, 57 of 57.
- **Trial merge with `origin/main` 56b9497:** merges cleanly; 3,251 passed; ruff and imports clean.

### Data unchanged

`git diff 514d43b b377af2 -- research/data/` changes only the README and `gaps.csv`:
- `gaps.csv` gains 14 rows: 9 `muhurat_session` (19 Oct 2017 to 21 Oct 2025, the calendar's 9 muhurat dates) and
  5 `special_session` (1 Feb 2020, 20 Jan 2024, 18 May 2024, 1 Feb 2025, 1 Feb 2026). That is the calendar's 6
  specials less 2 Mar 2024, which NSE's history lacks.
- The table and the manifest are byte-unchanged.
- Real `vix-history verify` against Drive, with the new walk over every manifest month: **"all 4019 days equal their
  archived month files"** (2 min 4 s).
- `vix-history check` rewrites the committed checks byte-identically (`git status` clean). It reports "2415 days
  compared (2017-01-02 to 2026-09-30): only_in_index_close 1, rounded 1488".

### Findings re-checked

| Judge 100 finding | Status | My evidence |
|---|---|---|
| Should-fix 1: `verify` misses missing rows | **MET** | My plant P1 (all of Aug 2010 deleted) now names "2010-08-02: table None, archived file (...)". My N1 (walk only the table's months) is caught |
| Should-fix 2: running month untested | **MET** | `months_to_fetch(start, end, today)` is a pure function with tests for mid-month, `--to` the running month, the month's last day and the 1st of the next. My M5 now fails 3 tests. N6 (a start before Jul 2010 kept) caught |
| Should-fix 3: known-at and session labels | **MET** | README "When a day's value was known": known after the 15:30 close, a 15:00 decision on d uses d-1 at the latest, `first_seen_at` is archive time and never a known-at time. "Which sessions the rows are": select `regular` through the A7 calendar. `gaps.csv` labels both kinds. My N3 (labels off) caught |
| Minor 1: sweep silent on a missing original | **PARTLY** | My plant P3 now prints "original MISSING from the archive, nothing compared 2010-08", and `cli.py` exits 1 on it. But my N4 (drop `not_archived` from the exit code) passes all 57 tests: the exit code is untested. Minor, see below |
| Minor 2 (A11 lookup), minor 3 (no schedule) | As agreed | Left; the README states the lane-1 rule for monthly fills |

### Self-review fixes checked

- **A damaged month could enter the table.** True at 514d43b: `VixTableBuilder._add` read the raw bytes without
  checking them against the manifest. It now stops at a month without a manifest row or with other bytes. My N2 (that
  check off) is caught.
- **A year after the calendar's last year was labelled `unverified`.** It is now `calendar_lacks_year`; my N5 is
  caught.
- **A table file without a final new line is refused rather than glued; NSE 403/429/5xx and setup failures print one
  `STOPPED` line and exit 1, with no traceback.** Read in the code.
- **My original 11 mutations re-run on the new code:** all caught. The SHA-check mutation was re-planted on the
  reworded line and is caught (2 tests fail).

**Mutations in this round:** 7 new and 11 re-run, **17 of 18 caught**. The one survivor is N4 (the sweep's exit code
on a missing original).

### The orchestrator's question: `raw_source.py:123` (HTTPError, no retry) outside A15's scope?

**Agreed, out of A15's scope.** The code is shared by every NSE dataset, so changing how it classifies and retries 403,
429 and 5xx changes A1, A10, A11, A12 and P8 as well. That is its own lane-1 A9 change, with tests across datasets.
A15 now handles the failure safely at its own edge:
- the CLI prints a named `STOPPED` line and exits 1;
- the sweep counts an `HTTPError` as no answer.

So nothing wrong is stored. Record the A9 change as an open item.

### Minor (new or remaining)

1. **The sweep's exit code is untested** (my N4). Add an assertion on `cmd_vix_history`'s return code for a missing
   original.
2. **"one-hour Diwali evening sessions"** (README) is wrong for 2025: NSE's 21 Oct 2025 muhurat ran 13:45-14:45 (the
   A7 calendar's row). Say "one-hour Diwali sessions". My judge 100 text had the same slip.
3. `build_vix_table_builder` uses a lambda with `noqa: E731`; a small named function would avoid the suppression.

**Verdict: PASS for b377af2f676a94582596819d414c47c0163cd357.** All three should-fixes are met with evidence; three
minors remain, none blocking. Merge it. After the merge I check the recomputed merge, that the branch files are
identical to b377af2, and CI.

## Addendum 2 (15 Oct 2026): merge check, A15 merged to main as 176a1a1

- **Parents.** 176a1a1's parents are db07101 (main) and b377af2 (the passed tip).
- **The merge matches my recomputation, apart from one resolved conflict.** `git merge-tree --write-tree db07101
  b377af2` conflicts only in `reviews/claude/README.md`, where both sides added index rows. 176a1a1 resolves it by
  keeping both rows. Its tree differs from the recomputed tree only by the 3 conflict-marker lines in that file.
- **Branch files arrived unchanged.** Every file the branch changed since its base e3179f0 is identical in 176a1a1 and
  b377af2 (`git diff b377af2 176a1a1 -- <branch files>`), except `reviews/claude/README.md`, which gains main's rows.
- **No unjudged change since.** From 176a1a1 to af9168f only `reviews/` files changed: judge verdicts and response
  index rows.
- **CI.** 176a1a1 was first pushed inside af9168f. Run 38669220644 (`checks`) on af9168f: **completed, success**.
- **End-to-end run (quality rule 8).** The orchestrator records `vix-history verify` on the merged tree: all 4,019
  equal, exit 0. That matches my own two runs at 514d43b and b377af2.

**Merge check: PASS.** The three minors of addendum 1 go to the builder as a follow-up. The `raw_source.py:123`
HTTPError item is recorded as a separate lane-1 A9 change.
