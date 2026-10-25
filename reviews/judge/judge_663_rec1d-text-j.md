# Judge 663: REC1d text amendment (the 08:50 and 20:05 sections), story/rec1d-sections at ccc71f331 (judge J, 1 of 2, round 1)

**FAIL** (text), lane 1: 1 should-fix, 2 minor. Markdown only: `docs/stories/REC1-recommender.md` (+39). Doc-reading
tests on the head: 932 passed, 13 xfailed.

## The orchestrator's checks
| Check | Verdict | My evidence |
|---|---|---|
| 08:50 shows the standing answer and the checks | MET | Item 3: the latest record before today, labelled "standing" with its day (plant (c) `<` vs `<=`); the latest checks in `check_text`'s words; "no recommendation recorded yet" on an empty history |
| 20:05 shows today's two answers and the fixed line | MET | Item 4: REC1b's words without the receipt part; the fixed "tonight's check runs after this edition" line; a session with no record named, with the run log's status |
| Each section under its own flag, never switching the other's | NOT MET | S1 |
| Both editions byte-identical with both off | MET in the text | Item 2 and plant (a); with S1 the cases are four, not one |
| A section failure never stops the edition | MET | Item 1 renders each section isolated with its own `failure_alert`; plants (b) and (d) |
| The privacy rule is the recommender's own | MET | Item 5: no strike, price or strategy internal, only REC1b's and REC1c's allowed words, no hash |

## Findings
**S1 (should fix) The school's flag switches the recommender's section.**
- Item 2 shows the section "only with `school.reports` on, and from `daily.live_from.recommend`".
- The code it plugs into confirms the coupling: `build_school_maker` returns the plain maker when
  `school_settings(config).reports` is false (`fno/school/reports/wiring.py:37-38`). So `extra=` sections hung on it
  vanish whenever the school's reports are off.
- The owner turned `school.reports` on today (`config.yaml:249`). If it is turned off again, say for a school fault,
  the recommender's answers would leave both editions too. That breaks the rule that neither flag switches the
  other's section.
- Fix:
  - The recommender's sections are added by their own wrapper in the composition root (`page_wiring.py`), outside
    `build_school_maker`, gated only by `daily.live_from.recommend`.
  - The school's maker keeps only its own flag.
  - Criterion (a) becomes the four flag pairs. Off/off is byte-identical to today. School-on/recommender-off is
    byte-identical to today's school-on output. School-off/recommender-on shows the recommender's sections only.
    On/on shows both, the school's first.
  - Plant: the recommender's section gated by `school.reports`.

**m1 (minor) "Check missing" catches only a day never checked.** Item 3 defines it as "a recorded day with no check
file dated after it". A day still open whose check did not run on the previous session (a failed evening routine) has
older check files, so it is not named. Define it as: a recorded day that was not final before the previous session
and has no check file dated that session. Also say "the previous session's evening" rather than "last evening", for
Mondays and holidays.

**m2 (minor)** Item 1 still waits for the orchestrator's yes on the placement, and for the FL1 owner's agreement to
the `page_wiring.py` change. Write both in before the code round. After S1's fix that call is the one place the
recommender's wrapper is wired.

## Plants
None (a text round). For the code round: S1's flag swap; m1's missed evening not named; and (a)-(e) as listed.

## Notes
- I did not coordinate with judge K.

## Addendum 1: the moved head, story/rec1d-sections at 21a5ccff2 (still round 1, the orchestrator's re-point)
**PASS** (text), lane 1: S1 and m2 closed; m1 open (minor). One Markdown commit on ccc71f331 (+42 -21). Doc-reading
tests: 932 passed, 13 xfailed.
- **S1 closed.** Item 2 gives each section its own switch: the school's on `school.reports`, the recommender's on
  `daily.live_from.recommend`.
  - The wrapper wraps when any switch is on, so `build_school_maker`'s early return (`wiring.py:37-38`) has to go,
    and the text requires that.
  - Criterion (b) tests each switch alone, with the plant "the recommender gated on `school.reports`".
  - Criterion (a) keeps all-off byte-identical to the plain maker.
- Conditions 2-5 are sound:
  - Isolation per section, alerting the edition, the section and the exception class only (e).
  - The school's sections first and unchanged; `tests/school/reports/` untouched.
  - A template guard on every line (g), outside the school's LEAK and rupee checks. That is right: those checks would
    withhold the check's after-cost totals, which REC1c already posts.
  - Explicit configs in the tests.
- **m2 closed.** The heading now records the orchestrator's yes for MS-P1g and FL1. MS-P1j's builder reviews the
  `fno/school/reports/` diff before the judges.
- **m1 still open (minor).** Item 5 still defines "check missing" as "a recorded day with no check file dated after
  it". A day still open whose previous-session check did not run is not named. Define it against the previous
  session's check; this can ride the code round.

## Addendum 2: the final head, story/rec1d-sections at 729a3c815 (by reading)
**PASS holds** (text), lane 1, and m1 is closed. Two Markdown commits on 21a5ccff2, `docs/stories/REC1-recommender.md`
only (+52 -38). Doc-reading tests: 932 passed, 13 xfailed.
- **S1 is built as asked.**
  - `with_recommend_section(maker, config)` in `fno/recommend/report_guard.py` wraps the lab's maker outside
    `with_school_sections`, and `fno/school/reports/` does not change.
  - Neither wrapper reads the other's switch.
  - With the recommender off, the maker comes back unchanged.
  - Criterion (a) covers all four switch pairs with golden files, and both plants ("gated by `school.reports`",
    "always added") are named.
- **Isolation is right.** The recommender's `try` covers its own section only, and plant (d) catches it wrapping the
  inner maker. Its alert gives the exception class, never the message.
- **m1 closed.** "Last evening" is the previous NSE session by the calendar. Only checks dated that session are shown,
  each with its date. Waiting days with no such check give "the previous session's check did not run" and are named.
  Criterion (g) has the plant.
- The 20:05 no-record line now carries the status and reason code only, read through a `DayInputs`-shaped port
  (criterion (h)).
