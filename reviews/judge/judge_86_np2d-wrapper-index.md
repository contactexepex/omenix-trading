# Judge 86: NP2d wrapper index (code), round 1 at dbb4905: PASS, on condition of one corrected sentence

**Lane 1 (the promotion gate and the shared commit guard); judge #1.** Branch `story/NP2d-wrapper-index`, frozen SHA dbb4905. Reviewed `git diff origin/main...dbb4905`: `record/{gate,writer,wiring,wrapper_index}.py`, `ops/commit_news_record.sh`, `news-promote.yml`, rows X1 to X6.

## Gates (locked venv; strong evidence)
1596 passed; ruff is clean; contract plants all `ok`.

## What holds (strong evidence)
- **Gate decisions are unchanged.** The index is optional in `ArticleWriter`; marking happens after the article's own row; X4 compares the Record files, `articles.csv` and the promote line against a gate built without the index.
- **Plants (each one undone; all fail tests):**

| Plant | Result |
|---|---|
| the no-op path not marked (no self-repair) | 1 failed |
| revisions marked | 1 failed |
| wrapper articles without a link marked | 1 failed |
| the index not checked for a torn line before writing | 1 failed |
| the commit guard ignoring `EXTRA_MANIFESTS` | 2 failed |

- **The commit guard.**
  - It loops over `$MANIFEST ${EXTRA_MANIFESTS:-}` with the same check: a good file is committed, a torn one is discarded and the run is red.
  - `news-promote.yml` names `wrappers.csv`; the cluster workflow leaves `EXTRA_MANIFESTS` unset, so its behaviour is unchanged.
- **Privacy.** The index holds hash ids and sizes only (the articles-manifest layout).

## Condition (text, the orchestrator can check): the story understates the staging-cleanup window
- "Said plainly" describes the loss as "one marker" in "the milliseconds between two appends". The real case is wider.
- If the **index file** is torn (a kill mid-append), the commit guard runs `git checkout -- wrappers.csv`, which reverts the **whole file**. Every wrapper row this run added is dropped, while a whole `articles.csv` is committed.
- S1's `NewsPollProof` requires the `articles.csv` row but **not** the index row. So after 7 days it may trash those polls.
- The only repair is the one the red run's alert names: promoting the same range again. `news-promote.yml` is dispatch-only today, so that needs the owner to re-run by hand within 7 days.
- Otherwise every Google News article of that run stays unindexed, and so is never resolved (reasoning only; it needs a kill mid-append plus no re-run).
- Correct the sentence to say this.

## Recommended follow-up (the root fix; small; lane 1)
Make S1's news proof also require the index row for a resolvable article: one `has()` in `NewsPollProof._held`. A poll is then never trashed while its index rows are missing, exactly as the article rows are protected today.

## Minor (reasoning only)
If the index ever held another SHA-256 for a key (only a hand edit could do that), `mark` would raise `RawFileConflict`. The gate would then count an article that *was* recorded as `record_conflict`. That is loud, not silent, so acceptable.

## Hard lines
No order path, no secret, no Groww call, no request; no Record file changes.

## Verdict: PASS round 1 at dbb4905, on condition of the corrected sentence. The S1 index check is the recommended follow-up.

## Addendum 1: round 2 at 2ac29df: PASS, on condition of one wiring pin

Reviewed `git diff dbb4905 2ac29df` (main with NP2c merged in).

**Gates (locked venv).** 1636 passed; ruff is clean; contract plants all `ok`.

**What changed, and what I checked.**
- **The round-1 condition is met:** the story now says a torn index loses the rows of its whole run, and that the repair is the `manifest_broken` re-run.
- **The recommended follow-up is built (X8).** `NewsPollProof._indexed` requires the index row (the same SHA-256 of the held bytes) for a resolvable article's main file. Plant: `_indexed` dropped → 1 failed.
- **Judge 85's F1 (X7):** a manifest that doesn't exist yet is skipped by `[ -e ]` before `git add`, so `set -e` no longer kills the commit step.
- **Judge 85's F2 (X9):** the resolve pass reads `wrappers.csv`. Plant: it reads `articles.csv` again → 1 failed.

**Condition (test or signature only): the X8 protection is not pinned at the wiring.**
- `NewsPollProof(..., wrappers=None)` skips the index check when no index is given.
- My plant removing the index from `staging_cleanup/wiring.proofs()` passes all 745 news and cleanup tests. So a wiring slip would silently turn the protection off.
- **Fix:** either make `wrappers` a required argument (preferred: there is no caller without it), or add a test that `proofs(..., sources=["news"])` builds a proof with an index. Then show my plant failing.

**Verdict: PASS round 2 at 2ac29df, on condition of the wiring pin.**
