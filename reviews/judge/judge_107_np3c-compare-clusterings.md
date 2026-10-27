# Judge 107: NP3c compare clusterings (code), round 1 at eb0ac05: FAIL (tests only)

**Lane 1, two judges; this is judge #1.** Branch `story/NP3c-compare-clusterings`, frozen SHA eb0ac05. I reviewed `git diff origin/main...eb0ac05`: `news/compare/` (191 lines), the CLI command, the workflow `news-compare-clusterings.yml`, tests, and contract rows J1 to J9.

## Gates (strong evidence)
In a venv installed from `requirements.lock`:
- 1981 passed;
- ruff check and format are clean, and check_imports is clean.

## B1 (required, tests only; strong evidence, plants survived the FULL suite): the key signal and two shape counts are not pinned
- **`url_joins_unlike_title` is not pinned.** The story calls it "the early warning that a generic URL is merging unlike stories". My plant makes that column print `url_joins` instead, and it passes all 1981 tests. The only run test asserts `url_joins_unlike_title 0` in a fixture where `url_joins` is also 0. A mislabelled warning column is the one error this read-only tool can make that misleads the owner's cutover decision.
- **`singletons` is not pinned.** The plant `sizes.count(1)` → `sizes.count(2)` passes the full suite, because the J1 fixture has exactly one singleton and one pair. Row J1 claims the singletons are counted, and the test cannot show it.
- **The "11 or more" bucket boundary is not pinned.** The plant `(11, …)` → `(12, …)` passes, because the fixture's largest cluster has 12 articles.
- **Fix:**
  - in J1, use different counts for each size and a cluster of exactly 11;
  - add a run test where `url_joins` and `url_joins_unlike_title` differ and are both nonzero;
  - add these three plants to the J rows.

## My other plants (each one undone; all fail tests)

| Plant | Result |
|---|---|
| spanning counts every group | 2 failed |
| merge and split swapped | 1 failed |
| `tagged_high` counts any tag | 1 failed |
| v2 clustered without the preparer (so v2 equals v1) | 1 failed |
| a stop ignored | 1 failed |
| exception text printed instead of its class | 1 failed |

## What holds
- **Read only, by code path (strong evidence):**
  - the run has no writer, manifest writer or receipt;
  - the workflow is `contents: read`, has no Slack token and no schedule (J7);
  - `AS_OF` reaches the shell through `env`, not through `${{ }}` in the script, so a crafted input cannot inject a command.
  - **Some evidence only:** the Drive credential is the same owner token the writing workflows use, so the code, not the token, is what makes it read-only. That is acceptable for an owner-dispatched tool; say so in the story.
- **Privacy:** the report is counts only. J8 and J9 plant a title and a symbol into the output, and the tests catch both. An unexpected error prints only its class.
- **A fair comparison:** both versions cluster the same articles with no previous file. Neither is carried from earlier runs.
- **Honesty:** the story says plainly that broad-against-targeted recall cannot be measured, because no feed id is kept in the Record. That is true; I checked that the article format has no feed field.
- **Scope (the owner's ingestion-only rule, 27 Oct 2026, as relayed):** in scope. It measures this repository's own derive step and serves no consumer.
- **Structure:** a pure metrics module, a run, a composition root, and a 202-line `cli.py`. The workflow count test was updated from 23 to 24.

## Notes (not blocking)
- **N1.** `ComparisonRun` ignores `source.skipped_rows`, which the cluster run treats as a stop (`manifest_row_skipped`). A skipped row hides an article from both counts. Report it as a count, so the owner knows the comparison is not over the whole window.

## Hard lines
No order path, no secret printed, no Groww call. No write and no commit.

## Verdict: FAIL round 1 at eb0ac05. B1 (pin `url_joins_unlike_title`, singletons and the 11 boundary) required; N1 requested.

## Addendum 1: round 2 at 9d16261: PASS

I reviewed `git diff e7961aa 9d16261`. Before that, e7961aa added judge 106's whitelist test (J10, J11) and merged `main`; I re-ran my plants there too. This round changes one line in `run.py` (the `input:` line), adds tests and adds rows J12 to J15.

**Gates (locked venv, strong evidence).**
- 1992 passed.
- ruff check and format are clean; check_imports is clean.

**B1 fixed (strong evidence, replanted).** Each plant was undone after its run.

| Plant | At eb0ac05 / e7961aa | At 9d16261 |
|---|---|---|
| `url_joins_unlike_title` prints `url_joins` | passed | 1 failed |
| singletons as `sizes.count(2)` | passed | 2 failed |
| the 11+ bucket starts at 12 | passed | 1 failed |
| the 6–10 bucket stretched to 11 (my new plant) | not run | 1 failed |
| `url_joins_refused` prints `url_joins` (my new plant) | not run | 2 failed |

- **The new run test.** It builds a URL join that is alike in title and one that is not, giving `url_joins 2` and `url_joins_unlike_title 1`. Both are nonzero and they differ.
- **The new J1 fixture.** Its sizes give 3 singletons and buckets (1, 2, 4, 4), with clusters of exactly 11 in the last bucket.

**N1 fixed.** A first line, `input: articles N, manifest_rows_skipped K`, reports `source.skipped_rows`. My plant hard-coding 0 there fails a test.

**Verdict: PASS round 2 at 9d16261.**

## Addendum 2: plant runner re-check at 9d16261: the PASS stands

I gave Addendum 1's PASS without running the full contract-plant runner, the same miss as in judge 108. I have now run `tools/contract_plants.py` at 9d16261 in the locked venv: **253 of 253 rows are `ok`**, with nothing unnoticed (strong evidence). The PASS at 9d16261 stands.
