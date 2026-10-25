# Judge 11: story A6 re-judged (round 2)

Verdict: **FAIL, pending only.** All six of judge 8's findings are accepted. No builder defect is left.

A6 stays not done until the two criteria that depend on other work are proven:
- **Criterion 4:** that F3 ignores unscheduled events, tested through `known_on`. This belongs to F3's story.
- **Criterion 5:** the commit order, checked at the challenge run.

I also spot-checked the C1 follow-up 58323c5: `reconciles()` now checks `tax` and `after_tax`, the tamper cases
were added, and its tests pass. That closes judge 10's minor finding.

Judged trading `main` after 562ab4e. The builder's response is
`reviews/claude/response_42_2026-10-13-a6-judge-8-fixes.md`. The builder is the orchestrator session, judged like any
other builder.

## Checks run by the judge

```
$ python -m pytest -q                                   428 passed
$ python -m pytest -q tests/research_data/test_events.py  21 passed
$ ruff check fno tests tools; python tools/check_imports.py   clean
read_events(events.csv): 61 events, all past source_url pass the official-host check
```

I reran my judge 8 break cases and added new ones. Each line below is the decision day, then what `in_window` returns
for the window ending on the date shown:

```
2022-01-10 (to 2022-02-20) -> [2022-02-09]   original Feb 7-9 date, known since 2021-03-31   (judge 8: [])
2022-02-07 (to 2022-02-20) -> [2022-02-10]   after the 6 Feb reschedule: the new date
2022-06-25 (to 2022-08-09) -> [2022-08-04]   original Aug 2-4                                 (judge 8: [])
2020-09-01 (to 2020-10-12) -> [2020-10-01]   original Sep 29-Oct 1                            (judge 8: [])
2020-09-30 (to 2020-10-12) -> []             postponed 28 Sep, new dates only on 6 Oct: unknown, correct
2020-10-06 (to 2020-10-12) -> [2020-10-09]   new dates announced that day
2020-05-01 (to 2020-06-10) -> [2020-06-05]   the scheduled June meeting, known before the 22 May emergency meeting
2020-05-23 (to 2020-06-10) -> []             replaced by the unscheduled 22 May meeting; never known ahead
2025-05-01 (to 2025-08-10) -> [2025-06-06, 2025-08-07]   August at its original date until the 6 Jun move
```

I also opened the first-announcement pages myself with curl and searched their text:

- **RBI 51350 (31 Mar 2021):** "Dates of meetings ... for 2021-22 ... February 7 to 9, 2022". This matches row
  2022-02-10, first announced 2021-03-31.
- **RBI 53486 (30 Mar 2022):** "... August 2 - 4, 2022 ...". This matches row 2022-08-05.
- **RBI 49700 (20 Apr 2020):** "June 3 to 5, 2020 ... September 29-30 & October 1, 2020". This matches rows
  2020-05-22 and 2020-10-09.

## Judge 8's findings: decisions

| # | Finding | Builder's fix | Judge's evidence | Decision |
|---|---|---|---|---|
| 1 | Rescheduled meetings vanish before the reschedule | Option (b): new columns `first_announced_on`, `first_announcement_source_url` and `first_withdrawn_on`. `known_on` shows the original date from its first announcement until the move (or withdrawal, or the replacing emergency meeting). Option (a) rejected as look-ahead. | Break cases above all correct, and the first-announcement pages confirm the dates. **The builder's reasoning against (a) is correct:** (a) would show the final date before the move was public, for example 10 Feb 2022 on 10 Jan 2022, when only 9 Feb was known. That is a small look-ahead on the date itself. The stated remaining gap is that the meeting replaced on 27 Mar 2020 stays unknown before 27 Mar, because no first-announcement page was opened. That is honest, and safe in the never-look-ahead direction. | ACCEPTED |
| 2 | Criterion 4 pending F3 | Story text: F3's story must test it through `known_on` | `docs/stories/A-data-foundation.md:323-325` | ACCEPTED (still pending) |
| 3 | Criterion 5 pending the challenge run | Story text | Same place | ACCEPTED (still pending) |
| 4 | Official domains not enforced | `OFFICIAL_HOSTS` with `_official`: https only, exact host or a subdomain | `events.py:58-60`. A look-alike host such as `fakepib.gov.in` does not match `.pib.gov.in`. All 61 rows pass and the refusal test exists. Announcement sources may still be press, which the story allows and labels. | ACCEPTED |
| 5 | "Conservative" imprecise | "never look-ahead, but it may treat an event as unknown for a few extra days" | Module docstring line 9 and the story text | ACCEPTED |
| 6 | 2019 election row's source lacks the counting date | Note in the row pointing to the ECI press note | Row description read | ACCEPTED |

## Criteria (re-judged)

| # | Criterion | Result |
|---|---|---|
| 1 | Official source link on every row | MET (enforced by code now) |
| 2 | Named dates and every RBI decision 2019-2026 | MET (unchanged, 61 rows) |
| 3 | Validator rejects bad rows | MET (21 tests, including the new column rules) |
| 4 | F3 ignores unscheduled events | NOT MET (pending F3) |
| 5 | Commit before the challenge results | NOT MET (pending the challenge run) |

## Engineering standards

`events.py` is 126 lines. `Event.as_originally_known` and `_move_known` are small single-purpose helpers, and the
constants sit at the top of the module. No breach.

No new findings.
