# Judge 66: P8 and P10 contract 2.5 blocks (session, indices, fno_events, flows) and two design fixes

Date: 14 Oct 2026 (about 03:40 IST). Code: trading bf1598c/5428068 and aaac24c/8629df0. Claims:
`reviews/claude/response_66_2026-10-13-p7-p8-p9-publishing.md` (last two addenda). Contract pinned to omenix-dashboard
6cc6b7a (2.5.0).

## Verdict: PASS on items 1-3 (two minor notes); item 4 (the real 07:10 IST publish) pending; main's CI is red for a reason outside this story

## 1. The four pages against 2.5

`tests/market_read_models`: 137 pass (my run at 8629df0), including the six in `test_frame_and_flows_blocks.py`. These
validate all four pages as served against the pinned 2.5 schemas, with `fno_events` equal to the contract's calendar
example field by field for its first four rows.

**Flows point in time, my plants:**

| Plant | Result |
|---|---|
| A later session's values read (`if covered <= day` made always true) | **caught** (1 failed) |
| The fetch window widened to copies taken up to two sessions later | **not caught** (137 passed) |

The second plant does not change today's values. A copy fetched later normally covers a later session and is
filtered out. So it is a test gap on the window's upper bound, not a live leak.

**Claims vs reality on the window (minor, reasoning only).** The builder says copies "fetched up to the next session"
are read, to catch "the morning copy". But `flows-download.yml` fetches once a day at 21:10 IST, after the 07:10 IST
publish. So when session D is published at 07:10 on the next session N, the copy dated N does not exist yet. The live
run reads only copies up to D.

A later **re-run** of D would also read N's 21:10 copy. If NSE had not yet replaced D's figures by then, that copy
could hold D's values as seen after the publish moment. A re-run could then differ from the live run. For strict point
in time, bound the window by the publish moment (fetched on or before D at 21:10), or record which copy each
publication used. Low impact; one test for the bound.

## 2. Muhurat (8 Nov): MET, with the known contract gap

`SessionBlock.pages` returns no page when the next session is muhurat, and every other page publishes (test with the
real 8 Nov 2026 calendar row). My plant, making the block build anyway (so the run stops with `figures_not_computed`
as before), is caught (1 failed). The missing "hours not issued" state is the contract owner's 2.6 change, as stated,
and is not judged.

**Owner action (unchanged):** give the calendar the muhurat hours when NSE's circular is out.

## 3. `market-publish.yml` order: MET

The workflow runs these steps in order:
1. `market archive`, with no database. Its manifest rows are committed by the command's recorder.
2. `db-check`, with `if: !cancelled()`, so it runs after a failed archive.
3. `publish`, only on `steps.dbcheck.outcome == 'success'`. It records `archive_incomplete` itself.
4. One failure alert, carrying the first `database check FAILED` or `Omenix F&O market archive` line as its cause. It
   is skipped when the publish already sent its own alert.

The builder's workflow-order test passes. Not run live by me.

## 4. The real 07:10 IST publish: pending

To be verified after today's scheduled run (about 01:40 UTC) through its run log and read-back line. Addendum to follow.

## CI on `main` (orchestrator's question)

- **G4 22ace2f:** yes, CI was red. The merges carrying 22ace2f without the fix failed: a31c36f (run 38472820401),
  b312262 (38472836510), 5428068 (38473230697) and 39e9173 (38474961845). They called `scoring_status` with 4
  arguments. 44090c1 fixed it: my run of `tests/forecast_scoring`, `tests/ai`, `tests/market_read_models` and
  `test_freeze_sections` gives 222 passed at 8629df0. Runs at c1bf97f and 43b92bd were green because they were on a
  line without 22ace2f.
- **Still red after the fix, for a new reason:** 1bec20d (run 38475051048) fails
  `tests/research_engine/test_lookahead.py::test_a_live_cutoff_changes_the_decision_days_own_closing_data`. I
  reproduced it at HEAD. With the panel from just before the first real A13 append (9cba740^) the file passes, 9 of 9;
  with the appended 13 Oct it fails. The sampled decision days are the same in both, which I checked.
- **Root cause (some evidence):** the test expects a true/false feature (VIX above its median) to change under a
  random perturbation. One draw may not flip it. The 2nd and 3rd trials' random numbers come after every later panel
  row is shaken, so each new day appended to the panel (about 1,900 option rows) changes them. The test therefore
  passes or fails by luck, and A13's daily appends will keep flipping it.
- **Fix (reasoning only):** draw each session's perturbation from its own seed (for example
  `Random(f"{seed}-{trial}-{day}")`), so new days never change old draws, and make the live-version test use a
  perturbation that must cross the median, or the "removed" case. Do not skip the test.

## Project rules

New blocks behind the existing block interface; contract pinned; no example values; Slack only to #fno-desk.

## Addendum 1 (flows window fix 5f6e0e0)

Flows now read only copies filed on or before the published session (the 21:10 IST download of that day). Each
publication records the copies behind each session's figures (dataset, session, filing day, SHA-256), so a re-run can
be compared copy for copy. My plant, widening the window back to the next session, is now caught (1 failed, 137
passed). The minor point from item 1 is closed. Item 4 (the real 07:10 IST publish) is still pending.

## Addendum 2 (contract 2.6, omenix-dashboard c6b4dc7; P10 build 803ca61)

**Item 2's gap is closed.** Contract 2.6 adds `Session.hours_status` (`known | not_issued`). With `not_issued`, the
schema makes `open_utc`, `close_utc` and `next_open_utc` null (an `if/then` rule), and India's response always
requires the field. The trading pin is at c6b4dc7.

P10 now publishes the 8 Nov muhurat as `not_issued`, with the session date set and the three times null, instead of
leaving the page out. `tests/market_read_models` passes 138. My two plants are each caught (1 failed each):
- `hours_status` always `known`;
- times filled for a muhurat session.

**Minor difference from the example (information):** the contract's `hours_not_issued` example has
`post_close_at: null`. Ours keeps the next 07:10 IST market run (9 Nov). The schema allows both. "When the next run
brings the close" is still true for a muhurat session, so I accept ours. The contract owner may want the example to
match.

Item 4 (the real 07:10 IST publish) is still pending my 02:40 UTC check.

## Addendum 3 (contract example fix, omenix-dashboard 66f129b)

The `getSessionIndia_india_hours_not_issued` example now has `post_close_at: 2026-11-09T01:40:00Z`. That is exactly
what P10 (803ca61) computes for the 8 Nov muhurat (`utc(9 Nov, 07:10 IST)`, my run). The contract and the publisher
agree.

Note: trading's pin is still c6b4dc7, from before this example change. Re-pin when convenient, so the pinned
examples equal the contract.

## Addendum 4 (item 4: the first real publish, run 38501152610)

**The run.** GitHub skipped today's 01:40 UTC cron (no scheduled run exists; the workflow file is a day old). The
orchestrator dispatched the run by hand at 02:27 UTC with `day=2026-10-13`, at code ede76ff. All steps succeeded.
- **Archive:** fo-bhavcopy and index-close were already there. cm-bhavcopy and security-delivery were uploaded. The
  index-close revision NSE made at 23:20 IST was kept as a version. Both flows copies were archived, and 5 manifest
  files were committed.
- **Database check:** TLS verify-full with pinned roots; the publisher's rights as expected.
- **Publish:** 1,110 blocks published as `nse-2026-10-13-41a81b0efcff`. Read-back: "every payload SHA-256 equals
  the built records". It lists `session`, `indices`, `fno_events`, `flows`, `risk`, `today`, every `chain_*` page
  (1,088 contract pages, 6 row pages), the screener and the overview pages.

**Item 4: PARTLY. The pipeline works end to end, but the flows page went out empty.**
- `research/data/publications/publication-inputs.csv` was not written: the log has no "publication inputs" line.
  The cause is that the flows block read **no copies**.
- I ran the branch's own `FlowsReader` on 13 Oct, reading Drive only. It returns 0 cash days, 0 NSDL days and 0
  copies.
- The copies exist in Drive: `nse/flows/fii-dii-cash/2026/10/13/` and `/14/`, and the same for NSDL. Both cover the
  13 Oct session.
- But `FiiDiiCashSource.first_day` and `NsdlFpiDailySource.first_day` are **2026-10-14**
  (`fno/storage/snapshot_source.py`). The reader starts at `first_day` and stops at the published day, so for 13 Oct
  it reads nothing.
- So the live flows page for 13 Oct has no days and no NSDL value, and nothing alerted. The block publishes an empty
  page as valid.

**Must-fix (P8 follow-up):**
- set `first_day` to the first copy really archived (13 Oct), or derive it from the archive;
- make an empty flows page on a session that has archived copies a failure with a reason, never a silent empty page;
- re-publish 13 Oct once fixed (same ID rules).

**Also (information, reasoning only):** the archive files a flows copy under the session it was run for (`--day`),
not the IST day it was fetched. The 13/ copies were fetched at about 08:00 IST on 14 Oct. `FlowsReader`'s docstring
says copies are filed under the day fetched. Because the archive runs just before the publish, no copy is newer than
its publication, so there is no look-ahead today. But the docstring is wrong, and the "filed on" field does not mean
what it says.

Run status (P7): the log prints no "NOT recorded" line, which is consistent with rows being written. I did not
connect to Azure to read them.

## Addendum 5 (item 4 closed)

After the P8 fix (judge 79), the hand-dispatched re-publish of 13 Oct (run 38509504961) published a non-empty flows
page (FII −1,305.13 cr, DII +2,439.24 cr, NSDL +2,000.73 cr), wrote its `publication-inputs.csv` rows and read back
all 1,110 pages equal.
- **Item 4: MET.**
- **Still open:** the scheduled 01:40 UTC cron has not yet fired even once. Tomorrow's run is the test of the
  schedule.
