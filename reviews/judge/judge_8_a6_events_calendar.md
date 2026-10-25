# Judge 8: story A6, events calendar

Verdict: **FAIL**.
- **Should fix (1):** a builder defect: rescheduled meetings vanish from what a trader knew.
- **Pending (2):** criteria 4 and 5 cannot be met until F3 and the challenge run exist. These are not builder
  defects.
- **Minor (3).**

**What I judged:** `main` at 6e3695a (story commits 3cc3c49 and 86a4316, 12 Oct 2026). I read in full
`fno/research_data/events.py` (74 lines), `research/data/events/events.csv` (61 rows), `tests/research_data/test_events.py`
and the story's implementation notes.

**No builder claims file for A6.** No `reviews/claude/response_*` names it. The claims are in the story's
"Implementation notes" and `conversations/2026-10-12.md:1557`. I judged from those, the story and the code.

## Checks run by the judge

```
$ python -m pytest -q tests/research_data/test_events.py     passes (the full suite passes)
counts per year (rbi_policy): 2019 6, 2020 6 (2 off-cycle), 2021 6, 2022 7 (1 off-cycle), 2023 6, 2024 6, 2025 6, 2026 6 (Dec upcoming)
budgets 10 (2 interim, incl. Sat 1 Feb 2020, Sat 1 Feb 2025, Sun 1 Feb 2026); election results 23 May 2019, 4 Jun 2024
```

**The story's "judge verifies" step.** I sampled 10 rows and opened their official links with curl. Each page was
saved and its text searched:

| # | Row | Link opened | What the page says | OK? |
|---|---|---|---|---|
| 1 | 2019-02-01 budget | PIB 1564292 | "the Interim Budget for 2019-20 was presented on Friday, the 1st February, 2019" | yes |
| 2 | 2019-05-23 election | PIB 1572600 | results list to the President "today (May 25, 2019)". The counting date is not on this page; the ECI press-note PDF (state CEO copy, 35 MB) timed out after 11 MB | partly (minor 3) |
| 3 | 2020-03-27 off-cycle | RBI 49581 | "MPC at its meeting today (March 27, 2020) decided to ... reduce ... repo rate by 75 basis points" | yes |
| 4 | 2020-10-09 (revised) | RBI 50463 | "the next meeting ... is scheduled during October 7 to October 9, 2020" | yes |
| 5 | 2022-02-10 (revised) | RBI 53228 | "scheduled during February 7-9, 2022 ... public holiday ... rescheduled to February 8-10, 2022" | yes |
| 6 | 2022-05-04 off-cycle | RBI 53652 | "at its meeting today (May 4, 2022) decided to: Increase the policy repo rate ... by 40 basis points" | yes |
| 7 | 2024-06-04 election | static.pib GESchedule.pdf | text (pdftotext): "Date of Counting of Votes ... 04.06.2024" | yes |
| 8 | 2025-08-06 (revised) | RBI 60612 | "scheduled during August 5 – 7, 2025. Due to administrative exigencies ... rescheduled to August 4 – 6, 2025" | yes |
| 9 | 2026-02-01 budget | PIB 2219294 (27 Jan 2026) | "Union Budget for 2026-27 will be presented ... on Sunday, the 1st February, 2026" | yes |
| 10 | 2026 RBI dates | RBI 62422; RBI 63742 | "April 6, 7 and 8, 2026; June 3, 4 and 5; August 3, 4 and 5; October 5, 6 and 7; December 2, 3 and 4, 2026"; Oct 2026 resolution: "next meeting ... December 2 to 4, 2026" | yes |

The second "judge verifies" item, the commit order, cannot be checked yet. There is no challenge-run commit in the
history (`git log --all | grep -i challenge` is empty).

## Point-in-time break test (the story's purpose: "without hindsight")

```
in_window(decision 2022-01-10, window to 2022-02-20) -> []     (the Feb 2022 MPC, Feb 7-9, was public since 2021-03-31)
in_window(decision 2022-06-25, window to 2022-08-09) -> []     (the Aug 2022 MPC, Aug 2-4, was public since 2022-03-30)
in_window(decision 2020-09-01, window to 2020-10-12) -> []     (an MPC ending Oct 1 was public since 2020-04-20)
```

Each rescheduled meeting has `announced_on` set to the day of the reschedule. Before that day, `known_on` therefore
treats the meeting as unknown, although traders knew a meeting at almost the same date for months. This is not
look-ahead; it is the reverse, knowledge erased. Either way, feature F3 ("event inside the holding window") would be
wrong on those decision days. The rows affected are 2022-02-10 (a 1-day shift), 2022-08-05 (1 day), 2025-08-06
(1 day earlier), 2020-10-09 and 2019-02-07.

## Criteria

| # | Criterion | Builder's claim | Judge's own evidence | Result |
|---|---|---|---|---|
| 1 | Every row has a source link to RBI, MoF / India Budget, ECI or PIB | "every date from a page actually opened" | Every `source_url` is an RBI or PIB page (checked over all 61 rows). Some *announcement* sources are press (2019, 2020 budgets, labelled in the row), a state CEO copy of the ECI note (2019) and Rajya Sabha (2023). The criterion is about the source link, so this holds. The validator does not check domains (minor 1). | MET |
| 2 | Includes the named budget and election days and every RBI decision 2019-2026, unscheduled marked "no" | 61 events: 49 RBI incl. 3 off-cycle, 10 budgets, 2 results | Counts per year above. The named dates are present (repository test). Off-cycle 27 Mar 2020, 22 May 2020 and 4 May 2022 are `no`. Spot checks 3, 6, 8 and 10 match RBI pages. | MET |
| 3 | Validator rejects unknown type, bad date, missing source, missing announcement source | tests | `test_bad_rows_are_refused` (5 cases) and the upcoming-meeting rule; read in `events.py:47-62` | MET |
| 4 | Unscheduled events kept with `no`, never usable ahead; **a test proves F3 ignores them** | `known_on` test | Unscheduled events are kept and excluded by `known_on` (tested). **F3 does not exist yet**: no code uses `known_on` / `in_window` (grep), so no test can show that F3 ignores them | NOT MET (pending F3) |
| 5 | File committed before experiment 1's challenge results | — | events.csv was committed in 86a4316 (12 Oct 18:48 UTC); no challenge run exists yet, so the order cannot be checked | NOT MET (pending the challenge run) |

## Claims vs reality

- **"61 events (49 RBI incl. 3 off-cycle, 10 Budgets incl. 2 interim, 2 election results)":** true.
- **"every date from a page actually opened":** consistent with my sample. Nine of ten rows were fully confirmed. Row
  2's counting date is not on the page linked as its source (it comes from the ECI note).
- **"Budget announcement dates are late bounds ... conservative, never look-ahead":** "never look-ahead" is true.
  **"Conservative" is not generally true.** Treating a known event as unknown lets an event filter *allow* trades
  that a live trader would have skipped. The safe direction depends on how F3 is used, so the word should go or be
  explained (minor 2).
- **"Rescheduled meetings keep the earlier date in `revised_from`":** true. But nothing reads `revised_from`, so the
  earlier, publicly known date is lost to the point-in-time logic (should-fix finding below).

## Project rules and engineering standards

`events.py` is 74 lines, the test file is small, constants sit at the module top, there are no secrets and no
breach of SOLID, DRY or KISS.

## Findings

1. **Should fix. Rescheduled events disappear from what was known before the reschedule.**
   - Evidence: the three `in_window` calls above.
   - Expected: the calendar must represent what was known on each day. Either:
     - (a) set `announced_on` to the first announcement of the meeting, accept the small date shift, and state it;
       or
     - (b) let `known_on` use `revised_from` as a separate known event from its own announcement date until the
       revision date.
   - Add tests on 2022-01-10 (Feb 2022 MPC known) and 2020-09-01 (Oct 2020 MPC known as Oct 1).
2. **Pending (criterion 4, not a builder defect now).** When F3 is built, its story must include the test that F3
   ignores unscheduled events, through `known_on`, not its own filter. Until then A6 criterion 4 is not met. The
   alternative is that the story owner moves that sentence to F3's story.
3. **Pending (criterion 5).** Recheck the commit order when the challenge run is committed.
4. **Minor.** The validator does not enforce criterion 1's official domains. A row with a non-official `source_url`
   would pass. Expected: an allow-list of hosts (rbi.org.in, pib.gov.in, indiabudget.gov.in, eci.gov.in, plus the
   ones the story owner accepts for announcements), with a test.
5. **Minor.** Replace "conservative" for late-bound announcement dates with the precise statement: never look-ahead,
   but it may treat a known event as unknown.
6. **Minor.** Row 2019-05-23's `source_url` (PIB, 25 May) does not show the counting date. Expected: a source page
   that states 23 May 2019, or a note in the row.
