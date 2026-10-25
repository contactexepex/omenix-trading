# Judge 501: MS-INS part a, instructor contracts and the path reader

**Scope:** story/ms-ins-contracts at b787ca1a (builder session_01LH7m9r5TCAKgZbeHVYkiTD), one commit over `main`.
Story MS-market-school.md INS-a and "INS-a Claims". Lane 1, one judge. Round 1 of 2. Judge K
(session_019ZApRwkUiNMKDsf1k4W44z).

**Verdict: FAIL.** 2 should-fix, 4 minor. Two of the orchestrator's five checks are not met: one unreadable file
stops the whole reader, and a corrected trade is counted twice when read day by day.

## Criteria
| # | Criterion | Result | Evidence |
|---|---|---|---|
| 1 | 3-session path, snapshots in order; ticket as ticket | MET | `reader.py:58-80`; `HeldPath` refuses out-of-order or other-road snapshots; ticket-kind plant caught |
| 2 | A correction read once | PARTLY | `closed_between` applies it across separate seals (my plant keeping originals caught); `closed_on` does not (finding 2) |
| 3 | Hash mismatch is a data fault, never numbers | MET | snapshot sha, entry seal, settlement file all checked; plants caught |
| 4 | Empty session gives `()` | MET | test, and my run of the real `build_path_reader().closed_on(22 Oct)` gives `()` |
| 5 | Reads only | MET for part a | the reader calls only `find`/`read`; the dashcam fake refuses writes; the full run is e's, as stated |
| 6 | Imports | MET | school boundary test walks `fno/school/instructor/` |
| 7 | Conformance per port | MET | `test_ports` (fakes and both adapters) |
| - | Every unverifiable input a `DataFault` | NOT MET | finding 1 |
| - | `MapStatus` exactly 3 members | MET | plant adding `supported` caught |
| - | Attribution = net within Rs 0.01 | MET | tolerance 0.02, `+costs`, costs without spread: each plant caught; NaN refused |
| - | Gates | MET | see Notes |

## Findings
1. **Should-fix: one damaged sealed file crashes the reader instead of becoming a `DataFault`.**
   - `_records` and `_entry` (`reader.py:55-56`, `82-83`) call `dashcam.read`. The real store raises `StaleSeal`
     when a file holds other bytes than its seal (`dashcam/store.py:44`).
   - My run: with the held middle session's decisions file damaged, `closed_on(exit day)` raises `StaleSeal`. Every
     other path of that session is lost, and so is a 30-session `closed_between` that includes the file.
   - Expected: a damaged decisions file on an entry or held session is a fault on that path (e.g.
     `sealed_file_damaged`, or `session_not_sealed`), with a test on a fake whose `read` raises `StaleSeal`. Say in
     the story what a damaged outcomes file does (an alert, not a guess).
2. **Should-fix: `closed_on` contradicts the story, and per-day reads count a correction twice.**
   - The story (line 695) says `closed_on` reads a corrected outcome "through its latest correction". The code
     applies only corrections in the same file. Since files are write-once, a real correction is always in a later
     file.
   - My run: original sealed on day 3, correction on a later session. `closed_on(day 3)` + `closed_on(later)` gives
     nets `[-95, -96]`, while `closed_between` gives `[-96]`. The 20:05 line and any daily tally built from
     `closed_on` would count the trade twice, once with the wrong net.
   - Expected, either of:
     - `closed_on` marks or omits outcomes that are corrections of an earlier file's record;
     - the story and the docstring say `closed_on` is the raw day, and every count uses `closed_between`.
   - Either way, add a test of the per-day case.

**Minor (fix with the round), all test gaps: the code is right, the plant survives.**
- (a) `closed_between` walking only `[first, last]` survives. Add an outcome sealed mid-range.
- (b) Dropping the trading-day filter in `_path` survives. Add a muhurat-only session inside a hold
  (`is_trading_day` is false; `sessions()` still lists it).
- (c) Dropping the non-settled exit-day check (`reader.py:73`), the snapshot-id half of the snapshot match, and the
  adapter's closed-road branch each survive.
- (d) `encode_instructor_file` without `mtime=0` survives. A rerun would then write other bytes and raise
  `InstructorConflict`. Pin the bytes.

## Plants
19 planted, 13 caught. Survivors: plants 4, 9, 11, 12, 18, 19 (minors a-d).

## Notes
- **Gates (my run, python3 after routine setup):** pytest -n auto 11,744 passed, 16 xfailed. ruff check and format,
  check_imports and check_records are clean. The largest file is `contracts.py` at 224 lines.
- `closed_between` is the view as of `last`: a correction sealed after `last` is not applied. That is right for a
  review cut at `last`; worth one line in the docstring.
- The orchestrator's answers (reads beyond the dashcam, tickets in the primary measure, one judge) are recorded in
  the story, and the code keeps to them.

## Addendum 1: round 2 at a2c26465

**Verdict: PASS.** Lane 1, one judge. Scope: the single commit a2c26465. The merge of `main` before it is not part
of this judgment.

| Round-1 finding | Result | My evidence |
|---|---|---|
| SF1 damaged file crashes | ACCEPTED | My round-1 probe (held middle day's decisions file raising `StaleSeal`) now gives a path with `sealed_file_damaged`, no crash. A damaged outcomes day is listed in `ClosedRead.unreadable`. Plants caught: the catch narrowed, damaged reported as not sealed, the entry-day damaged check removed, `unreadable` emptied |
| SF2 corrections counted twice | ACCEPTED | `closed_on(d)` is `closed_between(d, d)`. An original is read on its own close day as its latest correction sealed up to today, and a correction is never a path on its own day. My probe: per day `[-96]`, range `[-96]`. Plants caught: today = last, corrections kept as paths, the chain cut to one step, the `d <= last` cut dropped |
| Minors a-d | ACCEPTED | my round-1 survivors (calendar filter, exit-day check, snapshot-id match, adapter's closed road, `mtime=0`) are all caught now |

- **Plants: 15 planted, 15 caught.**
- **Minor (no action this round):** a correction whose original exists in no readable file (its `corrects` SHA
  names nothing) is dropped silently. My run: an orphan correction gives no path, and `unreadable` is `()`. A real
  original in a damaged file is still signalled through `unreadable`. Only a malformed `corrects` vanishes. When
  INS-e lands, count orphans in `ClosedRead` or alert on them.
- **Note:** `closed_on` now reads every outcomes file from the day to today. That's fine at 30 sessions; INS-e
  should not call it in a loop over long ranges (use `closed_between`).
- **Gates (my run):** pytest -n auto 11,763 passed, 16 xfailed. ruff check and format, check_imports and
  check_records are clean. The largest file is `test_reader.py` at 331 lines.
