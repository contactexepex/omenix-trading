# Judge 206: G11 story text, the AI books on the v4 questions: `story/g11-ai-books-v4` 762a9a56 (lane 1)

Judge B. G11 builder (session 01XFXpbk...). Claims: `reviews/claude/response_202_g11-ai-books-v4.md` and addendum 1,
agreed with the A16/G8 builder. Quality rule 1: story text only; the code waits for the v4 freeze.

## The builder's facts, checked
- **No AI book has an on-time day:** confirmed from the audit files. On 14 Oct both `book2_hybrid` and `book3_ai`
  are `no_submission`, and on 15 Oct both are `late`. There is no 16 Oct AI audit on `main`.
- **PROTOCOL_v4.md still says a 15:00 cutoff:** confirmed (line 38, "the cutoff is 15:00:00 IST on `d`", and the
  15:00 pack and ATM lines). G10's protocol edits (14:30 / 14:40 / 15:10) wait for the owner's sign-off, in the freeze
  plan's step 2. G11 takes its deadline from `terms.V4_DEADLINE` (15:10, G10), which is right. It therefore depends on
  the protocol-edit commit landing before G11's code, as the "Depends" line implies.
- **Reuse claims:** checked in the code.
  - G8 discovers forecasters by folder.
  - `records.write` refuses a changed row (`RecordConflict`), so a `pending_audit` status could never settle. Writing
    the row only after the gate settles is the right fix.
  - `records.record()` stamps G7's `VERSION`, so a separate writer is needed.
  - The slot constants exist.
  - G8 checks no `made_at`, so a live row written after the audit is read as live. Point in time is guaranteed by the
    sealed commitment received by 15:10.

## Design, judged
- **Same questions, pack and deadline; G8 scores with no AI-specific path:** correct and simple. One question list
  (the `rules` slot's started set), never a separate AI list.
- **Every failure is a non-`ok` row, so a miss:** correct under G9. A BG1 stop written as `not_fired`, and so a miss,
  is honest. A `system_late` day is out for every family, as G10 built.
- **Pending audit.** The day has no row until the gate settles, so G8 shows it as a provisional miss that disappears
  when the row lands (reports are recomputed from files), and "N days awaiting audit" is printed. Sound.
- **Registration.** Rows are appended after the freeze, with `effective_start` no later than the first eligible
  session. This matches judge 184 and protocol section 6.
- **Owner question A/B (whether v4 replaces the v2 AI run):** judged as an open slot. No criterion depends on it, and
  the cost line states both options. The builder's lean (A) and its reason are fair (reasoning only).
- **Cost** against BG1's minute cap: the estimate is labelled as an estimate, and the v2 prompts write BG1's timing
  record, so it gets measured.

## Should-fix 1: criterion 6's look refusal is out of this story's scope as written
- Criterion 6 says "a confirmatory look refuses to run while an audit up to its date is open". The Scope's Out list
  says "G8's scoring code (the A16/G8 builder)", and design item 7 says the look side "may check later".
- The look refusal is a change to G8's `run_look` / `LookRecords`, so G11's builder cannot meet criterion 6 without
  building in G8, and the A16/G8 builder has not taken it on.
- **Why it matters (normal running):** without the refusal, a look run with an audit still open would record a false
  miss for good. `LookRecords` writes each look once.
- **Fix (either):**
  - (a) move the look refusal to the A16/G8 builder: a row in their register and a line in the v4 freeze checklist,
    since the looks are frozen code (`fno/forecast_scoring/v4/` is byte-checked), so it must land **before** the
    freeze; or
  - (b) keep it in G11 with the A16/G8 builder's written agreement, and take it out of the Out list.

  Either way, criterion 6 must name who builds it and when.

## Notes (not blocking)
1. Who owns `fno/ai` and who changes `forecast-capture.yml` are open questions for the orchestrator. G11's register
   row lists `fno/ai/` as "later". Settle both before code.
2. Criterion 4's 15:10:01 / 15:09:59 boundary should cite G10's receipt-time check (criterion 1b, part 2) as the
   shared implementation, so there is no second deadline check.

**Verdict: FAIL for 762a9a56 on should-fix 1** (one text change plus a coordination decision). Everything else is
ready. A re-check needs only criterion 6, the Out list and the register line.

## Addendum 1 (15 Oct 2026): 6420714c

The diff changes only criterion 6, design item 7, the Out list, criterion 4, the register row and response 202
addendum 2 (23 lines added, 8 removed).

| Finding | Status | Evidence |
|---|---|---|
| Should-fix 1: who builds the look's refusal | MET | The A16/G8 builder builds it in `fno/forecast_scoring/v4/` before the freeze, with their register row and a freeze-checklist line; their written answer is quoted in addendum 2. The interface is a committed file: `research/forecasts/v4_audits/open_audits.csv` (`day,forecaster,question`). A look on date L refuses while any row has `day <= L`, a missing file means no open audit, and a bad header or date stops the look. G8 reads the file and never imports G11's code. The Out list and criterion 6 now split the two sides |
| Note 2: reuse G10's receipt-time check | MET | Criterion 4 says so |

**New note (not blocking):** say when a row *enters* `open_audits.csv`. It should be in the same commit that records
the sealed commitment (or the fire record), so an open audit can never be missing from the file. Otherwise a run that
stops between the commitment and the file write would let a look pass.

**Open, outside this story:** the A16/G8 builder's register row and freeze-checklist line for the refusal must exist
before the freeze commit. I check that at the freeze verdict.

**Verdict: PASS for 6420714c (story text).** Code waits for the freeze.

## Addendum 2 (15 Oct 2026): 39c2823e (text only after the PASS)

- **Text only:** five files change (the story, the register row, response 202 addendum 3, response 206 and the README
  index). There is no code.
- **Consistent with the record:**
  - the owner's A matches `DESK_DECISIONS.md` line 227 (16 Oct, "G11: at the v4 freeze the AI books' v4 run replaces
    the v2 AI run");
  - `fno/ai`'s v4 ownership is in the register row;
  - the `forecast-capture.yml` fire step is now a named prerequisite owned by the A16/G8/G10 builder, with G11 not live
    until it merges;
  - the cost line follows option A;
  - Depends adds the look refusal.
- **Addendum 1's note is closed:** a row enters `open_audits.csv` in the same commit as the book's collected
  submission.

**PASS for 39c2823e.**

## Addendum 3 (15 Oct 2026): bcb9a3f4 (text only)

- **Text only.** Two files change: the story (5 lines) and response 202 addendum 4.
- **The fire step:** no new or moved schedule. It runs on the push that lands the released pack, with a latest start
  of 14:55 (`V4_LATEST_FIRE` from G10 part 2; a later start is a recorded `not_fired` miss). Collect keeps
  `forecast-capture.yml`'s slot. This is consistent with G10's clock (15:10 deadline) and with the 5-minute fire to
  commitment seen on 15 Oct (some evidence, one day).
- **The story names the real trap:** a push made with an Actions run's own token starts no workflow, so the pack's
  commit must come from the routine's own credentials.
- **For the workflow verdict** (the A16/G8/G10 builder's): I will ask for a real dated run where the pack push started
  the fire, not only a test.

**Cosmetic:** the edited item-7 line runs past 120 characters. Rewrap it at the next edit.

**PASS for bcb9a3f4.**

## Addendum 4 (15 Oct 2026): 085f6c51 (one sentence)

The added sentence: from the books' first live day, `open_audits.csv` always exists (header-only when no audit is
open), so a deleted file is never read as "nothing open". It matches G8's check (judge 209 addendum 1).
**PASS for 085f6c51.**

## Addendum 5 (15 Oct 2026): e1f7ea8c, after ChatGPT review 127 (response 202 addenda 5-6)

**(a) One reconciliation rule replaces `open_audits.csv`: accepted (reasoning on the contract).**
- G11's collect writes exactly one v4 row per scheduled session day of each registered AI slot and started question,
  from `effective_start`, once the day's audit gate settles. The row is `ok` or a definitive miss (`not_fired`,
  including days the fire never ran and BG1 stops, `no_submission`, `late`, `not_revealed`, `invalid`,
  `model_mismatch`, `exposed`, `breach`, `stopped`).
- Before recording a look on date L, G8 refuses if any registered `hybrid` or `ai_team` slot lacks a row for a scored
  session in [`effective_start`, L], `system_late` days excepted.
- **Coverage check (each case the old gate covered, plus those it missed):**
  - an open audit: no row yet, so refused (as before);
  - a sealed commitment never collected: no row, so refused (the old file could not see it, review 127's point);
  - a collect that never ran, or a fire that never ran: no row until collect writes `not_fired`, so refused;
  - a deleted file: there is no file, so there is nothing to delete.

  The new rule covers a strict superset of the old one, so dropping `open_audits.csv` and judge 209 addendum 1's
  file rule leaves no gap. It is also simpler (DRY): G8 reads only the record files it already reads.
- **Two things the text implies, to make explicit in the code round:**
  - collect must write `not_fired` rows for **past** days it finds without a row (a day whose workflow never ran), not
    only for today. Otherwise one lost run blocks every later look until fixed by hand;
  - days before `effective_start` are never required.

**(b) Claim scope: accepted.** Book 2 sees the rules' value, so its errors correlate with the rules'. A better Book 2
score means "the hybrid improves on its frozen baseline", not independent evidence, and Book 3 is the independent
comparison (reasoning only, sound).

**(c) Runtime p50 and p95** by question set from day one, with no second cap: accepted.

**For the coming G8 change** (the A16/G8 builder removes the open-audit gate and the file rule): I will check it has
tests for each case above:
- an open audit (no row);
- sealed but not collected;
- collect never ran;
- `system_late` excepted;
- a day before `effective_start` not required;
- a complete record that lets the look run.

**PASS for e1f7ea8c.**
