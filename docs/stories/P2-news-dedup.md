# P2: news into Staging, clustered into one record per story (Phase 2 of docs/PIPELINE_DESIGN.md) — DESIGN

DESIGN, round 3 (the owner authorised it and chose the private feed list, variant A, 27 Oct 2026): the orchestrator's rulings (27 Oct 2026) and both judges' findings (judge 42 D1-D8 and its round 2, judge 43
N1-N12 and R1-R6) are written in. Lane 1 (a new outside source, Drive writes, write-once data, the privacy rule). Context:
[PIPELINE_DESIGN.md](../PIPELINE_DESIGN.md) ("News: dedup and credibility"), the gate in
[P1-staging-record-split.md](P1-staging-record-split.md), waits in [R1-resilience.md](R1-resilience.md). This is **new
capability**, so "never weaker than today" does not apply; the invariants below take its place.

## Invariants (each shown by a test and a plant)

1. **No headline, title, slug, article URL, search query or feed URL in the repository, and none outside Drive.** Not in a committed file, a log line,
   an alert, a receipt, a manifest, a snapshot-log row, a staging or Record path, or a commit message. The repository is
   public and the record scan cannot recognise a headline, so the master test below is the guard.
2. **One record per item key.** The key is defined per kind of item (D2); two distinct articles never share a key (D3);
   a repeat of the same article is a no-op or a kept revision, never a second record. Different outlets' copies of one story
   are merged by clustering only, never by the key.
3. **Nothing fetched is lost at the gate.** The gate has no age test (N6); a second version of an article is kept as a
   revision (N5), not dropped; every item of a poll is accounted for (N8). The guard here is the collision-free key.
4. **Clustering never deletes or hides an article.** Every article stays in the Record under its own id; a cluster file only
   lists article ids and is never edited. The guard here is the clustering contract, separate from invariant 3.
5. **No garbage in the Record.** A poll that does not parse, has no items, or is a block page stays in Staging with a fixed
   reason code and is alerted; nothing from it reaches the Record.
6. **No secrets, cookies or keys.** The feeds are public; nothing is signed in to and no consent is clicked through.
7. **Write-once.** Articles, revisions and cluster files are never overwritten; a changed algorithm writes a new version path.
8. **Polite.** Each host goes through the shared pacer and the resilience layer (a new source starts as strict as NSE).

## The master privacy test (N1, N2, N4, D1, D8)

A planted marker headline, marker article URL and marker search query run through fetch, gate and clustering, **including
the failure paths** (a request error whose message holds the URL, a poll that fails the gate, a block page). Then every
output that is committed or public is searched for each marker and must not hold it: manifests, receipts, snapshot-log rows,
staging and Record path names, run logs (captured stdout and stderr), alert text, and the commit message the commit step
builds. The master test captures logging at **DEBUG** (urllib3 logs the full request line, query included, R2-3) and also
scans `fno/`, `config.yaml`, `.github/` and `docs/` for any feed URL, query or headline marker (R1). Rules that make it pass:

- **The feed list lives outside the repository (R1; the owner chose this variant).** Each feed's URL or search query is in a
  private Drive file, read at run time through the Drive reader (no environment variable, which would show in logs, and no
  list in code or `config.yaml`). The code knows only opaque ids (`feed-01`, `feed-02`, never a name that shows the topic). A missing or
  unreadable list stops the run with a fixed reason code; there is no fallback list in code. The snapshot-log row, the staging
  path (`staging/news/<feed id>/<YYYY>/<MM>/<DD>/<HHMMSS>.xml`) and the receipts carry the opaque id, never the URL, `form` or
  `q=` parameter: a Google News query would show the owner's research intent. *The owner chose this over keeping
  the feeds in the repository, so queries are not published.* News gets its own snapshot-log row (feed id,
  path, sha256, size) and its own manifest, `date,article_id,status,sha256,size_bytes`, with no `url` column.
- **Fixed reason codes, messages withheld.** The P1 gate prints rejection reasons (`runs.py`, `_problem_line`) and a requests
  error carries the full URL. For news, a reason is one of a fixed list (`not_a_feed`, `no_items`, `item_missing_title`,
  `item_missing_link`, `item_missing_time`, `block_page`, `fetch_failed`) plus counts; an exception is named by class only,
  like the close read's `WITHHELD`. Alerts and logs carry counts, feed ids, a reason code and 8-character hash prefixes.
- **Commit messages** are fixed text with counts.
- **No real feed bytes in test fixtures** (N3): every fixture is small, hand-written and synthetic.

## What it does, in four steps (each its own judged round, one in flight at a time)

- **P2a, fetch into Staging.** One fetcher per feed id (Google News RSS search feeds first; a few publisher RSS feeds later)
  saves each poll's raw bytes to Staging, append-only, tagged source and seen_at. A block (N11, below) stops the host for the
  run. New workflow `news-fetch.yml` with **`workflow_dispatch` only and no active cron**, like the thirteen workflows whose
  schedules stay off until cutover: merging it starts no external fetch and no Staging write.
- **P2b, the gate for articles.** Checks: the poll parses as a feed; each item has a title, a link (or guid) and a time. An
  item without a usable time is **not rejected**: it is kept with `time_source=seen` and its first seen_at is used for
  clustering. There is **no age check at the gate** (N6): everything fetched enters the Record, so a late arrival (an
  outage, the first real run, a zone-less date) is never dropped. Passing items are written write-once, one file per key.
- **P2c, clustering** (a pure function, no I/O), described below.
- **P2d, the cluster record:** the gate writes a cluster file per run, write-once, with a SHA-256 receipt in GitHub.

## Keys and the gate (D2, D3, D4, N5, N6, N8)

- **The key per kind of item (D2).** A publisher item: SHA-256 of its canonical URL. An unresolved Google News item (its
  link is a redirect wrapper that is not resolved; the orchestrator's ruling): SHA-256 of `google-news:` plus the item's own
  `guid` when it has one, else of the **full published timestamp to the second** plus a hash of the normalised title and
  the summary plus the source name (R2-2: a date alone would collide two same-title items of one day, such as "Stocks to
  watch today", and hide the second as a revision). **Test:** one item seen in two polls gives one article; so does one
  without a guid; two same-title items a minute apart give **two** keys.
- **Canonical URL (D3).** An explicit allow-list of parameters to remove (`utm_*`, `fbclid`, `gclid`, `igshid`, `mc_cid`,
  `mc_eid`), the fragment and a default port; the host is lower-cased; every other parameter is kept, in sorted order.
  **Gate tests:** two URLs that differ only in tracking parameters give one key; two URLs that differ in a **non-tracking**
  parameter (`id=123` against `id=124`) give **two** keys and the second article is never rejected as a false duplicate.
- **The article file (D4)** has fixed fields: key, feed id, source name, title, the feed's short summary if it has one,
  canonical URL (publisher items), published time, `time_source`, and the **first** seen_at. A re-poll compares on the fixed
  fields **without seen_at and without the feed id** (R4: one guid appearing in two feeds is the same article, not a revision);
  identical is a true no-op.
- **Same key, different content (N5).** A later copy whose fixed fields differ (a live blog, a correction, a recurring title
  such as "Stocks to watch today") is **not dropped**: the first copy stays the record and the later one is kept through P1's
  revision pattern (`RevisionSink`, no version lost). Staging holds every poll in any case.
- **Per-poll reconciliation (N8).** For each poll the gate checks `items = recorded + revisions + no-ops + rejected`, with
  each rejection counted by reason code, and writes that line to the run log. **Plant:** a gate that skips an item makes the
  sum fail.

## Blocks (N11)

A Google "sorry", CAPTCHA or consent page, answered with HTTP 200 or a redirect, is a **block** as in the Yahoo source (A17e):
a response that is not a feed (no feed root element), or a redirect to a consent or `sorry` address, stops that host for the
run, is reported with the `block_page` code, and is never retried with a cookie, another user agent or another address. The
next scheduled run asks once more the same way. It is not a parse failure that would be re-polled in a loop. Requests are
sent with `allow_redirects=False` and **any redirect is a block** (R5). The news session carries a **reject-all cookie
policy** (R3), scoped to the news session only so that NSE's and Yahoo's cookie handling (the shared `PacedSession`) is not
changed; **test:** the second request of a news session carries no `Cookie` header, and a plant that accepts cookies fails.

## Clustering (P2c; N7, N9, N10, D5-D7)

- **Stages.** (1) the same key; (2) near-duplicate titles: lower-case, punctuation and the trailing publisher name removed,
  word shingles, Jaccard similarity above a threshold, within a time window; (3) a shared **entity** (an F&O symbol or index
  name from a fixed list) may only **constrain** a title match (raise or lower its bar). **Nothing is merged on an entity
  alone, and similarity is not chained**: A~B and B~C do not put A and C together unless A~C. **Test (N7):** two distinct
  NIFTY stories on one day stay **two** clusters, and a plant that merges on the entity alone fails it.
- **Required test:** one story seen through both a Google News wrapper and its publisher feed (different id bases) lands in
  **one** cluster; a plant that removes the title stage must fail it.
- **The assignment rule (R6) is explicit and non-chaining:** articles are taken in order of (published time, key); each
  joins an existing cluster only if it is similar to that cluster's **anchor** (its earliest member), never to any other
  member, else it starts a new cluster. An article similar to two anchors joins the cluster with the **earlier anchor** (ties:
  the smaller key); the two clusters are not merged, which is what keeps it from chaining.
- **The cluster id (D5)** is the hash of its earliest article's key, earliest by publication time, ties broken by the smaller
  key. When a later-arriving earlier article changes an id, the new file has a
  `previous_cluster_ids` column naming the ids it replaces, so a consumer can follow a story. When the anchor itself ages out of the window, the cluster is re-anchored to its earliest
  remaining member and the same column names the old id (R6).
- **The file header (D6)** states the algorithm version, the window end (the run's as-of time) and the input rule (articles
  with first seen_at at or before the window end and effective time `max(published, first seen_at)` within the window before it).
  Deterministic: sorted inputs, no randomness; the same inputs give the same bytes, so a rerun is a no-op.
- **The window applies to clustering only (N6), and an article belongs to it by `max(published, first seen_at)`** (R2), so a
  late arrival (published three days ago, first seen today) enters a cluster instead of being lost to clustering. **Test:**
  an article published before the last window and first seen now appears in the next cluster file. The window length is set in P2c from collected data, not guessed.
- **Articles that leave the window (D7)** stay in the Record for ever under their own ids; they stop appearing in newer
  cluster files, and the older files that listed them stay as they were.
- **Concurrent runs (N9).** The promotion job has a workflow `concurrency` group with `cancel-in-progress: false` (as
  `global-cues.yml` does), so runs are serial and window ends strictly increase. The file name is the window end; a second
  write to the same name with other bytes is a reported conflict.
- **"As known at T" (N10).** The latest file holds only the window, so for a story with effective time e = `max(published, first seen_at)` (the same time the window rule uses, R2) a reader takes
  the latest file with window end at or before T **whose window covers e**. A reader helper does exactly this and a test shows it
  reaches a story older than the newest file's window.
- **Corroboration** = the number of independent outlets in the cluster (a wire story printed twice counts once where a wire
  credit is visible; an owner decision, below).

## Dedup state

There is **no separate mutable dedup state.** The Record's article files are the state; each clustering run recomputes from
them. Nothing is updated in place, so it is write-once safe and idempotent.

## Where each piece runs (extends [RUN_LOCATIONS.md](../RUN_LOCATIONS.md) when built)

All in this repository's GitHub Actions (no key needed): `news-fetch.yml` (P2a) and a promotion job for P2b-d, each ending
with the pause-log step (`ops/commit_pause_log.sh`). Unlike the Groww and O1 pieces, their behaviour is verifiable from this
repository's logs and Drive.

## Decided (orchestrator, 27 Oct 2026)

- **No cron** on `news-fetch.yml` or the promotion job; the first real fetch and promotion are on the owner's go-live list.
- **Google News links are not resolved** (no second request per item); P2a measures the split of Google News and publisher
  items.
- **P2a starts on the Google News RSS feeds** and proposes the publisher candidate list in its own story.
- **The reference repository is not part of this build** (below).

## OWNER decisions (flagged, not assumed by this plan)

- **Which publisher feeds, and their terms.** None are named here; each must be fetched and its terms read first.
- **R1, decided:** the owner chose the private feed list (feeds outside the repository, opaque ids). Nothing is left open here.
- **Residual risk, named (judge 43):** an article key is the SHA-256 of a public URL, so someone who guesses a URL could
  confirm it is archived. Very low risk; stated so the owner can accept it.
- **N12: does owner rule 50a79a43 (source terms do not block private research; values stay in Drive) cover publishers'
  headlines and summaries?** The plan keeps all of it in private Drive; whether that is permitted for news is the owner's.
- **What counts as independent.** Proposed default: count the *origin* where a wire credit (PTI, Reuters, ANI, Bloomberg) is
  visible, the outlet otherwise.
- **The similarity threshold, window and the window length.** Set from collected data and a labelled pair set (true
  duplicates, near-misses, same-topic-different-story), with precision and recall brought to the owner for sign-off, since
  they trade a false merge (a lost story, an inflated corroboration count) against duplicates.
- **Retention.** Staging copies are never deleted today (P1 gap list). Reasoning only, every figure an assumption (no feed
  has been fetched): about 10 feeds polled every 15 minutes is 960 polls a day of 50-100 KB, so roughly 50-100 MB a day,
  18-36 GB a year, mostly repeated headlines. Options: (1) leave Staging unbounded; (2) prune Staging by age once its articles
  are promoted, keeping the Record for ever; (3) poll less often (hourly is fourfold less). Suggested default pending the
  owner: poll hourly first and decide pruning after a week of real sizes. **Whatever is chosen, a poll that failed the gate
  is never pruned before someone has looked at it.**
- **The reference repository.** The design suggests studying `contactexepex/agentic-stock-prediction` for a proven dedup;
  attaching it mints credentials, so it is the owner's decision, and nothing here depends on it.

## P2a as built (fetch into Staging)

- **Code:** `fno/ingestion/news/` (`feeds.py`, `session.py`, `response_check.py`, `fetcher.py`, `snapshot_log.py`, `job.py`,
  `cli.py`, `wiring.py`), the command `python -m fno news fetch`, and `.github/workflows/news-fetch.yml` with
  `workflow_dispatch` only (a test fails if a schedule is added).
- **Feed list (Judge 1's versioning point):** write-once files `feeds/feeds-v<N>.json` in a private `config` area of the Drive
  folder; the newest by number is used (v10 beats v9); the owner adds a version instead of editing one. A missing, invalid or
  older-than-already-used list stops the run before any request, with a fixed code. **An edited version is detected:** the
  first use of each list version logs its SHA-256 (`feed_lists.csv`); a version whose file no longer has that hash was edited in place, is
  skipped, the next older good version is used, and the run reports `feed_list_damaged` and alerts (never silent); if every
  version was edited the run stops with the same code before any request.
  **To change the feeds the owner adds a new file** `feeds/feeds-v<N+1>.json` (the next number) in the private `config`
  area; the next run reads it with no halt. Never edit an existing version. The highest version used is read back from
  `feed_lists.csv` in the poll-log folder (one row per version ever used: its first-use time and its SHA-256; a run of
  unchanged polls still leaves it). The list is read directly from Drive **with no receipt** (it is not a
  Record file and does not go through the verified cache); its integrity is checked by the SHA-256 logged when a version is first used. **The list format requires a random `salt`
  of 16 or more characters** (a list without one is refused), so the committed hash cannot confirm a guessed list.
  Cases: a first-time invalid version stops the run (`feed_list_invalid`, so a typo is caught at once and the previous list
  is not silently used); a version edited after use falls back to the last good one and alerts. **The fallback can
  therefore go below the highest version used** (an alerted rollback): that is intended, because the newer file was damaged
  and the older one is known-good. The two cases differ on purpose: a never-used invalid version has no known-good meaning
  and stops the run so an owner's typo is caught at once, while an edited used version had one. Reasoning only for adding a
  version rather than editing: the owner never halts the pipeline and a bad version leaves the previous one in place.
- **Session:** `NewsSession`, a subclass of the shared `PacedSession` used by the news fetcher alone: a reject-all cookie
  policy and `allow_redirects=False`. NSE's and Yahoo's sessions are unchanged. The session
  also pins the `urllib3` logger to WARNING, because at DEBUG it logs the host and the full request line, query included
  (judge 44 F1; tested through the real session against a local HTTP server with DEBUG captured).
- **Hosts stay out of the committed pause log (judge 44 F3).** The shared pacer's committed log and its #fno-desk alerts name
  the host. The news session therefore has its own pacer (`NEWS_PACER`), never attached to either: a news pause lasts for the
  run only, with no memory across runs (the workflow is manual). Tested with the real pacer, with a control showing the shared
  session does write the host. The alternative, declaring the news hosts non-private and using the shared pacer for
  cross-run memory, is the orchestrator's and owner's call; this is the safe default.
- **Answers:** a redirect, or a 200 without a feed root element, is `block_page`; 403/429 is `refused`; both stop the rest of
  that host for the run, as does `host_paused` from the shared pacer. Other failures are `fetch_failed`. Only the fixed code is
  kept: never an exception message, a URL or a title.
- **Staging:** the raw bytes go to `news/<feed id>/<YYYY>/<MM>/<DD>/poll/<stamp>`; an unchanged poll (the same bytes as the newest
  staged copy) is not stored again, which also slows the growth of Staging. A poll-log row is written only after Staging accepted
  the bytes.
- **Not in P2a:** the gate (P2b), clustering (P2c), the cluster record (P2d), the article key, the revision handling and the
  per-poll reconciliation of items: they need the parsed items.
- **Proof:** 64 offline tests (no network, no Drive; a real local HTTP server for the cookie test) including the privacy test
  over a planted marker URL, query, host and headline, the failure paths and DEBUG logging; mutation plants on the cookie policy,
  redirects, the feed check, the host stop, file-first ordering, the privacy paths, the version rules, the alert and the schedule.
  One plant survives and is equivalent: `return_ok` returning True changes nothing while `set_ok` stores no cookie.

## Deferred to the owner's go-live (not done in this build)

A scheduled run of `news-fetch.yml` and of the promotion job; the first real fetch into Staging; the first real promotion of
an article, a revision or a cluster to the Record. Until then the proof is offline: tests on synthetic sample feeds (no
network), mutation plants, and two judges per step.

## Gates

Per step: full suite, ruff, imports, numbers, size (350 lines per file and class), record scan; mutation plants for every
invariant above; two judges. Clustering also gets the labelled pair set with measured precision and recall stated, not assumed.
