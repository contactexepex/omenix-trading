# NP2d: the wrapper index

Lane 1, two judges (it changes the promotion gate and the shared commit guard). Orchestrator approved the idea on 27 Oct 2026
("a real root-cause fix, not a nicety"); planned and built in one step because the change only adds. Contract rows X1 to X6.

## The problem it fixes
The articles manifest cannot say which article is a Google News one. The resolve pass ([NP2c](NP2c-resolve-pass.md)) therefore
read every unresolved article of its 3-day look-back to find the few it can resolve: about 1,500 a day against a 600-read cap
(reasoning from NP0's counts). Most Google News articles would never be reached, age out unresolved, and the dashboard would
show blank links; the page-read pass (NP4) has the same need. NP2c made that loud (an alert on every pass); this removes the cause.

## What changes
- The gate adds one row to `research/data/manifests/news/wrappers.csv` (same layout as `articles.csv`: `date,article_id,status,
  sha256,size_bytes`; hash ids only) for each recorded **Google News article that has a redirect link** (`record/wrapper_index.py`).
  The row's SHA-256 is that of the article file the Record holds. A revision adds no row (X3); a publisher article, or a Google
  News item without a usable link, never does (X1).
- **It only adds.** No gate decision changes: the Record files, the articles manifest and the promote line are byte-for-byte what they
  were (X4, tested against a gate built without the index). `ArticleWriter` takes the index as an optional argument.
- **Idempotent and self-repairing** (X2): the row is added after the article row; a run killed between them leaves the article
  without its row, and the next promote of the same poll (a no-op for the article) adds it. The index is an index of the Record, not
  a Record file: nothing in Drive, no receipt.
- **Guarded like the articles manifest** (X5, X6): a torn index stops the promotion before any write; a row that is not whole is
  reported; the shared commit step (`ops/commit_news_record.sh`) now guards `$MANIFEST` and every file in the new optional
  `EXTRA_MANIFESTS` the same way (a torn one is discarded from the commit and turns the run red, the good ones are committed), and
  `news-promote.yml` names the index there.
- The resolve pass reads this index instead of the articles manifest, so its 600 reads go to Google News articles only.

## Said plainly
- No back-fill: an article recorded before this change has no row and is never resolved. The orchestrator confirmed none has been
  promoted yet; if some exist when the owner enables promotion, a one-off `index-wrappers` scan of the Record would be needed.
- A staged poll whose articles are all in the Record can be trashed by the staging cleanup after 7 days. A kill between the article
  row and the index row that is never followed by another promote of that poll within 7 days would lose that one marker (the window is
  the milliseconds between two appends; reasoning only).
- Size: one more small csv, one row per Google News article (about 1,300 a day, about 100 bytes each; reasoning from NP0's counts).
