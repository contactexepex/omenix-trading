# Judge 78: NP3a company list (code, lane 1, privacy), judge #2

Frozen SHA `6504962` (branch `story/NP3-company-list-and-feed-planning`, with main merged in). Reviewed
`git diff origin/main 6504962`:
- `news/companies/*`;
- `news/versioned.py` and the `feeds.py` extraction;
- `codes.py`, the story, rows Q1-Q7 and their plants.

The deleted judge_75 lines seen in that diff come only from an older base.

**Gates** (in the venv from `requirements.lock`, `--require-hashes`): 1506 passed; ruff check and format clean; imports
clean (537 files); code size passed; contract plants all ok.

**My plants (6 of 6 killed):**

| Plant | Tests failed |
|---|---|
| no-overwrite check off | 2 |
| `--apply` ignored | 2 |
| name source order reversed | 3 |
| duplicate alias check off | 3 |
| ReDoS check off | 6 |
| a name printed | 1 |

## Checked and correct

- **The `feeds.py` extraction matches the old code.**
  - `VersionedFiles` uses the same `^feeds-v(\d+)\.json$` pattern.
  - `latest` keeps the same missing, rolled-back and damaged-skip order, and the same SHA comparison.
  - `kinds_ever_listed` iterates `every_version()` and keeps its `None` handling.
  - The 487 feed and news tests are unchanged and pass.
- **Seed command:** report-only by default; it refuses when any company file exists (`COMPANY_LIST_EXISTS`), and the
  write is write-once anyway.
- **Name source order:** the equity list, then the Nifty 500, then the master (plant killed).
- **No company name leaves the program:** fixed codes only; an unexpected error is reduced to its class name; the
  printed line is counts only.
- **Only the four public index names ship in code** (`seed.py:15-20`), as stated.

## Findings

1. **F1 (must fix): the ReDoS restriction misses polynomial blow-up.** `QUANTIFIED_GROUP` only refuses a quantifier
   after a group. I measured patterns it accepts, each against a 90-character text:

   | Pattern | Time |
   |---|---|
   | `.*.*.*.*.*.*Z` | **31.3 s** |
   | `\w*\w*\w*\w*\w*\w*!` | **8.1 s** |

   NP5's tagger will run every exclusion on every headline and summary, so one such typo in the owner's file stalls a
   tagging run for hours. The story and row claim "exclusions are restricted", which is not true for this class of
   pattern.

   Fix: also cap the unbounded quantifiers (`*`, `+`, `{n,}`) in a pattern, for example at most 2. Every one of
   agentic's real patterns in the test has at most one. Add these two patterns to the refused-pattern test, and a
   plant.
2. **F2 (must fix): the seed can write a file its own parser refuses, and then never replace it.**
   - `build_seed` takes symbols and names from the Nifty 500 and equity lists without the parser's checks. I fed it a
     Nifty 500 row with a symbol over 20 characters, a lower-case symbol, and a company named only "Ltd".
   - The seed's bytes then fail `parse_company_list` (`company_list_invalid`).
   - With `--apply`, that file is written once to Drive. Every consumer stops on it, and `seed-companies` refuses ever
     to write again (`COMPANY_LIST_EXISTS`), so the owner must repair the private file by hand.
   - Real NSE symbols rarely break the pattern (reasoning only), but two symbols whose *full* names also clean the same
     do. Fix: skip and count entries that would not pass, and parse the finished bytes with `parse_company_list` before
     writing, refusing with a fixed code. Add a test with such rows.
3. **F3 (must fix, privacy): the tests carry real company names and the owner's earlier exclusion patterns,
   contrary to the plan.**
   - The NP3 plan I passed says "fixtures in tests use invented names only" (section 5b).
   - The parametrized "accepted exclusion" test (`tests/ingestion/news/companies/test_parse_and_file.py`, about lines
     65-68) ships four of agentic's real exclusion patterns. The story calls them "agentic's real exclusions" (line 28).
   - Exclusions exist only for a company the owner tracks, so in a public repository those patterns tell anyone which
     companies the owner follows. That selection is what NP3 keeps private.
   - Other test lines (`:35`, and `test_seed_and_cli.py:74`) use real listed names as well. They are weaker leaks: they
     do not mark a selection.
   - Fix: replace all of them with invented names of the same shape, and say in the story that the patterns are of
     agentic's *shape*.
   - Note: git history keeps the branch's commits. If the branch is never merged and is deleted, nothing reaches main.
   - My own first push of this verdict quoted the patterns. They are removed in the next commit, but they remain in
     main's history at `f735e94` (disclosed to the orchestrator).

**Verdict: FAIL** (round 1, `6504962`). Each fix is small: one more check, one self-parse, and renamed fixtures.
