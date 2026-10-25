# Judge 125: story D3b text, a book's timely decision is its first original run (quality rule 1; judge C)

Date: 15 Oct 2026 (UTC). Branch `story/d3b-first-timely-decision` at **5251ddc447b9a3454a3679ad00924a11362ab10e**
(text only: `docs/stories/D-playbook-decisions.md` D3b, response 125), from `main` 49b09b1. Checked against:
- the orchestrator's decisions 58, 59 (b) and 60;
- judge 123 (E5b);
- the code at 5251ddc: `committed_decisions.py`, `decision_store.py`, `book1_records.py`, `evaluation/order.py`,
  `recorded_c4.py`, `decision_timing.py` and `scoreboard/*`.

## Verdict: PASS (text); 4 minor

**The design is right:**
- **The first original run is collected.** Corrections are recorded and shown apart, never collected or scored.
- **One shared order function.** It has a test that no caller sorts by itself.
- **The `-r10`/`-r2` name-sort bug is real.** I checked it: `DecisionStore.runs` sorts by folder name.
- **The builder's key finding is real.** `book1_records.decided_trades` globs every run's records on disk
  (`book1_records.py:34`), committed or not, and the last one with a trade ID wins. The fix (the opening run named in
  the entry day's run log) is the right source.

### The orchestrator's points

**(a) The reader table is complete for order-dependent readers. Two readers are missing (minor 1); neither depends on
order.**

My grep for `DecisionStore`, `DECISIONS_FOLDER`, `SUMS_FILE` and `.runs(` over `fno/` and `tools/` finds 16 files.
Beyond the table:
- `fno/desk/recorded_c4.py` reads the **collected** run's record and its `edited` check (`recorded_c4.py:24-32`), so it
  follows the collector.
- `fno/playbook/decision_timing.py` judges one given run and has **no caller** today.
- `book1_orders.py` builds orders from the run E3 hands it.
- `book1.py` (E5b) checks only whether a run exists.
- `no_decision.py` writes the marker file.
- `forecast_scoring/score_sources.py` matched on its own `RECORDS_SUFFIX` (`_forecasts.csv`), which is not a decision
  run.

Nothing in `market_read_models`, `cards`, packs or `tools/` reads decision runs.

**(b) Commit time as the key: two runs in one commit, and clock skew.**
- **One commit holding two runs:** both have the same commit time, and the counter as a number orders them. That is
  covered.
- **Clock skew (minor 2, reasoning only).** Commit time is the committing checkout's own clock.
  - Two checkouts racing on one book (both commit, one push is rejected, it pulls with a merge and pushes) give two
    commits on parallel branches. With a fast clock, the later decision can carry the earlier time and be collected as
    "first".
  - If the second commit was made after pulling the first, the first is its **ancestor**. Ancestry is the true landing
    order and immune to skew.
  - Suggested rule: order by ancestry where it decides (`git merge-base --is-ancestor`), and by commit time only for
    commits on parallel branches.
  - The risk is small: cloud clocks are synced to within seconds, and E5b prevents a second Book 1 run. But this story
    is the guarantee "whatever writes the run".

**(c) Can an uncommitted run ever be collected? No.**
- The collector's `_decision` returns None when no commit added the run's `records.sha256`
  (`committed_decisions.py:50-55`), so an uncommitted run has no commit time and is never compared with the deadline.
- "Sorts after committed runs" only places it in the run log's list.
- S1's `first_counted_decision` already asks git for each run's `records.sha256` (`order.py:61-62`). The shared order
  must keep "uncommitted is never first counted": say so in criterion 4b.
- A run committed locally but not pushed is a separate case, governed by E3's unchanged visibility rule. In the daily
  run's checkout, E2b's stray-commit refusal stops the run at its next commit (fail closed).

**(d) Trades opened by a run that later gets a correction: right, with one gap (minor 3).**
- The trade follows its opening run, and a later record naming the trade is alerted once and shown apart. That is the
  correct rule: a correction is information, never a change to a live position.
- **The gap:** the story makes the entry day's run log the source of the opening run. It does not say what happens when
  that log is missing, or names a run whose folder or `records.sha256` no longer matches.
- Say: alert once and never fall back to "the latest record". Also say how the trade's exits keep running in that case,
  since design 9 requires risk-reducing exits always to run, for example from terms held with the open position, or
  refused with an alert naming the trade.

## Minor

1. **Add the two missing readers to the table:** `recorded_c4.py` (reads the collected run; follows the collector) and
   `decision_timing.py` (one given run; no caller).
2. **Order by ancestry where it decides, commit time otherwise** ((b) above), or state why commit time alone is enough.
3. **State the opening-run fallback** ((d) above): run log missing or mismatched means an alert, never the latest
   record, and the exits' behaviour is named.
4. **Today `decided_trades` also counts trades from runs that were never collected or never filled**, for C2's view of
   the book (`book1_records.py:31-40`, "every trade the book's committed records chose"). With the opening-run rule,
   say that only trades opened by fills, from their opening run, are in the book, and add that to criterion 5's test.

## Project rules

- Lane 1, since it decides which decision trades. Rule 9 applies: ChatGPT after my code PASS.
- `fno/evaluation/order.py` is in no freeze: `research/evaluation/` holds no `FREEZE_v*.md` on `main` (checked).
- With criterion 7, any existing test that asserts the "latest timely run" must be named with its reason, which keeps
  changed tests visible.

**Verdict: PASS for 5251ddc447b9a3454a3679ad00924a11362ab10e** (story text). Code may start. Minors 1-4 go into the
text or the claims, and I check them in the code.

## Note (15 Oct 2026): the owner's "keep the design simple" rule

Under `docs/DESK_DECISIONS.md`, 15 Oct row "Keep the design simple", a judge's finding needs a path that happens in
the normal running of this system. Under that rule:
- **Minor 2 (ancestry for clock skew) is withdrawn.** It needs racing checkouts with skewed clocks.
- **Minor 3 (a missing or mismatched opening run log) becomes one line under the story's Known limits, with no code.**
  After E2b, the run log is committed with every step.
- **Minors 1 and 4 stand.** Minor 1 is text only. Minor 4 is a real path: a chosen trade that does not fill is a normal
  outcome.

## Addendum 1 (15 Oct 2026): D3b code at 5ff83b2e16c67b223ba412b6e56dee480a08e9ff

Judged under the owner's "keep the design simple" rule: only paths from normal running, no planted mutations.
- Gates: 4,992 passed; ruff, format and imports clean.
- `main` merged in: `merge-tree` with `origin/main` shows no conflict, and `main` has 8 commits since.
- The story's own tests: 27 of 27 pass (first timely, opening runs, run order, one-order guard, S1 order, uncollected
  runs).

## Verdict: PASS (code)

| Real path | Status | Evidence |
|---|---|---|
| The collector takes the first timely original run, and a late first run gives nothing | MET | `committed_decisions.py` `committed()` goes through `ordered_runs`, skips uncommitted runs and corrections, returns the first, and returns None when that one is at or after the deadline. The decisions step records the other runs, with corrections, as `others` |
| `-r2`/`-r10` order for every caller | MET | `run_order.ordered_runs` sorts by commit time, then `run_counter` as an int; uncommitted runs come last. My probe: r1, r2 and r10 with one commit time, plus an uncommitted r11, give r1, r2, r10, r11. Its callers are the collector, `others`, S1's `first_counted_decision`, and Book 1's alert listing (counter, never chooses). `test_one_run_order` guards against a caller sorting by itself |
| Book 1's terms and exits come only from each filled trade's opening run | MET | `opening_runs` reads the entry day (first `FILL_OPEN`) and that day's run log, and checks the run against its own `records.sha256`, so a shallow clone works. `opening_trades` takes the chosen record only from that run, and other runs naming the trade are only listed (`other_runs`, alerted at each review). Unfilled chosen trades no longer count, so my minor 4 is closed |
| C2's book view fails closed | MET | `recorded_terms` holds filled trades with an opening run only. An open trade without one raises `RiskInputError` in `book_view._open_trade:33-34`, so C2 refuses |
| Exits for a trade with no opening run | MET | There is no time exit, with an alert naming why. E4's own risk-reducing exits (protection unverified, expiry settlement, an exit already ordered) still run, as the `book1_exits` docstring states (design 9) |
| S1 unchanged on r1-r9 | MET | `test_order_runs` (criterion 4b). An uncommitted run is never first counted, because it has no commit |
| Corrections shown apart | MET | `CommittedRuns.uncollected` lists them for scoreboard B, never scored (`test_uncollected_runs`) |

**Note (does not change a trade):** `DecisionStore.every_run` and the old `decided_trades` listing order are used
only to read all runs and to list them in an alert. Nothing "first" depends on them.

**Verdict: PASS for 5ff83b2e16c67b223ba412b6e56dee480a08e9ff** (code). Rule 9: ChatGPT next, then the merge (pull,
full suite on the merged tree).

## Addendum 2 (15 Oct 2026): merge check of 3760640

- **The merge is clean.** 3760640 is a `--no-ff` merge of 5ff83b2 (my PASS) into 3cba029. Its tree
  (`7271bbf…`) equals git's own `merge-tree` of the two parents byte for byte, so no hand edit was made in the merge.
  Against the first parent it carries exactly the PASSed diff: 28 files, 851 insertions and 75 deletions.
- **Gates on the merged tree:** 5,198 passed (the orchestrator's figure); ruff and imports clean.
- **ChatGPT review 107** came before the merge (rule 9). The one change it asks for (an integrity alert when a book
  has more than one original run on a day) goes into E5b's code, and I check it there.

**Merge check: MET.**
