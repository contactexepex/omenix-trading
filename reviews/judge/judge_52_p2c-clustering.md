# Judge 52: P2c (news clustering, a pure module), judge #1, single judge

**SHA:** `bab61e31448fa766d6b63490af35407c1b5c11e6` (`story/P2c-clustering`). The new package is
`fno/ingestion/news/cluster/`, 8 files and 262 lines, each under 70.
**Verdict: FAIL, round 1 of 2, on one determinism hole.** Everything else holds under attack.

## Gates

- Suite: 806 passed, 2 runs out of 2.
- ruff and imports (457 files): clean.
- Size: 3 passed.

## What holds (strong evidence: plants and experiment)

| Item | Evidence |
|---|---|
| 1. Purity | The AST test walks every file in the package and forbids `requests`, `urllib`, `socket`, `subprocess`, `os`, `pathlib`, `logging`, `random` and `time` imports, and `open`, `now`, `today`, `read_text`, `write_text` and `print` calls. The code imports only `hashlib`, `re`, `datetime`, `dataclasses`, `abc` and `collections.abc` and the in-repo article and cluster modules. The only module-level state is constants. I found no hidden impurity. |
| 2. Privacy | The test runs the real `cluster_articles` and searches `repr` plus a JSON dump of the result for a marker headline, host, path, query, the outlet and the entity word: none appear. Output fields are keys, SHA-256 ids, counts and `as_of`. An exception can come only from `fromisoformat` on a time field, so the message carries a date, never text. A plant that builds the id from the title is caught. |
| 3. No chaining (N7) | A plant matching against any member instead of the anchor is caught. A plant letting an entity merge alone (bar 0) is caught (4 tests). |
| 4. Nothing hidden | A plant that drops new clusters is caught (4 tests). |
| 5. Order (partly) | A plant that skips the sort is caught. But see C1. |
| 6. The window equivalence | `effective_time = max(story_time, first_seen)` is never earlier than `first_seen`, so `effective <= as_of` implies `first_seen <= as_of` for every input. The removed check was unreachable; I accept its removal, and no dead code is left. A plant that windows on publication time only is caught. |
| 7. Lineage | A plant that empties `replaced_ids` is caught. |
| 8. Repeated key | A keep-last plant is caught. |
| 9. Thresholds | The "defaults, not findings… nothing derived from clusters may be trusted" warning is in `similarity.py`, `window.py` and `cluster.py`. The labelled result (5 true positives, 3 false negatives, 0 false positives) is pinned, and a plant changing the threshold to 0.5 is caught. **It is not fitted to the 16 pairs.** I computed every pair's score: the negatives all score 0.0 to 0.091, and the positives 0.286 to 1.0. Any bar from about 0.1 to 0.29 would give 8 of 8, so 0.55 was not tuned to them. |

Also caught: a plant that removes the match window.

## Required to PASS

### C1. Same key, same first-seen time, different content: the result depends on input order

Reproduced. Two articles share a key and `first_seen_at`, but their titles differ: two revisions seen in one poll, for
example the same URL listed twice with an updated headline. A third article matches only the second title.

- Order `[x1, x2, y]` gives `[(a,), (b,)]`.
- Order `[x2, x1, y]` gives `[(a, b)]`.

The cause: `cluster_articles` sorts by `(first_seen_at, key)`, which is a tie here. The stable sort keeps the input
order, and `setdefault` then keeps whichever came first. That breaks the module's own stated contract ("same inputs
give the same output in any input order") for exactly the repeated-key case it counts.

Fix: break the tie on content, for example `(first_seen_at, key, article.to_bytes())`. Add a test with my two-order
reproduction.

## For the owner (reasoning only, not a finding)

The invented negatives are all trivially far apart (≤ 0.091), so the pair set has no hard near-misses. One such pair,
`"Nifty closes at record high"` against `"Nifty closes at record low"`, scores 0.6 against the shared-entity bar of
0.45, and **merges**: two opposite stories become one, which over-counts corroboration.

This supports the warning already in the code. The real-data re-tune needs near-miss negatives like this one, not only
easy ones.

## Hard lines

A pure module: no I/O, nothing committed, no secrets.
