# P2: news into Staging, clustered into one record per story (Phase 2 of docs/PIPELINE_DESIGN.md) — PLAN

PLAN, with the orchestrator's rulings of 27 Oct 2026 written in, for a design review before any code. Lane 1 (a new outside source, Drive
writes, write-once data, the privacy rule). Design: [PIPELINE_DESIGN.md](../PIPELINE_DESIGN.md) ("News: dedup and
credibility"); precedent for the gate: [P1-staging-record-split.md](P1-staging-record-split.md); waits and politeness:
[R1-resilience.md](R1-resilience.md). This is **new capability, not a refactor**, so "never weaker than today" does not
apply; the invariants below take its place.

## Invariants (what must hold, each shown by a test and a plant)

1. **No duplicate records.** An article's id is the SHA-256 of its canonical URL; saving it again is a no-op (same bytes)
   and a different body for the same id is kept as a later copy in Staging, never an overwrite of the Record.
2. **No garbage in the Record.** A poll that does not parse as the feed's format, has no items, or has items without a
   title, link or time stays in Staging with its reason and is alerted to #fno-desk; nothing reaches the Record.
3. **No secrets, no cookies, no keys.** The feeds are public; nothing is signed in to. Raw text and clusters live in
   private Drive only; GitHub gets receipts, manifest rows and counts (never a headline), under the existing record scan.
4. **Write-once.** Articles are written once under their id; a cluster file is never changed (a story that gains a source
   later appears in a *later* cluster file), exactly as the global-cue copies work.
5. **Clustering never deletes or hides an article.** Every article stays in the Record under its own id; a cluster is a
   view that only lists article ids, so a dedup cannot drop a real new record (a clusterer that drops a member fails a test).
6. **Polite.** Each host goes through the shared pacer and the resilience layer (a new source starts as strict as NSE); a
   429 or 403 pauses the host and is never retried another way.

## What it does, in four steps (each its own judged round, one in flight at a time)

- **P2a, fetch into Staging.** A fetcher per feed (Google News RSS search feeds and a few publisher RSS feeds) saves each
  poll's raw bytes to Staging, tagged source + seen_at (`staging/news/<source>/<YYYY>/<MM>/<DD>/<HHMMSS>_<feed>.xml`),
  append-only, with a snapshot-log row like the global cues. A new workflow `news-fetch.yml`, **`workflow_dispatch` only
  until the owner approves go-live** (a cron would start real writes to Staging on merge; see "Deferred").
- **P2b, the gate for articles.** New promotion checks: the poll parses; each item has title, link and a time; the item's
  time is inside a freshness window; the canonical URL is computed (tracking parameters and fragments removed). Passing
  articles are written write-once to the Record, one file per article id (title, source name, published time, seen_at,
  canonical URL; no article body).
- **P2c, clustering (a pure function, no I/O).** Articles inside a rolling window are grouped by: exact canonical URL, then
  near-duplicate titles (lower-case, punctuation and the publisher suffix removed, word shingles, Jaccard similarity above
  a threshold, within a time window), then shared entities (F&O symbols and index names found by a fixed list). Output:
  clusters with a stable id (hash of the earliest article's id), member article ids, first-seen time per source.
  **Deterministic**: sorted inputs, no randomness, an algorithm version in the file header; the same inputs give the same
  bytes, so a rerun is a no-op and a changed algorithm writes under a new version path.
- **P2d, the cluster record.** The gate writes a cluster file per run (`news/clusters/v1/<YYYY>/<MM>/<DD>/<HHMMSS>.csv`,
  write-once, SHA-256 receipt in GitHub). A consumer asks "the clusters as known at time T" = the latest file with
  created_at at or before T: the project's point-in-time rule. Corroboration = the number of *independent* outlets in the
  cluster.
  **Required test (P2c):** one story seen through both a Google News wrapper and its publisher feed (different id bases)
  lands in ONE cluster, never two (the title-shingle and entity stages must catch it); a plant that removes the title stage
  must fail it.

## Dedup state: where it lives

There is **no separate mutable dedup state**. The Record's article files are the state; each clustering run recomputes
from the last N hours of them. That keeps it write-once safe (nothing is updated in place) and idempotent.

## Where each piece runs (extends [RUN_LOCATIONS.md](../RUN_LOCATIONS.md) when built)

All new pieces are GitHub Actions workflows in this repository (no key needed): `news-fetch.yml` (P2a) and a promotion job
for P2b-d. Verifiable from this repository's logs and Drive, unlike the Groww and O1 pieces. The pause-log step
(`ops/commit_pause_log.sh`) goes at the end of both.

## Decided (orchestrator, 27 Oct 2026)

- **No cron.** `news-fetch.yml` and the promotion job ship with no active schedule; the first real fetch and the first
  promotion are on the owner's go-live list.
- **Google News links are not resolved.** No second request per item. Google News items use title, source name and time;
  publisher feeds use the canonical URL. P2a measures the split. The P2c test above covers the cross-source case.
- **P2a starts on the Google News RSS feeds** (no owner URL decision needed) and proposes the publisher candidate list in
  its own story; it does not wait for the owner on publisher feeds.
- **The reference repository is not part of this build.** The design suggests studying `contactexepex/agentic-stock-prediction`
  for a proven dedup; attaching it is the owner's decision (it mints credentials), and nothing here depends on it.

## OWNER decisions (flagged, not assumed by this plan)

- **Which publisher feeds, and their terms.** None are named here; each must be fetched and its terms read first. Owner rule
  50a79a43 (terms do not block private research; values stay in Drive) is assumed to cover news as it covers Yahoo.
- **What counts as independent.** Default proposed: count the *origin* where a wire credit (PTI, Reuters, ANI, Bloomberg) is
  visible, the outlet otherwise. The owner may override. The forecasting engine's use of the count is application-side.
- **The similarity threshold and window.** Not guessed: set from collected Staging data and a labelled pair set (true
  duplicates, near-misses, same-topic-different-story), with the measured precision and recall brought to the owner for
  sign-off, since it trades a false merge (lost signal) against duplicates.
- **Retention.** Staging copies are never deleted today (P1 gap list), so polling for months grows Drive; no rule yet.
- **The reference repository** above.

## Deferred to the owner's go-live (not done in this build)

A scheduled (cron) run of `news-fetch.yml` and of the promotion job; the first real fetch into Staging; the first real
promotion of an article or a cluster to the Record. Until then the proof is offline: tests on recorded sample feeds (small synthetic files, no network),
mutation plants, and two judges per step.

## Gates

Per step: full suite, ruff, imports, numbers, size (350 lines per file and class), record scan; mutation plants for every
invariant above; two judges. Clustering also gets a labelled pair set (true duplicates, near-misses, same-topic-different-
story) with the measured precision and recall stated, not assumed.
