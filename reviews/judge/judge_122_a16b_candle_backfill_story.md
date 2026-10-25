# Judge 122: A16b story text, NIFTY 15-minute candle back-fill: `story/a16b-candle-backfill` d7bfd66a26d44ac0f6a69f3a0cb963045a68d2cc (quality rule 1, text only)

**Number:** 122, the story's claims number (`response_122`).

**What I checked:**
- the new story file, the only change from main 6320f0b;
- A16's `fno/intraday/read_only.py`;
- A17's `provenance` (`fno/global_cues/table.py:36`);
- the `growwapi` 1.5.0 wheel. I unpacked and read it, without installing or running it.

I made no live Groww or NSE read. Step 0's figures are the builder's, and I label them so.

## The orchestrator's questions

**(a) Is 3 days of 15-minute vs 1-minute equality enough? No, for two reasons (should-fix 1).**
- **The equality is structural, but only if Groww aggregates the same way in every year.** The 15-minute candle that
  starts at T-15 should close on the last trade of its last minute, which is the 1-minute close at T.
- **All 3 sampled days are in Sep-Oct 2026:** 1 Sep, 13 Oct and 14 Oct. About 95% of the back-fill is 2020-2025, where
  Groww's history may have been built from another feed or aggregation. So there is no direct evidence for the years
  that matter most. Label: some evidence for 2026, reasoning only for 2020-2025.
- **Criterion 5's re-check has no consequence.** It reads 5 sessions "spread over the range" and only prints how many
  marks are equal. A mismatch would still let every row be written as A16's levels.
- **Cost of checking.** The builder measured about 0.8 s per one-day 1-minute read, so all 1,680 sessions would take
  about 22 minutes and 1,680 calls. A per-session check therefore costs the same as a 1-minute back-fill. That is why a
  stratified sample with a stop rule is the right middle (reasoning only).

**(b) Which direction voids, and is the 23 Mar 2020 error caught? Not guaranteed as written (should-fix 2).**
- **What voids as written:** one of the 26 *levels* (the 09:15 open and the 25 closes) lying below NSE's low − 0.05 or
  above NSE's high + 0.05.
- **Groww's range inside NSE's:** it never voids. That is right: 12-14 of 40 sessions are that kind, and the two "NSE
  low = pre-open open" sessions are inside too.
- **23 Mar 2020 was a candle *high* 196.30 points above NSE's high.** A spike inside a candle need not move that
  candle's open or close. So the levels-only check can pass a session whose candles hold a value NSE says never
  happened. That session is void anyway (23 candles), but the same error on a full session would pass. It would show
  only as a negative `nse_high_gap`.
- **The story's own principle** is "a level NSE says never happened cannot be used". Data whose high is impossible is
  not trustworthy for its closes either.
- **Cost of voiding on it, from step 0's sample:** 0 of 40 sessions apart from 23 Mar 2020 had Groww's high or low
  outside NSE's range. So it is cheap (some evidence, 40 sessions).

**(c) Is one allow-list constant really no new call surface? YES.**
- `CANDLE_INTERVAL_MIN_15 = "15minute"` is a plain string attribute of `GrowwAPI` (`growwapi/groww/client.py:91`, beside
  `CANDLE_INTERVAL_MIN_1 = "1minute"` at :86).
- `get_historical_candles` is already in `READ_CALLS` (`read_only.py:15`). Adding the name to `CONSTANTS` lets one more
  string through `__getattr__` and no callable.
- Criterion 10 also pins "exactly one constant".

**(d) Rule 5 cases: mostly covered, with named gaps (minor 1, and should-fix 3 for the ordering).**
- **Covered:**
  - muhurat is ignored (criterion 3);
  - 10 Oct 2025 with no candles gets a void row `missing_candles:25` (criterion 3);
  - one missing candle (criterion 2);
  - the 09:15 and 15:15 boundaries;
  - an empty answer;
  - 0.05 / 0.06 at the NSE check;
  - the provenance boundary 09:14:59 / 09:15:00.
- **Not named:**
  - the two halt days, 13 and 23 Mar 2020 (23 candles);
  - 24 Feb 2021: 5 candles, and NSE extended trading to 17:00 that day, which is likely the "few after 16:00 on one
    day";
  - the 2024 short specials, 2 Mar and 18 May (10 candles each);
  - the session after 10 Oct 2025, whose previous close does not exist.
- **Should-fix 3 (ordering).** "The run goes on to the next window" (criterion 1) plus "the row is written once"
  (criterion 4) gives a real defect.
  - If window *n* fails, the first session of window *n+1* has no previous session derived yet. It is written once with
    a void overnight part.
  - When window *n* is fetched on the rerun, that row's inputs change. The rerun then either keeps a wrong void, or is
    refused as "different inputs".
  - A transient Groww failure would permanently damage a row.

**(e) Provenance and labelling: SOUND, with two points to pin (minors 2 and 3).**
- **A17's rule matches.** `live` when first seen before 09:15 IST of the first NSE session after the row's session, else
  `backfilled`. That equals `provenance()` in `fno/global_cues/table.py:36-39`.
- **`first_seen_at` is the raw copy's fetch time.** A later re-fetch with other bytes keeps the first version (A11's rule
  as A17 applies it). That is right.
- **`measure = candle_close` and `method = rv-candle-15m-v1`.** These keep the series apart from A16's quote-snapshot
  measure. Criterion 11 keeps the files apart.
- **"Never counts as a live forecast" is delegated to G6.** That is reasonable, since G6 owns the forecast label. But it
  says nowhere that G6 has been told. See minor 3.

## Other checks

- **The A16 finding is correct by construction.** NSE's official open is the pre-open auction price. The 09:15
  1-minute open is the first trade after it, so A16's "report every difference above 0.05" fires on every session.
  It is rightly kept out of this story; see minor 4.
- **The gaps are differences, as A16 set the precedent.** `nse_high_gap` plus NSE's public high gives Groww's maximum
  candle high, which is close to the public index level. It is the same kind of derived figure A16's open difference
  publishes (judge 108). Note only.
- **The orchestrator's conditions are respected:**
  - raw to Drive only;
  - written once;
  - nothing over A16's files;
  - its own composition root;
  - no scheduled task.
- **Rule 9 is stated, not skipped:** no money path.

## Should-fix (text)

1. **The equality evidence and its stop rule.** Replace criterion 5's 5-session print with a stratified re-check that
   has a consequence. For example:
   - at least 2 sessions per calendar year 2020-2026 (14 or more), plus every special session and the sessions next to
     the 8 holes;
   - every mark compared, 15-minute close against 1-minute close;
   - any mark differing by more than 0.05: that year's rows are not written, every differing session is named, and the
     run exits 1. The owner decides then.

   The orchestrator may instead choose a per-session check, about 22 min and 1,680 calls by the builder's own rate,
   voiding a session on mismatch. Either is acceptable; the choice and its reason go in the story. Also say in step 0
   that the 3 days are all 2026.
2. **Void on a candle high or low outside NSE's range.** Extend `outside_nse_range` to any of the 25 used candles'
   **high** above NSE's high + 0.05 or **low** below NSE's low − 0.05, not only the 26 levels. Add a test shaped like
   23 Mar 2020: a full session whose closes are inside NSE's range but one candle's high is 196.30 above, which must
   void. State the cost from step 0 (0 of 40 besides 23 Mar 2020).
   - Or keep levels-only, with a stated reason and the gap reported loudly. But then the story's own principle reads
     wrong.
3. **Order-dependent rows after a failed window.** A session whose previous recorded session has no derived row in this
   run, or before it, must not be written. It is deferred, and the run exits 1 naming it. The exception is a previous
   session that exists with a void 15:30 level, such as 10 Oct 2025, which gives a void overnight part. Tests:
   - a failed middle window, then a resume: the next session's overnight part is computed and nothing is refused;
   - the session after 10 Oct 2025: overnight void, intraday computed.

## Minor (text)

1. Name these rule-5 cases with their expected rows:
   - 13 and 23 Mar 2020 (23 candles);
   - 24 Feb 2021 (5 candles, and its candles after 15:30 are not levels and are counted in `outside_candles`);
   - 2 Mar and 18 May 2024 (10 candles each). Also say whether such structurally short specials count in criterion 7's
     5% void share or are shown apart;
   - 26 Sep 2025 (22) and 29 Sep 2026 (20): unexplained holes. Say whether NSE had a disruption, or that they are
     Groww's holes.
2. **Provenance: one function.** Compute `provenance` with A17's function, not a copy (DRY). If it must move to a
   shared module for both packages, say where, and keep A17's verify using it.
3. **"Never a live forecast":** name where G6 is told: a line in G6's story open questions, or a decision row. Then the
   condition does not live only in this story's "Out".
4. **A16's NSE-open finding:** name where it was reported, a decision or claims row, so it reaches A16's owner and
   judge.
5. **A 90-day window's answer:** if Groww truncates or caps an answer, the per-session `missing_candles` void catches it.
   Say so, and print each window's candle count against the expected 25 × sessions, so a cap shows as one line, not as
   scattered voids.

## Verdict: FAIL for d7bfd66a26d44ac0f6a69f3a0cb963045a68d2cc (story text)

- **What is sound:**
  - the scope, the separation from A16, the Drive-only raw data and the write-once table;
  - the provenance rule (equal to A17's);
  - the allow-list change, which is verified as a plain string constant with no new call.
- **Three should-fix, all text:**
  - the equality evidence covers 2026 only, and its re-check has no consequence;
  - the 23 Mar 2020 kind of error is not guaranteed to void;
  - a failed window can permanently damage the next session's row.
- **A re-check needs only the story file.**

## Addendum 1 (15 Oct 2026): a correction to my own text

**I withdraw "The A16 finding is correct by construction"** (section "Other checks").
- **What I said.** I wrote that A16's NSE-open condition "fires on every session". My only grounds were step 0's "40 of
  40" and the mechanism, not my own data.
- **Contrary evidence.** The orchestrator reports that the A16 builder's 6-session check found the 09:15 open equal to
  NSE's open on 2 of 6 sessions. The 09:14 pre-open close matched on 6 of 6.
- **Why the mechanism does not settle it.** The first trade after the auction can equal the auction price, so "every
  session" does not follow from it.

**Status of step 0's claims:**
- "differs on 40 of 40" and "fires on every session": **unverified, conflicting evidence**;
- "the pre-open close equals NSE's open": consistent in both samples, 40 of 40 and 6 of 6 (some evidence).

**What changes:**
- **Minor 4 now also asks** that step 0's open counts be rechecked and corrected, with the session list, before the
  re-check. The A16 report must state the reproduced figure, not 40/40.
- **The verdict is unchanged: FAIL.** None of the three should-fix findings depends on that count, because A16b's void
  rule does not use the 09:15-vs-NSE open.

## Addendum 2 (15 Oct 2026): revision at d7894440d8d3d7f466da676ffc701864594c7b00 (d7bfd66..d789444, story file only)

| Judge 122 finding | Status | Check |
|---|---|---|
| SF1: equality evidence and its stop rule | **MET (decision 55)** | Every session with 25 candles is checked against its own 1-minute candles at all 26 marks. A difference above 0.05 voids the session (`candle_mismatch:<marks>`). There is never a fall-back. Paced: one call at a time, at least 0.5 s between starts; 3 failures in a row stop the run. Tests at 0.05 / 0.06, empty, a missing minute, pacing. Step 0 now says the 3 days are all 2026 |
| SF2: candle high and low against NSE's range | MET | The void covers the 26 levels and the 25 used candles' highs and lows. There is a 23 Mar 2020-shaped test. The cost, 0 of 40, is stated (some evidence) |
| SF3: order after a failed window | MET as written, **but see new should-fix 1** | Deferred, named, exit 1. The session after 10 Oct 2025 gets a void overnight part and a computed intraday part. There is a test of a failed middle window then a resume |
| Minor 1: named cases | MET | Halt days, 24 Feb 2021, the 2024 specials, the two Groww holes and 10 Oct 2025, each with its expected `missing_candles:n`. The void share counts the short sessions and also lists them apart |
| Minor 2: one provenance function | MET (text) | `provenance()` moves to `fno/provenance.py`, and A17's table and verify import it. `global_cues/table.py` is in no freeze (I searched the manifests and JUDGE.md). In the code round I check that it is a pure move (the same body, A17's tests unchanged and green) and plant one mutation in the moved function that both A17's and A16b's tests must catch |
| Minor 3: G6 told | MET | Decision row 56 in response 113, plus an open item in response 122. I check that both exist in the code round |
| Minor 4: A16's NSE-open finding | MET | Recounted: 67 of 74 recent sessions differ, 7 within 0.05. The random sample was 40 of 40. The 40/40 is now limited to its sample and the correction is stated. The finding is recorded as decision 53, with the fix in A16d (judge D). This also settles my addendum 1 |
| Minor 5: per-window count | MET | Each window prints its candle count against 25 × sessions. Tested with a window one candle short |

**The orchestrator's question: are the 26 Sep 2025 and 29 Sep 2026 holes adequately marked as Groww's? YES.**
- They are labelled "reasoning only" with the evidence given: NSE's normal index-close file exists for both days, and
  the calendar has no disruption.
- The label is right. A normal close file does not by itself rule out an NSE trading interruption, so it is not strong
  evidence.
- Both sessions are void either way, so the label changes no row.

## New should-fix (text)

1. **A transient failure and a permanent absence are treated alike, and one of them blocks the series forever.**
   - **The cascade.** A session whose 1-minute answer arrives but lacks a needed minute is "not written ... `no_1m_check`,
     exit 1". By the Order rule, the next session is then deferred, because its previous session has no row. The one
     after that is deferred too, and so on.
     - If Groww simply has no such minute, a permanent 1-minute hole, every later run fetches the same answer, never
       writes that session, and defers **every session after it**.
     - The back-fill can never get past the first such hole, and every run exits 1 for ever.
     - Groww does have holes: the 15-minute holes of 26 Sep 2025 and 29 Sep 2026. So a 1-minute hole on a day with all
       25 15-minute candles is plausible (reasoning only; not measured).
   - **The same class in the NSE check.** "NSE's file missing **or unreadable**: void `nse_unchecked`" writes a
     write-once void row on what may be a transient Drive read error. When Drive recovers, the inputs differ and the row
     is refused. That is the very defect should-fix 3 removed for Groww windows.
   - **Expected fix:** separate the two cases.
     - **Transient** (a call or read failed, no answer): not written, deferred, exit 1, retried next run.
     - **Permanent** (an answer was received and archived, but the data is not there: the 1-minute answer lacks the
       minute, or NSE's archive has no file for that day): a **void row**, `no_1m_check` or `nse_unchecked`. It is
       written once, named, and listed apart. The next session then gets a void overnight part, as after 10 Oct 2025.
       This is still never a fall-back: the session is void, not trusted.
   - **Tests:**
     - a 1-minute answer missing one needed minute: void row, and the next session is written with a void overnight
       part;
     - a failing 1-minute call: deferred, then written on resume;
     - an NSE file absent: void row;
     - an NSE read error: deferred.

## Minor (text)

1. Name where `NseSessionCalendar.next_open` comes from for A16b. It lives in `fno/global_cues/cue_calendars.py`. Say
   whether A16b imports it from there or it moves beside `provenance()`, so the intraday package does not depend on the
   global-cues package for a calendar.

### Verdict: FAIL for d7894440d8d3d7f466da676ffc701864594c7b00 (story text)

- **All 3 earlier should-fix and all 5 minors are met.**
- **One new should-fix:** separating transient from permanent outcomes. It was caused by combining the new 1-minute
  check with the new Order rule, and it would stop the back-fill at the first permanent 1-minute hole.
- **A re-check needs only the story file.**

## Addendum 3 (15 Oct 2026): final SHA 3e8e6c90222f60c59de2ec83304284ee3c858d08 (d789444..3e8e6c9: two commits, story file only)

**What changed:**
- **A16d's wording, "the last pre-open 1-minute candle's close",** in step 0, the NSE check and criterion 5. The
  pre-open check now reads from the session's 1-minute answer, not the 09:00 15-minute candle. That is consistent with
  step 0, which compared the 1-minute pre-open close: 40 of 40 and 74 of 74.
- **Decision 56 cited in the gap list.** It is on `main`, `response_113` line 67: "rows with provenance backfilled never
  count as live forecast inputs, and G6's text must carry this". Minor 3 is now verified, not only stated.

**New minor 2.** Sessions void before the 1-minute check (fewer than 25 candles) have no 1-minute answer, so their
`nse_open_gap` cannot be computed. Say that it is blank there, and that the "pre-open gap above 0.05" count is over
the checked sessions only.

**Not changed:** addendum 2's new should-fix 1, transient against permanent outcomes. The text still says:
- a 1-minute answer lacking a needed minute is "not written ... exit 1", which with the Order rule defers every later
  session;
- "NSE's file missing or unreadable" gives a write-once `nse_unchecked` void.

### Verdict: FAIL for 3e8e6c90222f60c59de2ec83304284ee3c858d08 (story text)

- Same single should-fix as addendum 2.
- Minors: addendum 2's minor 1 (`next_open`'s home) and minor 2 above.

## Addendum 4 (15 Oct 2026): revision at 1c9c5c3c7c8359c9d5cad5f9559f36431096ed5a (3e8e6c9..1c9c5c3, story file only)

| Finding | Status | Check |
|---|---|---|
| Addendum 2 should-fix 1: transient against permanent | **MET** | A new "Transient or permanent" definition (detailed below). Criterion 5 has four tests, each with its outcome: a Groww error on the 1-minute call defers and is then written; a missing minute gives a void row and a next session with a void overnight part; a Drive read error or NSE `RawSourceUnavailable` defers; no copy plus 404 gives a void row and a next session with a void overnight part |
| Addendum 2 minor 1: `next_open`'s home | MET | `provenance()` from `fno/global_cues/table.py` and `NseSessionCalendar.next_open` from `fno/global_cues/cue_calendars.py`, imported, not moved or copied. A17's files are unchanged (the earlier move is withdrawn), so there is no A17 code change to check in the code round. The intraday package then depends on `global_cues` for these two names. That is acceptable, and stated |
| Addendum 3 minor 2: `nse_open_gap` with no 1-minute answer | **NOT IN THE TEXT** | No line says that the gap is blank for sessions void before the 1-minute check, or that the pre-open count covers checked sessions only. Carried to the code round as a minor: the claims must state it and a test must show it |

**The "Transient or permanent" definition:**
- **Transient, deferred:** a Groww error or timeout, an unreadable answer, a Drive read error, or NSE's
  `RawSourceUnavailable`. It is deferred, no row is written, and the run exits 1.
- **Permanent, a void row:** the answer was received and archived but the data is absent. That is `no_1m_check`,
  `missing_candles`, or `nse_unchecked`.
- **"No NSE file" is definitive only** when Drive has no copy **and** NSE answers 404. That is A9b's `RawFile(None)`,
  so it is consistent with the policy merged in 16661ec.
- **The permanent 1-minute hole** now gives a void row, so the Order rule no longer blocks the rest of the series.

**Residual risk (note, not a finding).** A day that Groww refuses with an *error* every time, rather than answering
empty, would stay deferred and block the sessions after it. It is visible: named, with exit 1, on every run. Step 0
saw Groww answer empty for a no-data day (10 Oct 2025, 0 candles), not with an error. So this is reasoning only, and
the owner would see it at once.

### Verdict: PASS for 1c9c5c3c7c8359c9d5cad5f9559f36431096ed5a (story text)

- No blocking or should-fix finding is left.
- **Carried to the code round:**
  - minor 2 (the open gap blank, and the count over checked sessions);
  - the four transient/permanent tests;
  - the 23 Mar 2020-shaped high test;
  - the deferral resume test;
  - JUDGE's planted mutations: the 09:15 open against the close, the 25-candle set, the 0.05 tolerance, the provenance
    boundary, the void rule, and transient against permanent.
- **Rule 9:** none needed, no money path. Code may start.

## Addendum 5 (15 Oct 2026): final SHA 1109296a491a21e48de616de22cf8b3bc8c5b1be (1c9c5c3..1109296, story file only, 5 lines)

| Finding | Status | Check |
|---|---|---|
| Addendum 3 minor 2: `nse_open_gap` with no 1-minute answer | MET | Sessions void before the 1-minute check (`missing_candles`) have a blank `nse_open_gap`. The pre-open count covers sessions that had a 1-minute answer, and its line prints how many there were. A test is named |

Nothing else changed.

### Verdict: PASS for 1109296a491a21e48de616de22cf8b3bc8c5b1be (story text)

- **No minor is left from the text rounds.**
- **Carried to the code round, as in addendum 4:** the tests and the planted mutations.

## Addendum 6 (15 Oct 2026): A16b code at 305e1f1b64869e11f0a3aeee5f11e0fa3bd77780 (merge-base 0a1cfa9; claims: `response_122_a16b-candle-backfill.md`)

**Gates, run myself on the exact SHA (main merged in):**
- `env -u FNO_SLACK_BOT_TOKEN python -m pytest -q`: 4740 passed;
- `ruff check fno tests tools`: clean; `ruff format --check fno tests tools`: clean (902 files);
- `python tools/check_imports.py`: clean.
- A16b's own tests: 86. A16 (`tests/intraday`): 180. A17 (`tests/global_cues`): 98.

**Live reads.** I made no live Groww read: I hold no Groww credentials, and none may be put in a file or chat. The live
evidence is the builder's two dry runs (Q1 2020 and all of 2020) and its read-only search for where the 1-minute
history starts. I mark these as the builder's evidence.

### Text change since my PASS at 1109296: decision 62, "Incomplete sessions too": SOUND

- **What it adds.** A session with some but not all candles is also checked on its present marks, and any failed mark
  makes its levels untrusted. This is stricter than 1109296, where a partial session skipped the check: no level is
  now used unchecked.
- **The code matches.**
  - `check_minutes` skips only absent levels.
  - `derive` trusts only `missing_candles`.
  - `last_level` gives `None` for untrusted rows, so the next session's overnight part is void.
- **Tests.** Four named tests exist, and J10 is caught.
- **The `nse_open_gap` sentence** ("blank only for a session with no candle") is consistent with it.

### The A16 files changed beyond the allow-list constant: BEHAVIOUR-NEUTRAL (verified)

| File | Change | Check |
|---|---|---|
| `realised_vol.py` | `QuoteSnapshotRv15m.compute`'s body moved, unchanged, into `session_rv()`; `CandleCloseRv15m` calls it | Diff read line by line. **J9** (overnight from `levels[1]`) fails A16's 2 and A16b's 2 tests. **J9b** (intraday without the first level) fails A16's 2 and A16b's 1 |
| `rv_table.py` | Class attributes `fields`/`file_name`/`pattern` default to A16's constants; `row(day)` split out of `write_once`, the same comparison | Diff read; A16's 180 tests pass |
| `session_rv.py` | `_figure` renamed `figure`; a local `figure` renamed `shown` | Rename only |
| `cli.py`, `dry_run.py` | `_inside_repository` moved to `dry_run.inside_repository`, the same body; the backfill subcommands added | Diff read |
| `test_safety.py` | `backfill_wiring.py` allowed as a composition root | It is on CLAUDE.md's list (the branch adds it) |
| `read_only.py` | `CANDLE_INTERVAL_MIN_15` only | Plain string `"15minute"` (judge 122, question c) |

A16's `wiring.py` and all of `fno/global_cues/` are unchanged against the merge-base.

### Addendum 4's list

| Item | Status | Evidence |
|---|---|---|
| The four transient/permanent tests | MET | `test_a_groww_error_on_the_1_minute_call_defers_and_the_next_run_writes_it`, `test_a_received_1_minute_answer_missing_a_minute_is_a_void_row`, `test_a_failed_nse_read_defers`, `test_nse_s_definitive_absence_is_a_void_row`. **J6** (a failed NSE read treated as absent) is caught, 5 failed |
| The 23 Mar 2020 high test | MET | `test_one_high_19630_above_nse_voids_although_every_close_is_inside`. **J3b** (range on levels only) is caught, 2 failed |
| The deferral resume | MET | `test_a_failed_middle_window_defers_then_resumes_without_a_refusal`. **J8** (no deferral without a previous row) is caught, 5 failed |
| The open gap blank / checked-sessions count | MET | `_gap`; the report line "of N sessions with a 1-minute answer" |

### Planted mutations (separate worktree; A16, A16b and A17 suites each run): 18 of 19 caught

| # | Mutation | A16b (A16 / A17) |
|---|---|---|
| J1 | 09:15 open → close | 24 failed |
| J2 | `used` = every candle of the day (pre-open, 15:30 and later) | 32 failed |
| J3 | tolerance 0.06 | 5 failed |
| J3b | NSE range on levels only | 2 failed |
| J4 | provenance boundary `<` → `<=` in A17's shared function | 4 failed (A17: 2 failed) |
| J5 | `nse_unchecked` trusted for the next overnight | 1 failed |
| J6 | a failed NSE read becomes "absent" (transient → permanent) | 5 failed |
| J7 | a 404 counts at once (21:00 rule off) | 1 failed |
| J8 | no deferral without a previous row | 5 failed |
| J9 / J9b | shared `session_rv` overnight / intraday | 2 / 1 failed (A16: 2 / 2 failed) |
| J10 | incomplete sessions not checked (decision 62) | 3 failed |
| J12 | stop after 4 failures, not 3 | 1 failed |
| **J13** | **pacing 0.4 s, not 0.5** | **survived** (minor 1) |
| J14 | the first version not kept | 1 failed |
| J15 | a missing minute ignored | 2 failed |
| J16 | untrusted levels computed | 4 failed |
| J17 | an unreadable answer archived | 1 failed |
| J18 | `first_seen_at` = earliest copy, not latest | 1 failed |

### Self-review fixes M1-M3: MET

- **M1.** The row and the previous close now come from the same kept copy: `PreviousClose.of` reads the previous
  row's own `copy_15m`. J14 is caught.
- **M2.** Identical bytes keep their first manifest row and fetch time (`CandleArchive.save`).
  `test_a_rerun_after_a_deferral_keeps_the_first_fetch_time_and_verifies` covers it.
- **M3, the 21:00 rule.** NSE's 404 counts as absent only from 21:00 IST on the day after the session (`nse_final`).
  Before that the session is deferred, with the "not published yet" reason. This matches the repository's 21:00
  archive time (A13) and the CLI's `latest_finished` (today only from 21:00). It is the safe side: a late file is never
  mistaken for no file. `test_nse_s_404_defers_until_the_file_is_final_then_voids` covers it, and J7 is caught.

### Is `backfill-verify` truly read-only? YES

- `build_candle_verifier` builds no Groww object.
- Its NSE library has `archive_to=None`, so `RawFileLibrary.get` never calls `put` (`raw_library.py`).
- `CandleArchive.load` only `get`s.
- The verifier writes no table row and no deferral row; `_verify` only prints.
- `test_the_verifier_is_built_without_groww_and_archives_nothing` covers it.

### Claims against reality

- **Criterion 14 (the real run): NOT MET at this SHA.**
  - The story says: "The claims show the full back-fill, 1 Jan 2020 to the latest finished session, as counts".
  - The claims show a dry run of 2020 only: 251 of about 1,680 sessions, 15%.
  - The full run is deferred to "after the PASS and merge, under owner rule 1 B". But the owner's "1 B" (DESK_DECISIONS
    15 Oct) says only that builders run their own commands. It says nothing about running after the merge.
  - A **dry run** of the full range writes nothing to Drive or the repository, as the 2020 one showed. So it can be
    made before the merge.
  - **Why it matters.** Rows are written once. A defect that only 2021-2026 data shows would be fixed into the real
    series on the first real run, and could then only be corrected by a new method version. Such data includes:
    - the 15:45 candles from 2025;
    - 24 Feb 2021's extended session;
    - the 2024 specials;
    - the 26 Sep 2025 and 29 Sep 2026 holes;
    - any era of 1-minute mismatches.
  - The void share for 2021-2026 is unmeasured.
- **Every other claim checked against the diff holds:**
  - the 4740 / 86 counts reproduce;
  - "A16's wiring.py and global_cues unchanged" is true;
  - the decision-62 tests exist.

### Hunt for unclaimed bugs (none blocking)

- **Note.** An NSE file present but without a NIFTY 50 row raises `ValueError`. That is transient, so the session is
  deferred on every run. This is consistent with the story ("an unreadable answer is transient"), and it is visible in
  `deferred.csv` with a count of runs.
- **Ordering.** The 15-minute window, then the 1-minute copy, then NSE: the 1-minute copy is archived even when NSE
  then defers. That is harmless: the same bytes keep their first row and first fetch time (M2).
- **Secrets.** Errors are named by class only (`CandleCallFailed`, the CLI's `except Exception`). The planted-secret
  test covers it.

## Findings

**Should-fix 1: criterion 14's evidence.**
- **Evidence:** the claims' "Not yet done: the full back-fill run (criterion 14)"; the story's criterion 14; DESK_DECISIONS
  "1 B".
- **Expected fix, one of:**
  - **(A) recommended.** The builder runs `intraday backfill --dry-run <folder>` over 1 Jan 2020 to the latest finished
    session, plus verify over that folder, and adds the counts to the claims: windows, calls, sessions, ok, void by
    reason, void share, provenance, pre-open gaps, verify. Never a level. About 23 min of 15-minute calls plus about
    1,700 one-minute checks at 2 a second, by the builder's own rate. Rule 8 then repeats it for real after the merge.
  - **(B)** The orchestrator changes criterion 14 to say the full run comes after the merge, with a stated reason. That
    is a lane-1 text change, and I re-check it. I would accept it only with a reason, given the write-once risk above.

**Minor 1.** The pacing test checks against `MIN_GAP_SECONDS` itself, so changing the constant to 0.4 passes (J13).
Pin the story's figure: assert `MIN_GAP_SECONDS == 0.5`, or measure gaps of at least 0.5 directly.

### Verdict: FAIL for 305e1f1b64869e11f0a3aeee5f11e0fa3bd77780

- **One should-fix:** the full-range run in the claims (A), or a reasoned text change (B).
- **The code itself is sound.** Everything else is met: the gates, the 18 caught mutations, behaviour-neutral A16
  changes, transient against permanent, read-only verify, M1-M3, and decision 62.
- **A re-check after (A)** needs only the claims' new counts and minor 1's one-line test change. I re-run the gates
  only if code changes.

## Addendum 7 (15 Oct 2026): criterion-14 re-check at 497ffaf9 (305e1f1..497ffaf: builder commit 5b383cd, claims only, then a merge of main)

**What changed.**
- **The builder's own commit, 5b383cd:** `response_122` and the claims README only. No code or test change.
- **The merge of main:** it brought main's code in, and none of it touches A16b's files.

**Gates.** I made a trial merge of 497ffaf with origin/main as of now (5d61e34). It has no conflict apart from the claims
README, which merged automatically.
- `env -u FNO_SLACK_BOT_TOKEN python -m pytest -q`: **5240 passed**;
- `ruff check fno tests tools`: clean;
- `ruff format --check fno tests tools`: clean;
- `python tools/check_imports.py`: clean.

| Addendum 6 finding | Status | Check |
|---|---|---|
| Should-fix 1: criterion 14's full-range run | **MET** | Live, read-only dry run of 1 Jan 2020 to 14 Oct 2026: 29 windows, 1,679 one-minute calls, 1,680 sessions, 1,661 ok and 19 void (1.1%), 0 deferred, 0 CHANGED, 1,680 backfilled. Verify: 1,680 of 1,680 equal, exit 0. Builder's live evidence: I hold no Groww credentials. Checked below for internal consistency and against committed data |
| Minor 1: pin 0.5 in the pacing test (J13) | **Not done** | The pacing test still compares with `MIN_GAP_SECONDS` itself. Under the owner's 15 Oct rule, a pacing constant changes no signal, trade or stop, so this stays a one-line note: a later change of the constant would show in review, not in a test |

**Checks of the new counts:**
- **Internally consistent.**
  - The 19-row table gives `missing_candles` 8, `no_1m_check` 8, `no_previous_close` 10 and `outside_nse_range` 5, as
    the reason line says.
  - By year: 2020 5, 2021 2, 2022 2, 2023 0, 2024 4, 2025 4, 2026 2, which sums to 19.
  - Each `no_previous_close` row is the session after a void day, or 1 Jan 2020.
  - The 1,679 one-minute calls are 1,680 sessions less 10 Oct 2025, which has no candle.
- **Against the committed A7 calendar (`research/data/calendar/nse_sessions.csv`):**
  - 2 Mar and 18 May 2024 are the DR-drill specials (F&O 09:15-10:00 plus 11:30-12:30), which fits 10 of 25 candles.
  - 20 Jan 2024 is a full Saturday special.
  - 1 Feb 2025 and 1 Feb 2026 are the budget sessions with normal timings, which fits all 26 levels being ok.
  - 20 May 2024 is a holiday, so 21 May follows 18 May.
  - 10 Oct 2025 is not a holiday, so it is a regular session with no Groww candle: Groww's hole.
- **The full run earned its cost.** 7 Mar 2022 is a full session whose Groww high is 251.60 above NSE's, with 2 needed
  minutes missing. It is caught by the candle-high rule (judge 122 should-fix 2) and voided. The 2020-only sample could
  not have shown it, and a write-once row would otherwise have carried it.
- **The 15:45 candles** come from 6 May 2025 on, plus 24 Feb 2021 to 17:00, 28 Jun 2021 and 1 Dec 2023. They are all
  counted in `outside_candles` and are never levels (criterion 2).
- **Observation (note).** On 106 ok sessions, NSE's high or low lies beyond every Groww candle, by up to 91.95 points,
  mostly in 2025-2026 (40 and 30 sessions). The closes pass the 1-minute check, and the realised variance uses closes
  only, so no realised-variance figure, signal or trade changes. The gap is recorded per row (`nse_high_gap`,
  `nse_low_gap`). Anyone later using Groww's highs or lows should read those columns first.

### Verdict: PASS for 497ffaf9 (A16b code and claims)

- **No should-fix left.** Criterion 14 is met by the full-range dry run, and every other criterion was met in addendum
  6 (the code is unchanged).
- **Notes:** minor 1 (the pacing pin), and the 106-session high/low observation.
- **Rule 8, after the merge:** the real `backfill` of the full range, then `backfill-verify`. Its counts must equal this
  dry run's, or show any difference as CHANGED lines. I check that in the merge check.

## Addendum 8 (15 Oct 2026, judge D): rule 8 for A16b, the real back-fill on `main` (1d68c447)

**Criterion 14 / rule 8: MET.** The real run equals addendum 7's dry run in every count.

**Counts, from the committed files (my own count of `research/data/intraday/rv-candle/`).**
- 1,680 files and 1,680 rows: 1,661 `ok` and 19 `void`. Every row has provenance `backfilled`.
- Void reasons: `no_previous_close` 10, `missing_candles` 8, `no_1m_check` 8, `outside_nse_range` 5.
- Voids by year: 2020 5, 2021 2, 2022 2, 2024 4, 2025 4, 2026 2.
- All identical to addendum 7. 7 Mar 2022 is again void with `nse_high_gap` -251.60.

**The manifests in the same commit.** `groww-candles/nifty-15m.csv` has 28 windows and `nifty-1m.csv` 1,680 days.
- The builder says the dry run showed 29 windows because it resumed from a 2020-only folder. That explains the only
  field difference reported (`copy_15m` on 28-31 Dec 2020): the same candles, cut into a different window file.
- The 1-minute copies are content-addressed, so they cannot differ silently.

**Drive copies, my own read-only check with this session's Drive credentials.**
- 4 of the 28 15-minute windows (first, 2022, 2024, last) and 8 random 1-minute days: each file read from Drive has
  the SHA-256 and size of its manifest row. 12 of 12 match.
- My full `python -m fno intraday backfill-verify` run did not finish inside my 25-minute limit, with no output by
  then. So the full-verify result ("every candle-close row equals its Drive copies", exit 0) is the builder's, from
  main. I checked the sample above in its place.

**Notes carried over (not findings).**
- Minor 1, the pacing pin, is still undone.
- Groww's highs and lows lie beyond NSE's on 106 ok sessions; read `nse_high_gap` / `nse_low_gap` before using them.
- These rows are `backfilled` and never live inputs (decision 56). G7 reads only `rv/`, as checked in judge 127.
