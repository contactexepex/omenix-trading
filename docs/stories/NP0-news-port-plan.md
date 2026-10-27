# NP0: port the mature news intelligence of agentic-stock-prediction into omenix's news pipeline (PLAN)

PLAN for the orchestrator's check before any code (owner decision relayed by the orchestrator, 27 Oct 2026). Nothing here is built.
**Round 2** (after Judge 70's FAIL of `0e9401a`, findings N1, N2, N3, the unreproducible cluster numbers and the pacing wording): every
change is listed in section 8, each with what I checked.
Each story it proposes is lane 1 with two judges (it fetches from outside services, writes the Record, touches the privacy rule).
This plan is itself a functional document, so it takes lane 1 too (CLAUDE.md "Functional documents are reviewed like code").
Context and the pipeline being extended: [P2-news-dedup.md](P2-news-dedup.md), [P2b](P2b-article-gate.md), [P2c](P2c-clustering.md),
[P2d](P2d-cluster-record.md), [PIPELINE_DESIGN.md](../PIPELINE_DESIGN.md) "News: dedup and credibility".

**Evidence labels** (CLAUDE.md): *strong* = I read the code or counted real rows; *some* = a single sample or a partial read;
*reasoning only* = my inference, not checked.

## 0. What I read, and what I measured

Reference repo `contactexepex/agentic-stock-prediction` at commit `f1b9bb6` (public, cloned read-only, treated as untrusted data):
`config/news_sources.yaml` (227 lines, 112 domains: 12 primary, 23 tier1, 77 tier2; 11 marked `fetch: false`), `config/markets/india.yaml` (229), `routine/NEWS_PROMPT.md`, `scripts/marketbrief/constants/{news,
articles,article_collection,news_clusters}.py`, `collectors/{news,news_fetch,news_links,news_wire,articles,article_candidates,
article_rows}.py`, `sources/{google_news_decoder,article_fetch}.py`, `analytics/{article_pages,article_extraction,news_sources,news_tags,
news_dedup,news_clusters,cluster_items,cluster_origins}.py`, `requirements.txt`. Omenix: all of `fno/ingestion/news/` (2,025 lines) and its
story documents.

Real numbers from agentic's own India data, 5-27 Oct 2026 (strong evidence; recounted independently by Judge 70 on the same data).
**Counting method:** files under `data/india/{news,news_articles,news_clusters}`. Rates are per day that has a file (17 news days, 16
article days, 16 cluster days; not per calendar day). A cluster is rewritten whenever it changes, so its state is its row with the
**latest `as_of` per `cluster_id`**; by its first-seen state the figures differ (21 clusters, not 35, have two or more independent
origins), so every cluster figure below says which. These figures describe agentic's algorithm on agentic's 20 companies; omenix's
own rates are measured in NP6.

| Measure | Value | What it tells us |
|---|---|---|
| news rows | 25,433 (about 1,500 a day), 21,793 from Google News (about 1,280 a day) | every Google row stores `news.google.com/rss/articles/...`: the real publisher URL is **not** in the row (this is the blank-source-URL gap) |
| article reads (material headline of one watchlist company) | 1,533 (about 96 a day) | reading only the material headlines is a small load; decoding **every** Google headline would be about 1,280 a day (see 2b) |
| access outcome | skipped_unlisted 793 (52%), full 502, blocked 125, paywalled 82, partial 17, undecoded 14 | decoding works (under 1% failed); **half of the material headlines come from outlets not on the allowlist** |
| extractor that produced the text | jsonld 422, trafilatura 92, description (paywalled) 82, newspaper 4 | `newspaper4k` won 4 of about 600 reads: not worth its weight (see 2e) |
| distinct clusters / with 2 or more independent origins (latest state) | 1,237 / 35 (2.8%); by first-seen state 21 (1.7%) | corroboration is rare **in agentic's data**; omenix's rate is unmeasured until NP6 |
| cluster flags (latest state) | unread 762, no_vetted_origin 760, low_tier_only 587, single_source 442, promotional_provider 233 | most clusters have no vetted origin: the per-article label (outlet, tier, real URL) is likely worth more than the count (reasoning only) |

## 1. Gap map: agentic vs omenix P2

| Capability | agentic | omenix P2 today | Plan |
|---|---|---|---|
| Fetch headlines (RSS) | Google News queries from the watchlist + 6 outlet feeds, catch-up window, polite stop on 429/503/captcha | `NewsFetcher`: each private feed once, raw bytes to Staging, one block stops the host; host cooling-off | **REUSE** the fetcher. NEW: queries generated from the watchlist (NP3) |
| Parse / article identity | id = normalised title + source domain; link/title dedup in a 9-day window | `parse_feed`, `Article`, key = SHA-256 of canonical URL (publisher) or guid/time/title (wrapper) | **REUSE** omenix's key. Do not port `news_dedup.py` (a second dedup) |
| Real publisher URL | `googlenewsdecoder`, one GET per link + one POST per batch of 10, requests refused unless HTTPS to google.com | **none**: `canonical_url` is "" for a Google News item (P2 ruling: "Google News links are not resolved") | **NEW** (NP2). Reverses that ruling; the orchestrator asked for it |
| Outlet allowlist, tiers, names | 112 domains, tiers primary/tier1/tier2, label names, `fetch:false`, `same_as`, `https_links`, `opinion_unless_path` | none | **NEW** (NP1) |
| Fetch the article page | allowlisted HTTPS only, hand-followed redirects (every hop checked), 4 MB cap, 1.5 s pause, 20 s timeout | none | **NEW** (NP4) |
| Extract | JSON-LD, then trafilatura, then newspaper4k; paywall = description only | none | **NEW**, JSON-LD + trafilatura only (NP4) |
| Wire-agency origin | byline/provider/dateline/attribution patterns for 8 agencies | none | **NEW** (NP5) |
| Promotional exclusion | provider/domain/text lists | none | **NEW** (NP5) |
| Material terms, company tagging | weighted title regexes; names/aliases/exclusions per company; headline first | `cluster/entities.py`: a fixed list of 22 names, only moves the similarity bar | **NEW** (NP5); **REPLACES** `entities.py` |
| Clustering | title tokens (Jaccard), 72 h window, MinHash copy test, per-ticker | `cluster/*`: title shingles, entity bar-mover, 72 h window, write-once cluster file with hash ids | **REUSE** omenix's clustering; **NEW** origin counting on top (NP6) |
| Corroboration | `independent_origins` over tiered origin groups, flags | none | **NEW** (NP6) |
| Storage | append-only JSONL in git (titles and URLs public), DuckDB views | write-once files in the private Drive, hash-only receipts in git | **keep omenix's**; nothing from the DuckDB side is ported |
| LLM news analyst, claim checker, Neo4j, MotherDuck, validate gate | yes | no | **OUT OF SCOPE**: research consumers, not ingestion |

**Duplication to remove (we keep one pipeline).** (1) `cluster/entities.py` (hard-coded names) is replaced by the watchlist-driven
tagger. (2) Nothing is removed from the wrapper item's identity: **its key (guid, else time + title + summary + source) never changes and
never depends on whether the link was resolved** (N2); the resolved URL lives in a separate file, never in the key (section 3). (3) Nothing of
agentic's `news_dedup.py` is ported; its one good idea, treating `www.`/`m.`/`amp.` hosts and `same_as` domains as one outlet, goes into
the allowlist lookup (NP1). (4) After the cutover (NP7) agentic's own collectors stop; until then both run and omenix is the one that is
write-once. Not ported at all: pandas/DuckDB, the enrichment prompt, the claim phase, Neo4j, the warehouse sync.

## 2. Mapping onto omenix's architecture

Everything new sits behind an interface with one adapter and one line in a composition root (CLAUDE.md "Design for change"). Files stay
at or under 350 lines; the news code stays in `fno/ingestion/news/` in new sub-packages (`sources/`, `resolve/`, `pages/`, `origin/`).

**(a) Discovery from the watchlist and material terms.** A private, versioned, write-once `news/queries-vN.json` in the Drive config
area (the same discipline as `feeds-vN.json`: newest wins, no roll-back, edited-in-place versions skipped, errors are fixed codes). It
holds the companies (name, aliases, exclusion regexes) and the query template; `QueryPlan` expands it to Google News feed URLs at fetch
time and hands `NewsFetcher` ordinary `FeedEntry` objects, so the fetcher, staging, poll log and cooling-off are unchanged. **Constraint
found:** `feeds.py` allows at most `MAX_FEEDS = 50` feeds with ids `feed-NN`/`feed-NNN`; a watchlist of 20 companies fits, the F&O universe
(about 200 underlyings) does not. The query plan therefore does not go through `feeds-vN.json`; it has its own cap (decision 1).
Material terms are **not** used to build queries (agentic does not either: it queries by company name and filters by terms afterwards);
they decide which articles are *read* (NP4/NP5). Google News pacing: at least 1.5 s between two `news.google.com` requests, enforced by
that host's entry in the host pacer (the news fetcher has its own `NEWS_PACER` instance, `news/session.py`, reading the same
`HOST_SPACING_SECONDS` table). Outlet-feed requests keep today's 1.0 s default and are **never** loosened to agentic's 0.5 s. Agentic's polite stop (429, the `/sorry/` page, HTML
instead of RSS) already maps onto `response_check` (403/429 = refused, a non-feed answer = block_page, a host stop) plus `SourceCoolingOff`
(strong evidence: I read the codes); a 503 is not named there and NP3 checks it. The Google 1.5 s spacing is one new entry in
`HOST_SPACING_SECONDS` (`fno/shared/nse_pacer.py`, today only the two NSE hosts); a spacing **across hosts** (section 2d) is not a table
entry but new code, because the pacer is per host.

**(b) Resolving the real publisher URL.** Interface `LinkResolver.resolve(wrapper_link) -> Resolved(url | None, code)`. Adapter
`GoogleNewsDecoderResolver`. Hard rules, all pinned by tests: every request, redirects included, must be HTTPS to `google.com` or a
subdomain (agentic's `google_only` request hook, ported); batch of 10 (one GET per link, one POST per batch); 1.5 s pacing; at most 80 per run;
a failure is a fixed code, never the link; the result is accepted only if it is `https`, has a host, no credentials and no port, and
passes `canonical_url`. **The article's identity does not depend on it (N2).** The wrapper key is untouched (`keys.py`: guid, else time + title + summary +
source). The resolved URL is never part of any key and never changes an article file.
**Where it runs and how a failed item is retried (N3).** One mechanism, a **resolve pass** (NP2c) over the Record, not over Staging:
it reads the articles manifest of the last 3 days (as the cluster source does), reads each wrapper article's file (read only), skips
those that already have a resolution file, resolves the rest newest first (priority by NP5 once it exists) up to the run's cap, and
writes each success as a write-once **resolution file** `news/resolved/<key[:2]>/<key>.json` (resolved URL, its host, resolver
version, whether the host agrees with the feed's claimed `source_domain`) with receipt and manifest row (reusing `NewsManifest`'s
`file_name`, as the cluster record did). A failure writes nothing and is counted; the item is tried again on the next pass until it is
3 days old, then counted as `expired` and left unresolved. What this needs from the Record: the wrapper link itself, so **format 2
stores `wrapper_link`** (the Google redirect link, kind wrapper only, private Drive; excluded from the version comparison so a changed
redirect token never makes a revision). Because the pass reads only the Record, the staging cleanup (S1) trashing a promoted poll after
7 days loses nothing the pass needs (explicit interaction), and the gate's `--from` range does not matter.
**Why a separate file and not a revision** (Judge 70 suggested revisions as an example; this is my variant, for the judges to overrule):
a re-polled item is rebuilt from the feed as "unresolved", so with a resolved URL inside the article file every re-poll would differ
from the held file and be recorded as a false revision unless the planner learned an asymmetric "facts only improve" rule; a separate
write-once file needs no change to the planner and cannot churn. The dashboard reads the article file plus its resolution file (NP7's
read contract); the effective source URL is the resolution's if present, else the publisher link, else none.
**Volume against the cap (strong evidence for the inputs, reasoning for the sum).** Google headlines are about 1,280 a day (section 0).
Resolving all of them is about 1,280 GETs plus 128 POSTs, about 1,400 requests, which at 1.5 s apart is about 35 minutes a day of paced
calls: about 53 items (80 seconds) per hourly pass, inside a cap of 80 a pass (1,920 a day). Scheduled runs here start hours late, so a
pass may carry a backlog; the 3-day look-back absorbs it. If the owner prefers fewer requests, resolve only watchlist-tagged material
headlines (about 96 a day in agentic's data) once NP5 exists: a one-line selection change (decision 8).
**Honest risk (some evidence):** `googlenewsdecoder` drives an unofficial Google endpoint; it can break without notice, and it pulls
`httpx[http2]` and `selectolax` (supply chain). Agentic's 14 failures in 1,533 reads show it works today. NP2b starts with a read-only
probe from a GitHub runner, and the interface lets us swap in our own small `requests` implementation if the library is a problem
(decision 3).

**(c) Allowlist and tiers.** A file `config/news_sources.yaml` (outlet domains, tiers, wire names, promotional lists: generic public
knowledge, reviewable by git; **public in the repository or private in the Drive is the owner's decision H**, section 7, and until it is
answered nothing is merged) loaded by `SourceRules` (`fno/ingestion/news/sources/rules.py`). Lookup is by host and
its parent domains (`m.economictimes.com` finds `economictimes.com`, then its `same_as`). A host not listed is `unlisted`: never fetched,
never counted. The **companies and queries are not in this file**: they stay private (decision 1; the repository is public).

**(d) Fetching article pages (allowlisted only).** `ArticlePageFetcher` behind `PageFetcher`: HTTPS only, TLS verification always on, host on
the allowlist at **every redirect hop** (redirects followed by hand), `fetch: false` outlets never requested (their headline still gets
its tier from the decoded host), 4 MB cap, 20 s timeout, one polite User-Agent, at least 1.5 s between page fetches across all hosts (**new code**: the shared pacer spaces requests per host only), at most 80 pages and
900 s per run. Only the Staging/Record stages call it; it is never reachable from a fetch of a feed.
**Re-test needed:** agentic's `fetch: false` list was measured from its own cloud environment on 6 Oct. GitHub Actions runners have other
IP ranges; NP4 re-probes the 112 listed domains once (read-only, one request per outlet) and the result goes to the owner before any outlet is
marked fetchable.

**(e) Extractors.** `Extractor` strategy: `JsonLdExtractor`, `TrafilaturaExtractor`; per-outlet order from the allowlist. **`newspaper4k`
is dropped** (it won 4 of about 600 reads, strong evidence, and it is the heaviest dependency). A page whose JSON-LD says
`isAccessibleForFree=false` is paywalled: only the description and OpenGraph text are read. Page text is untrusted: it is parsed, measured
and discarded, never executed, never followed as an instruction.

**(f) Wire-agency dedup.** `OriginReader` (pure): an item whose byline, JSON-LD provider, dateline, title or lede attribution names one of
the 8 agencies is a copy of that agency's story: one origin however many outlets carry it. Ported with its tests and the 3-sentence lede
rule.

**(g) Promotional exclusion.** `PromotionalFilter` (pure): provider/byline/source label, domain, or marker phrase; flagged `promotional`
and never an independent origin.

**(h) Material terms.** `MaterialTerms` (pure): weighted title regexes; only an item whose weight is at least 1 and whose title names
exactly one watchlist company (high tag confidence) is read (agentic's selection). Every headline is still recorded; reading is the
filtered step.

**(i) Tiered clustering.** Omenix's title-similarity clustering stays the grouper. NP6 adds, per cluster, the independent origins
counted over origin groups (agency, outlet, tier, promotional/opinion excluded) and the flags (`single_source`, `low_tier_only`,
`no_vetted_origin`, `promotional_provider`). A new matcher rule joins two articles with the same canonical **source URL** (a wrapper copy
and its publisher copy are then one story by identity, not by title luck). The copy test by MinHash is **not** ported in the first cut
(it needs `datasketch`; reasoning only: title and URL joins plus wire detection cover most of it, to be measured in NP6).

## 3. The Record shape for the dashboard

Article file `format: 2` (deterministic JSON, sorted keys, as now). It adds only **facts the feed gave**: `source_domain` (the host of
Google's own `<source url>` element for a Google News item, or the host of a publisher item's https link; "" when none) and, for a
Google News item only, `wrapper_link`. **It does not hold a tier, a wire, a promotional flag, tickers or a priority** (I wrote them into
the first draft of this plan; that was wrong): each depends on a rule file, so editing the allowlist or the watchlist would change the
compared fields of every re-seen article and record a mass of false revisions in the write-once Record. Those judgements are computed
when the article is read (NP5/NP6). The article file also never holds the resolved URL (2b); a publisher item's own https link is its
existing `canonical_url`. Two further write-once files per article, both outside the article file: the **resolution file** (2b) and, for an article page read
under NP4, a **read file** per article read
(`news/reads/<key[:2]>/<key>.json`): final URL, access outcome, extractor, character count, dates, byline, provider, at most 3
key sentences of at most 40 words each (agentic's `extract`), normalised numbers and a content hash. **No article body is stored, ever;
no HTML.** The key sentences are the one place article-derived text appears (a short extract, as agentic stores today); decision 4 asks
the owner whether to keep them.

**The summary the dashboard shows** is the feed's own description, cut to 280 characters at a sentence or word boundary, with HTML removed
(Google News descriptions typically are an HTML snippet that repeats the headline and the outlet name, some evidence; they are
cleaned and, if they only repeat the title, left empty). **The source URL is mandatory and spoof-resistant** in this sense: the effective URL comes only from (1) the resolution file, written
by the resolver after the checks in 2b (https, plain host, no credentials, no port, and Google-only egress), or (2) a publisher item's
own https link; the feed text, the `<source>` label and anything inside a page can never set it. The **tier** is computed on read from
the host of that URL through the allowlist, never from a label alone; an item with no resolution file has tier `unlisted` and is not
counted as an origin until it is resolved (stricter than agentic, which falls back to the label; this lowers the counts a little:
decision 5). The feed's claimed `source_domain` is only a hint and a cross-check: a resolved host that disagrees with it is recorded
as a disagreement in the resolution file, never trusted over the resolver.

**Two migration traps (strong evidence from the code, both reproduced by NP2a's tests).** (1) `planner.UNCOMPARED = ("first_seen_at",
"format")`; if `format: 2` adds fields to the compared set, every existing `format: 1` article differs from its format 2 twin and is
written again as a "revision". NP2a therefore compares two files on the **fields they share**, and leaves `wrapper_link` out of the
comparison. (2) `cluster_record/article_source.py` raised on any format other than the current one, so bumping the format would make every
format 1 article "unreadable" and the cluster run would write nothing; NP2a reads formats 1 and 2 through one shared definition.
Existing articles are not rewritten and not back-filled.

**Privacy.** Title, summary and URLs stay in the private Drive, as today. The repository gets only SHA-256 receipts and counts. Run
summaries and Slack lines carry counts only: **no domain names**, so the public repo does not show what the owner reads (agentic's
`unvetted_domains` list goes to a private Drive review file instead). The record scan does not block domain names, so each story that
prints a summary adds a **marker test** that its summary lines contain no host name (Judge 70's point). **The outlet allowlist is a
separate question (decision H, section 7):** the watchlist and the queries are always private (they show what the owner reads); the
list of 112 reputable outlets is generic, and the same list is already public in the owner's agentic repository, so publishing it
here adds little exposure, but whether it lives in the repo or in the private Drive (like `feeds-vN.json`) is the owner's call.

## 4. The watchlist

Agentic's watchlist is `company_meta` in `config/markets/india.yaml` (20 NSE companies, two per sector; name, aliases, `news_exclude`
regexes, ADR) plus add/remove events in `data/india/watchlist_events/` (read by `scripts/company.py` and its lifecycle loader). Queries
are `"<name>" share`, plus 20 general category queries (RBI, FII/DII, crude, rupee, USFDA, monsoon ...) and 6 outlet RSS feeds.
For omenix this is **an owner input I cannot guess**: omenix is an F&O tool, so the natural watchlist is a chosen subset of the F&O
underlyings (the NSE F&O master is already archived in Drive and gives symbols but not company names, aliases or exclusion phrases, which
are what makes tagging safe: "Mahindra" needs 7 exclusion patterns in agentic's file). Plan: a private `news/watchlist-vN.json` in Drive, seeded
from agentic's 20 as a starting point *if the owner confirms them*, extended by the owner. Decision 1.

## 5. Rules that carry over unchanged

| Rule | Where it lives in agentic | In omenix |
|---|---|---|
| Free, non-commercial, personal research, low volume | `news_sources.yaml` header, User-Agent | same text in the User-Agent; no paid source |
| HTTPS only, TLS verification always on | `article_pages.url_check`, `news_links.secure_link` | `https_links: true` upgrade only for listed hosts; nothing fetched over http |
| No full article text stored | `articles.py` docstring | enforced by a size cap in the read-file writer and a plant |
| Respect bot protection (`fetch: false`); never evade | allowlist `fetch` flag | same flag; a 401/403/challenge is recorded and the outlet is not retried that run |
| Pacing: at least 1.5 s between news.google.com requests | `news_fetch.py`, `pause_seconds` | host pacer entry (Google 1.5 s); outlet feeds keep today's 1.0 s (never loosened to agentic's 0.5 s); page fetches at least 1.5 s apart across hosts is new code |
| Allowlist-only fetching, every redirect hop checked | `fetch_page` | same; a hop to an unlisted host stops the read |
| Untrusted content: never execute or follow anything from a page or feed | `articles.py` | no `eval`, no template, no shell; parsers are the standard library, `lxml` (no network, no DTD) and trafilatura |
| Google News polite stop (429/503, `/sorry/`, HTML instead of RSS) | `GOOGLE_STOP_*` | `response_check` codes + `SourceCoolingOff`; 503 to be added if missing |
| Opinion is never an origin (`opinion_unless_path`) | allowlist | same |

Omenix's own hard lines also apply: no orders, no secrets in files, the public-record scan, write-once Record, no Groww (none is used here).

## 6. Stories (each small, lane 1, two judges unless stated)

| # | Story | Contents | New dependency | Lines (est., reasoning only) |
|---|---|---|---|---|
| NP1 | Source rules | `config/news_sources.yaml` (ported, secrets-free), `SourceRules` lookup (host, parents, `same_as`, tiers, `fetch`, wires, promotional, opinion), contract rows, plants | none (PyYAML is there) | ~350 code + 120 yaml + tests |
| NP2a | Article format 2 | `RawItem` reads Google's `<source url=...>` attribute (the outlet's host, no request), `Article` format 2 adds `source_domain` and (Google items) `wrapper_link`; formats 1 and 2 read through one definition; versions compared on shared fields, `wrapper_link` uncompared; the wrapper key is untouched | none | ~200 |
| NP2b | Link resolver | `LinkResolver` interface, Google-only egress guard, pacing 1.5 s, accept rules (https, plain host, no credentials, no port), read-only probe from a runner first | `googlenewsdecoder` (+`httpx[http2]`, `selectolax`) or our own adapter (decision 3) | ~300 |
| NP2c | Resolve pass | `news/resolved/` write-once resolution files with receipt and manifest, the pass over the last 3 days of the Record (newest first, cap 80, `expired` count), own `workflow_dispatch` workflow in the `news-record` concurrency group, S1 interaction pinned by a test | none | ~350 |
| NP3 | Discovery | private `queries-vN` + `watchlist-vN`, `QueryPlan` to `FeedEntry`, cap, tests | none | ~300 |
| NP4 | Page reads | `PageFetcher`, redirects by hand, `Extractor` strategies, read file, no-full-text cap, outlet re-probe | `lxml`, `trafilatura` (+ its transitive set, hash-locked, SEC1) | ~600, split in two if the judges want |
| NP5 | Origin filters | `OriginReader` (wires), `PromotionalFilter`, `MaterialTerms`, `Tagger` (replaces `entities.py`) | none | ~450 |
| NP6 | Tiered clustering | origin groups, `independent_origins`, flags, same-source-URL matcher rule, cluster file format 2 (new algorithm version folder, old files untouched) | none | ~300 |
| NP7 | Cutover | the read contract the dashboard uses; retire omenix's old pieces; plan for agentic to read omenix instead of collecting | none | docs + small code; owner decision |

Order and dependencies: NP1 then NP2a then NP2b then NP2c (these four deliver the owner's dashboard requirement: title, short summary,
real source URL); NP3 any time after NP1; NP4 and NP5 after NP1 and NP2b; NP6 after NP5; NP7 last. Each story ships with its contract
rows (`docs/RECORD_CONTRACT.md`) and mutation plants (`tools/contract_plants.py`), runs only as `workflow_dispatch` until the owner's
go-live, and is merged only after two judge PASSes **and** after this plan has passed and any open owner decision it depends on is
answered (NP1 waits for decision H; NP2b and NP2c wait for decisions 2 and 3; NP3 waits for decision 1).

## 7. Effort, risks, and what the owner must decide

**Effort (reasoning only).** One story is roughly one focused implementer session plus two judge rounds; NP2b, NP4 and NP6 are the heavy
ones. Total about 8 stories, 12 to 18 sessions of work in all with judge rounds, i.e. several days of wall-clock, not hours. The
dashboard requirement alone (NP1 + NP2a + NP2b) is about a third of it.

**Risks, said plainly.**
1. The decoder is an unofficial endpoint (some evidence it works today: 14 failures in 1,533). If it breaks, new articles are recorded
   as unresolved (no resolution file, tier `unlisted`), never lost, and the resolve pass (NP2c) fills them in when it works again.
2. Half of material headlines come from outlets outside the allowlist (strong evidence, 793 of 1,533). They get a real URL but tier
   `unlisted`. Whether the dashboard shows them, hides them or flags them is a product call.
3. Corroboration looks rare in agentic's data (35 of 1,237 clusters by latest state, 21 by first-seen state), but that is agentic's
   algorithm on 20 companies; omenix's rate is unmeasured. NP6 is therefore the story I would build last and tune on omenix's own runs.
4. The query count: one Google News request per company per run at 1.5 s apart; 20 companies take 30 s, 200 take 5 minutes (fits).
5. Scheduled GitHub runs arrive hours late (observed today); catch-up windows and idempotent steps matter more than exact timing.
6. New dependencies (`lxml`, `trafilatura` and what it pulls in, `googlenewsdecoder`) widen the supply-chain surface; all must go through
   `requirements.lock` hashes (SEC1) and `tests/test_pinned_installs.py`.

**Owner decisions needed (nothing starts without them):**
1. **Watchlist:** which companies (agentic's 20, a chosen F&O subset, or the whole F&O universe), their aliases and exclusions, and the
   confirmation that they live in the private Drive, not in this public repository.
2. **Terms for fetching publishers' pages and for Google News:** whether owner rule 50a79a43 (source terms do not block private research;
   values stay in Drive; recorded in P2 as open question N12) covers *fetching article pages* and *resolving Google News links*.
3. **Decoder:** accept the unofficial library, or have us write the small adapter ourselves (same endpoint, our maintenance).
4. **Short extracts:** keep up to 3 key sentences of at most 40 words per read (as agentic does), or store no article-derived text at all
   (title, feed snippet, URL, tier only).
5. **Strictness:** an undecoded item is not an origin (stricter than agentic); accept the lower counts?
6. **Allowlist breadth and the outlet re-probe** from GitHub runners (NP4) and whether `unlisted` items are shown.
H. **The allowlist file: public in this repository or private in the Drive?** The watchlist and queries are always private. The 112-outlet
   list is generic and already public in the owner's agentic repository (so the added exposure is small), but it is still a list of
   what the owner's system trusts. Public = reviewable by git and read without Drive credentials; private = same discipline as
   `feeds-vN.json`, loaded from the Drive config area. NP1 builds either way (the loader takes a path now and would take bytes from
   Drive); nothing is merged until the owner answers.
7. **Retire agentic's own collection:** now (after NP2b), after a dual-run period, or never. Agentic reads its own JSONL in git today, so
   the cutover needs a defined read path (an export or a `data-cache` read of the omenix Record); that contract is NP7's first deliverable.

8. **Resolve every Google headline or only the material ones?** About 1,400 paced requests a day for all (35 minutes of Google calls), or
   about 96 reads a day for watchlist-tagged material items only. Default in this plan: all, newest first, cap 80 a pass.

Nothing in this plan places an order, touches Groww, or stores a secret.

## 8. Round 2: what Judge 70 found and what I did (each checked against the code or the data)

| Finding | Verdict | Change |
|---|---|---|
| Cluster numbers 32 / 766 / 768 / 595 / 439 / 223 not reproducible; day counts mixed | **Accepted, reproduced.** My file-order count was wrong; by latest `as_of` per cluster the figures are 35 / 760 / 762 / 587 / 442 / 233, by first-seen 21. News files cover 17 days, article and cluster files 16 | section 0 states the method and says which state each figure is; rates per day with a file (1,500; 1,280; 96, not 67) |
| N1: a public tiered allowlist contradicts "the repo must not show what the owner reads" | **Partly accepted.** Judge 70 later rated it an owner decision (the same list is public in agentic). The watchlist and queries stay private; the allowlist's place is decision H | sections 2c, 3 (privacy), 7 (H); a marker test per summary |
| N2: decoding must not change the article key | **Accepted; the first draft was ambiguous.** The wrapper key is untouched and independent of resolution | sections 1 and 2b; NP2a does not touch `keys.py` |
| N3: "retry through revisions" has no input; S1 trashes the poll; the cap leaves most items undecoded | **Accepted, a real gap.** The retry input is the wrapper link, which the Record did not keep. Chosen: `wrapper_link` in the article, a separate write-once resolution file, a resolve pass over the Record, so S1 is irrelevant. I did not use a revision (it would record a false revision on every re-poll without a planner change) | section 2b, story NP2c, volume worked out against the cap |
| Pacing wording: cross-host spacing is new code; feeds must stay at 1.0 s | **Accepted** | sections 2a, 2d, 5; the `NEWS_PACER` instance named |
| My own correction found while building NP2a | Tier, wire, promotional, tickers and priority are **not** written into the article file (they depend on rule files and would cause mass false revisions); a second migration trap (the cluster reader refuses other formats) | section 3 |
