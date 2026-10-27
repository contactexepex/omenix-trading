# News pipeline: go-live checklist (NP7c)

This page describes `main` **after NP8** (the material-first read order, the pass note and their codes); it is merged after NP8 so every line is true on main.

The one owning document for turning the news pipeline on. **Ingestion only** (CLAUDE.md, "Scope"): this repository fetches, derives and stores
write-once to the Drive; what a dashboard or an API reads is another repository's job and is not described here. Every news workflow is
`workflow_dispatch` only today (no `schedule:`, checked on main): nothing runs until the owner dispatches it or enables a schedule. No news
workflow calls Groww, so the market-hours rule does not touch them. **Nothing in this chain has run against real feeds.** Every rate, size and
run time below is unmeasured; the first runs will show them in their one-line counts.

## 1. What the owner provides (private files in the Drive's `config` area; never in this repository)
| File (folder, version rule) | Used by | What it is | Without it |
|---|---|---|---|
| `feeds/feeds-vN.json` | fetch | the feed list and its private salt (NP3b describes the format) | nothing is fetched |
| `discovery/discovery-vN.json` | `news plan-feeds` | the query templates the planner turns into feeds | no planned feeds |
| `companies/companies-vN.json` | tagger, cluster v2, read order | the company list: names, aliases, exclusions. `news seed-companies --apply` writes `companies-v1.json` from NSE's archived lists | no tags; cluster v2 has `companies_version 0` |
| `materiality/materiality-vN.json` | read order | weighted title terms; **optional** | the read pass reads newest first |
Rules for all four: the newest version is used; never edit a version in place (a run that finds one changed stops or degrades, see section 4);
a correction is a new version number. The public rules (outlets, tiers, agencies) are `config/news_sources.yaml` in this repository.

## 2. Gates the owner checks before any schedule is enabled
1. **Reach:** run `news-probe-outlets` (leave `include_refusing` off) and `news-resolve` without `apply` once; read the counts. A runner that
   cannot reach the outlets or the resolver is the most likely first problem (unmeasured).
2. **Honest readers:** the first `news-resolve --apply` and `news-read-pages --apply` runs finish without `resolver_failing` or `reader_failing`.
3. **Files exist:** a feed list; a company list (seed it, then add aliases and exclusions as a new version); a discovery file if planning is used.
4. **Compare the two clusterings:** dispatch `news-compare-clusterings` (read only, counts only). Read `url_joins_unlike_title` first: above zero
   means the URL rule lets generic links merge unlike stories. Merges that version 2 makes and version 1 does not are not proof that version 2 is
   right; there is no ground truth, only a human reading real pairs.
5. **Dry runs:** every workflow has a `dry_run` input that proves the runner, the dependencies and the command load; run each once.

## 3. Order of the first runs, then of the schedules
First, by hand (one at a time, reading the one-line counts after each): fetch; promote (`from_date` = today); resolve with `apply`; read-pages
with `apply`; cluster with `algorithm` 1 and then 2; compare-clusterings; staging cleanup **report only** (never `apply` on the first run).
Then, only at the owner's go and one workflow at a time, enable schedules in the same order: **fetch, promote, resolve, read-pages, cluster,
staging cleanup** (report only first; `apply` after the owner has read the report). Each is a lane 1 workflow change, and the first scheduled run
of each is watched. Cron times are not decided here (reasoning only: they depend on measured run times, which do not exist yet).
Why this order: each stage reads what the stage before it wrote. Nothing flows from fetch to the Record until promote runs, and the later
passes find nothing until resolve and read-pages have something to work on.
Dispatch notes: `news-cluster` takes `algorithm` 1 (default) or 2. Algorithm 2 may be dispatched now that the company-list pin (NP7b) is on
main. `news-resolve` and `news-read-pages` are probes unless `apply` is ticked.

## 4. What a red run means (the fixed codes the logs print)
| Code | Meaning | What to do |
|---|---|---|
| `resolver_failing`, `reader_failing` | the pass asked and almost nothing came back | check reach (gate 1); the outlet or resolver may block the runner |
| `unexamined`, `budget_stopped` | the read cap or the time budget left work undone | normal for a backlog; watch whether it persists |
| `company_list_invalid/rolled_back/damaged/unavailable`, and `company_list_missing` for a list used before | the company list cannot be used. **Cluster v2 STOPS** (it archives grouping built from tags). **The read pass DEGRADES** to newest first, red, reads continue, no pass note | publish a new, higher version number; never edit a version in place |
| `materiality_invalid/rolled_back/damaged/unavailable`, and `materiality_missing` for a file used before | the same for the materiality terms, which only order reads: always degrade, never stop | as above |
| `pass_note_unreadable` | the last read-pass note is damaged, so the pin cannot be checked | the pass degrades; look at the newest note under `news/read-passes/1/` |
| `read_conflict`, `cluster_conflict`, `resolution_conflict` | a write-once file exists with other bytes; nothing was overwritten | investigate; do not delete |
A file that was **never configured** is not an error, for either run: **cluster v2 records `companies_version` 0 and the run is green; the read pass is green and newest first.** A file **used before and now gone** is red: `company_list_missing` stops cluster v2 and degrades the read pass; `materiality_missing` degrades the read pass (cluster v2 does not use the materiality file).

## 5. Retiring the version 1 cluster run
Only after the owner reads gate 4 and switches the scheduled cluster run to algorithm 2: the version 1 run stops; its files stay forever
(write-once) and the parser keeps reading them. The code for version 1 (`cluster/entities.py` and its preparer) can then be deleted as a lane 1
change that includes a test proving the old files still parse. Until then nothing is removed.

## 6. Decisions still the owner's
Cron times; whether to enable resolve and read-pages for every article or only some; the key-sentences question for page reads (default: no
sentences are stored); whether outlets that refuse automated reads stay excluded (default: honoured); the keep-or-delete call on the
code with no pipeline caller (`ArticleViewer`, `OriginReader`, `PromotionalFilter`, `corroborate`, listed in the 27 Oct log); the git-history
note about a judge file that quoted real exclusion patterns (history is not rewritten here); agentic's own collection is not touched by this
repository.

## 7. Not measured yet
Whether the runner reaches the outlets and the resolver; the unresolved share; the share of material headlines; the run time of one read pass
(ranking up to 300 articles, then at most 100 resolution reads) and of one cluster run (one Drive read per Google News item in the window);
the merge rates of the two clusterings. Each of these appears in the one-line counts of its first run.

## 8. Recommended hardening after go-live (not built, optional)
A scheduled `data-cache sync raw/news --unreceipted` check (judge 62 F-a) is **not built and is not a gate**. Nothing runs it today. What
protects the Record already is the writer's order (the Drive file, then its receipt, then the manifest row) and the commit guard
(`ops/commit_news_record.sh`: a torn manifest never reaches main, its receipts do). The case the walk would catch is a run that dies between
the file and its receipt, leaving a file with no valid receipt that `DriveCache.sync` cannot see; the walk is detective defence in depth, run by
hand today with the command above. It is a small lane 1 workflow addition (called NP7d, unwritten) that the owner can ask for.
