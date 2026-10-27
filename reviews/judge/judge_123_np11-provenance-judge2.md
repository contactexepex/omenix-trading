# Judge 123: NP11 feed provenance (judge #2, code, privacy focus)

**Subject:** `story/NP11-provenance` at `e01cb08`.
- What it adds:
  - `news/provenance/`: model, file, index, writer, recall and wiring;
  - the gate collects pairs and flushes closed IST days;
  - `NewsPollProof` gains a pair gate;
  - `news-promote.yml` `EXTRA_MANIFESTS` gains `provenance.csv`;
  - an optional feed `scope`;
  - the `news-provenance-recall` workflow.
- The plan passed in judge 113, Addendum 1. Lane 1.

**Gates (locked venv, `__pycache__` cleared):**
- `pytest -q -n auto`: 2015 passed.
- `ruff check` and `ruff format --check`: clean.
- `check_imports`: 636 files clean.
- `test_code_size`: 3 passed.
- `check_numbers`: clean.
- `tools/contract_plants.py`: every plant caught.

## Privacy: holds (*strong evidence*)

- **The seal:** `seal_of(salt, path)` = HMAC-SHA-256(salt, `"provenance\0" + path`), a field of every file. The file's
  public receipt SHA cannot be rebuilt without the salt.
- **The manifest id** is `<day>` or `<day>-<n>` (`provenance_id`). There is no feed id or key in a name, a row or a
  code.
- **Recall:** the workflow is dispatch-only with `contents: read` and no writer, and prints counts only. The whitelist
  test is in place.
- **The cleanup gate:** `_recorded_feeds` requires every (key, feed) pair of the poll in its IST day's files. An
  unreadable day propagates, so the copy is kept as a `proof_error`.

## Blocking

1. **B1: a routine "--from today" promotion never writes provenance at all, and the polls are then kept staged
   forever** (*strong evidence*, reproduced at `e01cb08`).
   - Pairs are collected only from the polls inside the run's own `--from`/`--to` range (`gate.promote`, then
     `seen.add`).
   - `flush` writes only days before today (`writer.py`: `d < self.today()`).
   - So a closed day's file is written only by a later run whose range still includes that day. That is the
     opposite of plan item 8, which I required in judge 113: the day's pairs come from ALL staged polls of that IST
     day.
   - Reproduced with the branch's own fixtures. A poll is staged on DAY, then promote runs once a day with `--from` and
     `--to` equal to that day, for DAY, DAY+1 and DAY+2. Result: **no provenance file at all**.
   - Two consequences:
     - the cleanup gate then never proves those polls, so they stay staged for good;
     - the planned `provenance_polls_missing` count does not exist. `codes.py` defines only `poll_skipped`,
       `unreadable`, `conflict` and `failed`. Both the plan's item 7 and row P13 name it, so the "never silent" promise
       is not met.
   - **Also:** staged polls sit under UTC days, but provenance days are IST. IST day D spans UTC D-1 18:30 to D 18:30.
     So even a run of `--from D` writes IST day D without the D-1 evening polls, and only a run covering D-1 adds them.
   - **Fix (the design is the implementer's choice):** when a closed IST day is flushed, build its pairs from every
     staged poll of the two UTC days that cover it, independent of the promotion range, which is plan item 8 as
     written. Then:
     - add `provenance_polls_missing`, counted by the writer, or by the proof when a poll fails only the pair gate;
     - add a test of daily "--from today" runs, where the day file appears the next day;
     - add a plant that restricts collection to the run's range.

## Notes (not blocking)

- **N1: relabelling.** A feed whose scope changes, for example unknown becoming broad in a later list version, produces
  supplements that add (feed, broad) beside the stored (feed, unknown) for every past day still in range. The bucket
  logic handles it: broad wins, and `with_unknown_feed` counts it. Say it in the story.
- **N2: the plan correction.** Broad Google News queries are labelled broad, company queries targeted, and publisher
  feeds broad. That is correct, and the story should record it as a change from the plan.

**Verdict: FAIL** (round 1, `e01cb08`). B1 means the feature writes nothing under a normal schedule.
