# Judge 116: A17b story text, guards before any consumer reads a global cue: `story/a17b-cue-guards` ba95c561e0b841f3fb99758d0951bdd854548923 (quality rule 1, text only)

**What I checked:**
- The A17b section of `docs/stories/A-data-foundation.md` at this SHA, the only file changed.
- It against my judge 103 minors 1-5, judge 100's A15 minors and the orchestrator's design points.
- The US 10-year table's dates, against the stock-market calendar the story proposes.

## What is right

- **Coverage of the findings.** Every judge 103 minor (1, 3, 4, 5) and judge 100 minor maps to a scope item and a
  criterion. FBIL stays an owner item, recorded.
- **The shape of a reading.** `reading_for` returns a status, an age and an expected date. Callers must refuse `stale`
  and `none`, and a `behind` must be stated in a caller's own rules. That is the right contract, and `value_for` stays
  unchanged for research.
- **The 4-day US limit.** It covers a Monday holiday (Friday's close read on Tuesday) and Good Friday (Thursday's
  close read on Monday).
- **Muhurat in the label.** Muhurat is not an open, and every committed row stays `backfilled`, so no past label
  changes.
- **`adopt`.** It cross-checks Drive's creation time within 10 minutes, refuses when the store cannot give it, and
  does one real check on the four copies.
- **Failed attempts capped at 3 a day,** with times and outcomes only in the log.
- **The unscheduled NYSE closures listed** (2 Jan 2007, 29-30 Oct 2012, 5 Dec 2018, 9 Jan 2025) are the ones I know
  of since 2007. Each must carry its source, as the story says.

## Should-fix (text)

1. **The US 10-year is not on the NYSE calendar.** The story gives the S&P 500, the Nasdaq 100 *and* the US 10-year
   their expected date from NYSE rules. The Treasury follows the bond market (SIFMA) calendar instead. The committed
   `us10y.csv` shows the difference both ways:
   - **No value on days NYSE trades:** Columbus Day (14 Oct 2024, 13 Oct 2025) and Veterans Day (11 Nov 2024,
     11 Nov 2025).
   - **A value on days NYSE was closed:**
     - Good Friday 3 Apr 2015, 2 Apr 2021 and 7 Apr 2023;
     - 29 Oct 2012 (Hurricane Sandy, day 1);
     - 2 Jan 2007 (President Ford);
     - 9 Jan 2025 (President Carter).

   So the US 10-year would read `behind` after every Columbus and Veterans Day, and on those Good Fridays its value is
   *newer* than the NYSE expected date. Fix: give the US 10-year its own calendar (SIFMA's recommended closes, sourced),
   or treat it like USD/INR, a stated simplification that can only read `behind`. Check its archived dates against
   whichever calendar it uses.
2. **The statuses overlap, and one case has no status.**
   - **`current` vs `stale`.** "`current`: the value is the expected date's" and "`stale`: older than `max_age_days`"
     can both hold. After Hurricane Sandy, Friday 26 Oct's close is the expected value on Wednesday 31 Oct, at
     **5 days**, above the 4-day limit. After Ford's mourning day, 29 Dec 2006's close on 3 Jan 2007 is also 5 days.
   - **A Tuesday after a US Monday holiday is exactly 4 days.**
   - **Fix:** state the precedence. A value of the expected date is `current` whatever its age; `stale` applies only to
     a value older than the expected date and beyond `max_age_days`.
   - **Newer than expected:** the US 10-year on Good Friday, or USD/INR when RBI publishes on an NSE holiday, gives a
     value newer than the expected date. The text gives it no status. Name it, for example as `current`, and record
     that the expected date was wrong.
   - **Brent** has "no expected date; age only". Say which statuses it can take (`behind` or `stale`, never
     `current`), so a caller cannot mistake an 8-day-old Brent for a fresh one.
3. **The archived-calendar test cannot read the private tables.** "A test checks the archived US tables against the
   calendar", but the S&P 500 and Nasdaq 100 tables are in Drive only (owner decision a927390), and CI has no Drive.
   Say how this runs:
   - as a command against Drive, with its result (dates and counts only) recorded in the claims; or
   - from a committed dates-only list. Trading dates are public facts, but the owner's Drive-only rule covers the
     tables, so a dates-only list needs the orchestrator's call.

   The US 10-year can be checked in CI from its committed table.

## Minor (text)

1. USD/INR's expected date says "the previous NSE weekday". Say whether that means an NSE *session* (the A7 calendar)
   or Monday to Friday. The two differ on NSE holidays.
2. FBIL trails a week, so with an NSE-day expected date it reads `behind` almost always. Say so, since it only fills
   RBI's 2018-2022 hole.
3. Criterion 1's 27 Nov 2026 case needs the US calendar to cover 2026, including Thanksgiving week. Fine, but name
   that dependency.

## Verdict: FAIL for ba95c561e0b841f3fb99758d0951bdd854548923 (story text)

Three should-fixes, all in the text:
- the US 10-year's calendar;
- the status precedence and the newer-than-expected case;
- how the private-table calendar check runs.

Code may start once they are fixed. The re-check needs only the A17b section.

## Addendum 1 (15 Oct 2026): revised story text at 464f5ffda2c242606a629b3ba66ff1fa471722f6 (ba95c56..464f5ff, text only)

| Judge 116 finding | Status | Check |
|---|---|---|
| 1. The US 10-year is not on the NYSE calendar | **MET** | The stock calendar is now for the S&P 500 and Nasdaq 100 only. The US 10-year's expected date is the previous Monday-to-Friday weekday, with a sourced SIFMA calendar out (stated). Under that rule a bond holiday reads `behind`, and a Good Friday value read on Monday is `current`, because the rule expects Friday. A weekday rule can never make the US 10-year `ahead`, since a weekend value is impossible. Its own dates get a CI check. My cited dates are restated in the text |
| 2. Status precedence and the newer-than-expected case; Brent | **MET** | Order: `none`, `current` (expected date, any age), `ahead` (newer, usable, flagged), `behind`, `stale` (behind **and** over age). The Sandy and Ford cases become `current` (31 Oct 2012 is in criterion 1). Brent: `behind`, `stale` or `none` only. The 27 Nov 2026 case names Thanksgiving (26 Nov) from the computed calendar |
| 3. The calendar test without Drive | **MET** | A dates-only `us_trading_dates.csv`, derived from the Drive-only S&P 500 table, under the orchestrator's logged decision 19. Trading dates are exchange-calendar facts, not index values; the owner may confirm. CI tests the computed NYSE calendar against it, both ways |
| Minors 1-3 | MET | USD/INR uses NSE **sessions** from the A7 calendar; FBIL "will almost always read `behind`" is stated; the 2026 calendar dependency is named |

**One new minor (text), from a check on the Drive tables (dates and counts only).** The Nasdaq 100 table has **83 dates
the S&P 500 table lacks**, US holidays from 1 Jan 2007 on. **82** of them repeat the previous value.

Under the new order, a Nasdaq 100 reading on the day after such a holiday finds the holiday row first. It reads
`ahead`, "usable like `current`", with that day's repeated value. The level is right, but a day-change feature would
see a zero move on a holiday.

Say in scope 1 or 2 that for the Nasdaq 100 a row on a date that is not an NYSE session is skipped, so the reading is
the last NYSE session's row. Or say that `ahead` with a repeated value is reported as a holiday row. A test should
cover it.

**Verdict: PASS for 464f5ffda2c242606a629b3ba66ff1fa471722f6** (story text). Code may start. The new minor can be
folded into the code round; I check it there.

## Addendum 2 (15 Oct 2026): A17b code at 1b4d9705373e645abfaf1f17e1f228c156b7e0c2 (response 116)

### Gates

- **Exact SHA** (it already holds a merge of `main` at f97c9d2), Slack token unset: **3,876 passed**. `ruff check`,
  `ruff format --check` (827 files) and `check_imports` (839 files) are clean.
- **`origin/main`** has moved 2 commits since, with no code, and merges cleanly.
- **Sizes.** Largest file `wiring.py`, 151 lines; `fno/global_cues/` totals 1,724 lines.

### My own checks

| Check | Result |
|---|---|
| NYSE calendar vs the dates file | My own loop over every day from 3 Jan 2007 to 14 Oct 2026: **0 mismatches** against the 4,977 S&P 500 dates. Spot checks: 24 Dec 2021 (Christmas observed), 20 Jun 2022 and 19 Jun 2023 (Juneteenth), 18 Jun 2027 (Saturday Juneteenth observed) and 3 Jul 2026 are closed; 31 Dec 2021 is open (Saturday New Year, no Friday close). All correct |
| Dates file vs Drive | `us_trading_dates.csv` equals the Drive-only tables' date sets exactly, for both S&P 500 and Nasdaq 100. It holds dates and 0/1 flags only, no value |
| Readings on real tables | Dates, ages and statuses only. **15 Oct 09:15 live:** sp500 current (14 Oct); nasdaq100 **behind** (13 Oct, expected 14 Oct). **27 Nov 2026:** sp500 **stale** at 44 days, expected 25 Nov (Thanksgiving skipped). **31 Oct 2012:** sp500 **current** at 5 days (Sandy); us10y behind (29 Oct, expected 30 Oct). **14 Oct 2025** (Columbus Day): us10y behind. **10 Apr 2023:** us10y **current** with Good Friday 7 Apr. **26 Dec 2025:** nasdaq100 current with 24 Dec, so the Christmas holiday row is skipped. **USD/INR on 14 Oct 2026:** 15:00 current on the same day; 09:15 current on 13 Oct. **brent** behind at 9 days, then stale at 52. **fbil** behind at 8. **2027:** USD/INR raises `CalendarError`, naming the missing circular |
| Mutations (12, in a separate worktree) | **11 caught:** holiday rows not skipped; `current` only within age; age boundary; future rows usable; Saturday New Year; Juneteenth before 2022; closures ignored; muhurat as a USD/INR session; adopt window off; four attempts; no `started` row. **Survived:** `available_at <= cutoff` in `expected_date`. No real source publishes exactly at 09:15 or 15:00 (US close 01:30/02:30, Treasury 03:30/04:30, rate 13:30, Brent 23:59 IST), so it is equivalent on today's sources. Minor 1 |
| A15 minors | The sweep's exit-code test passes (9 of 9 in `test_sweep.py`). The `lambda` with `noqa` in `build_vix_table_builder` is replaced by a named function; the remaining `lambda` in `build_vix_checks` predates the story and is fine. The README's muhurat times are per year |

### Criteria

| # | Criterion | Result |
|---|---|---|
| 1 | Readings in the stated order, each status covered | MET (my readings; H2, H3, H5 caught) |
| 2 | US calendar cases; CI test against the dates file; us10y missing weekdays never `current` | MET (0 mismatches by my own loop; H6-H8 caught) |
| 3 | Muhurat is not an open; committed labels recompute | MET (H9 caught; `test_committed` passes) |
| 4 | `adopt` creation-time window | MET (H10 caught). The real four copies were created 4-9 s after their path times, per the builder; not re-read by me |
| 5 | Attempts logged and capped | MET (H11, H12 caught) |
| 6 | A15 minors | MET |
| 7 | FBIL owner item in the README | MET |
| 8 | Quality rules, gates, no frozen file | MET |

### Rulings on the builder's deviations

- **One `CueCalendar` interface instead of `UsSessionCalendar`:** ACCEPTED. The same seam serves NYSE, weekdays and
  NSE sessions. A US-only interface would duplicate it, which is DRY under the "one new class" rule.
- **`CreationTimes` as its own interface:** ACCEPTED. Only adopt needs it (interface segregation), and a store without
  it refuses, as the story asks. `GoogleDriveStore.metadata` does not check the HTTP status. A 403 or 404 gives a body
  without `createdTime`, so the result is None and adopt refuses: it fails closed.
- **Nasdaq cross-check against the S&P 500 table rejected (skip by the NYSE calendar):** ACCEPTED. The calendar
  matches the S&P dates exactly, so the two rules give the same rows, and the calendar needs no Drive.
- **Before 2017 the next NSE open is the next weekday:** ACCEPTED. Every pre-2017 row was fetched in 2026, so it is
  `backfilled` either way; the committed recompute test passes.
- **Owner items:** `us_trading_dates.csv` (decision 19: calendar facts; it does make the S&P's weekday gaps derivable,
  which the builder states) and FBIL public. Both are recorded for the owner, and neither blocks.

### Minor

1. Add a boundary test for `expected_date` (a source whose `available_at` equals the cutoff), so a future source at
   exactly 09:15 or 15:00 is pinned. The mutant is equivalent today.
2. **Two of the five closure sources are not primary:** an investinglive news page and a BOX Exchange circular for
   Hurricane Sandy. Prefer NYSE or ICE notices when next touched.
3. Response 116's verdict table gives brent "2 Oct, behind (13 days)" for 15 Oct 09:15 without naming the view. The
   live view gives 6 Oct at 9 days (my probe); 2 Oct is presumably the research view, where 6 Oct is not available
   until 16 Oct. Label the view.

**Verdict: PASS for 1b4d9705373e645abfaf1f17e1f228c156b7e0c2.** Merge it; then I check the merge. Consumers (M1, the
weather, forecasts) must read cues only through `CueReader` or `reading_for` and refuse `stale` and `none`.

## Addendum 3 (15 Oct 2026): merge check, A17b merged to main as af96586

- **Parents.** af96586's parents are 4362a94 (main) and 1b4d970 (the passed tip).
- **The merge matches my recomputation exactly** (empty diff; no conflicts).
- **Branch files arrived unchanged.** Every file the branch changed is identical in af96586 and 1b4d970.
- **No unjudged code since.** No file under `fno/`, `tests/`, `tools/`, `.github/` or `config.yaml` changed after it.
- **CI.** Run 38680360001 (`checks`) on af96586: **completed, success**.
- **End-to-end run (rule 8).** The orchestrator records `global-cues verify` against Drive on the merged tree as clean.

**Merge check: PASS.** The three minors of addendum 2 go to the builder's follow-up.

**The consumer rule goes into the M1 and weather briefs:** read cues only through `CueReader` or `reading_for`,
refuse `stale` and `none`, and state any use of `behind`.

## Addendum 4 (15 Oct 2026): A17c minors at cc739e7d1d28bfdc2eef7209208d12203cbaf79b (response 116 addendum 1)

cc739e7 = 7601e4f plus a clean merge of `main`. The changes:
- one test in `tests/global_cues/test_us_calendar.py`;
- two source rows in `us_market_closures.csv`;
- response 116's table.

No `fno/` code changes.

| Minor | Status | My evidence |
|---|---|---|
| 1. `expected_date` boundary test | **MET** | The new test covers 01:30:00 vs 01:30:01 IST (US summer time), 02:30:00 vs 02:30:01 (winter), and 9 and 10 Mar 2026 around the 8 Mar clock change: good, boundary and both time zones. **Broken-code proof, by me:** `available_at(day) < moment` changed to `<=` in a separate worktree fails it (1 failed, 7 passed). The mutant that survived in addendum 2 is now caught |
| 2. Sandy source | **MET, limit adequately disclosed** | I fetched the cited euronext.com release myself: "The industry decision to close the U.S. markets for two trading days due to Hurricane Sandy". It is primary (NYSE Euronext), but it does not name the days. Response 116 addendum 1 says so plainly. It names the 28 Oct statement that does name them, available only as news reprints, and the S&P table's missing rows on 29-30 Oct 2012. My addendum 2 check (0 mismatches against the S&P dates) confirms those are the two days. The `reason` column says "two trading days". Adequate. A NYSE or ICE page naming the dates would be better, but it is not required |
| 3. Brent row names its view | **MET** | Re-run by me on the public table, 15 Oct 2026 09:15: research view `behind`, 13 days, 2 Oct; live view `behind`, 9 days, 6 Oct. That matches the response, which now states the research view above the table |

**Gates.** At cc739e7, Slack token unset: **3,877 passed** (one more than A17b, the new test). `ruff check`, `ruff
format --check` (827 files) and `check_imports` (839 files) are clean. It merges cleanly with current `origin/main`,
which has no code change since.

**Rules 4-6:**
- broken-code proof: the boundary mutant, planted by me;
- cases: summer, winter and the clock change, at, just after and around the boundary;
- real sample: the Brent readings, run by me.

**Verdict: PASS for cc739e7d1d28bfdc2eef7209208d12203cbaf79b.** Merge with `--no-ff`; I check the merge afterwards.

## Addendum 5 (15 Oct 2026): merge check, A17c merged to main as 4e74d8a

- **Parents.** 4e74d8a's parents are 1fdbc68 (main) and cc739e7 (the passed tip). It is a `--no-ff` merge.
- **The merge matches my recomputation exactly** (empty diff).
- **Branch files arrived unchanged.** The test, `us_market_closures.csv` and response 116 equal cc739e7. The judge
  files differ only by `main`'s own later addenda.
- **No unjudged code since.** a103793 brought only judge and response files.
- **CI.** Run 38682721169 (`checks`) on a103793, the first push carrying the merge: **completed, success**.
- **End-to-end run (rule 8).** The orchestrator records `global-cues verify` as clean.

**Merge check: PASS.** A17, A17b and A17c are done.
