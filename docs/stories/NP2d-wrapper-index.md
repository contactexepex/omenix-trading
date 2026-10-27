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
- The resolve pass reads this index instead of the articles manifest (`resolve/wiring.py`, X9), so its 600 reads go to Google News
  articles only. NP2c was merged first (main 3ffd7c2) and this story carries the switch, so the fix is delivered here (judge 85 F2).
- **The staging cleanup keeps a poll while a Google News article in it has no index row** (X8, judge 86's recommended follow-up):
  `NewsPollProof` now also checks the index, exactly as it already checks the articles manifest row. A poll that is the only way to
  repair a missing row is therefore never trashed.
- **The commit guard tolerates a manifest that does not exist yet** (X7, judge 85 F1): `check-manifest` calls an absent file whole, and
  `git add` of it was fatal, so the first promotes would have committed and pushed nothing. Reproduced by the judge with the real script.

## Said plainly
- No back-fill: an article recorded before this change has no row and is never resolved. The orchestrator confirmed none has been
  promoted yet; if some exist when the owner enables promotion, a one-off `index-wrappers` scan of the Record would be needed.
- **A torn index loses the rows of its whole run, not one** (judge 86, judge 85 note): the commit guard discards a torn `wrappers.csv`
  with `git checkout`, dropping every row that run added, while a whole `articles.csv` is committed. The repair is the re-run of the
  same range that the `manifest_broken` alert asks for (promote is dispatch-only, so the owner runs it). Until it is done, those polls
  are now protected from the staging cleanup (X8), so the repair stays possible; before X8 it was possible only for 7 days.
- A held format-1 article seen again in format 2 is indexed by the hash of the held format-1 file, which has no `wrapper_link`, so the
  resolve pass counts it as not a wrapper. No format-1 news exists today (judge 85, not live).
- Size: one more small csv, one row per Google News article (about 1,300 a day, about 100 bytes each; reasoning from NP0's counts).
