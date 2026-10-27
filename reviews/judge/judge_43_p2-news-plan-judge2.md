# Judge 43: P2 news and dedup, design (judge #2)

Branch `story/P2-news-plan`, SHA `f23aeff1faacfd56151bd33c48e83b63865989e7`, `docs/stories/P2-news-dedup.md`, lane 1.
**FAIL** (round 1). This is an independent review: below are findings beyond judge #1's D1-D8, though some touch the
same areas. I agree with D1-D8; I do not repeat them.

## 1. Other paths by which a headline, a URL or a search query reaches GitHub or a public log

1. **N1 (must fix): the committed snapshot log stores each request URL.** P2a says "a snapshot-log row like the
   global cues". `SnapshotRow` keeps `url` and `form` (`global_cues/snapshot_log.py:16-26`). The global-cue log is
   committed (`global_cues/wiring.py:63`, under `MANIFEST_FOLDER`).
   - For a Google News search feed, the URL holds the query (`q=...`), which reveals what the owner researches, in
     a public repository. It is not a headline, but it is research intent.
   - The staging path `<HHMMSS>_<feed>.xml` names the feed the same way, and receipts carry paths.
   - Fix: the news snapshot row and the path carry a feed id (a short fixed key from config), never the URL or the
     query. Feed URLs live only in Drive, or in config.
2. **N2 (must fix): the public Actions run log.** This repository is public, so its workflow logs are too. P2 adds two
   paths into it:
   - The P1 gate prints every rejection's reasons (`promotion/runs.py:85-86`). A news check reason written naturally
     ("item without a time: <title>", "bad link <url>") puts a headline or URL in the log.
   - `requests` puts the full URL in its errors (`429 Client Error ... for url: https://news.google.com/rss/search?q=...`).

   The record scan does not catch either, because it looks for secrets, not headlines. Fix: an invariant that no news
   reason, line or alert carries item text or a URL. Reasons are fixed codes plus counts, with exception messages
   withheld as the close read already does (`WITHHELD`, `close_read/reader.py`). Add a test that feeds an item whose
   title is a marker string and asserts the marker never appears in printed lines, alerts, receipts, manifests or
   commit messages.
3. **N3 (should fix): test fixtures.** "Recorded sample feeds (small synthetic files)" must be invariant-level: never
   real fetched feed bytes in `tests/`, because those are real headlines, someone else's text, in a public
   repository. State it as a rule, and back it with a check or a marker convention.
4. **N4 (should fix): the plan leans on the record scan.** Invariant 3 says "under the existing record scan". The scan
   cannot recognise a headline, so privacy here rests on output shapes. Name each committed output (receipts, the
   news manifest, the snapshot log, the pause log, commit messages) and pin each one's columns or format with a test.

## 2. Can dedup or clustering drop, hide or duplicate a real article?

5. **N5 (must fix): one id with a new body is trapped in Staging forever, hiding real articles.** Invariant 1 keeps
   "a different body for the same id" as a later Staging copy, never in the Record. Real cases:
   - a live blog that keeps one URL all day;
   - a corrected or re-titled story;
   - for Google News items without a URL id, the same title from the same source on different days ("Stocks to
     watch today", "Sensex, Nifty today").

   The second article, or the correction, then never reaches the Record. That is the data loss the plan rules out.
   P1 already solved this for NSE: a new version goes to the revisions area with its index row
   (`promotion/gate.py:4`, "no version NSE published is lost"). Use the same: a changed body is a revision of the
   article in the Record, with its own seen time. Pin it with tests for a re-titled story and a repeated daily title.
6. **N6 (must fix): the freshness window drops late arrivals for good.** P2b rejects items outside a freshness window.
   - Late arrivals are normal: after a feed outage, at the first run after go-live, or when Google surfaces an older
     item.
   - A pubDate parsed in the wrong zone (an IST time with no zone, or a non-RFC-822 date) falls outside the window.

   Such items stay in Staging with a reason and are never promoted, so the Record misses real articles with no path
   back. Fix:
   - "stale by time" is a distinct, counted reason that never blocks the Record;
   - or the window applies to clustering only, never to recording;
   - plus a test with a timezone-less date.
7. **N7 (must fix): the entity stage merges distinct stories.** P2c's third stage groups by "shared entities (F&O
   symbols and index names)". Nearly every F&O article names NIFTY, so with transitive grouping (A with B, B with C)
   most of a day's news collapses into one cluster. No article file is deleted, but the cluster view, which is what
   a consumer reads as "one record per story", hides distinct stories and inflates the count of independent outlets.
   That is the "lost signal" the threshold section worries about. Fix:
   - an entity may only constrain a title match (same entity AND similar title), never merge on its own;
   - groups must not chain: each member must match a cluster's anchor, not just any member;
   - add a test: two different NIFTY stories on one day stay two clusters.
8. **N8 (should fix): every poll must be accounted for.** There is no reconciliation. Add an invariant and a test:
   for each poll, items = recorded + new revisions + known duplicates + rejected with a counted reason. A plant that
   silently skips an item must fail it.
9. **N9 (should fix): two clustering runs at once.** Two overlapping promotion runs can write two cluster files for
   the same second with different inputs. "The latest file at or before T" is then ambiguous. Fix: a workflow
   `concurrency` group, plus a tie-break rule in the as-of read (for example, the later run id).
10. **N10 (should fix): the rolling window and "as known at T".** Each cluster file covers only the last N hours, so
    "the latest file at or before T" does not hold stories older than N hours. A consumer asking about an older story
    at time T gets nothing back, though the story existed. Either the as-of read takes, for each story, the latest
    file that covered it, or each file states its covered window in its header. This touches D7; I add the
    reader-side failure.

## 3. Missing invariants and hard lines

11. **N11 (should fix): a block that answers 200.** Invariant 6 covers 429 and 403. Google answers automated traffic
    with a "sorry" or CAPTCHA page, or a consent redirect, at HTTP 200 or 302. Under the plan that is a parse failure:
    Staging plus an alert each run, while polling continues. Apply the Yahoo rule (A17e): a redirect, or a page that
    is not the feed format, is a block, the host stops for the run, redirects are not followed, and it is never
    retried another way.
12. **N12 (owner): the terms for news.** The plan assumes owner rule 50a79a43 (made for index values) covers
    publisher headlines. News text is a different class of content. Ask the owner to confirm it in words, rather
    than assuming.
13. No orders, no secrets, no sign-in: covered and correct. Write-once: correct for the files, but see N5 for how a
    revision is recorded.

## What is sound

- No mutable dedup state; clustering as a pure, deterministic function with a version in the path.
- No cron until go-live.
- No second request per Google News item.
- The labelled pair set with measured precision and recall before any threshold is chosen.

**Verdict: FAIL** (round 1). Must fix: N1, N2, N5, N6, N7. Should fix: N3, N4, N8-N11. Owner: N12.
