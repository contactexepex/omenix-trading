# NP3c: compare clustering version 1 with version 2 (the measurement before the cutover)

Lane 1, two judges (a new workflow that reads the Drive and the owner's private company list). Plan: the NP3c paragraph of
[NP7](NP7-company-list-safeguard-and-cutover.md). Contract rows J1 to J7. **Read only: it writes nothing to the Drive or the manifests,
commits nothing, sends no alert, and prints counts only.** Dispatch-only workflow; nothing runs until the owner dispatches it.

## What it is
`python -m fno news compare-clusterings [--as-of ISO]` (workflow `news-compare-clusterings.yml`, `contents: read`, no schedule, no Slack token)
reads the recent articles of the Record, clusters them with algorithm version 1 and with version 2 in memory (version 2 through
`SymbolGrouping`: the company list and the resolution files, read only), and prints five lines:
1. `v1:` and `v2:` (clustered articles, clusters, singletons, the largest cluster, clusters per size bucket 2, 3 to 5, 6 to 10, 11 or more);
2. `v1 vs v2:` the number of version 2 clusters that merge several version 1 clusters, and of version 1 clusters that version 2 splits;
3. `v2 inputs:` `url_joins`, `url_joins_refused`, **`url_joins_unlike_title`** (the early warning that a generic URL is merging unlike stories,
   judge 96 C1), `companies_version`, `resolutions_used`;
4. `tags:` how many articles name a company, how many with high confidence, and how many companies reach 1, 5 and 20 tagged articles (no
   symbols, no names).
A company list that exists but cannot be read stops it with its code (red, exit 1); no list at all compares with `companies_version 0`.
The company-list pin of NP7b is not applied here: nothing is written, so nothing needs protecting.

## How to read the result (reasoning only until real numbers exist)
- Many `v2_clusters_merging_v1_clusters` with a high `url_joins_unlike_title` means the URL rule is letting generic links through: tighten it.
- Many merges with a low `url_joins_unlike_title` and `companies_version` above 0 means the company-driven bar is doing it; read a few by hand
  (the owner can: the command prints no titles by design) before trusting it.
- `companies_version 0` or `tagged 0` means no list was read; the comparison then says nothing about version 2's bar.
- No threshold here is a finding. There is no ground truth: the counts show how the two algorithms differ, not which is right.

## What it does NOT measure (said plainly)
- **The recall of broad feeds against targeted queries (the question NP3b left open) cannot be measured from the Record.** The article file
  deliberately holds no feed id (the feeds are private), so which query found an article is not recorded. Measuring it needs the feed id of
  a hit to be kept somewhere, which is a Record format decision for the owner, not a change made here.
- Whether a merge is right or wrong. Only a human reading real pairs can say.
- Run time and Drive load of the first dispatch are unmeasured; the command reads every article file of the window and one resolution file
  per Google News item.
