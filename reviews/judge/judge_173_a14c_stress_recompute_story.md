# Judge 173: A14c story text (the stressed-margin factor recomputed from NSE's SPAN files), rule 1

**Verdict on c6c2b97f3df4011a6004f2774f2731e196614a21 (`story/a14c-stress-recompute`, text only): PASS.** No blocking
or should-fix findings and three notes.

Applied: `docs/JUDGE.md` rule 1; the owner's rules "keep the design simple" and "one builder per function".

## The finding the story carries: checked and true

- **The code.** `fno/risk/margins.py` (docstring and `_span`) multiplies only the scanning risk:
  `max(0, k x scan - NOV) + min(0, NOV) + exposure`.
- **My recomputation from response 77's 14 Oct table.**
  - SF 100: unstressed 822.25 + 59,077.07 = 59,899.32; stressed 1.45 x 822.25 + 59,077.07 = 60,269.33, which is +0.62%.
  - SC 300: 71,427.59 / 67,594.67 = +5.67%.
  - Every BF row: 0%, because NOV covers the stressed scan.
- **What it means.** 1.45 was measured on the whole margin (response 77: "today's method", scan plus exposure), but the
  rule applies it to a part that is 1-14% of the margin. Today's crash buffer is about 0-6%, as the story says (strong
  evidence).

## The orchestrator's four points

1. **Criterion 1 (reproduce 1.127 within 0.001): sound, with one dependency to name (note 1).** 1.127 is response 77's
   Sep-Oct 2026 window (29 entries, BF 100). The criterion's "or explain each difference with the files' figures" is
   right for a hand-run reference.
2. **The 2020 short-option minimum: acceptable as written.**
   - SPAN takes the larger of the scan figure and the minimum charge.
   - Response 77's own caveat says 2020's margins "simply tracked the index (+26.5% from 7 Apr 2020)", with the
     minimum binding for all structures alike (1.265). Whenever the minimum binds, the held rise equals the index's
     rise, whatever the exact aggregation.
   - Criterion 4's "by hand" test is written by the same builder as the rule, so it is not independent (note 2).
3. **The four owner questions: fair, each recommendation labelled.**
   - Q1 gives both options with their costs. The report gives both figures until the owner decides. "Recommended: B"
     is marked reasoning only.
   - Q2-Q4 are balanced. Q3 keeps the owner setting every risk value (A for now), and the run lands about a week
     before expiry.
   - One balance point: note 3.
4. **The 13 Nov lapse timeline: correct.**
   - `_factor` refuses when `(day - as_of).days > max_age_days`. With `as_of` 2026-10-14 and 30 days, 13 Nov is day 30
     and still valid; from 14 Nov C2 refuses every trade.
   - The plan (text by about 20 Oct, build and back-fill by 3 Nov, first run 6 Nov, owner and judge by 11 Nov) leaves
     two days of margin. That is tight but stated.

## Notes (one line each where they go)

1. **Criterion 1 needs September 2026 files that are not in Drive yet.** The archive starts on 1 Oct 2026
   (`research/data/manifests/span-bod.csv`, first row 2026-10-01), and response 77's 2026 window has entries from
   September. Say that criterion 1 runs after the back-fill of question 2. If the owner picks "every day since 2020",
   it covers this.
2. **An independent anchor for 2020 and 2024, cheap once the back-fill exists.** Extend criterion 1 to also reproduce
   response 77's 1.265 (Jan-Apr 2020) and 1.407 (May-Jun 2024, BF 300 entered 5 Jun) within 0.001, or explain each
   difference. That checks the 2020 minimum's modelling against a figure the builder did not write. The 2024 window is
   today's binding value.
3. **Q1's option B, its effect said in numbers (for neutrality).** Under B, k = 1.45 on the whole margin raises a held
   SF 100 from about 59,900 to about 86,900 a lot. C2 would then refuse more trades for the same capital. The owner
   should see that cost beside B's benefit before answering.

## Coordination

The work register has A14c's own row (`fno/nse_margins/` later). Owner question 1's option B would be a separate C2
story, not built here. No duplicate with A14 or C2 work in flight.

## Addendum 1 (15 Oct 2026): revision at 83e7f6ef2a454c9832a7daf9ad4f2bd1328b2021 (owner's answers to Q1 and Q2)

**Verdict: PASS.** One note carried over.

- **Q1 and Q2: recorded, and the text follows them.** `docs/DESK_DECISIONS.md` has both 15 Oct rows: "Crash buffer
  applies to the whole margin" and "Stressed-factor recompute uses everything since 1 Jan 2020".
  - The run now measures the held rise of the whole margin C2 counts (`max(0, scan - NOV) + min(0, NOV) +
    exposure`, the "C2 counts" column of response 77's table), the same quantity C2c makes k multiply. The scan's own
    rise is reported for information only.
  - The back-fill covers every session since 1 Jan 2020 (about 1,700 files, about 16 GB).
  - Criterion 6 requires C2c to merge before any value from this run is entered, so the factor is applied as it was
    measured. Q3 and Q4 stay open with their recommendations, to be answered before the first value.
- **My note 1: met.** The full back-fill includes the September 2026 files that criterion 1 needs.
- **My note 3: moved to C2c**, where it belongs. C2c (branch `story/c2c-whole-margin-stress`) is the story that changes
  C2. Its text should state the effect on C2's room, for example a held SF 100 at about 86,900 a lot at k = 1.45 against
  about 59,900 today. I will check that when C2c comes to me.
- **My note 2: still a note.** Reproducing response 77's 1.265 (2020) and 1.407 (2024) as well as 1.127 gives the 2020
  short-option minimum an anchor the builder did not write. After the full back-fill it costs nothing extra.
- **On the builder's doubt about criterion 1.** Response 77's "margin (today's method)" is its table's "C2 counts"
  column, which is the quantity this revision now names. So 1.127 can be reproduced on that definition, and the
  criterion's "or explain each difference" covers any gap in response 77's hand run.

## Addendum 2 (15 Oct 2026): final text at 010adb2152581670de451fd7ff62bae3e9ed53bd (83e7f6e..010adb2)

**Verdict: PASS, with no notes left.**

- **Note 1: met.** Criterion 1 runs after the full back-fill and says why (the archive starts on 1 Oct 2026, and the
  2026 window has September entries).
- **Note 2: met.** Criterion 1 now reproduces all three of response 77's windows within 0.001, or explains each
  difference: 1.127 (2026), 1.265 (2020, the minimum binding) and 1.407 (2024, today's binding value). These are
  anchors the builder did not write.
- **Note 3: met.** Q1 states C2c's effect: a held SF 100 goes from about 59,900 to about 86,900 a lot (today's
  scan-only stress gives 60,269). "About 31% fewer lots" checks out: 1 - 1/1.45 = 0.310.
- **The decision commit.** Criterion 6 cites `d68b1a9c` ("Decision rows: … whole-margin crash buffer, recompute
  windows"), and that commit holds the two 15 Oct rows.
- **Still the owner's.** Q3 (who enters the value) and Q4 (NSE circulars) stay open, to be answered before the first
  value. C2c is with judge G.

## Addendum 3 (15 Oct 2026): revision at 5bb1c5993bfa94b8eb4a9bdeab96fb0deb6b7acf (owner's Q3 and Q4 answers)

**Verdict: PASS.** No should-fix findings and two notes.

- **Q3 (automatic, with an alert): sound and simple.**
  - Each run appends one row to an append-only `stress_factor.csv`. C2 and C4 read the latest row through C2d (judge
    G). `config.yaml` is never edited.
  - Guardrails: a result below 1.0, or a shrunk archive, is refused with no row; a rise applies; a fall is held with an
    alert. Criteria 7-9 test each case, including a mutation that applies a fall.
  - C2d's seed row keeps today's 1.45 until the first run, so nothing lapses in the switch.
- **Holding every fall (the builder's choice, against the orchestrator's 0.05 proposal): accepted.**
  - The rule is the maximum over a window that only grows. The incremental run computes `max(last unrounded, new
    entries)`, which by construction can never fall, and rounding up to the next 0.05 keeps that order.
  - So a fall can only come from a `--full` run that disagrees, a data fault or a method change. Each of those is
    exactly what the owner should see before a crash buffer is lowered, and holding them costs nothing in normal
    running.
  - The 0.05 band would let such a fault lower k unseen.
- **Incremental equals full (criterion 8): right.** It is also the guard for the point above.
- **Q4 (accept the circular limit, plus one Groww comparison): sound.**
  - The read-only Groww check runs where Groww's key already is (the daily Claude routine), never in Actions (no broker
    key in GitHub).
  - The tolerance (SPAN within Rs 1, exposure within 1% after rescaling to Groww's index) is met by response 77's own
    check 2.
  - A mismatch alerts but does not hold an NSE-based factor. That is the right split: it flags A14's coded exposure
    rule, not the measurement.
- **The weekly Actions job: acceptable.**
  - The owner's 15 Oct row puts time-critical jobs on routines because GitHub's timer runs 4-5 hours late and skips
    slots. This job has no time window: any hour on Sunday, or a late run, still writes the week's row.
  - It also needs no broker key, which fits the same row ("downloads with no time window" stay on Actions).
  - With `max_age_days` 30, about four Sundays must all fail before C2 refuses, and C2's refusal is loud.

**Note 1 (coordination with O1).** The Groww comparison adds a step to the daily Claude routine, whose prompt O1 owns
(orchestrator ruling, judge 169). Send that one prompt line to O1 through the orchestrator, as A4c and G10 do; do not
write a second copy of the prompt. Name O1 in Depends.

**Note 2.** The owner's Q3 and Q4 answers are not yet rows in `docs/DESK_DECISIONS.md`; Q1 and Q2 are, in d68b1a9c.
Criterion 6 already requires the rows before the first automatic row. Adding them now keeps the story's citations
checkable.

## Addendum 4 (15 Oct 2026): revision at f2192b2f3893839844b35515fc603153e216331a (5bb1c59..f2192b2, text only)

**Verdict: PASS, with no notes left.**

- **Note 1: met.** The Groww check is a command (`margins stress-broker-check`), and O1 adds its one routine line (O1
  is in Depends; no second prompt copy).
  - It runs first in each session's daily run, before the 3 pm quote parts, so its single read-only request never
    overlaps the 14:55 capture.
  - It is idempotent: once per `applied` row, "nothing to check" otherwise, and a Groww failure exits 1 and retries
    next session.
  - It writes only `stress_broker_check.csv`. Criterion 9 tests the second-run case.
- **Note 2: met.** `da0f769d` adds the owner's two 15 Oct rows ("applied automatically, with an alert"; "NSE circular
  changes … with one Groww comparison"). Criterion 6 cites them, and the hold-every-fall rule is recorded there.
- **The judge 176 point (judge G, C2d).** The first run, and any run after a row with an empty `unrounded` (C2d's hand
  seed of 1.45), is `--full`, so the hand value is never a floor of the measured series. Criterion 8 tests planted
  files whose true maximum is 1.30: computed 1.30, then `held` against the seed.
- **The stated consequence: correct and intended.** If the measured whole-margin maximum is below 1.45, the first run
  holds it, and 1.45 stays until the owner approves the lower value. A `held` row carries the run day as `as_of` with
  the old factor, so holding never makes C2's 30-day freshness lapse.

## Addendum 5 (15 Oct 2026): ChatGPT review 117 applied, at 096c94f5432b61092ead28a19fec3c3ef48c2d52 (f2192b2..096c94f)

**Verdict: PASS.** One note.

- **The fix is right.** A session count is passed by a same-count archive with a different date missing, and by an
  archive that ends one session early, which would write a fresh `as_of` on stale data and reset C2's 30-day age.
  - The run now derives the required dates from A7's calendar (regular and special, not muhurat-only) from 2 Jan
    2020 to the latest session before the run day, and checks each against the A9 manifest. Any gap is named, no row
    is written, and one alert goes out. `coverage_through` is recorded.
  - Criterion 8 tests (a) the swapped missing date, (b) the missing last session (no age reset) and (c) the complete
    case.
- **Real-data check (mine, read-only).** NSE publishes an `i1` file for the special sessions the calendar names. HEAD
  requests to NSE's archive returned 200 for 20 Jan 2024, 2 Mar 2024, 18 May 2024, 1 Feb 2025 and 1 Feb 2026, as well
  as 2 Jan 2020 and 23 Mar 2020. So requiring every regular and special session is satisfiable. I found no evidence of
  an NSE gap that would block every run.
- **Note (text consistency).** Criterion 3 still says "a missing day in a holding is named in the report and that entry
  is excluded, never filled". Under the new coverage check, a missing day refuses the whole run before any entry is
  computed, so that exclusion path cannot happen. Change criterion 3 to point at criterion 8, or drop its exclusion
  clause. If NSE ever turns out not to have published a session's file, that becomes an owner decision then.

## Addendum 6: A14c at e828860 (addendum 5 note applied)

**Verdict: PASS, no notes left.**

- `git diff 096c94f e828860` changes one line, `docs/stories/A-data-foundation.md`, criterion 3. It now reads "a
  missing day refuses the whole run before any computation (criterion 8), so no entry is ever filled". The exclusion
  clause is gone, so criteria 3 and 8 agree. There is one commit in the range and nothing else changed, so the
  addendum 5 PASS carries over to e828860.
