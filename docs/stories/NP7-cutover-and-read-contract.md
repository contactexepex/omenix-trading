# NP7: the read contract and the cutover (PLAN)

PLAN for the orchestrator's check and one judge before any code. Lane 1 for the code that follows (it writes a new kind of Record file,
defines what the dashboard reads, and retires the old collector). Plan: [NP0](NP0-news-port-plan.md) rows NP7 and decision 7, with the
changes below. **This document builds nothing.** What I have not read: the dashboard repository (`exepex/omenix-dashboard`) and agentic's
consumers of its JSONL; I do not know what either needs beyond NP0's list (title, short summary, real source URL, tier, tags, flags), so
the fields below are reasoning only and the owner or the dashboard's builder must confirm them before NP7a is built.

## The problem in one paragraph
The engine on `main` (NP1 to NP6) judges articles when they are READ: tier, agency, promotional, tags, material, origins and flags depend
on rule files and the owner's private lists that change after a file is closed. No consumer has a defined way to read all that. If each
consumer re-implemented the rules (the dashboard in one place, agentic in another) the two would disagree, and a consumer would need Drive
credentials and our code. NP7 gives them one file to read.

## NP7a: the view file (the read contract)
**A new write-once Record file per cluster run: `news/views/1/<window end>.json`** (format 1), built by a new read-only `news views` command
from the version 2 cluster file of the same window plus the articles, resolution files, read files, source rules, company list and materiality
terms of that moment, with the NP5b `ArticleViewer` and the NP6b `corroborate`. It is a derived snapshot (CLAUDE.md: derived data also lives
write-once in Drive) and is never edited; the next run writes the next snapshot, so a rule edit shows from the next file, not in an old one.
- **Header:** `format`, `window_end`, the cluster algorithm version, `companies_version`, `materiality_version`, `rules_sha256` (SHA-256 of
  `config/news_sources.yaml`, so the count in a file names the rules it came from; this is the `rules_version` NP6b left to the caller),
  counts (including `clusters_dropped`, see "Which clusters" below), the cluster file's own path, and `view_rules_version` (a constant for the
  judgement code: a code change can alter the output with no file version changing, judge 101 recommended 1). A git SHA is NOT used for it: it
  would make a re-run of a closed window after any unrelated deploy a write-once conflict. Instead a test hashes the source of the judgement modules
  and fails when it differs from the digest recorded beside the constant, so a change to them forces a deliberate bump (reasoning only: the
  judge may prefer another mechanism).
- **Which clusters (owner decision, judge 101 recommended 2).** Option A (the default of this plan): only clusters with at least one article tagged
  to a company, primary or mentioned. Cost: market-wide news (a rate decision, crude, FII flows) drops out unless an index alias catches it.
  Option B: A plus clusters that name an index or a market-wide term (the owner writes the terms). Option C: every cluster (the size above).
  Under A or B an empty company list (`companies_version` 0) would make an empty view, so the view command STOPS with `company_list_missing`
  instead; and the header reports `clusters_dropped`, so a loss is counted, never silent.
- **Per cluster:**
  `cluster_id`, `independent_origins`, `unverified_origins`, `flags`, `reads_used`, and its members. **Per member:** `key`, `title`, `summary`
  (the feed's snippet, plain text, capped), `url` (the effective source URL or ""), `outlet`, `tier`, `listed`, `opinion`, `wire`, `wire_via`,
  `promotional`, `tag` (primary, mentioned, confidence), `material`, `access`, `published_at`, `first_seen_at`.
- **Where it lives and who reads it:** the private Drive Record, with a receipt and a manifest row (`views.csv`) like every file; never in git
  (titles and URLs stay private, only counts and codes reach logs). A consumer reads it through the verified cache (`data-cache sync
  news/views`, the existing O9b reader), so a changed or missing file is detected. The dashboard needs Drive read access or a copy
  it is given; I do not know which it has (**owner/dashboard question**).
- **One owning document** `docs/NEWS_VIEW_CONTRACT.md` (the format, every field, what is computed from what, what a consumer may rely on).
  NP7a is lane 1, two judges.
- **Size (reasoning only, unmeasured):** a window of 48 h holds roughly 3,000 articles (about 1,500 a day, agentic's count); at about 600
  bytes a member a full snapshot is about 1.8 MB if every cluster were kept, hourly = about 40 MB a day. Keeping only company-tagged
  clusters should cut that a lot, by an unknown amount. The first dispatch reports the real size; if it is too large the cadence becomes
  daily or the window shorter (a decision with the number in hand). The file is rewritten whole each run; no delta format is planned.
- **Dispatch-only workflow** `news-views.yml` (new, same `news-record` concurrency group, counts-only output), like every other NP workflow
  until the owner enables schedules.

## NP7b: the company-list rollback and edit rule (N4, from judge 100; B1 of judge 101)
`PrivateCompanyFile` is built with `lowest_version=0` and no `used`, so a run would accept an OLDER list than the one it used before, and
would not notice a list EDITED IN PLACE under the same version number (`VersionedFiles.latest` detects an edit only through
`used={version: sha}`). Fix, in two parts:
1. The version 2 cluster file records `companies_sha256` beside `companies_version` (the SHA-256 of the list bytes; it sits in the private
   Drive file, never in git or a log). The run reads the previous file (it already does, for `previous`) and builds the list reader with
   `lowest_version` = that `companies_version` and `used={companies_version: companies_sha256}`. An older list stops the run with
   `company_list_rolled_back`; a list whose bytes differ from the recorded ones stops it with `company_list_damaged`. `PrivateCompanyFile.companies`
   also refuses when `latest` skipped a damaged newer version (`Picked.damaged` non-empty) instead of quietly using the older one.
2. The same for `materiality_version` and `materiality_sha256` in the view header (NP7a), and for the company list the view command reads.
The first v2 file has no previous one, so it only records. Adding `companies_sha256` changes format 2, which no file uses yet (version 2 has
not been dispatched); the NP6a row Z15 and the parser are updated with it. Lane 1 (the same code path as Z6), small.

## NP7c: the cutover (mostly documents and owner decisions)
1. **A gate list the owner checks before any schedule is enabled** (a runbook section in `docs/NEWS_VIEW_CONTRACT.md` or its own page, whichever
   keeps one owner per fact): the outlet and resolver probes ran from a runner and their counts are acceptable; the resolve and read passes
   ran with `resolver_failing` and `reader_failing` not red; the scheduled `data-cache sync --unreceipted raw/news` check exists and ran clean
   (judge 62 F-a: nothing runs it today, so a Record file with no receipt would pass silently); a company list, a materiality file and a discovery file exist (private); the
   version 1 against version 2 clustering comparison (NP3c below) was reviewed, including `url_joins_unlike_title`; a view file was written
   and its size and run time were reported.
2. **Order of enabling (judge 101 B2).** Every news workflow, including fetch and promote, is dispatch-only on main today
   (`news-fetch`, `news-promote`, `news-resolve`, `news-read-pages`, `news-cluster`, `news-probe-outlets` have no schedule), so nothing flows
   until the owner enables them, and a later stage reads what an earlier one wrote. The order, each step a lane 1 workflow change at the owner's go,
   one at a time, each first run watched: **fetch, promote, resolve, read-pages, cluster (algorithm 2), views, then staging cleanup**
   (`staging-cleanup.yml`: report only first, apply only after the owner reads the report). Groww's market-hours rule is untouched (none of
   these call Groww).
3. **Retire omenix's old pieces, only after the owner switches to version 2:** the scheduled version 1 cluster run stops; the version 1 files
   stay forever (write-once) and `parse_cluster_file` keeps reading them. `cluster/entities.py` and the version 1 preparer can then be deleted
   (lane 1, with the removal proven by a test that old files still parse). Until then nothing is removed.
4. **Agentic stops collecting (decision 7 of NP0) is NOT done by this repository.** It needs a dual-run period in which both collect and the
   owner compares, then agentic reads the view files instead of its own JSONL. That change is in agentic and is not planned here. What this plan
   gives it is the contract file; what the dual-run compares is NP3c.

## NP3c (kept separate, dispatch-only): the measurement the cutover needs
A read-only `news compare-clusterings` that clusters the same window with version 1 and version 2 in memory and writes nothing: counts of
clusters, size distribution, joins by URL, `url_joins_refused`, `url_joins_unlike_title`, and the number of articles tagged per company
(no titles, no symbols). And, with it, the recall question NP3b left open: how many tagged articles the broad feeds alone find against
the targeted ones. Owner-dispatched (it reads the Record and the private lists). A separate small story with its own plan paragraph; not designed
further here.

## Decisions I am making (the judge should overrule what is wrong)
- A derived snapshot file, not a read library for consumers: one implementation of the rules, plain JSON for the reader. Cost: a file per run
  and a snapshot that is only as fresh as the last run.
- Company-tagged clusters only (option A) as the default, with B and C named for the owner. Cost: an untagged story is not on the dashboard
  until a company alias catches it (the aliases are the owner's list).
- `url_joins_unlike_title` and the URL rule are not touched until the measurement (agreed with the orchestrator).

## Said plainly
- I do not know what the dashboard or agentic read today. This plan is built on NP0's list of what the dashboard needs; the fields and the
  access path must be confirmed before NP7a is built.
- Nothing in NP1 to NP7 has run against real feeds: no outlet probe, no resolver call, no page read, no company list exists yet. Every rate,
  size and run-time figure here is reasoning only until the owner dispatches the first runs.
- The privacy line holds: view files are in the private Drive; no title, URL, symbol or company name is written to git or a log.

## Judge 101 round 1: accepted after checking the code
B1 (`versioned.py` detects an in-place edit only through `used`, confirmed by reading `latest`), B2 (confirmed: none of the six news workflows has a
`schedule:`), and both recommendations. Changes are in NP7a (header, which clusters), NP7b and NP7c above.

## Contract rows planned (new section "The news view file (NP7)")
V-series is taken; the rows will use the next free letter. Planned claims: the file is built only from the named inputs and carries their versions;
only company-tagged clusters are kept and none is dropped silently (counts add up); the effective URL is never a feed claim; the same inputs
give the same bytes and a re-run with other inputs is refused by write-once; an older company list or materiality file stops the run; a view
file names no title or URL in a log or a code; the format document and the writer agree on the field list.

## Size and order
NP7a about 350 lines of code in three small files plus the contract document; NP7b about 60 lines; NP7c documents. Order: NP7b first (small,
independent), NP7a, NP3c in parallel, NP7c last (owner decisions).
