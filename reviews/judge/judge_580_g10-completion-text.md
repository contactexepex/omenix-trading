# Judge 580: G10 completion story text, v4's daily clock (story/g10-completion @ d4e72f20d), judge B

**FAIL (round 1 of 2; 3 should-fix, 4 minor). Lane 1, rule 1 (text first).** Markdown only, judged by reading:
first at c876ede53, then re-read at the head d4e72f20d (2f508ae15, e5626aabf, d4e72f20d add the `fno/quotes` owner,
criterion 6's three readers and `v4_expiry`); every finding holds there. Doc tests at d4e72f20d: 829 passed, 15 xfailed.

## Criteria (is the text complete, true and safe?)

| # | Check | Result | My evidence |
|---|---|---|---|
| Why 1-6 | the audit's facts | MET | `QUOTE_PARTS` has nifty, nse, indices (`quote_parts.py:66-75`); `V4_DAYS_FOLDER` is `research/data/v4_days` (`forecast_scoring/v4/wiring.py:29`); `days.py:1-5` leaves a no-file day unlabelled vs `PROTOCOL_v4.md:115`; `commitment.on_time` has no caller (my grep) |
| Gap list vs 1.6 | 14 rows | PARTLY | every 1.6 line has a row; row 10 is wrong (finding 3) |
| Steps, pathspecs | order and O1's parts | MET | the clash is real: `GROWW_QUOTES` `groww/**/nifty_*` matches `groww/derivatives/quote-snapshots-v4/...` (`window.py:32-33`, `config.yaml` `quotes.windows.v4`); the narrowed glob keeps all 44 `quote-snapshots/` files and does not match `niftyweekly_*`; the 14:03 early limit is 14:30 - 30 min + `START_MARGIN` 3 min |
| Takeover | the three commits | MET | 1fe605bd1, 7cab92b06, f313ae15f on `story/g10-part2b-pack` with the files listed; `v4-fire.yml` there runs `ai fire --protocol v4` on `receipts/data/v4/days/**` |
| G7b/G11 interface | names, paths, triggers | PARTLY | names exist on main (`release.py`, `guard.py:12`, `commitment.py:26,42`); G7b's pack reading is not tied to the guard (finding 3) |
| Groww load | timing and safety | PARTLY | 23 Oct 14:55:00-14:57:38 and 22 Oct 14:58:58-15:01:30 complete, as written (sidecars); counter-evidence left out (finding 2) |
| Monday | what runs, record-only | MET | no merge window 14:00-16:15 (DESK_DECISIONS 24 Oct); nothing counts without `FREEZE_v4.md` |
| D1, D3 | clear for the owner | MET | each gives the value, the reason, the alternative and its one code place; see minor 2 |
| Rehearsal | DRY reruns | NOT MET | finding 1 |

## Findings

1. **Should fix: the text never says what a rehearsal does with the three new pieces, and DRY reruns are the owner's
   first goal.** In a rehearsal every step that is not live runs anyway (`rehearsal/live_wiring.rehearsed_live`, REH1c;
   handover section 1). So the `v4` part, `v4_release` and `v4_deadline` all run there. REH1b's recorded source, also
   for the named window (`quotes/window_wiring.py:31`), serves only recorded attempts (`recorded_quotes.py:49-71`),
   and no `quote-snapshots-v4` attempt exists. So every rehearsal ends the `v4` part with "no recorded in-window
   attempt", writes `system_late` for the day and the catch-up days into `dryrun/`, and, under D3, ends "day done
   with problems: v4_release" with the card's warning [strong: code read]. Fix: add a criterion naming each piece's rehearsal outcome and line, and say whether the
   `v4_pack` key goes through `rehearsed_live` and whether D3's failure is right in a rehearsal of a day with no
   capture. Add a test with the mode on.
2. **Should fix: the Groww-overlap evidence leaves out the one overlap that failed, and the fallback's trigger cannot
   be seen.** The text cites 22 Oct's 15:00 overlap as clean. The repository's sidecar
   `quote-snapshots/2026/10/nifty_20261022_151500.meta.json` was the capture that ran over A16's 15:15 mark. It had
   four `GrowwAPIException (provider message withheld)` failures and was incomplete; 23 Oct's 15:15 was clean (both
   checked). Also, A16 was decided "from Fri 23 Oct" (`conversations/2026-10-22.md:319`); the 22 Oct 15:00 mark row
   cited is in Drive, so name its receipt. Because Groww's messages are withheld, "its failures name a rate limit" can
   never be true. Fix: state both overlaps (one failing). Make the trigger observable, for example any failure in
   either job during 14:30:00-14:31:30, reported with the counts.
3. **Should fix: gap row 10 and criterion 7 contradict the interface on who reads the pack.** Interface row G7b 5
   says `forecasts_v4_pack` reads the released pack. Protocol 1.6 says such a forecaster names the pack's SHA-256 or
   is refused. Yet row 10 says "its first pack reader is G11", and `PACK_READERS` is only the two AI books
   (`guard.py:12`), which criterion 7 relies on ("outside PACK_READERS ... later V4/V5"). As written, G7b's V4/V5 rows
   would never be checked against the released SHA. Fix: name G7b's step as the first pack reader in row 10, and say
   who brings it under `check_pack_binding` (G7b, in the interface table; d4e72f20d's `v4_expiry` adds to what G7b
   reads). Keep the 15:10 check keyed on something other than `PACK_READERS`, or say how the two sets differ.

## Minor

1. `v4_release` "waits for the `v4` part to end (at most until 14:45:00), never runs while it records": say what
   happens at 14:45 with the part still running (stop it and write `system_late`, or wait).
2. "Until the owner answers D1 and D3, the code waits for their values": say whether the code may be built and judged
   with the recommended values and only the merge waits.
3. Criterion 4's good case "`A` at 14:33" does not match the timeline (capture to about 14:34, release about 14:35).
4. 3a imports `first_v4_expiry` from "G7b's first commit"; no branch defines it yet (my `git grep`): add it to "Depends".

## Plants and notes

None (text). Add plants: the NIFTY glob widened in CLAUDE.md only; `v4_release` in a rehearsal (finding 1). D1 and D3
are clear enough for the owner; I do not rule on them. D2 (catch-up from 22 Oct) matches 1.6's "no release record".

## Addendum 1

**G10 completion story text, round 2 (story/g10-completion @ 1fd56d8ec), judge B: PASS (2 minor). Lane 1, rule 1.**
First read at d0182a3e9; 1fd56d8ec adds only the Depends line. One file changed from main, so I judged by reading.
Doc tests at 1fd56d8ec: 829 passed, 15 xfailed. The owner's D1 and D3 stay open: the code is built with the recommended values, and only the merge
waits.

| Item | Outcome | My evidence |
|---|---|---|
| SF1 rehearsal | **Accepted** | criterion 12: `v4_pack` is not in `KEPT_REAL` (`live_wiring.py:21-30`); with no recorded `v4` attempt, `RecordedRecorder.record` ends "window closed" (`recorded_quotes.py:49-60`); D3's rehearsal case is ok only with no recorded capture, and its line says so; the deadline checks only the replayed day |
| SF2 Groww overlap | **Accepted, with my correction** | all three overlaps are tabled, the 22 Oct 15:15 one failing; the trigger is now any failure (criterion 11). My round-1 "row in Drive" was wrong: `research/data/intraday/slots/2026/10/22/nifty_20261022_1500.csv` is in the repository (good, 220 of 220), and so are the 22 and 23 Oct 15:15 rows (good, 216 of 216) |
| SF3 pack readers | **Accepted** | gap row 10 and interface G7b 5 now name G7b's V4/V5 as the first pack readers under `check_pack_binding`; criterion 7 excludes only a new `SEALED_COMMITMENTS`, not `PACK_READERS`; `CommitmentTimes.file_received_at` exists (`commitment.py:22,39`) |
| Minors 1-3 | **Accepted** | a hung part at 14:45 is stopped and the day `system_late`, with a plant; build now, merge after the owner; criterion 4's timeline fixed |
| Minor 4 (`first_v4_expiry` in Depends) | **Accepted** at 1fd56d8ec | Depends names G7b's first commit, merged before 3a's code; my `git grep` finds the function on no branch yet |
| G7b's asks (a), (b) | **Sound** | (ii) covers `receipts/data/v4/records/live/`; `FutureQuote` on main has no `last_trade_time` or `volume` (`model.py:26-33`) |

## Minor (round 2)

1. Criterion 12 does not say where D3's rehearsal exception lives. The release step may not read the mode:
   `test_only_the_composition_roots_know_the_mode` (`tests/rehearsal/test_guard.py:70`) forbids it, so it belongs in
   `fno/rehearsal/` or a root. Also say how the one `v4_pack` note reaches the quote part (not a `DayStep`) and both steps.
2. Criterion 11's boundary "A16's row missing ... as 23 Oct's 14:30" is not what the record shows: 23 Oct's 14:30 row
   exists with status `missed` (`slots/2026/10/23/nifty_20261023_1430.csv`). Test both a missed row and no row at all.
