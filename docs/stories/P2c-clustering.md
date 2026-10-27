# P2c: clustering — articles into stories (PLAN)

PLAN for the orchestrator's check before any code. Lane 1 (it will feed a Record file in P2d; the privacy rule applies). Design,
invariants and the assignment rule are in [P2-news-dedup.md](P2-news-dedup.md#clustering-p2c-n7-n9-n10-d5-d7) (merged, double-PASSed);
this plan only turns them into files and tests. **P2c is a pure function: no I/O, no clock, no network.** It reads article values
(P2b1's `Article`) and returns clusters; nothing is written until P2d.

## Files (`fno/ingestion/news/cluster/`, each under 100 lines, one purpose)

| File | Purpose |
|---|---|
| `title_text.py` | the title form compared: lower-case, punctuation and the trailing outlet name removed; word shingles |
| `similarity.py` | Jaccard similarity of two shingle sets (a `Similarity` interface, one implementation, so a better measure is one class) |
| `entities.py` | the fixed list of F&O symbols and index names; `shared_entity(a, b)` only; a list in the code is a decision, not data |
| `matcher.py` | `same_story(a, b)`: stage 1 same key; stage 2 title similarity above the threshold within the time window; stage 3 an entity may only raise or lower the bar, never merge alone |
| `assign.py` | the R6 rule: order by (effective time, key); join the cluster of the earliest similar **anchor**, else start a new one; never chain |
| `cluster_id.py` | D5 id (hash of the earliest article's key; ties by the smaller key) and `previous_cluster_ids` when an earlier article arrives or the anchor ages out |
| `window.py` | effective time `max(published, first_seen_at)` (R2) and the window rule (N6) |
| `cluster.py` | the value types (`Cluster`: id, member keys, previous ids) and `cluster_articles(articles, as_of)` that wires the above |

## Tests, and the invariant each plant guards

- Same key is one cluster (stage 1). Plant: skip stage 1.
- A Google News wrapper copy and its publisher copy of one story are one cluster. Plant: remove the title stage.
- Two different NIFTY stories on one day are two clusters (N7). Plant: merge on the entity alone.
- A~B and B~C without A~C stay apart (no chaining). Plant: compare to any member instead of the anchor.
- An article similar to two anchors joins the earlier anchor; the clusters are not merged. Plant: merge them.
- Cluster id: deterministic, smaller key breaks ties; an earlier late arrival changes the id and names the old one in
  `previous_cluster_ids`; an aged-out anchor re-anchors with the same column. Plant: drop the column.
- Window: an article published before the window but first seen now is in the next run (R2). Plant: window on `published` only.
- Determinism: shuffled input order gives identical output; a random-order property test over many shuffles.
- Nothing hidden (invariant 4): every input article key appears in exactly one cluster; articles outside the window appear in none
  and are reported by count. Plant: drop a singleton.
- Privacy: no function returns or logs a title; clusters hold keys only. The master privacy marker test runs through clustering.

## How it meets the Record, the version, the output and the privacy surface

- **Reads, never writes (P2c has no I/O).** The reader that feeds it is P2d: it lists `news/articles/` and reads each article file
  from the Record (revisions are NOT inputs: the first file is the story's text of record; a revision only matters to a reader
  who asks for it). P2c itself takes `Article` values, so the Record cannot be mutated from here; the P2d wiring test proves the
  reader has no `put`.
- **Versioned clusterer.** `ALGORITHM_VERSION` is a constant written in the cluster file header (design D6); a changed
  threshold, window, stage or entity list bumps it, and a new version writes a new path, never over an old file (invariant 7).
- **Point in time.** The input rule is the design's: articles with `first_seen_at` at or before the window end and effective time
  `e = max(published, first_seen_at)` inside the window. The same inputs give the same bytes; a rerun is a no-op.
- **Output (P2d, not P2c).** One cluster file per run in the Record, `news/clusters/<algorithm version>/<window end>.json`, write-once,
  with a SHA-256 receipt and a manifest row like an article. P2c returns the values only.
- **Privacy surface.** A cluster holds the cluster id, member **keys** (hashes), `previous_cluster_ids`, counts and the header.
  No title, URL, query or feed id appears in any value, log line or alert; the P2c privacy test runs the marker headline and URL
  through clustering and searches every returned value and every log line.
- **New risks.** (1) Cost: pairwise comparison inside a window is O(n²); a window of 1,000 to 3,000 articles is fine, and shingle
  buckets are the next step if it is not (reasoning only; not measured). (2) The entity list can raise or lower the bar, so a wrong
  entry changes which stories merge, never whether an article is kept (invariant 4 holds regardless).

## Why revisions are not clustering inputs, and a scale watch

- **Revisions.** An article's key is stable across versions, so a corrected title changes no key and no cluster id. The
  point-in-time rule uses `first_seen_at`, which a revision never changes. A cluster holds keys only, so a changed title is never
  copied into it. A reader who wants the revised text follows the key into the revisions area. Accepted cost: a correction that
  would make a story match a different one is not re-clustered, because the design clusters on the first text of record.
- **Scale watch.** Pairwise comparison inside a window is O(n²). The window bounds it; a wide `--from` backfill is the risk, so
  the run reports the number of articles in the window, and a window over a stated cap (set in P2d, not guessed here) is reported
  rather than silently slow.

## What I cannot prove, said plainly

- **The threshold and the window length have no real data behind them yet.** The design says they are set from collected data;
  nothing has been collected (the first real fetch is the owner's go-live). I will ship a default threshold and window as
  named constants, tested only on **synthetic labelled pairs** that I write. Precision and recall measured on invented pairs is a
  check that the code does what the rule says, **not** evidence about real news. Reasoning only. Ask: accept shipping
  unmeasured defaults and re-tune after the first week of real polls, or hold P2c until then?
- **The entity list is a guess** (F&O symbols and indices that the project already holds can seed it; the list lives in code).
- **Wire-credit outlet counting (corroboration)** is an owner decision (design) and is **not** built in P2c; it is a later field.

## Decision (orchestrator, 27 Oct 2026) and the warning that goes with it

Ship named default constants for the similarity threshold and the window, behind the `Similarity` interface so re-tuning is a
one-line change, and re-tune from the first week of real polls. **Until then, neither a story count nor a corroboration
count may be trusted, in either direction:** under-merging inflates the story count and deflates each story's corroboration (its
outlets are split over the pieces), and over-merging does the reverse. The defaults are reasoning only, tested on invented pairs, which
proves the code obeys the rule and says nothing about whether the threshold is right for real news. The same warning is in the
constants' docstring. The hard guards (no merge on an entity alone, no chaining) bound the damage of a wrong threshold to
"too many or too few clusters", never to a lost or hidden article. Corroboration and wire-credit counting stay out (owner
decision). One judge, as for P2b1 (a pure module), after P2b3 merges.

## P2c as built

- **Code:** `fno/ingestion/news/cluster/` (`title_text`, `similarity`, `entities`, `window`, `matcher`, `assign`, `cluster_id`,
  `cluster`), 270 lines in all, each file under 70. No I/O, no clock, no logging, no randomness (an AST test pins the imports
  and calls). `cluster_articles(articles, as_of, previous=())` returns `Clustering` (clusters of hash keys, the counts of articles
  outside the window and of repeated keys, `ALGORITHM_VERSION`).
- **As planned:** same key; title shingles (2-word) and Jaccard at `THRESHOLD` 0.55 within a 36-hour match window; an entity
  moves the bar by 0.10 (lower when shared, higher when each names only others) and never merges alone; the anchor rule with no
  chaining; the cluster id is the SHA-256 of the anchor's key; `previous_cluster_ids` names replaced ids (an earlier article
  arriving, or an anchor that left the 48-hour window); window membership by `max(published, first seen)`.
- **Decisions made while building:** a repeated key is one article and its EARLIEST sighting is kept (as the Record keeps the
  first file); an article first seen after the run's end waits for a later run; the redundant `first seen <= as_of` check was
  removed because the effective time is never earlier than the first-seen time.
- **Measured, on invented pairs only (test_labelled_pairs.py):** 17 pairs I wrote (8 the same story, 9 not). Precision 5 of 6 and
  recall 5 of 8. The defaults under-merge short rewordings ("wins" against "bags", "a record low" against "record low") and
  cannot tell a one-word reversal from a rewording: a hard near-miss added on Judge 1's request ("Nifty closes at record high"
  against "record low") MERGES. Under-merging inflates a story count and deflates each story's corroboration; the false merge
  does the reverse; so neither number is trustworthy until the threshold is re-tuned on real data. I did not tune on my own
  pairs: that would fit the numbers to my own invention. Reasoning only; no real news is behind any of it.
- **Proof:** 31 tests; plants fail a test for stage 1, the title stage and the outlet trim, an entity merging alone, the entity
  bar, the match window, chaining, the two-anchor choice, the assignment order, the id hash, `previous_cluster_ids`, the window
  edges and the effective time, the earliest-sighting rule, the repeated-key count, a dropped article, and input order.

## Order and gates

P2c, then P2d (the cluster record). Gates: full suite, ruff, imports, numbers, size (350 per file and class), record scan,
mutation plants for every line above, one judge (a pure module; the Record writer is P2d, with two).
