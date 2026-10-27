# Judge 126: DOC2 docstrings and the NP11 "Not guaranteed" section (lane 2 audit, after merge): PASS

**A lane 2 audit after merge, requested by the orchestrator; judge #1.** Commits 77926a7 and 34b1961, `story/DOC2-docstrings`, both on `main` (I audited at main 4013b27). Changed files:
- `docs/NEWS_RECORD_CONTRACT.md` (+9, now 387 lines);
- the docstrings of `tests/test_record_contract.py` and `tools/contract_plants.py`.

No executable line changed.

## Gates (the text-only rule)
- The doc-reading tests plus `tests/test_record_contract.py`: **79 passed**.
- `python tools/check_numbers.py`: clean.

## The docstrings are accurate (strong evidence, read)
- **`tests/test_record_contract.py`.** It already checks both documents (`DOCS = ("RECORD_CONTRACT.md", "NEWS_RECORD_CONTRACT.md")`, line 14), and the docstring now says so.
- **`tools/contract_plants.py`.** It runs every claim in `contract_plants.json`, which covers both documents' rows, so naming both documents is correct.

## The "Not guaranteed" wording neither overstates nor understates (checked against the NP11 code I passed, judge 124)
1. **The late-staged poll.**
   - "Picked up only by a promotion run whose `--from`/`--to` reaches that day" is true: the sweep reads only days without a file.
   - "The cleanup gate keeps the poll staged, so no article is lost" is true (B21). The article itself is promoted regardless; only its provenance waits.
   - "Shows its articles as `no_provenance`" is true for recall.
   - "Rare" is reasoning, and stated as such.
   - **Not said, and worth one clause (recommended):** with only the routine `--from today` runs, such a poll stays staged until someone runs a promotion over its day. It is not picked up by itself.
2. **Scope as written.**
   - "A label added later does not relabel old files" is true.
   - **Not said (recommended, my judge 124 N1):** if the poll is still staged and a range pass re-reads it after the label is added, a supplement holds `(feed, broad)` beside the old `(feed, unknown)`. The article is then counted in the labelled bucket **and** in `with_unknown_feed`. The section's "the owner sees how much of a number rests on unlabelled feeds" stays true, but the overlap is worth one clause.
3. **The closed day with no articles** is correct as written.

Neither omission makes a statement wrong. Both are small clarifications for the next text change; neither blocks.

## Verdict: PASS (lane 2 audit) at 77926a7 and 34b1961. Two one-clause clarifications recommended.
