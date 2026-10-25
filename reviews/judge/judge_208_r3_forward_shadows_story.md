# Judge 208: R3 story text, first forward shadows (judge G)

- **Judged:** `story/r3-forward-shadows` at `2ad91597` (builder session 0145TfSwzmpk6MBrH92f5h4G): the R3 section of
  `docs/stories/R-factory.md`, a work-register row and `response_201`. Quality rule 1 (story text before code),
  lane 1. 208 (first written as 206; 206 and 207 were taken by other judges at the same time).
- **Verdict: FAIL (text).** One should-fix: Book 1's scoring isolation is not specified or tested. There are also 3
  notes. The code claims are true, the E8 split is clean, and the trial rule matches the factory rules.

## The orchestrator's points

1. **The crash claim is true (strong evidence, code read on main).**
   - `RuleEvaluator.evaluate` calls `shadow_books.account(strategy)` for every `playbook.shadow_on(day)` version
     (`fno/playbook/evaluate.py:52-53`) with no handler.
   - `JournalShadowBooks.account` raises `ValueError("... has not been started")` (`fno/desk/shadow_books.py:38`).
   - `start_shadow_books` (`fno/desk/wiring.py:49`) is called only in `tests/desk/test_shadow_books.py:35-36`.
   - So the first `research` registration stops Book 1's whole evaluation that day, not just the shadow's.
   - **There is a second crash path the text understates.** `_parts` passes Book 1's `recorded_terms` to every shadow
     book (`fno/books/book1_wiring.py:92-94`), and `load_risk_book` indexes `terms[trade.trade_id]`
     (`fno/risk/book_view.py:40`). Once a shadow holds a trade, its ID is not among Book 1's terms, so the run raises
     `KeyError`. Criterion 2 fixes this; the context should say the wrong terms are a crash, not only wrong figures.
2. **Shadows never touch Book 1's account.** Accounts are isolated, as the text says:
   - D2's `real.overlap` check refuses a shadow that would draw on a real account (`evaluate.py:54-57`);
   - each shadow writes only `journal/shadow/<name>-v<n>/account/`;
   - criteria 3, 4 and 9 and test plan item 4 cover the accounts.

   **Scoring is not covered.** See the finding.
3. **E8 is the only fill path:**
   - "no separate shadow fill step";
   - criterion 6: nothing fills a shadow before E8's code;
   - E8 never creates an account, and a missing account fails loudly;
   - the E8 builder's agreement is recorded.

   It is consistent with E8's scope ("every paper entry and exit of every book and shadow candidate",
   `E8-owner-timing-fills.md:243`). The interface names are reasoning only until E8 part 1b, which is stated.
4. **The trial-count rule for screened ideas** ("a ledger row first; the trial count includes screened-out ideas")
   matches `research/FACTORY_RULES.md:23-24` and `:74`: every idea is a trial from G0, and screened-out ideas stay in
   the count. `research/ledger.csv` already holds 54 trials (W1-W5, R2, FT1 included). B0 would be trial 55, labelled
   `measurement`, never promoted, as `FACTORY_RULES.md:90` allows.
5. **The two owner questions, as slots.** Both are stated plainly, with options, a recommendation and its evidence
   label:
   - Q1: register B0. "Some evidence on cost, reasoning on exercising the path" is honest.
   - Q2: build order. Its answer A is supported by the real crash above.

   The text is complete for either answer: B0's registration is "(if yes)", and the account opening stands alone.

## Findings

### Should fix

1. **Book 1's scoring isolation is unspecified and untested.**
   - Shadow orders are written by Book 1's own order writer "in the day's journal", with account `shadow:<name>-v<n>`.
     The text does not say which journal: the shadow account's, or Book 1's run folder.
   - Criterion 9 ("nothing changes a book's account, decision or fill") names none of Book 1's readers:
     - E5's one-decision-a-day and its trade counts (`DeskTradeCounts` on Book 1's records);
     - E6's book (non-shadow) scorecard section;
     - S2's scoreboard B for Book 1;
     - S3's scoreboard A.
   - **Path:** every shadow order on every day a shadow fires.
   - **Fix:**
     - name the location: the pending order lives in the shadow account's own journal, or, if it must sit in a shared
       day file, every Book 1 reader filters by account;
     - extend criterion 9 and test plan item 4: with one book trade and one shadow trade on the same day, Book 1's
       trade counts, E6's book section, S2's Book 1 board and S3's Book 1 actions are byte-identical to a run without
       the shadow.

### Notes

1. Say in the context that Book 1's terms reaching a shadow is a crash (`KeyError`, `book_view.py:40`) once a shadow
   holds a trade, not only a wrong figure.
2. **B0's stop ("a single loss above Rs 10,000"):** say who stops it and how, for example a playbook status change by
   the owner or desk on the scorecard's alert. Otherwise the "measurement" label carries no mechanism. A one-line
   procedure is enough.
3. **Test B:** "zero shadows still give undecided" is right. With B0 only, Test B gets about 12 trades a year and stays
   "undecided" for years. That is fine (response 92's own estimate), and worth one line next to Q1 so the owner reads
   it there.

## Project rules

- **Register:** the work-register row is added, with the E8, G8 and S3/S6 overlaps agreed.
- **Simplicity and reuse:** there is no new fill or exit code, and the existing `start_shadow_books` and E8's path are
  reused. The change is small.
- **Discipline:** nothing is registered without the owner, and nothing is invented to fill the queue.

## Addendum 1: re-judge at `5605b224` (judge G)

**Verdict: PASS (text).**

- **Should-fix 1 is accepted, and it is a real leak, not only a text gap.** I checked it in the code:
  - `decision_record._action` maps `Decision.SHADOW_TRADE` to `chosen_action: "trade"` (`fno/playbook/decision_record.py:45-46`);
  - D2 writes shadow records into Book 1's own decision folder;
  - `book1_records._chosen` checks only `chosen_action` and the structure, never `mode` (`fno/books/book1_records.py:104-110`).

  So Book 1's opening trades and terms would take a shadow trade as Book 1's own. The revision fixes this:
  - every Book 1 reader skips `mode: shadow`;
  - a shadow's orders, fills and account live only under `journal/shadow/<name>-v<n>/`, so the journal is now named;
  - criterion 9 lists each Book 1 reader (E5's counts and one-decision rule, opening trades and terms, E6's Book 1
    section, S2's Book 1 board, S3's Book 1 actions);
  - test 4 compares each reader with and without the shadow, and a planted mode-blind reader must fail.
- **The builder's correction on the error type is accepted; I was wrong.** `_open_trade` checks
  `trade.trade_id not in terms` first and raises `RiskInputError("... has no recorded terms ...")`
  (`fno/risk/book_view.py:37-39`), not `KeyError`. It is still a crash of Book 1's evaluation, because
  `evaluate.py:52-53` has no handler. The context now says so.
- **B0's stop: partly accepted, with one wording fix to the text.**
  - The code facts are right: C2's per-trade cap prevents an oversized B0 trade; a research version is alerted, never
    paused (`fno/scorecard/pauses.py`); retiring is owner-only (`fno/playbook/transitions.py:19`).
  - So my note's "by the owner or desk" was wrong on the desk.
  - But the text says this is "against judge 208's note that it needs none". My note said no such thing: it asked who
    stops B0 and how. Please reword it to "judge 208 asked who stops it: the owner, on E6's alert". This is minor and
    not blocking.
- **Test B's line is added.**
- **The owner's decisions are in.** 1 A (B0 registered after the build) and 2 A (account opening, per-shadow terms and
  the Test B path now; orders and fills with E8 part 1b) are recorded, and the criteria are split to match.

**Addendum 1 note (builder's correction at `d0ad58ca`): agreed.** The leak was latent, not live:

- `opening_trades` keeps only trade IDs in Book 1's own filled-trade openings (`book1_records.py:56-66`). A shadow
  record that `_chosen` picks up is never used unless its ID matches one of Book 1's filled trades, and shadow IDs
  carry the `shadow-` prefix.
- Isolation rested on that prefix alone. R3's explicit `mode: shadow` check makes it hold by rule.
- Criterion 9 and test 4 are unchanged and still right.

## Addendum 2: text `d10f2e91` after ChatGPT review 129 (judge G)

**PASS (text).** `git diff 5605b224 d10f2e91` changes only R3's text, plus review 129 and response 208. The changes:

- B0 is labelled `measurement` on every output that shows it (E6, the tracker, the post-mortem), and it is excluded
  from G6 promotion and from every candidate count.
- E6's B0 alert has review 129's wording, and a second loss escalates as a possible simulator defect.
- Criterion 8 is extended to match.
- The latent-leak correction is written into the context.
- My misquote note is fixed: "Judge 208 asked who stops it: the owner, on E6's alert".

All of this is consistent with `transitions.py` (retiring is owner-only) and `pauses.py` (research is alerted, never
paused).
