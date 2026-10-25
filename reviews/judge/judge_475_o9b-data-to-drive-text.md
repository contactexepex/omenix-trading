# Judge 475: O9b, fetched data out of GitHub into Drive, story text (story/o9-data-to-drive @ 36fdda21)

Judge F. Round 1 of 2. Lane 1 (Drive; forecast and score records' inputs; frozen files). Labels: **strong**,
**some**, **reasoning only**.

## Verdict: FAIL (1 blocking, 1 should fix). The plan's shape is right.

What is right:
- the owner's 22 Oct rows 300-301 are followed exactly (what stays in GitHub; history left as is, with each option's
  cost);
- one five-step method per group;
- the byte-equality criterion;
- restore-to-path for frozen readers;
- step 5 only after a scheduled run on the new path;
- the VIX pilot alone, since only its own CLI reads it (I checked: `fno/vix_history/cli.py` and the workflow);
- one builder for global cues with GC2.

## Blocking

**B1. No gap list (quality rule 2, `docs/JUDGE.md`).** This is an umbrella story, so either list it here (rows 300-301,
O9 rules 1-5, the freeze records, O8 and O10, O5's hook, the 14:00-16:15 merge window, quality rules 5, 6 and 8), or
add one rule: "each step's text carries its own gap list", which I then check per step. Either is fine; saying
nothing is not.

## Should fix

**SF1. The inventory misses readers whose evidence is GitHub's push time [strong: code read].** Step 3 promises "each
reader's output identical", but these readers are not listed:
- **O8, the daily health check:**
  - `fno/health/expectations.py` reads `research/data/intraday` (A16's marks), `nifty-panel/warmup_closes.csv` and
    `nifty-panel/manifest.json` (G1);
  - `fno/health/quote_checks.py` reads `research/data/quotes` (G5's NSE day files beside Groww's markers).
  - O8 judges "on time" by GitHub's push receipt of those files. Once they leave git, that evidence must come from
    each file's receipt push time, or the check reads `unknown` or `missed` every day.
- **v4 scoring:** `fno/forecast_scoring/v4/wiring.py` reads `research/data/intraday` (`RvTable`, "A16's 15:30 run
  commits each day's flag"). That is a scored-record input whose time evidence is the commit.
- **The owner-timing desk:** `fno/desk/owner_timing/wiring.py` reads A16's `SlotLedger` from the same folder (E8 is
  listed; this second reader is not).

Fix expected:
- add these readers to the inventory, with their owners;
- add one design line: wherever a reader's evidence is a data file's push time, it becomes that file's receipt push
  time (O9 already keeps receipts in git for this);
- add a criterion: O8's result for a recorded day is identical before and after each switch, and a receipt pushed
  late is still `late`.

## Minor

The G3 global-cues row names FL1's `facts.py:19` path read. Name `fno/global_cues/cue_calendars.py` and
`check_files.py` too, which also read `research/data/global-cues/` by path. Some are the hand list
`us_market_closures.csv`, which stays in GitHub; say which.

Plants: none (text round).

## Addendum 1: round 2 at fb69fec2

**Verdict: PASS for the O9b umbrella text.** Each step's text is judged on its own, with its own gap list.

| Finding | Answer | Check | Result |
|---|---|---|---|
| B1: no gap list | A gap list here, plus the rule that each step's text carries its own | read | **Accepted** |
| SF1: push-time readers missing | Section 1 names O8's `expectations.py`, `quote_checks.py` and `desk_checks.py`, v4 scoring's `RvTable`, and the owner-timing desk's `SlotLedger`. A design line moves push-time evidence to the receipt's push time. Criterion 7: O8 identical on a recorded day, a late receipt still late, a missing one missed | read; matches the readers I found, plus `desk_checks.py` | **Accepted** |
| Minor: global-cues path readers | Named; `us_market_closures.csv` stays as a hand list | read | **Accepted** |

The builder's own per-group reader index (from a grep of every `fno/` module) found three more readers I had not
named:
- VIX's overlap check reads G1's `warmup_closes.csv`;
- FL1's `sections/global_cues.py`;
- `behind_alerted.txt`, which is alert state and stays.

That is good practice. Each step's claims should cite that index for its group.
