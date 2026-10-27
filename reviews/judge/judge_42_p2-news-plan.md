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
