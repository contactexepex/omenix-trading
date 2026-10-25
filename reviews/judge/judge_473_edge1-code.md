# Judge 473: EDGE1 code, freeze and protocol revisions 4-6

**Scope:** story/edge1-build at 3152ed44 (FREEZE.md; code frozen at b4a9a855), builder session_01UkTaDeTRF9ksDgQB9cTU5C.
It covers protocol revisions 4-6, the 19 study files, the two shared engine changes and the tests. Round 1 of 2.

**Verdict: PASS.** Nothing blocking, nothing to fix. Three conditions apply to the runs (none needs a code change).

## Gates (my run, on 3152ed44)
- pytest `-n auto`: 9904 passed, 16 xfailed.
- `ruff check` and `ruff format --check`: clean (research/edge1 included).
- `check_imports`: clean.
- Freeze hashes: all 21 FREEZE.md hashes (PROTOCOL, LOT_CHECK, 19 .py) and the 2 shared engine hashes match the
  files. b4a9a855..3152ed44 adds FREEZE.md only.

## Checked
- **Shared engine changes.** Neither changes an existing caller: `ShortCondor(offset)` defaults to CONDOR_OFFSET, and
  `resampled_means(block=)` defaults to BLOCK_LENGTH. Apart from these two files, the code this study imports is
  identical on origin/main today (config.yaml, costs, research_engine, factory, scoreboard, itm_chance, research_data,
  price_ranges, fo_bhavcopy, nse_margins).
- **Seal (rev 3 and 468.4).** Rows are cut at load, then relabelled; the NIFTY panel is sealed, then relabelled. The
  order is correct as read; no test covers it, which the builder states as gap 1. Run 1's settlement is called only
  for expiries on or before the seal.
- **Expiry relabel (rev 6).** It is keyed by the future's (year, month). Every move named (28 Jun 2023, BANKNIFTY
  Mar 2024 and Jan 2025, Tuesday Sep 2025) stays inside its month, because "last X of the month" never crosses one.
  Options move only on days when a future carries their date, so weeklies are untouched.
- **Lots (rev 5).** UDiFF starts on 1 Jan 2024, so NIFTY's 2024 changes (50 to 25 to 75) and BANKNIFTY's (15 to 30
  to 35) come from NewBrdLotQty, not the schedule. The legacy schedule matches NIFTY 75 then 50 from Jul 2021, and
  BANKNIFTY 20, then 25 from Jul 2020, then 15 from Jul 2023. A trade keeps its entry day's lot.
- **Trades.**
  - Entry happens only if every leg traded, at the widest width that fits the cap.
  - SL2 fires at 3 x credit and TP50 at 0.5 x credit, strictly between entry and the T21 day, on fully traded days.
  - EXP trades have no exit pad, and settlement STT falls on long ITM legs only (`fno.costs`: closing side sell).
- **Statistics.**
  - G1 = the t-bound on sd_gross minus cost minus `Tail.extra_loss`, the same as `MeasuredGross.edge` in `factory
    screen`.
  - p is re-centred, with +1/(B+1); Holm runs across both indices; k is fixed by sorted names; the floors are 30 and
    20.
  - The nomination's 4 conditions match section 11. Ordering by raw p equals ordering by Holm-adjusted p.
  - Expected run-2 cycles = 44, which matches the probe.
- **Rev 4 (card order).** It follows the factory's own gate order (G1, then G2, then G3); measurements are cards with
  `measurement: yes`.
- **Owner's block-2 line** (section 10, lines 192-193) and the 468.3 against-cap rows: present.

## Plants: 14 of my own, 4 caught
- **Caught:** narrowest width first; panel options not relabelled; lots not relabelled.
- **Equivalent on real data** (they cannot change any result):
  - trigger allowed on the T21 day (same close, label only);
  - run-1 decisions to 14 Feb 2023 (the expiry filter drops them all);
  - lot change `>` instead of `>=` (no expiry falls on the 1st).
- **Survived on decided figures; the current code is correct, as read above:**
  - tail at 3x instead of 2x (G1);
  - G1 bound on sd_net instead of sd_gross (G1);
  - settlement STT sides swapped (EXP net);
  - nomination's run-1 mean on all trades instead of complete ones;
  - RUN1_YEARS 3 (G3's frequency).
- **Survived on report figures only:** p without +1; drawdown unsorted; against_cap dropping trigger exits.

These survivors are not a should-fix. The code is frozen, so any edit breaks the guard's hash, and no normal run
reaches them. Tests are outside the guard, though, so the builder can add the five decided-figure tests without a
re-freeze. Recommended, not required.

## Conditions on the runs (no code change)
1. **Both runs on the frozen engine.** `fno/`, `config.yaml` (its `charges` table, read at run time) and the shared
   files must be byte-identical between the run-1 and run-2 commits. Never merge `main` into the branch between the
   runs; the guard does not check these files. At reproduction I check `git diff <run1> <run2> -- fno config.yaml`;
   a non-empty diff means run 2 is invalid.
2. **Copy G1 inputs exactly.** Each card's G1 inputs are copied from selection.json's `g1.inputs`: `mean_gross`,
   `sd_gross` (not `sd_net`), `n`, `mean_cost`, `tail_share`, `tail_mean_loss`. I check every card against
   selection.json at reproduction.
3. **Probe stays out of the frozen folder.** Gap 2 (the probe outside the repo) needs no commit: run 1's
   `cycles`/`not_taken` figures restate its counts. A probe committed under research/edge1 would need a hash
   (re-freeze).

**Next:** run 1. I reproduce selection.json byte for byte and check the cards; then run 2.

## Addendum 1

**Scope:** run 1 (selection.json at d4ea08d6, from frozen 3152ed44; 5fc0c445 adds tests only) and the builder's
proposed deviation after the freeze, for exit prices that cannot be real. Round 1 of 2 on this deviation. Run 2 has not
been read.

**Verdict on the deviation: ACCEPTED IN PRINCIPLE, with three changes (below) before the re-freeze.**

**The problem is real.** I checked 2 of the 3 cases against the committed NIFTY panel:
- 8 Aug 2019, the 29 Aug expiry:
  - 11650 PE closes at 715.20 on a volume of 3 contracts, while NSE's settlement price is 600.35;
  - 11350 PE closes at 323.10;
  - the put spread is 392.1 on a width of 300.
- 21 Dec 2020, the 28 Jan expiry:
  - 13300 PE closes at 339.60 on 5,176 contracts;
  - 13150 PE closes at 183.15 on 3 contracts;
  - the spread is 156.45 on a width of 150.

The root cause is the engine's `leg_price`: a traded leg uses `close`, the last trade, which on a fast day can be hours
old for a thin strike. NSE's settlement price is no cure: in the 2020 case it equals the stale close. A validity check
is the right fix.

**Why I accept it after the freeze.**
- It is a validity rule, not tuning. It is triggered by prices that cannot exist, and it removes wins and losses alike
  (the +21,533 trade is above its own maximum gain of 18,850; the -15,810 trade is beyond the cap).
- Run 2 is unread.
- Run 1 is already exploratory. The re-run is a labelled second look, and both selection.json files stay committed.
- Keeping the frozen result (option B) would send BANKNIFTY SF TP50 to run 2. It was picked partly on one impossible
  trade: without that trade, its mean falls from 2,250 to 1,286. That is the worse error.

**Changes required (each a should-fix for the re-freeze):**
1. **Check each vertical, not only the position.** For every bought-sold pair of the same type (SF and SC each have a
   put spread and a call spread), require 0 <= spread value <= width. A position total can hide two violations that
   offset each other: a put spread inverted by 100 plus a call spread at 150 sums to 50, inside the position's bounds.
   Apply this one rule identically at entry (today's `bad_prices` is position-level only), at every trigger day and at
   the T21 exit.
2. **No impossible price in the "all trades" figure.** A T21 exit on an invalid day is flagged `incomplete_exit` and
   kept out of the decided mean, as proposed. But nomination condition 3 and `all_mean_net` include incomplete exits.
   There, value each failing vertical clipped into [0, width], labelled as a proxy, never at the raw close.
   Otherwise -15,810 (beyond the cap) and +21,533 (beyond the maximum gain) still enter condition 3.
3. **Report the bias of the exclusion.** Stale prices come from fast days, which are mostly losing days for short
   premium, so dropping those exits flatters the decided mean. Each variant reports its invalid-day count (entry,
   trigger days skipped, exits) and the decided mean beside the clipped all-trades mean.

**Limits to state in section 14:**
- A stale price inside its bounds cannot be detected.
- NS and NT have no bounds, so this rule does not touch them.
- `leg_price` is shared: the simulator, STR1 and FT1 use the same last-trade close. The orchestrator should decide
  whether experiment 1's results need the same check. That is outside EDGE1.

**Next:**
1. The builder writes section 14 and the code, with tests and plants for changes 1-3, and re-freezes.
2. I judge that (round 1 of the code deviation).
3. Run 1 is re-run, and I reproduce both selection.json files.
4. Run 2 follows.

## Addendum 2

**Scope:** EDGE1 revision 7, re-frozen at 312c10c4 (rule commit f43006c0). Round 1 of 2 on revision 7. The
orchestrator asked: is it one general rule, and is it not tuned to the passer?

**Verdict: FAIL.** The rule is general, but it leaves out two of 473.1's three required changes. The builder's message
crossed 473.1, so this is the first time these points reach that code.

**Passes the orchestrator's question.**
- `_possible(legs, prices)` has no index, structure, exit-rule or date branch.
- The same `run_trade` serves run 1 and run 2.
- EXP is untouched.
- `fno/` and `config.yaml` have no diff since 3152ed44, so 473's run condition 1 holds.
- On NS and NT the bounds are (-inf, 0], so the rule never bites there, as 473.1 expected.
- `selection_rev6.json` is kept with its hash in FREEZE.

**Should-fix 1: check each vertical, not only the position (473.1 change 1).** A stale price can invert one spread
while the other spread offsets it.
- The run's own case, BANKNIFTY SF TP50, Nov 2021: the put spread is inverted by 204.75 (long 37400 at 1960.40 above
  short 38300 at 1755.65), and the mark is -131.75.
- Had the call spread closed 206 instead of about 73, the mark would be about +2. That is inside [0, 754], so the
  impossible put inversion passes and the target can still fire on it.
- Fix: for each bought-sold pair of the same type, require 0 <= spread value <= width. Apply the same check at entry:
  today's `bad_prices` is position-level only, so section 14's line "entry already refused such prices" is true only
  for the total.

**Should-fix 2: the all-trades mean still uses the impossible prices (473.1 change 2).**
- Section 14 says an impossible exit is "in the all-trades mean". That mean feeds nomination condition 3
  (`all_mean_net`, `all_mean_net_pad2`).
- So NIFTY SF T21's -15,810 (beyond the Rs 10,000 cap, at a spread of 392 on a 300 width) still enters a deciding
  condition at a price that cannot exist.
- Fix: in the all-trades figures, value an impossible exit with each failing vertical clipped into [0, width],
  labelled as a proxy.

**Note: reporting (473.1 change 3), done in part.** `impossible_exits` is counted. Add the number of trigger days
skipped as impossible, per variant, so the owner can see how often a stop or target was suppressed. The decided mean
sits beside `incomplete_mean_net` already.

**Plants:** none run this round, because the design gaps decide the verdict. The plants on the vertical check and
the clip come with the fix.

**Next:** fix 1 and 2 plus the skipped-day count, then re-freeze. Round 2 of 2 on revision 7. Run 1 is not re-run
before that.

## Addendum 3

**Scope:** EDGE1 revision 7, re-frozen at bf2d9e4e (code 0cad8879). It replaces 312c10c4 and answers 473.1 and 473.2.
This is round 2 of 2 on revision 7.

**Verdict: PASS.** Run 1 may be re-run from bf2d9e4e.

**Gates (my run, on bf2d9e4e):**
- pytest: 9922 passed, 16 xfailed.
- `ruff check`: clean. `check_imports`: clean. `guard.check_code`: passes.
- No diff in `fno/` or `config.yaml` since 3152ed44, so condition 1 holds.
- `selection_rev6.json` = d4ea08d6's selection.json (sha256 edc4fd83...).
- The rev-6 hash table is kept in FREEZE.md as history; the guard reads only the "## Analysis code" table, which
  matches the files.

**473.1 and 473.2 are met.**
- **Each vertical, plus the position.** `verticals.valid` requires every sold-and-bought pair of the same type to lie
  in [0, width], and also the position bound. It runs at entry (`impossible_prices_at_entry`, then the next width, as
  for untraded legs), on every trigger day (skipped and counted) and at the T21 exit.
- **The builder's push-back is correct, and I accept it.** For a condor, each vertical can be valid while the
  position is worth more than one width, because only one side can finish in the money. So keeping both checks is
  right; my word "replacing" was wrong.
- **The all-trades figure.** An impossible T21 exit uses `proxy_value`: each failing vertical clipped, then the
  position clipped into its bounds. `raw_net` keeps the raw figure. `all_mean_net` and condition 3 never see the raw
  close.
- **Reports.** Each variant reports invalid entries in `not_taken`, `trigger_days_skipped`, `impossible_exits` with
  their raw mean, and the decided mean beside all-trades.
- **No variant branch.** NS and NT have no verticals, so `valid` returns True. The orchestrator's question is
  answered again: one general rule.

**Read and correct:** the proxy gross (proxy_value minus the entry value) x lot equals `PositionCosts.gross`'s
convention (sum of side x (exit - entry) x lot).

**Plants: 10 of my own, 6 caught.**
- **Caught:** verticals across types, clip only below, no position clip, proxy not applied, skipped days not
  counted, no entry check.
- **Survived:**
  - the vertical's upper bound dropped (redundant: with both verticals at 0 or more, a vertical above its width puts
    the position above its bounds);
  - the vertical's lower bound dropped;
  - the proxy gross sign flipped;
  - entry stopping instead of trying the next width.

  The lower-bound survivor is the offsetting case from 473.2 (one inverted spread hidden by the other). It is correct
  as read and frozen, so it is not a should-fix, but it is worth a test: tests are outside the guard, so no
  re-freeze is needed. Add tests for the sign and the next width too.

**Note:** `ruff format --check` would reformat `mutation_proof.py`: `# fmt: skip` does not cover a tuple spread over
several lines. Neither CI nor JUDGE.md gates format on research/, and a fix would change a frozen hash. Leave it.

**Next:** re-run run 1 from bf2d9e4e. I reproduce both selection files and check that the cards' G1 inputs come from
the new one; then run 2 under the same code.

## Addendum 4

**Scope:** EDGE1's three run outputs, the factory gates and the results file. The outputs are run 1, original and
corrected (selection_rev6.json at d4ea08d6, selection.json at 81f02afe), and run 2 (final.json at 1e43260c). The
gates are on main; RESULTS.md is at c259a454. Round 1 of 2 on RESULTS.md.

**Verdict: runs REPRODUCED; RESULTS.md FAIL** (two wording and label fixes; no number is wrong).

## Reproduction (my runs, through Drive, guard passing)
- **Run 1, corrected:** `study.py --select` at 81f02afe matches byte for byte (sha256 1f398d57...).
- **Run 1, original:** at 3152ed44 it matches byte for byte (edc4fd83...).
- **Run 2:** `study.py --final` at cee43008, in a clean clone so the read-once check applies, matches byte for byte
  (61f308f2...).
- **Code between the runs:** bf2d9e4e..cee43008 changes tests only, and `fno/` and `config.yaml` are unchanged, so
  473's condition 1 holds.

## Factory and cards
- The 24 cards match selection.json: every G1 input, by script (e7a2029d).
- gates.csv: 28 G0 rows; G1 23 screened_out and 1 passed (trial 94: bound 1214.4, cost 606.3, net 608.1, as
  selection.json says); G2 exploratory; G3 exploratory_shadow with n = (1.6449 x 4250.57 / 608.1)^2 = 132.2, so 133,
  which is 25.33 years at 5.25 trades a year.
- final.json: tested [BANKNIFTY SF TP50]: n 40, mean -337 (Rs 2 pad -530), all-trades -432, p 0.9091, Holm
  false; nominated [].
- RESULTS.md's run-2 and naked-measurement tables equal final.json.

## Should-fixes in RESULTS.md
1. **The answer overstates its scope.**
   - Defect: "No simple rule-based variant made money after real costs out of sample." Only 1 of the 24 variants was
     run out of sample. The other 23 failed G1 on run 1 and, by section 11, were never run in run 2.
   - Test it must pass: the answer says that the one run-1 passer lost money in run 2, and that the other 23 failed
     run 1 and were not tested out of sample. The bracketed "no edge found among these 24 variants" can stay.
2. **Figures with no committed source are not labelled.**
   - Defect: the "Today's lot (30) re-run" row (2,244 and -473) and the take-profit marks (lowest mark over credit,
     median 0.93, min 0.52) appear in neither selection.json nor final.json and are not in the protocol. The builder
     says the marks were checked after final.json was committed.
   - Test it must pass: each is labelled "post-hoc, after run 2, not decided on", with the commit or script that
     reproduces it. Otherwise remove it.

**Note (no action):** the statistician's "about 2.4 passes by chance" is labelled reasoning only and is right as an
upper figure (10% x 24).

**What stands:** no variant is nominated. The one candidate reversed out of sample (p 0.91), and its sample plan
needs 133 trades, about 25 years. The naked measurements show the tail the cap exists for (single losses 2.6-8.5x
it).

**Next:** fixes 1 and 2 in RESULTS.md, then round 2.

## Addendum 5

**Scope:** RESULTS.md at e35b7f62 (story/edge1-build). Round 2 of 2 on the results.

**Verdict: PASS.**

- **Fix 1, met.** The answer now reads "None of the 24 variants passed both runs ... 23 failed run 1's cost screen and
  were therefore not tested out of sample (section 11); the one run-1 passer lost money in run 2". The evidence
  label is narrowed to "these 24 variants show no edge after costs".
- **Fix 2, met.**
  - Each post-hoc figure is labelled "post-hoc, after run 2, not decided on" and names its script in
    `research/edge1-posthoc/`. That folder is outside `research/edge1/`, so the guard and the freeze are unchanged.
  - "Never fired" now cites final.json, whose exits are all planned.
  - I ran `today_lot.py` from e35b7f62: run 1 gives 21 complete trades with a decided mean of 2244; run 2 gives 40
    complete with -473. Both equal RESULTS.md.
- **Stated limit, accepted.** Section 12 asked for today's-lot figures beside every variant. The frozen outputs do not
  carry them, and RESULTS.md says so. It is a report figure only and decides nothing.

**EDGE1 is complete on my side:**
- protocol rev 7: frozen and judged;
- runs 1 (both) and 2: reproduced byte for byte;
- gates: G0 to G3 logged;
- results: honest about scope.

The answer is no simple rule found among these 24 after costs, and no nominee. The branch's merge into main (it
touches `fno/`) follows the orchestrator's timing: on or after Mon 26 Oct, never 14:00-16:15, as a merge commit so
the frozen commits stay in history.
