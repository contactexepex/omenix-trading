# NP6: tiered clustering and independent origins (PLAN)

PLAN for the orchestrator's check and one judge before any code. Lane 1 for the code that follows (it changes the write-once
cluster record, adds a new algorithm-version folder, and decides what counts as an independent origin). Plan:
[NP0](NP0-news-port-plan.md) section 2i, with the changes below. **This document builds nothing.** I read agentic's
`analytics/cluster_origins.py` (all 156 lines) and the constants file; I have not read `verification_status.py`, so the
verification status layer on top of the origin count is NOT planned here (see "Not in NP6").

## Two parts, built in this order
**NP6a, the grouper (clustering algorithm version `2`).** Same Jaccard title score, 36 h match window, 48 h run window and
non-chaining anchor rule as version 1. Three changes, each a strategy behind the existing `Matcher`:
1. **The entity bar-mover reads the company list, not a fixed list in code.** `cluster/entities.py` (22 hard-coded names) is replaced by
   `Tagger.tag(title, source=article.source)` (NP5a; the source is passed so an outlet suffix never tags, judge 92 F2) run on the title only; a
   symbol "tagged" means `primary` or `mentioned`: the bar is lowered when two titles tag a common symbol, raised when each tags only other
   symbols, else unchanged (same `ENTITY_STEP`, same rule as now: an entity alone merges nothing). One more reason to do it: the fixed
   list tags only 22 names, the owner's list is the F&O universe. Version 1 keeps its own list, so old files stay reproducible.
2. **Same source URL is one story, but only a URL that can identify a story (judge 96 B1).** The resolver's `accept` and
   `clean_https_link` take any https link, so a home page, a section page or a consent page could be recorded as an article's URL, and
   one such URL would merge every article in the window by identity. A URL counts as an identity only if it has a path of at least one
   non-empty segment beyond `/` or a query; a bare host, `/`, or a path of a single segment with no query and neither a hyphen nor a digit in it is refused (a section name such as `/markets` has neither; an article slug or id has one; reasoning only, a guess to be measured by the refused count) (counted in
   `url_joins_refused`, never joined). Two articles whose identity URL is the same after a fixed normalisation (lower-case host, no
   fragment, no `utm_*` and `fbclid` parameters, nothing else; the query stays because some sites identify a story by it) are one story,
   whatever their titles. **The URL is tried before the title, and one URL belongs to one cluster (the first that took it)** (judge 96 item 6). The URL comes from `ArticleViewer` (NP5b: the resolution file's URL for a Google News item, the article's own
   link for a publisher item; never a feed claim, judge 94 B1). **A URL match joins an article to a cluster that holds the same URL in ANY
   member, not only the anchor** (identity is transitive, so this cannot chain A~B~C the way a score would); a title match still compares
   with the anchor only. The 36 h window still applies (reasoning only: it is safe; a story re-published after 36 h with the same URL is
   split, and this will be counted).
3. **Cluster file format 2** in the new folder `news/clusters/2/`. Same hash ids and counts, plus `companies_version`, `resolutions_used`, `url_joins` and `url_joins_refused`. **`companies_version` is `0` only when no company list
   exists at all** (the bar is then never moved). **A list that exists but cannot be loaded or verified stops the run with a fixed code and
   writes nothing** (judge 96 B3): never a silent fallback to an unmoved bar, which would record a quietly different grouping.
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
- **A wire read from the title only (`Origin.via == title`, no page read) does not verify** (judge 96 item 7): a title attribution is a
  heuristic. Only `domain`, `provider` or `byline` evidence verifies, so `ArticleView` also carries `wire_via` (one more field filled from
  `Origin`; agentic counted a title as evidence, **mine to be stricter**).
- **Countable view:** tier listed (`primary`, `tier1`, `tier2`), not promotional, not opinion. **Verified group:** a countable view
  whose page was read (`access` in full, partial, paywalled) or whose wire has evidence other than the title (above). `independent_origins` = number of verified groups.
- **Flags** (ported names): `promotional_provider` (any promotional view), `single_source` (1 independent origin),
  `no_vetted_origin` (0), `origins_unverified` (countable origins that are not verified), `opinion`, `low_tier_only` (no listed
  tier at all), `unread` (no page of the cluster was read). Not ported: `sources_say` (needs agentic's attribution-verb patterns, not
  read) and `duplicates_removed` (omenix has no duplicate pass; a repeated key is already counted by the clustering).
- `Corroboration` also records the rule-file version and how many read files it used, so a count can be tied to the rules it came from.
- `ArticleView` gains `outlet` (the outlet key; one field, filled by `rules.outlet_key(host)`), so NP6b needs nothing else from NP5b.

## What the run reads and writes (NP6a)
It reads, as now, articles from the Record (read only) and, new, the resolution files of the window's Google News articles (read only,
through the verified cache) and the newest company list. It writes one cluster file per run at a new path (write-once, receipt, manifest
row, as today). **Determinism, stated as the guarantee it is (judge 96 B2):** the same articles, the same resolution set and the same company
list give the same bytes. A re-run of a closed window that sees a different input (a resolution or an article recorded since) is
refused by the write-once rule and reported, as version 1 already does for a late article. There is NO day cutoff on resolutions (a
resolution recorded later on the window-end day would still change the bytes on a re-run, so a cutoff adds code and solves nothing), and
NO time in the resolution file (it would break that file's same-bytes property). The file records `resolutions_used` (how many were read).
If exact re-runs are ever needed, a time column in the manifest row is a separate lane-1 story.

## Decisions I am making (the judge should overrule what is wrong)
- Tag with the title only for the bar-mover, not the summary: a summary tag is `mentioned`, and a bar moved by a passing mention would merge or split
  stories on noise.
- Origins stay out of the cluster file. Cost: anything that reads a cluster must also read its members and apply the rules itself (a consumer is another repository's job, see the scope rule); benefit: editing the
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
W1 the bar moves by tagged symbols only, an entity alone merges nothing; W2 same normalised URL joins any member, the URL is tried before the title and one URL belongs to one cluster; W2b a URL with no path or query, or one segment with neither a hyphen nor a digit, never joins and is counted; W2c the file counts URL joins whose title score with the anchor is below the match bar (`url_joins_unlike_title`), which is how a generic URL the rule accepts (`/stock-market`, `/news/business`) shows up; W3 a feed-claimed domain never
joins; W4 a title match still compares with the anchor only (no chaining by score); W5 version 2 writes only under `news/clusters/2/` and
never rewrites version 1; W6 `companies_version` is recorded, `0` only for no list at all, and an unloadable list stops the run with a code and writes nothing; W7 label order wire, then outlet; W8 a promotional or opinion or
unlisted view never counts; W9 verified means read or a wire with non-title evidence; W10 each flag fires exactly on its rule; W11 the corroboration is pure (same views,
same result, any order); W12 `parse_cluster_file` accepts formats 1 and 2 and refuses others with one code.

## Size and order
About 300 lines of production code in four small files (`cluster/url_identity.py`, `cluster/symbol_bar.py` (replaces `entities.py` for
version 2), `corroboration/origins.py`, `corroboration/flags.py`) plus wiring of the run and format 2. Two stories: NP6a then NP6b (NP6b needs
only NP5b; they can be built in parallel). Both lane 1, two judges for the code.

## Held for the owner or the orchestrator
- Whether version 2 replaces version 1 in the scheduled run, and when (NP7).
- The comparison of version 1 and version 2 merge rates on real data before cutover.

## Judge 96 round 1 (judge #2), all accepted after checking the code
B1 (reproduced by reading `clean_https_link`: no path rule), B2 (the day cutoff does not close the re-run case), B3, and items 4 to 7 are
edited in above. The 36 h window stays on URL joins (splitting is the fail-safe side). Origins stay out of the cluster file.

## Judge 96 round 2: PASS, with condition C1 for the NP6a code
The path rule is a guess and `url_joins_refused` counts only what it turns away. NP6a must add `url_joins_unlike_title` to the format-2 file
(W2c, with a plant), and the v1-against-v2 comparison before NP7 must report it.
