# Judge 400: F6/F7 code, Book 3's decision engine and matched shadows (story/f6-book3-engine at c58117f3; a4059b60 merged)

**Verdict: FAIL, 2 should-fix findings and 4 minor. Lane 1** (a new story; it decides trades). The number was
claimed with O12's tool. The engine is sound where money flows:
- orders replay the stored picks, and an edited run refuses every order;
- a C4 block is never ordered;
- the decider refuses changed packs, a changed sheet or a second run;
- `new_or_reused` is decided by code;
- the Rs 10,000 cap is enforced at the boundary;
- shadow files are timed and hash-checked.

The findings are about one bad spec stopping the whole day, and an exit criterion that is promised but not built.

## Gates (run myself on c58117f3 merged with `origin/main`, local 55c37809)
- `pytest -q -n auto`: **7,961 passed, 15 xfailed** (240 s).
- ruff, format (1,433 files), `check_imports`, `check_records` (6,776 files): clean.
- The F6 files at a4059b60 are byte-identical to c58117f3; only main-merge files differ.
- No file is over 350 lines.

## Shared code read myself
- `decision_inputs`, `decision_record`, `decision_run`, `decision_timing`, `schema`, `book1_inputs`, `book1_wiring`,
  `validity_adapter`: Book 1's stored bytes are unchanged (`selection` and `opens` are written only when present).
- `served` = `{**context.served, **own}`, so the playbook and config entries win.
- `rule_sha256` uses parsed values, and thresholds are always floats (`fields.number`), so "1" and "1.0" give the same
  key.
- The registry's `spec_sha256` = `parameters_sha256`, consistent with D3's record.

## Adversarial pass (a review agent in my session: 30 mutations, plus repros; the two key items checked again by me)
- 25 of 30 mutations caught, including: the validator off in orders, the trade filter dropped, the sheet compared by
  ID only, the fired-packs check off, the same-day `>=`, the shadow late rule, the hash checks, the cap boundary, the
  unknown cards, the C2 path, `threshold`, stored picks, `strategy_id`, a missing shadow entry, and timing at the
  snapshot.
- 5 survived: M9 and M28 are redundant guards (equivalent in effect); M18, M20 and M30 are below.

## Findings

**Should-fix 1. One damaged registered spec stops Book 3's whole day.** Strong evidence: code read by me, plus the
agent's repro.
- `Book3Strategies.on` (`fno/book3/strategies.py:33-37`) catches only `NotRegistered`.
- D5's `require_registered` parses the committed spec with `strategy_from_text` (`registry.py:116`) before its checks,
  so a spec committed as invalid YAML raises `PlaybookError`. That propagates through `on()` and `decide()`.
- `Book3Proposer._registered_rules` (`proposals.py`) parses every committed spec without a guard too.
- Repro: two registered specs, then the second one's file overwritten with `name: [unclosed` and committed. Both
  `on()` and `decide()` raise `PlaybookError`, so the good strategy cannot trade, and the error is not
  `DecisionRefused`.
- It fails closed (F1t records the exception as `refused`), but it contradicts the design: "`excluded` holds D5's
  reason ... never traded", one strategy at a time.

Fix: catch the parse failure per strategy, both in `on()` and in `_registered_rules`, as excluded with its reason. Add
a test where one damaged spec leaves the other strategy tradable.

**Should-fix 2. Criterion 15 is not met, and the exit rule has no regression test.** Strong evidence.
- The story says: "Editing or deleting today's spec file changes no exit and **sends one alert**."
- Book 3 uses Book 1's `PlaybookExitRules`, whose `_warn` alerts only on an unreadable file or an unenforceable exit.
  The agent's repro: today's spec rewritten with `exit_days_before_expiry: 5` (still valid) gives `ALERTS []`. The
  exit is correctly unchanged.
- The exit itself is right: `decided_exit_days` reads the spec from the run's own `inputs.json`
  (`book1_records.py:84-92`, read by me). But the only test deletes today's file, so a regression to "read today's
  spec" passes. The agent's M20 survived with exactly that change.

Fix: add the edit-alert (compare today's text with the run's), or amend criterion 15 through the text if an alert is
judged unnecessary. Either way, add a test that edits today's spec's time exit and asserts the decided exit day is
unchanged.

**Minor.**
1. **M18.** "These two always win" (`decision_run.py`, `served`) is untested; flipping the merge order passes 437
   tests. Add a test where an AI context's `served` tries to override `playbook` or `config`.
2. **M30.** No reader test asserts that `no_trade` is absent from the shadow reader's result.
3. **D3, fails closed.** `Book3Strategies.on` lists strategies from the working-tree registry. A missing
   `registry.csv` silently gives an empty tradable set, with no excluded reason and no log line. List from the
   committed registry at the decision commit (already read as `registry_text`).
4. **Text alignment.** Criterion 1 says C4 blocks an unregistered or edited strategy "with D5's reason". In the code
   such a strategy is dropped before D2 and recorded in the day log's `excluded_strategies`. That is safer; reword
   criterion 1. Item 8 names `fno/book3/exits.py`/`Book3ExitRules`, but the code uses a builder function that returns
   `PlaybookExitRules`. Reword that too.

## Claims vs reality
- "37 of 37 mutations caught": their set was not checkable here. A different set of 30 found 3 real gaps.
- "Unreadable specs refused alone": true for proposals, false for registered specs (should-fix 1).
- Criterion 13 (a sheet value changes the pack hash): untested here, since the BookSheet port is E2e's (judge 309,
  now passed at b1838eb3). The plug-in follows.
