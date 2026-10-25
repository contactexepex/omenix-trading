# Judge 151: A4c story text (the other index options at 3 pm), rule 1

**Verdict on 2a9ff6236878f08886d1d4805a807ff8bd3f148f (`story/a4c-all-indices`, text only): FAIL.** There is one
should-fix, the coordination with the NSE recorder now in the same 3 pm routine, plus one minor and one scope point
for the owner.

Applied: `docs/JUDGE.md` rule 1; the owner's rule "keep the design simple" (real cases only); the owner's coordination
rule (`docs/WORK_REGISTER.md`: a duplicate or a contradiction is a FAIL).

## Should-fix: the routine step ignores the NSE recorder that the same routine now runs

- **What the owner decided (15 Oct).** `conversations/2026-10-15.md` records: "Run the NSE recorder inside the 14:33
  Claude routine? => YES". The handover session then changed the routine (`trig_01M5iCBwkfvQhRFpdqBvzxEN`): it "now
  runs the Groww and NSE recorders in parallel from 14:33; pushes Groww first (before 15:13), then NSE". The work
  register lists that session's row ("Handover / routines … NSE in the 3 pm routine"; area "CLAUDE.md 3 pm section,
  routine prompts") and a known overlap on the 3 pm routine.
- **What A4c says.** Its proposed step 3b ("After NIFTY is pushed, run `record-indices` … then commit
  `research/data/quotes/` and push") and its whole timing (15:01-15:13, done by about 15:08) assume nothing else runs
  in the routine between NIFTY's push and the indices. It never mentions the NSE step, its push or its commit.
- **The real path.** Tomorrow's routine runs NIFTY (Groww) and NSE together, then pushes Groww, then NSE. Where
  `record-indices` goes is undefined:
  - If it waits for the NSE push, its window shrinks by however long the NSE recorder runs. The NSE recorder captures
    from 14:55 and, like A4, may retry towards 15:10. That could leave about 3 minutes for about 990 paced calls that
    need 6.6, so the indices would end "none".
  - Its `git add research/data/quotes/` would also stage whatever NSE files exist at that moment. That is harmless
    (write-once data), but the push order between the two would no longer be what either session wrote.
- **Expected fix (text only).**
  - Agree the order with the handover session through the work register, and write it into A4c.
  - Name the step's place relative to the NSE step and the push order. For example: `record-indices` starts right
    after NIFTY's push, alongside the NSE recorder, and each pushes its own files when done.
  - Put the agreed wording into `CLAUDE.md`'s 3 pm section, which on main still does not mention the NSE step either.
  - Add an acceptance line that the first live day shows NIFTY's, NSE's and the indices' sidecars all committed.

## Checked and correct

- **(a) The shared Groww rate budget.**
  - A16's 15:00 snapshot took 53-57 s (A16 step 0), so it ends by about 15:00:57, before 15:01:00.
  - The index run ends by 15:13, before A16's and E3's 15:15 marks.
  - If A16 runs a few seconds late and overlaps, the total is 5 + 2.5 = 7.5 starts a second, under the about 10 a
    second where Groww failed (some evidence, one morning).
  - The 0.4 s minimum gap and the 15:01/15:13 limits are tested with a fake clock (criterion 3).
- **(b) The 15:13 cut-off.**
  - `.github/workflows/forecast-capture.yml` triggers on any `research/data/quotes/**/*.canonical` push and is
    serialised by `concurrency: group: forecast-capture`, with a gate allowing one capture a day.
  - So an index marker's push starts a run that waits and then stops at the gate. The story states this as a known
    limit; nothing is needed for it.
- **NIFTY unchanged.** The default `NIFTY` keeps today's file names byte for byte, and criterion 2 keeps A4's baseline
  test and the G1 v2 golden cases.
- **NIFTY-only cross-check.** An index with no trade is recorded complete with invalid rows and no alert (criterion
  4), which is right for NIFTYFPI's real 0 of 120.
- **No duplicate.** No register row or merged story records other indices' options. A16 records NIFTY's intraday chain
  and A4 NIFTY at 3 pm. The O7 setup script is untouched.
- **Raw quotes stay out of the repository.** A4b's store, `.gitignore` and scan rule cover `groww/**.csv`.

## Minor (one line under "Known limits")

NIFTY's own retries can run to 15:10 (A4's rule), and `record-indices` starts only after NIFTY's push. On such a day the
indices get the last minutes of their window and may end "none". This is real (A4's retries exist because incomplete
captures happen) and harmless (data only), but say it.

## Scope point for the owner (not a finding)

NIFTYNXT50 (276 contracts, 8 traded on 14 Oct) and NIFTYFPI (120, 0 traded) are 396 of the about 982 new quotes: 40% of
the calls and of the run's 6.6 minutes, for 8 traded contracts. Their names are also unproven at Groww (step 0). The
owner's "record all F&O" covers them, so this is the owner's call, not a judge's. If the owner wants the simplest version,
the other three indices give about 586 quotes and about 4 minutes.

## Addendum 1 (15 Oct 2026): revision 2 at db4a9f7dfbf3ec22ed904f51ca9bae21576e577d (2a9ff62..db4a9f7, text only)

**Verdict: FAIL.** The should-fix above is still open. The revision was written before it reached the builder.

- **Scope, now correct.** BANKNIFTY, FINNIFTY and MIDCPNIFTY only, per the owner's row in `docs/DESK_DECISIONS.md`
  (15 Oct: "drop NIFTYFPI and NIFTYNXT50, record only the traded indices"). That is 586 quotes (220 + 146 + 220) plus
  about 6 calls, about 4 minutes, done by about 15:05. The three names are a constant; a name the previous NSE file no
  longer lists as `IDO` gives an incomplete attempt with a reason. The quiet-day no-alert rule is restated for
  FINNIFTY and MIDCPNIFTY. The work-register row is updated. My scope point is closed.
- **Should-fix (open).** The text still places `record-indices` "after NIFTY is pushed" with no word on the NSE
  recorder the same 14:33 routine now runs in parallel with Groww, pushing Groww then NSE. The fix is as stated above:
  agree the order and the push order with the handover session, write it into A4c and the proposed `CLAUDE.md`
  step, and add the first-live-day line.
- **Minor (open).** The one line saying NIFTY's retries to 15:10 can squeeze the index window is still missing. The
  shorter run (about 4 minutes) makes it less likely to bite.

## Addendum 2 (15 Oct 2026): revision 3 at e10c811123e8ab3eee49d562145ece5c2b34360c (db4a9f7..e10c811: story text and CLAUDE.md's 3 pm section)

**Verdict: PASS.** The should-fix and the minor are met. One note.

- **Should-fix: met.**
  - The routine order now matches the handover session's live routine. NIFTY (Groww) and NSE start together;
    `record-indices` starts right after NIFTY's push, alongside NSE if it is still running.
  - Each part commits and pushes only its own files, one commit at a time, NIFTY always first. Nothing does
    `git add research/data/quotes/` as a whole.
  - `CLAUDE.md` steps 2, 3 and 3b say this. On main, the 3 pm section did not mention the NSE step at all; now it does,
    with the owner's YES cited.
  - New criterion 8 (first live day) asks for NIFTY's, NSE's and the indices' sidecars and markers, each in its own
    commit, NIFTY pushed first.
- **The paths, checked against the real tree and in a scratch repository with A4b's `.gitignore` line.**
  - The NSE recorder writes under `research/data/quotes/nse/` (e.g. `nse/derivatives/quote-snapshots/2026/10/
    nifty_20261015.canonical` on main).
  - `git add ':(glob)research/data/quotes/groww/**/nifty_*'` staged exactly NIFTY's `.meta.json` and `.canonical`,
    exit 0. It did not stage `banknifty_*` (the glob anchors at the file-name start) and did not stage the ignored
    `.csv`.
  - So each part's paths take only its own sidecars and markers. Criterion 6's `git add --dry-run` test keeps this.
- **Minor: met.** The text now says NIFTY's retries to 15:10 can leave the indices "none" on such a day.
- **Gates.** A trial merge with `origin/main` has no conflict. The tests that read `CLAUDE.md` plus code size: 1,155
  passed.
- **Note (not a finding).** On a day when a part writes nothing, its glob `git add` matches no file and git prints
  "pathspec did not match". The routine then simply has nothing to commit. That is the same for NIFTY's existing
  step, so no rule is needed.
- **Coordination.** A4c now writes the NSE step into `CLAUDE.md`, which the handover session's register row also owns.
  The wording follows that session's own log entry ("runs the Groww and NSE recorders in parallel … pushes Groww
  first, then NSE"), so it records, rather than contradicts, the live routine. The owner copies steps 2-3b into the
  routine prompt.
