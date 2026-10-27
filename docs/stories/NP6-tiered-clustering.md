# NP6: tiered clustering and independent origins (PLAN)

PLAN for the orchestrator's check and one judge before any code. Lane 1 for the code that follows (it changes the write-once
cluster record, adds a new algorithm-version folder, and decides what the dashboard calls "corroborated"). Plan:
[NP0](NP0-news-port-plan.md) section 2i, with the changes below. **This document builds nothing.** I read agentic's
`analytics/cluster_origins.py` (all 156 lines) and the constants file; I have not read `verification_status.py`, so the
verification status layer on top of the origin count is NOT planned here (see "Not in NP6").

## Two parts, built in this order
**NP6a, the grouper (clustering algorithm version `2`).** Same Jaccard title score, 36 h match window, 48 h run window and
non-chaining anchor rule as version 1. Three changes, each a strategy behind the existing `Matcher`:
1. **The entity bar-mover reads the company list, not a fixed list in code.** `cluster/entities.py` (22 hard-coded names) is replaced by
   `Tagger` (NP5a) run on the title only: the bar is lowered when two titles tag a common symbol, raised when each tags only other
   symbols, else unchanged (same `ENTITY_STEP`, same rule as now: an entity alone merges nothing). One more reason to do it: the fixed
   list tags only 22 names, the owner's list is the F&O universe. Version 1 keeps its own list, so old files stay reproducible.
2. **Same source URL is one story.** Two articles whose effective URL is the same after a fixed normalisation (lower-case host, no
   fragment, no `utm_*` and `fbclid` parameters, nothing else; the query stays because some sites identify a story by it) are one story,
   whatever their titles. The URL comes from `ArticleViewer` (NP5b: the resolution file's URL for a Google News item, the article's own
   link for a publisher item; never a feed claim, judge 94 B1). **A URL match joins an article to a cluster that holds the same URL in ANY
   member, not only the anchor** (identity is transitive, so this cannot chain A~B~C the way a score would); a title match still compares
   with the anchor only. The 36 h window still applies (reasoning only: it is safe; a story re-published after 36 h with the same URL is
   split, and this will be counted).
3. **Cluster file format 2** in the new folder `news/clusters/2/`. Same hash ids and counts, plus `companies_version` (the number of the
   company list used; `0` when none was available, in which case the bar is never moved) and `url_joins` (how many articles joined by URL).
   Old `news/clusters/1/` files are untouched and still parse (`parse_cluster_file` accepts format 1 and 2).

**NP6b, the corroboration read-model (pure; nothing stored).** `corroborate(views, rules) -> Corroboration` over the `ArticleView`s
(NP5b) of one cluster's members. Computed when read, not written into the cluster file, because it depends on the rule files, the
resolutions and the read files, which all change after a cluster file is closed (NP0 section 3).
- **Origin label** of a view: `wire:<agency>` if it has one, else `outlet:<outlet key>` (the outlet key joins one outlet's hosts, `same_as`).
  Ported: agentic also has a `provider:` label from the JSON-LD provider; NP5b's `Origin` already puts a named provider that is an
  agency into `wire`, and a non-agency provider is not an origin in omenix, so there is no third label (**mine**).
- **Origin groups:** views with the same label are one origin. **Not ported in the first cut:** agentic's MinHash copy test that also
  joins different outlets carrying copied text (needs `datasketch`; judged in NP0 2i). Effect, reasoning only: two outlets that copy a
  non-agency story count as two origins, so `independent_origins` can be too high. The flag below says when it is unverified.
- **Countable view:** tier listed (`primary`, `tier_1`, `tier_2`), not promotional, not opinion. **Verified group:** a countable view
  whose page was read (`access` in full, partial, paywalled) or that has a wire. `independent_origins` = number of verified groups.
- **Flags** (ported names): `promotional_provider` (any promotional view), `single_source` (1 independent origin),
  `no_vetted_origin` (0), `origins_unverified` (countable origins that are not verified), `opinion`, `low_tier_only` (no listed
  tier at all), `unread` (no page of the cluster was read). Not ported: `sources_say` (needs agentic's attribution-verb patterns, not
  read) and `duplicates_removed` (omenix has no duplicate pass; a repeated key is already counted by the clustering).
- `ArticleView` gains `outlet` (the outlet key; one field, filled by `rules.outlet_key(host)`), so NP6b needs nothing else from NP5b.

## What the run reads and writes (NP6a)
It reads, as now, articles from the Record (read only) and, new, the resolution files of the window's Google News articles (read only,
through the verified cache) and the newest company list. It writes one cluster file per run at a new path (write-once, receipt, manifest
row, as today). **Determinism:** the same articles, resolutions and company list give the same bytes; a resolution that appears after a
file was written changes only a LATER file (hourly runs), never the closed one. Re-running an old window later may therefore give other
bytes at the same path, which the write-once rule refuses and reports (the same as a new article does today for `first seen <= end`;
reasoning only: to avoid it, the run reads only resolutions recorded on or before the window end, and I propose that: a resolution file
has no timestamp of its own, so this uses its manifest row's day, which is coarser than the window end; the judge should decide whether a
day-level rule is acceptable or the resolution file must carry its time (a format change to NP2c)).

## Decisions I am making (the judge should overrule what is wrong)
- Tag with the title only for the bar-mover, not the summary: a summary tag is `mentioned`, and a bar moved by a passing mention would merge or split
  stories on noise.
- Origins stay out of the cluster file. Cost: a dashboard that reads a cluster must also read its members' views; benefit: editing the
  allowlist never leaves a stale count in the write-once record.
- Version `2` runs in a new folder beside version 1, nothing deleted or rewritten. The workflow stays dispatch-only until NP7 (cutover).

## Said plainly
- **The threshold (0.5 Jaccard, ENTITY_STEP) and the windows are still defaults, not findings.** NP6 changes what moves the bar, so
  version 2's merge rate must be measured on real polls against version 1 before anything is built on it (the orchestrator's NP3c-like
  measurement; counts only, no titles). Agentic's 2.8% corroboration rate (35 of 1,237 clusters) is for 20 companies; omenix's rate is unmeasured.
- Two outlets carrying one non-agency story count as two origins (no copy test). Measured later with counts; a `datasketch`-free copy test
  (shared long title shingles, or a shared read-file `text_hash`) is a possible later strategy behind the same interface, not planned.
- No test reads a real title; companies and outlets in tests are invented.

## Contract rows planned (docs/RECORD_CONTRACT.md, new section "Tiered clustering (NP6)", each with a plant)
W1 the bar moves by tagged symbols only, an entity alone merges nothing; W2 same normalised URL joins any member; W3 a feed-claimed domain never
joins; W4 a title match still compares with the anchor only (no chaining by score); W5 version 2 writes only under `news/clusters/2/` and
never rewrites version 1; W6 `companies_version` is recorded and `0` moves no bar; W7 label order wire, then outlet; W8 a promotional or opinion or
unlisted view never counts; W9 verified means read or wire; W10 each flag fires exactly on its rule; W11 the corroboration is pure (same views,
same result, any order); W12 `parse_cluster_file` accepts formats 1 and 2 and refuses others with one code.

## Size and order
About 300 lines of production code in four small files (`cluster/url_identity.py`, `cluster/symbol_bar.py` (replaces `entities.py` for
version 2), `corroboration/origins.py`, `corroboration/flags.py`) plus wiring of the run and format 2. Two stories: NP6a then NP6b (NP6b needs
only NP5b; they can be built in parallel). Both lane 1, two judges for the code.

## Held for the owner or the orchestrator
- Whether version 2 replaces version 1 in the scheduled run, and when (NP7).
- The comparison of version 1 and version 2 merge rates on real data before cutover.
