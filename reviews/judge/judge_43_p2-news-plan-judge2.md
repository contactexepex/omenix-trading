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

## Addendum 1: design round 2, ca6a8c5 (FAIL: three new gaps the rewrite leaves open)

Branch `story/P2-news-plan`, SHA `ca6a8c5aca97039e2c49be53ea90ace7fb0b6290`.

**My round-1 items, as written:**

| Item | Where in round 2 | Verdict |
|---|---|---|
| N1 committed outputs | feed ids in the snapshot row, staging path and receipts; a news manifest with no `url` column | resolved for those outputs, but see R1 below |
| N2 / N4 | fixed reason codes, exceptions by class, the master marker test across failure paths, logs, alerts and the commit message | resolved |
| N3 | synthetic fixtures only | resolved |
| N5 | same key, other content -> `RevisionSink` | resolved (see R4 for a false-revision source) |
| N6 | no age check at the gate; `time_source=seen` | resolved at the gate; see R2 for the cluster layer |
| N7 | an entity only constrains a title match, no chaining, the two-NIFTY test and plant | resolved |
| N8 / N9 / N10 / N11 | reconciliation and skip plant / `concurrency` with `cancel-in-progress: false` / as-of reader helper / block page | resolved, except that N11 never says whether redirects are followed (R5) |

**New gaps.** Three must fix.

1. **R1 (must fix): the search queries would still be public, in the code.** "Each feed has a fixed short id **in the
   code** (`gn-nifty`, not its URL)". The id has to map to a URL somewhere, and every place the design offers is
   committed to this public repository: the code, and `config.yaml` (`git ls-files config.yaml`). So the `q=` research
   intent that N1 kept out of the logs and manifests sits in the source tree instead. The id `gn-nifty` also names
   the topic.
   - Fix: the feed list (id to URL) lives outside the repository, for example a private Drive config file read at run
     time, or a GitHub Actions secret or variable. Ids are opaque (`gn-01`).
   - Extend the master test to the source tree, as plain text in `fno/`, `config.yaml` and `.github/`.
   - If the owner is content to publish the queries, that is the owner's call and should be written as one; it should
     not be decided by default.
2. **R2 (must fix): a late arrival is in the Record but no cluster ever includes it.** The cluster input rule is
   "first seen_at at or before the window end **and published within the window**". Take an article published 3 days
   ago and first seen today (after an outage, at the first real run, or surfaced late by Google):
   - It is in the Record (N6), but no window seen since then covers its publication time.
   - The N10 reader looks for "a file whose window covers t", but those files were written before the article was
     seen.

   So no cluster file ever lists it, and the cluster consumer never sees it: the N6 loss moved from the gate to the
   cluster layer, against invariant 4 ("never hides"). Fix: window membership by `max(published, first seen_at)`, or
   a late article enters the first run after it is seen, flagged `late`. Add a test: an article published before the
   last window and seen now appears in the next cluster file.
3. **R3 (must fix): "no cookies" is not met by the session the design reuses.** Invariant 6 says no cookies.
   `PacedSession` is a `requests.Session` with no cookie policy (`http_pacing.py`), and a `requests.Session` stores
   every `Set-Cookie` and sends it back. Google sets cookies on news.google.com answers, so polls after the first
   would carry Google's cookies. Fix: the news fetcher's session refuses cookies (a cookie policy that rejects all,
   or a jar cleared before each request). Add a test: an answer that sets a cookie, and the next request carries no
   `Cookie` header.
4. **R4 (should fix): the feed id is one of the compared fields, so one article in two feeds becomes a false
   revision.** The article file's fixed fields include the feed id, and a re-poll compares on those fields. A Google
   News item (one `guid`, so one key) that appears in two search feeds then differs by feed id, and is stored as a
   revision with no real change. Fix: leave the feed id out of the compared fields (it belongs in the poll's
   reconciliation and snapshot row); keep the first feed in the file if wanted.
5. **R5 (should fix): redirects.** The block rule speaks of "a redirect to a consent or sorry address" but does not say
   redirects are not followed. Following one is a second request to another host (and, with R3, may set a consent
   cookie). State `allow_redirects=False` and that any redirect is a block, as in the Yahoo source.
6. **R6 (should fix, minor): cluster lineage when the anchor leaves the window.** When a cluster's earliest article
   ages out of the window, its remaining members get a new earliest article and so a new id.
   `previous_cluster_ids` should cover that case too, not only a late earlier article or a merge. Also name the
   assignment rule that, under no-chaining, decides which cluster an article joins when it matches two anchors (for
   example, the earliest anchor). Determinism holds already; the rule makes it reviewable.
7. Residual, accepted (reasoning only): `article_id` is a SHA-256 of a public URL, so someone holding a guessed URL
   can confirm the owner archived it. This is very low risk; I name it so the owner knows.

**Verdict: FAIL** (round 2). This is decisive, so R1-R3 go to the owner with the orchestrator. Each is small and
concrete:
- R1: a private feed list;
- R2: one changed input rule and a test;
- R3: a cookie policy and a test.

R4 to R6 are one-line text fixes.

## Addendum 2: design round 3, 06e3467 (owner-authorised; PASS)

Branch `story/P2-news-plan`, SHA `06e3467212d5bf17f1a357b25ddcf7684eba7392`, docs only. The owner chose the private feed
list (variant A).

| Item | Written in as | Verdict |
|---|---|---|
| R1 | the feed list in a private Drive file read through the Drive reader; opaque ids (`feed-01`); none in code or `config.yaml`; a missing list stops the run; the master test scans `fno/`, `config.yaml`, `.github/` and `docs/` and captures DEBUG logging (urllib3's request line) | resolved. Also checked: the Drive cache is `work/drive-cache` (`data_wiring.py:17`), which is git-ignored (`.gitignore:43`), and no workflow uploads artifacts, so a cached feed list has no path to GitHub |
| R2 | window membership and the as-of reader both by `e = max(published, first seen_at)`; the late-arrival test | resolved, but see the text fix below |
| R3 | reject-all cookie policy on the news session only (NSE and Yahoo unchanged); test plus plant | resolved |
| R4 | feed id and seen_at left out of the compared fields | resolved |
| R5 | `allow_redirects=False`; any redirect is a block | resolved |
| R6 | anchor-only assignment taken in (published, key) order; two anchors -> the earlier (then the smaller key), never merged; re-anchoring recorded in `previous_cluster_ids` | resolved |
| Residual (hash of a public URL) | in the owner section | resolved |

**One text fix the R2 change left behind (not a new design gap).** The D6 header bullet (doc lines 114-115) still
states the old input rule: "published, or if `time_source=seen` seen, within the window". That contradicts the new
`e = max(published, first seen_at)` rule written two bullets below. Correct the header line to the `e` rule in the P2c
story, so the header and the membership rule are one rule. I will check it in the P2c code round.

**Noted, accepted (reasoning only):** judge #1's fallback key (published second, plus a hash of title and summary, plus
the source) means an edited summary on a guid-less Google News item gives a new key rather than a revision. So one
article becomes two records, which clustering then merges. That is a duplicate, never a loss, and it is the right side
to err on.

Also noted: since an article is seen after it is published, `e` is in practice the first seen_at. The rule is still
correct, and it guards against a future-dated `published`.

Nothing else new. **Verdict: PASS** (design round 3, judge #2).
