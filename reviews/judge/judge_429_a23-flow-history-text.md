# Judge 429: A23 FII/DII flow history, story text (story/a23-flow-history @ 9d2c6bda)

Judge F (independent), quality rule 1. Story `docs/stories/A23-flow-history.md` plus its register row. Lane 1 (new
story; NSE, Drive, a workflow). Authorised by the owner's 21 Oct row "Use the data we collect: three starts", start 3.
Labels: **strong**, **some**, **reasoning only**.

## Verdict: FAIL (1 should fix, 2 minor)

What is right:
- Step 0 reads both NSE archives back to 2019.
- NSDL FPI is out, with its terms quoted, pending the owner.
- No forecaster is wired (a study decides).
- The design reuses A9's librarian and O9; the daily job follows judge 359's fallback-step pattern and sits on
  capture-watch.
- Availability is a conservative next-session rule.

## Step 0 re-checked (21 Oct 2026, about 21:10 UTC, from this session)

| File | My read |
|---|---|
| `fo/fii_stats_02-Jan-2019.xls` | 200; `Last-Modified: Wed, 06 Mar 2019 09:59:50 GMT` (rewritten 2 months later, as stated) |
| `fo/fii_stats_21-Oct-2026.xls` | 200; `Last-Modified` 13:44:03 GMT = 19:14 IST the same day, as stated |
| `nsccl/fao_participant_vol_02012019.csv` | 200; `Last-Modified` 17 Jan 2019 12:44:19 GMT (rewritten later, as stated) |
| `nsccl/fao_participant_vol_21102026.csv` | 200; 13:44:02 GMT |
| `fo/fii_stats_20-Oct-2026.xls` | 404 (20 Oct was an NSE holiday, Dussehra: "a 404 on a holiday is not a gap", as criterion 3 says) |

## Should fix

**SF1. History files rewritten after publication are not flagged, so a study at t+1 can read values corrected weeks
later [strong for the rewrites; the look-ahead risk is reasoning only].** The text records that old files were
rewritten: 2 Jan 2019's FII statistics on 6 Mar 2019, and the participant volume on 17 Jan 2019. It still gives every
row `available_from` = the next session. A rewrite can change figures (A8 found exactly that for the sister file,
participant OI). Using the rewritten copy as if it were known on the next session is a quiet look-ahead.

Judge 15 made this a should-fix for A8, and A8 now bounds such days by their last write (judge 16).

Fix expected:
- keep each archived file's `Last-Modified` in its manifest row;
- flag every session whose file was written after its next session (`rewritten_after = Last-Modified`), so a study
  can drop those days or treat them as known only from the rewrite time;
- add a criterion with a planted rewritten file;
- report how many of the about 1,940 sessions are rewritten in the first back-fill's claims.

## Minor

1. Say where and how long the back-fill runs. Two sets of about 1,940 files at the NSE politeness limit (at most one
   request a second, `fno/http_pacing.py`) take about an hour each. That suits a resumable `data-librarian` run in a
   session or a dispatched workflow (under the 6-hour job limit), not the daily job.
2. **The daily slot.** 21:30 IST lands at about 01:00-02:30 IST given GitHub's 3-5 h lateness, which is still before
   the next session's 09:15 (`available_from`). Name the morning retry's time, and add an O8 freshness row (file
   archived by 09:00 of the next session), so a slot that never starts is seen the same day.

## Open questions, correctly sent to the owner

NSDL FPI (terms: "Reproduction, redistribution and transmission ... strictly prohibited"; the archive is a form):
skipping it until needed is the right default. The `xlrd` pin follows the `pypdf` precedent.

## Addendum 1: re-judge at fdc3b2b0

**Verdict: PASS for the A23 story text.** Code may start.

| Finding | Answer in the text | My check | Result |
|---|---|---|---|
| SF1: rewritten history not flagged | A8's `LastWriteSweep` (`fno/research_data/write_sweep.py`, built through `build_last_write_sweep` in `fno/composition.py`) records every file's `Last-Modified`. A session whose file was written after the next session's 09:15 open is `rewritten` and is available only from the first session after that write. Boundaries: 09:15:00 is not rewritten, 09:15:01 is; a missing `Last-Modified` counts as rewritten. Criterion 2b reports the count and share per dataset | Both classes exist on main. Treating an unknown write time as rewritten is the safe default | **Accepted** |
| Minor 1: where the back-fill runs | a `workflow_dispatch` of the librarian, about 35 minutes per dataset, resumable | about 1,940 files at one request a second is about 32 minutes plus Drive writes; consistent | **Accepted** |
| Minor 2: daily slot and a witness | 21:30 IST plus a 07:15 IST retry; an O8 row "archived by 09:00 IST of the next session" | read | **Accepted** |

For the code round: the daily copy is archived on its first fetch, so its `Last-Modified` is the original write. A
later NSE rewrite of a recent file is A11's revision sweep's job (keep the later version beside the original). The
claims should say whether these two datasets join A11's sweep, as participant OI does.

## Addendum 2: 236389de (the owner's NSDL and xlrd answers applied)

**Verdict: the PASS stands at 236389de.**

The owner's answer is on main: DESK_DECISIONS row 279 (195b3f0f), item 5: "a one-time NSDL FPI back-fill for personal
research only, private in Drive, never shown or shared (NSDL's terms prohibit redistribution; owner's choice, 21 Oct);
xlrd allowed, pinned". The text follows it exactly:
- scope 5: about 94 form posts (one per month, January 2019 to the last full month), at least 10 s apart, one pass,
  one retry per month, no loop;
- raw HTML write-once in Drive with receipts;
- no value in the repository, a log, an alert, a card, a screen or Slack;
- no daily NSDL job;
- every row labelled `publication_time_unknown` and available from the session after its reporting date. That is
  conservative, given NSDL's note that a reporting date carries the previous trading day's trades;
- criterion 7 pins the pacing with an injected sleeper, the single retry, resume, refusal of a wrong title or a date
  past the asked one, and a grep that no NSDL value reaches committed paths, logs or alert lines;
- `xlrd==2.0.2` is pinned.

For the owner, stated once more and not as an objection to their choice [reasoning only]: NSDL's terms prohibit
reproduction and redistribution, which the private, Drive-only design respects. The site also discourages saving
(blocked save keys), and an automated form back-fill, however slow, is a use NSDL did not offer. The owner has
weighed this and chosen; the text makes the back-fill one-time and private, as decided.
