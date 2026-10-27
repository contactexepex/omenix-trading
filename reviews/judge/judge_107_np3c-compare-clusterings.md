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
