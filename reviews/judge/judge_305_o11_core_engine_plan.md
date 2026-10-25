# Judge 305: the O11 core-engine plan (story/o11-core-engine-plan at 8caaa2a3, docs/CORE_ENGINE_PLAN.md)

**Verdict: FAIL: 3 should-fix findings and 2 minor.** The request named 97e28a92; 8caaa2a3 adds only the "Found by the
O11 replay" section, so I judged 8caaa2a3.

The plan does its main job. It states the goal with the owner's words and sources; I spot-checked rows 238, 239, 243,
244, 245 and 246 of `docs/DESK_DECISIONS.md` and they say what the plan quotes. It traces 16 expectations to stories
and is blunt about what serves nothing now.

## Findings

**Should-fix 1. The plan is stale: owners and states have changed since it was written.** Strong evidence.
- Owners now exist for:
  - D3: judge 300 PASS;
  - F1t (session_01PLbKH1), F5 (01SFDjjZ), F6/F7 (01KTAQCD), F2 (01WSMMv5), G13 (01UkTaDe);
  - O10: judge 350 exists;
  - A19, A20, F8c, A17 schedules, and the Book 2 pack rule default (register rows 23, 81, 85, 94-98).
- O1 is merged: edb4e2b6 is on `main`. D4 is merged. D5 (9a9a1b96) and E8 part 1 (dd3ed6bb) are not.
- Table (b), table (c) and step 5 of (e) ("needs an owner") still say "none" or "missing".

Fix: refresh every state and owner from the register at the new `main`.

**Should-fix 2. The owner's go-live gate is missing.** Strong evidence. `docs/DESK_DECISIONS.md` line 247 (16 Oct,
owner: "10-day trial (Recommended)") sets the gate:
- the O11 replay green and judged;
- then 10 trading days in a row of full live capture and daily runs with zero silent failures;
- any silent failure restarts the count;
- "live" also needs the owner's routine creation, the per-part live switches and the v4 freeze.
The critical path ends at "O11 green", and section (a) has no expectation for the gate.

Fix: add the gate as the last steps of (e) (the routines and switches, then the 10-day trial and its restart rule),
and trace it under E10/E11.

**Should-fix 3. Functions the owner expects are missing or wrongly dropped.**
- **Books 2 and 3 fills and exits.** Strong evidence. "Hand to E4/E8" needs a per-book `OrderBuilder` and
  `ExitRules`. Book 1's replay the playbook (`fno/books/book1_orders.py`, `book1_exits.py`), and no story owns Book 2's
  or Book 3's (judges 301 and 302).
- **AI books' model reporting.** Strong evidence. The model "unknown" means no trade (orchestrator's ruling). The
  forecast audits show "unknown" on 3 of 4 answered book-days. Without a fix, Books 2 and 3 rarely trade even when
  live (judge 301 should-fix 1).
- **Capture health items from the gap audit.** Strong evidence. Section (e) step 3 names only the NSE recorder's
  retirement. The audit's other health gaps have no step: the `nse-margins` 03:30 cron that never started, the
  `participant-oi-release` second slot cancelled each evening, and `health-check.yml` with no recorded runs. Under row
  246, "up to date. That is non-negotiable", each needs an owner, or must be folded into O10 explicitly.
- **"Drop F3 and F4 as separate stories."** Reasoning only. Dropping F4, the AI judge of design 12.3/12.4, is a design
  change. It needs the owner's word, not the plan's. The orchestrator has also just approved amending F4's text
  (orchestrator to judge E, 16 Oct), which assumes F4 stays. Put it to the owner as a question with the
  recommendation, and keep F4 until answered.

**Minor.**
1. "F7 folds into F5/F6 as one field each": F6's text keeps F7 as its own section in the same file (judge 302). That
   is fine; update the wording. "F2 v1 = one analyst first" now matches F2's text, and I agree (judge 303).
2. "LR3 CUSUM ... build no code": the owner accepted LR3's four design answers on 16 Oct. Record that the design is
   settled and only the code waits for trades, so the deferral is not read as a reopening.

## Completeness and over-engineering
- Against rows 244-247 and section (a)'s sources, every owner expectation has a line, apart from the gate (should-fix
  2).
- The drop/defer list is right on P2/W3 (no UI), BR1 (descriptive only), G7b b-d, LM1 2b and the NSE recorder.
- The "judge paperwork" row adds nothing actionable.
- The replay findings are real and useful. The NSE fallback's contract IDs parse as `OPTIDXNIFTY` in C5's bucket map.
  The private pack differs after 15:00 because it holds the decisions folder. I did not reproduce either (reasoning
  only for me). Give each an owner in (e).

## Addendum 1: a4044ecf (revision 2, response 267)

**Verdict: FAIL, 1 should-fix left. Should-fix 1, should-fix 2 and minors 1-2 are closed.**

- **Should-fix 1, stale owners and states: closed.** Section (c) gives every gap its owner and state from the
  orchestrator's 16 Oct assignments. Two items still lag: D3 shows "code with the judge", but it merged as e5906769
  (without ac966350's F4 text). Update both rows.
- **Should-fix 2, the go-live gate: closed.** "Definition of done" quotes the owner's 16 Oct gate (row 247): O11 green
  and judged with zero expected-missing rows, then 10 trading days with zero silent failures, the restart rule, and
  the owner's switches. It ends the critical path, and every expectation E1-E17 now has a "trial evidence" column.
- **Should-fix 3: partly closed.**
  - The F4 drop is withdrawn ("drop F4's overrides (already decided)"): accepted.
  - Books 2 and 3's orders and exits, and the model-reporting rule, are now owned in F1t's and F6's texts (judges 301
    and 302, addenda 1): accepted, though one line in (c) should say so.
  - **Still open, and re-checked today on GitHub (strong evidence):**
    - `health-check.yml` has **0 runs ever** (`actions_list`, total_count 0). Row E10 and E11's trial evidence relies
      on "O8's daily health message every evening", which has never once run.
    - `nse-margins.yml` has 1 scheduled run in total (16 Oct, 07:12 UTC, about 5 h after its 03:30 IST slot), plus 1
      manual run. Its early cron has never started.
    - The `participant-oi-release` second-slot cancels have no line in the plan either.
    - Under row 246 ("up to date. That is non-negotiable"), each of these needs an owner and a step in (e) before the
      10-day trial starts, or must be named as covered by O10's staleness alert with a test.
- The withdrawal of `quote-recorder-nse.yml`'s retirement, with its conditions (failures into O10, C5's
  contract-ID fix before it feeds the desk): accepted.
- The quote check: the builder grepped each quote. I spot-checked rows 244-247 again; they match.

## Addendum 2: 467a4433 (revision 4, main merged)

**Verdict: PASS (lane 2; the orchestrator merges it).**

**The last should-fix (capture health): closed.** Step 2b now comes before the trial and is on the critical path, with
an owner for each item:
- O8's first runs (012eM7Ti);
- nse-margins' early cron (01Vm1WnH);
- the participant-OI second slot (013YJ5gj, until A8's owner is named);
- O10's staleness alert proven on a never-started job, as a new O11 strict xfail.

**On O8 never having run, the builder's pushback is accepted, with a deadline.** I checked it myself:
- `health-check.yml`'s cron is `21 12 * * *` (17:51 IST);
- the workflow reached `main`'s first-parent history at c1593789, 15 Oct 18:46:41 UTC, after that day's slot;
- so its first scheduled run is due today, 16 Oct, at 12:21 UTC.
Zero runs so far is therefore not yet a failure. The plan names "no run by 18:21 UTC" as the failure. The orchestrator
should check that tonight. The nse-margins finding (1 scheduled run in total, about 5 h late) stands, and step 2b
carries it.

Also closed:
- D3's row: merged as e5906769, and F4's no-override text after it.
- F4 stays, its text amended.
- Books 2 and 3's orders and exits (F5, F6) and F1t's model reporting are rows in (c) and on the path.

Owner expectations: every row 244-247 expectation is traced, and the gate is the definition of done. I have no
completeness gap left to name. Over-engineering: the drop and defer list is sound.

## Correction (judge's own error, 16 Oct)
In addendum 1 and in judge 305, I wrote that nse-margins' "03:30 IST cron never started". That was wrong as a finding.
The 03:30 IST cron (`0 22 * * *`) reached `main` at 3c333417, 16 Oct 06:08:32 UTC (I checked with `git log -G`), so
its first slot is tonight at 22:00 UTC. The earlier late runs were the old morning crons (the file's own comment
records GitHub starting them 4-5 h late).

The orchestrator also reports that the participant-OI cancels are fixed in O10's branch (`due_day`). So all three
health items are "O10 plus a first-run check", as plan revision 4's step 2b already says. **The PASS of addendum 2
stands.** Tonight's checks: `health-check.yml` by 18:21 UTC, and `nse-margins.yml`'s first 22:00 UTC run.
