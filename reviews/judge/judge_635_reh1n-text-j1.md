# Judge 635: REH1n story text, a quote capture not on the replayed day, round 1 (judge 1 of 2)

Branch `story/reh1n-new-quote-parts` at `883937fa6` (one file: `docs/stories/REH1-rehearsal-mode.md`, +85).
**FAIL**, lane 1: 1 should-fix, 2 minor. Text only: judged by reading; doc-reading tests run.

## Criteria (the text against the code and the record it cites)

| Item | Verdict | Evidence |
|---|---|---|
| Finding's facts | MET | `recorded_quotes.py:71` answers "window closed"; `indices.py:28-29` has no such quiet status; first weekly marker on main is `quote-snapshots-weekly/2026/10/niftyweekly_20261022.canonical`; `fe89e640b` is 21 Oct 22:25 UTC; no `quote-snapshots-v4` marker on main |
| (a) `recorder.py` and `constants.py` drift only | MET | `story/v4-freeze` `FREEZE_v4.md:280,300` sit under "## Recorded, not byte-checked" (275); `freeze_check.drift` reads that section into drift lines, while `problems` reads only "## Frozen files"; `BYTE_CHECKED_GLOBS` names `fno/quotes/v4_extras.py` alone in `fno/quotes/` |
| (a) the touched files are unhashed; `window.py` | MET | `indices.py`, `quotes/cli.py`, `recorded_quotes.py` and `exercised_line.py` appear nowhere in `FREEZE_v4.md`; `window.py` is only named (line 383, "named, not hashed"). The design changes none of the three files the orchestrator named |
| Real runs unchanged (N4) | MET | only recorders set `RecordResult.status`; `GOOD_STATUSES` (`quotes/cli.py:29`) and `QUIET_STATUSES` gain a status no real recorder returns; `exit_code` then gives 0 |
| (c) no live record touched | MET | reads `mode.record` and writes nothing; every rehearsal write is under `dryrun/<run_id>/` (REH1 section 3), so an earlier rehearsal's "none" marker never carries over |
| (c) never a failure, never a success | PARTLY | named once in the exercised line, not counted missing (`indices_cli._missing`); but see finding 1 |
| (b) close_read, close_recheck | MET, wrong reason | finding 2 |
| Rules 2, 4, 5 | MET | gap list; N1-N5 each with a plant; N2 is the boundary; N5 has the empty case |

## Findings

1. **Should-fix: the rule's test is wider than its stated wrong case.** Design 1 decides "not a part" from canonical
   markers only, and design 2 applies it "before any wait", that is before the day's attempts are read. A4 writes an
   attempt's sidecar (`.meta.json`) at once and the marker only at the window's end (`recorded_quotes.py:112-115`;
   the real recorder's "none", `recorder.py:182`). So a capture's first day whose run died after an attempt also
   reads as "not a part": sidecars on D, no marker, nothing earlier. That is a real failure, hidden. The text says the
   one wrong case needs "no sidecar, no marker". Concretely: v4's first live day is Mon 26 Oct, so a crash in its
   14:32-14:40 capture after one attempt would rehearse as "not a part". The record has no such day today (32 sidecars,
   each with its day's marker), so this is a path, not an event. Fix: a stem is a part of D when the record holds a
   marker **or a sidecar** of it on or before D. Add N3's twin as a case and a plant: a sidecar on D with no marker
   stays a failure.
2. **Minor: (b) holds, but for another reason.** "A4h has recorded every session since" is one session: 23 Oct
   (receipts `2026-10-23.first.raw.json` and `.recheck.raw.json`; 24-25 Oct are weekend days). The real reason is
   structural. Each is its own step, `Alerted(LiveFrom(NotBefore(...)))` (`daily/wiring.py:132-135`), and `LiveFrom`
   compares the replayed day (`steps.py:105`), so a day before 23 Oct is `not_live` and REH1j's line takes it. A later
   day with no read is a true failure. Fix: one gap-list row saying so, covering every step with its own live key.
3. **Minor: no register row.** The REH1 row on `main` (`WORK_REGISTER.md:109`) names neither this branch nor
   `fno/quotes/indices.py` and `fno/quotes/cli.py`, which belong to A4c/A4f (merged rows 75 and 78). CLAUDE.md wants
   the row in the first commit. Fix: add the branch and both files to the REH1 row.

## Plants

None. The change is text only, so it was judged by reading, as JUDGE.md's merge procedure says. N1-N5 name the
builder's plants; I add finding 1's sidecar case.

## Notes

- Doc-reading tests on `883937fa6`: 922 passed, 14 xfailed. Record scan clean (9,270 files). The diff is Markdown only.
- `FREEZE_v4.md` is on `story/v4-freeze`, not yet on `main`; (a) was checked there at `631a47c28`.

## Addendum 1: round 2 at `5fa97694c` (the last round)

**PASS**, lane 1, judge 1 of 2. All three findings are fixed and nothing new was found. Judged by reading; the change
is text only (`git diff --name-only 82a26c344 5fa97694c`: `docs/stories/REH1-rehearsal-mode.md` alone).

| Round-1 finding | Verdict | Evidence |
|---|---|---|
| SF1. The rule read markers only | FIXED | Design 1: "no canonical marker AND no sidecar of that stem in that dataset on or before D"; design 2: an earlier marker or sidecar, or either on D, is served as today. "The one wrong case" now needs a crash before the first attempt's sidecar, and it names Mon 26 Oct (v4's first live day) as its one exposure. New case and plant: one attempt's sidecar on D with no marker stays "window closed", alerted, exit 1 (plant: markers only). Look-ahead is still excluded ("never reads a day after D") |
| m2. (b)'s reason | FIXED | New gap-list row: steps with their own live key (`close_read`, `close_recheck`, `card`, the v4 and G13 steps) are each a `LiveFrom` step, so a replayed day before the key's date is `not_live`, exercised by REH1j, never a failure. This matches `steps.py:105` |
| m3. Register row | FIXED | `main`'s `WORK_REGISTER.md` REH1 row names REH1n, `story/reh1n-new-quote-parts`, `fno/quotes/indices.py` and `fno/quotes/cli.py` |

Gates: doc-reading tests on `5fa97694c`, 932 passed, 13 xfailed.

## Addendum 2: round 3, the owner's grant (`80b522bf6`, text only)

**PASS**, lane 1, judge 1 of 2, with 1 minor. The change is `docs/stories/REH1-rehearsal-mode.md` only, answering
judge 639's SF1. I checked every new claim against the code and the record:

| Claim | Evidence |
|---|---|
| The run log lists the day's parts | `journal/runs/2026-10-21.json` and `2026-10-23.json`: `steps.quotes.inputs = {"parts": ["nifty", "nse", "indices"]}` |
| The plan is committed before any capture | main: "Desk run 2026-10-23 step quotes" at 08:37:14 UTC = 14:07:14 IST |
| Single and multi-stem parts | `quote_parts.py:81,83` (nifty, nse) and `v4_part.py:33` (v4) each hold one stem; `indices` holds 4 (`quote_parts.py:86`) |
| A recorded step's entry is never replaced | `run_log.py:48-51`: a done step raises; only a failed entry with `retry` is replaced |
| A part's sidecars reach the record at its end | `QuoteParts._finish` (`quote_parts.py:270-280`) commits the part's files |

The 3 paths (hung, not pushed, container lost) are each closed for nifty, nse and v4 by the 14:07 plan. Residuals 1 (a
day with no run log in the record) and 2 (a new `indices` stem's first day) are named honestly. N3's new case
has its 3 plants. Doc-reading tests: 963 passed, 13 xfailed; record scan clean.

**Minor:** the gap list's row "state the one wrong case plainly" still points to "The one wrong case"; the section
is now "The wrong cases".
