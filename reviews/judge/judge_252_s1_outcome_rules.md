# Judge 252: S1, the rules that decide an outcome, and the widened closure walk (judge A, lane 1)

**Checked:** `story/s1-outcome-rules` at `4effa3aa684339709ee43c4f13148ba50f10e78b` (the R2/G7 builder). The diff is
3 files:
- `PROTOCOL.md` `frozen_files` gains the "Rules that decide an outcome" bullet (`fno/scorecard/pauses.py`,
  `fno/playbook/run_order.py`);
- `test_scoring_closure.py` walks from every hashed module and gets five new exemptions;
- `test_scoring_files_frozen.py` pins the two files.

**Verdict: FAIL, 1 should-fix (an integration with main), no blocking.** The widened walk and the five exemptions are
sound. But on a trial merge with today's main, the closure test fails.

## The widened walk: sound

- It now starts at the scoring packages and at every hashed `.py`. That is the right closure: a hashed rule's own
  imports must be hashed or exempted too. It is what found `order.py` → `playbook/run_order.py`.
- **`pauses.py` hashed:** E6's automatic pauses decide which trades exist to be scored. That is the code behind
  `catastrophic_loss_strategy` and `immediate_pauses`, my note in 229 addendum 3.
- **`run_order.py` hashed:** it decides a day's first decision run for the freezer's order check and E3's collector.
- Both are pinned by `test_the_rules_that_decide_an_outcome_are_hashed`. My plant (`run_order.py` dropped from the
  bullet) fails 4 tests.

## The five exemptions: accepted, each checked

| Module | Used by the hashed code as | Ruling |
|---|---|---|
| `desk/trade_counts.py` | `version_key` (pauses): `"<name>-v<n>"` → (name, n) | a tag parser; no figure |
| `desk/pack_items.py` | `available_time` (run_order, line 71), on the commit time git reports | git times carry their offset, so the parse is fixed; acceptable |
| `playbook/lifecycle.py` | `StatusChanger` (pauses): writes the status the hashed rule chose | applies, decides nothing |
| `playbook/loader.py` | `Playbook` (pauses): reads the committed playbook files | a reader of committed rows |
| `alerts/sender.py` | sends the #fno-desk line | decides nothing |

## Should-fix

**SF1. On today's main the widened walk finds `fno/scorecard/measurement_alerts.py` unaccounted, so the branch is
red after the merge.**
- **Evidence:** B0's registration is now on main (R3, judge 229 addendum 3). Its `pauses.py` imports
  `measurement_alerts.py` (`single_loss_text`, `cumulative_text`). Once `pauses.py` is hashed, the walk reaches it.
- On the trial merge with origin/main ef7ca659 (tree 9ca6472):
  - `test_every_module_the_scoring_reaches_is_hashed_or_exempted_with_a_reason` fails with `{'fno/scorecard/
    measurement_alerts.py': {'fno/scorecard/pauses.py'}}`;
  - `test_dropping_a_computation_module_from_the_list_is_caught` fails on the same extra item.
  - Everything else passes, and main alone passes its 3 closure tests.
- **Ruling on the module:** it is alert wording only. Its three templates fill in the version, the cap figure the
  hashed rule already used, the reason and a count; it decides no pause and no figure. So it belongs in `EXEMPT`, for
  example "measurement versions' alert wording; decides nothing".
- **Fix:** merge main into the branch, exempt `measurement_alerts.py` with that reason, and re-run the closure tests
  green.

## Note for the owner (no fix asked)

The owner's 16 Oct row (07f62385) accepted the cost for the score-time modules. `pauses.py` and `run_order.py` are new
to that list. The same cost now applies to them: an E6 pause-rule or D3b run-order edit after S1's freeze needs a new
S1 version. Tell the owner in one line, as before.

## Gates

- On the branch as it is: `tests/evaluation` passes.
- On the trial merge with origin/main ef7ca659 (tree 9ca6472), `-n auto`: pytest 7090 passed and **2 failed** (SF1).
- `ruff check` is clean, `ruff format --check` shows 1261 files formatted, `check_imports` is clean, and
  `evaluation check` reports complete.

**A re-check needs only the merge of main and the one exemption.**

## Addendum 1: 40c6ad77 (main merged in): PASS

- **SF1: MET.** `test_scoring_closure.py` exempts `fno/scorecard/measurement_alerts.py` with "measurement versions'
  alert wording; decides nothing". That matches my reading in judge 252: three message templates and their
  formatting, with no pause and no figure decided.
- B0's `fno/playbook/measurement.py` exemption (judge 229 addendum 3) now sits on this branch through main.
- **Gates on the trial merge with origin/main 72742726 (tree f825f22, clean), `-n auto`:** pytest 7160 passed, with
  the closure tests green. `ruff check` is clean, `ruff format --check` shows 1272 files formatted, `check_imports`
  is clean, and `evaluation check` reports complete.

**Verdict: PASS.** The owner note of judge 252 stands: the cost of a new S1 version now covers E6 pauses and D3b's
run order.
