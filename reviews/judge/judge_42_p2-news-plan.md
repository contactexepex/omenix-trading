# Judge 42: P2 news and dedup plan (`docs/stories/P2-news-dedup.md`), design review, judge #1

**SHA:** `83ca7585b1758aed65ad9e65eb8964e36f33fce1` (`story/P2-news-plan`). The diff is the plan only (83 lines). Lane 1.
Reviewed as the orchestrator directed:
- **Decided:** dispatch-only workflows; Google News wrappers not resolved; the reference repository not attached.
- **Committed:** invariant 6 (clustering never deletes or hides an article); the wrapper-plus-publisher one-cluster
  test; retention as an owner question.

**Verdict: FAIL, design.** The write-once *storage* shape is sound: new files only, no mutable state, and
point-in-time reads by `created_at`. But four design gaps can produce duplicate records, lose a real article, or put
headlines into the public repository. Three of them touch hard lines (duplicates, write-once loss, privacy). **I ask for
the second judge** under the orchestrator's own rule.

## What is sound (reasoning, checked against the code where named)

- No mutable dedup state.
- Articles and cluster files are new files only.
- A changed algorithm writes under a new version path.
- The point-in-time read, "latest cluster file with `created_at` ≤ T", is the right rule and can be built
  write-once, the same way as the global-cue copies.
- Dispatch-only until go-live means nothing is written by merging.

## Required design fixes

### D1. Privacy: article URLs would go to GitHub through the standard manifest

Strong evidence, code read.

The plan says GitHub gets "receipts, manifest rows and counts (never a headline)". The repository's standard manifest
commits a `url` column: `MANIFEST_FIELDS = ("date", "url", "status", "sha256", "size_bytes")` (`manifest_folder.py:22`).
The global-cue manifests do the same: `fetched_at,path,url,...`.

A publisher's canonical URL usually *is* the headline: a slug such as `/markets/nifty-falls-200-points-...`. Reusing the
manifest for articles therefore publishes every headline. The record scan looks for secrets and channel IDs, not
headlines, so nothing would stop it.

The design must state that:
- no article URL, title or slug appears in any GitHub file, run log or alert;
- article receipts and rows carry only the article id (the hash), the feed name and counts;
- the feed URL, a search query, is allowed only if the owner agrees: the query text is public.

It also needs a test that fails if a row, receipt, log line or alert contains a planted headline or slug. This mirrors
the rule that raw quote files are kept in Drive only.

### D2. Duplicates: the article id for a Google News item is undefined

Strong evidence: the plan and the ruling read together.

- **Invariant 1:** id = SHA-256 of the canonical URL.
- **The ruling:** Google News wrappers are not resolved, so "title + source + time" is used for them. The design never
  says what the *id* of such an item is.
  - If it is the hash of the wrapper URL, the item gets a new id whenever Google changes the token for the same article,
    which I have not verified. Each poll could then write a new article record for the same item, which breaks
    invariant 1.
  - If it is the hash of title + source + time, an edited headline or a re-timestamped item becomes a second record.

Fix:
1. Define the id per item kind: the publisher canonical URL, or a stated Google News key.
2. Make invariant 1 say "one record per *item key*". Cross-source duplicates are merged at the cluster level, never
   deleted, matching invariant 6.
3. Add a test: the same Google News item over two polls gives one article file.

### D3. Over-normalising the canonical URL silently loses articles

Reasoning, but a direct path to data loss.

"Tracking parameters removed" has no list. If normalising strips a query parameter that identifies the article (some
sites use `?id=` or `?articleid=`), two different articles get the same id. Under first-copy-wins, the second becomes a
"later copy" in Staging and never reaches the Record. That is a real article lost before clustering, and invariant 6
does not cover it.

Fix:
- The removed parameters are an explicit allow-list: `utm_*`, `fbclid`, `gclid` and named others. Everything else is
  kept.
- Add a test that two URLs differing only in a non-tracking parameter give two ids.

### D4. "Same bytes" contradicts the stored fields

Strong evidence: the plan reads against itself.

Invariant 1 says re-saving is a no-op with the same bytes. But P2b stores `seen_at` in the article file, and it differs
on every poll. So every re-seen article within the freshness window would be "a different body for the same id". That
writes a later copy to Staging every poll, which is unbounded growth, and every one is a false revision.

Fix: the Record article file holds only fields fixed for the item (title, source, published time, canonical URL or key,
and the *first* `seen_at`). A re-poll compares on those fields, and a later `seen_at` alone is not a revision.

## Smaller design points (required in the revision, not hard-line)

- **D5. "Stable cluster id = hash of the earliest article id" is not stable.**
  - Earliest by which time? `published` is supplied by the feed and can be edited.
  - A late-promoted earlier article changes the earliest member, and with it the id. So do merges and splits between
    runs.

  It is not a write-once problem, because each run writes a new file, but "stable" is false. Either define the tie-break
  and say ids can change when membership changes, or add an explicit lineage column (the previous ids that a cluster
  continues).
- **D6. "The same inputs give the same bytes, so a rerun is a no-op" needs the window fixed.**
  - The inputs are "the last N hours" of the Record as read at run time. A later run, or a run after late promotions,
    sees different inputs.
  - State the window end (from the run's stamp) and the input rule (articles in the Record at `created_at` with
    `seen_at` in the window) in the file header.
  - Then point-in-time holds as "what was known at T", and a rerun for the same stamp is reproducible.
- **D7. Invariant 6 and the rolling window.** An article older than N hours drops out of later cluster files. The
  design must say where it can still be found: the article file always, and the last cluster file whose window held it.
  Otherwise "latest file at or before T" can look like hiding.
- **D8. Alerts for garbage polls (invariant 2)** must name the feed and the reason class only, never an item's title.
  This is the same rule as D1.

## Invariants: completeness

The five, plus the committed sixth, miss:
- (a) no headline or URL outside Drive (D1);
- (b) one record per item key, and the key's definition (D2 and D3).

Each needs a test and a plant. The rest are testable as written.

## Hard lines

No orders; no secrets, because the feeds are public and nothing signs in. Privacy is the one hard line at risk (D1).
Nothing is built, so nothing is at risk yet.

## Addendum 1: SHA corrected to f23aeff: FAIL stands, D1-D8 unchanged

The orchestrator corrected the SHA to `f23aeff1faacfd56151bd33c48e83b63865989e7`. The diff from 83ca758 writes in what I
had already reviewed as decided or committed:
- the "Decided" section;
- invariant 5, "clustering never deletes or hides an article";
- the P2c cross-source one-cluster test;
- the owner-decisions list, including retention.

None of D1-D4 is touched:
- invariant 3 still says "GitHub gets receipts, manifest rows" while the standard manifest carries a `url` column (D1);
- the article id for a Google News item is still undefined (D2);
- "tracking parameters removed" still has no list (D3);
- `seen_at` is still in the article file under a "same bytes" no-op (D4).

**D3 is outside the new invariant 5.** An id collision from over-normalising loses the second article at the gate,
before any clustering. "Clustering never deletes or hides an article" does not cover it. The design needs the
one-record-per-item-key invariant asked for above.

**The P2c test is right,** and it fits D2: two article records (wrapper and publisher), merged in one cluster, none
deleted.

**Verdict at f23aeff: FAIL (design).** D1-D8 as above. The second judge is still asked for.

## Addendum 2: design round 2, ca6a8c5: FAIL, two new gaps (D1-D8 resolved)

Reviewed `ca6a8c5aca97039e2c49be53ea90ace7fb0b6290`, a full rewrite (160 lines).

**My D-items are resolved in the text:**

| Item | How it is resolved |
|---|---|
| D1 | Invariant 1 and the master privacy test, failure paths included. Feed ids only. The news manifest has no `url` column. `revisions.py:25`'s `INDEX_FIELDS` carries a key-based path, no URL. |
| D2 | Keys defined per kind. |
| D3 | An explicit strip allow-list, and the gate test (`id=123` against `id=124` gives two keys). Invariant 3 is kept separate from invariant 4. |
| D4 | The fixed fields are compared without `seen_at`. |
| D5 | A tie-break plus `previous_cluster_ids`. |
| D6 | The header carries the version, the window end and the input rule. |
| D7 | Articles stay in the Record for ever. |
| D8 | Fixed reason codes, messages withheld. |

The block handling (N11), the serial concurrency (N9), the window-covers-t reader (N10) and the per-poll reconciliation
plant (N8) are sound too.

### New gap R2-1 (blocking, privacy): where the feed URLs live is not said

Invariant 1 forbids "search query or feed URL outside Drive". The fetcher needs the URLs, and the design says only that
"each feed has a fixed short id **in the code** (`gn-nifty`, not its URL)". If the URLs sit in the code or in
`config.yaml`, which are committed, invariant 1 is broken by construction, and the master test would not see it: the
test scans outputs, not the source tree.

The id `gn-nifty` also names the query's topic in the public code. The design itself says a query "would show the
owner's research intent".

Fix:
- The feed list (id → URL) lives in private storage: a Drive file read at run time, or a GitHub secret. Its absence is a
  named configuration error.
- Feed ids are neutral (`gn-01`), or the owner accepts topic-named ids in writing.
- A test scans the committed tree (`fno/`, `config.yaml`, workflows) for a `news.google.com/rss/search` URL.

### New gap R2-2 (blocking, an article hidden): the Google News fallback key can collide, and the collision hides the second article

The fallback key, used when there is no `guid`, is the normalised **title + source name + publication date**. Two
distinct articles from one outlet on one day with the same normalised title get one key. Examples: two "Sensex today
LIVE" or "Stock market highlights" items, or a morning and an evening edition.

Under N5 the second becomes a *revision* of the first. Revisions are kept, so the bytes are not lost. But clustering
reads the article Record, so the second article is never clustered or counted. In effect it is hidden, against the
spirit of invariants 2 and 4. Invariant 2's "two distinct articles never share a key" is false for this fallback.

Fix:
- Use the full publication time to the second, plus a hash of the summary if there is one, in the fallback key.
- State the residual case honestly: a collision is kept as a revision, and the reconciliation line counts it as
  `revision`.
- P2a measures on real data how often a Google News item lacks a `guid`, and the owner sees that rate.
- Clustering must also read revisions whose title differs, or the doc must say clearly that it does not.
- Add a test: two distinct same-title items, one minute apart, give two keys.

### Carried to the P2a code (not design-blocking)

**R2-3.** The master test must run with Python logging captured at DEBUG. A library can log a URL on its own: urllib3's
retry warnings name the request path, query included. Today there is no `HTTPAdapter` or `Retry` in `fno/`, so the fetch
code must not add one that logs, and the test must prove it.

**Verdict at ca6a8c5: FAIL (design).** R2-1 and R2-2 are small text fixes with one test each. This was the decisive round
(two-round rule), so the call goes to the owner. My recommendation to the owner: accept the design once R2-1 and R2-2 are
written in. Everything else is sound.

## Addendum 3: design round 3 (owner-authorised), 06e3467: PASS, with one new item for the owner and two text corrections

Reviewed `06e3467212d5bf17f1a357b25ddcf7684eba7392`. The diff from ca6a8c5 is the design doc only (+37/-16).

**Round-2 items, each written in correctly:**

| Item | How it is written in |
|---|---|
| R2-1 / judge 43 R1 | A private Drive feed list, opaque `feed-NN` ids, no environment variable, no list in code or config. A missing list stops the run. The master test scans `fno/`, `config.yaml`, `.github/` and `docs/`. |
| R2-2 | The fallback key uses the timestamp to the second plus a hash of title and summary plus the source. Test: same-title items a minute apart give two keys. |
| R2-3 | Logging captured at DEBUG. |
| Judge 43 R2 | `e = max(published, first seen_at)` for both window membership and the as-known-at-T reader, with the late-arrival test. |
| R3 | A reject-all cookie policy on the news session only (`PacedSession` unchanged for NSE and Yahoo), with a test and a plant. |
| R4 | Feed id and `seen_at` are out of the compared fields. |
| R5 | `allow_redirects=False`, and any redirect is a block. |
| R6 | The anchor rule, an earlier-anchor tie-break, and re-anchoring through `previous_cluster_ids`. |

**Two text corrections (incomplete folds, not new design).** They are required in the P2a/P2c story text and checked at
that step:
1. **The D6 header bullet still gives the old input rule:** "published, or if `time_source=seen` seen, within the
   window". The window bullet two lines below says `max(published, first seen_at)`. The header must state the new rule,
   or a P2c build could follow the wrong one.
2. **D5 still says "a merge of two clusters changes an id"**, but R6 now says clusters are never merged. Drop "or a
   merge".

**One genuinely new item, introduced by variant A. I raise it, as asked, for the owner.** It is not a safety issue.

Every Drive read goes through the verified cache. Only a file with a GitHub receipt counts, and bytes that differ from
the receipt are `DAMAGED` (`drive_cache.py:1-17`). The feed list is configuration the owner will *edit* (adding a feed),
and the design does not say how an edit is made:
- edited in place, the file fails the receipt check and every run stops;
- or the list needs a write-once versioned file (`feeds-v2`, a new receipt, the latest version chosen by name), or a
  reader outside the receipt rule.

It fails closed: no data loss, nothing published, no hard line touched. So my view is that it **does not block the
design**. Settle it in the P2a story with a test that adding a feed means a new version file. The orchestrator and the
owner decide whether it should instead go back to the owner now.

**Verdict at 06e3467: PASS on the design (strong evidence: each fold checked against the round-2 findings).** Three
items carry into the P2a/P2c story: the new item above and the two text corrections.
