# NP7: the company-list safeguard and the cutover (PLAN)

PLAN for the orchestrator's check and one judge before any code. Lane 1 for the code that follows (it changes the write-once cluster file
and the schedules of the workflows that call outside services). Plan: [NP0](NP0-news-port-plan.md) row NP7 and decision 7, **reshaped to
ingestion only (owner, 27 Oct 2026, relayed by the orchestrator): this repository fetches, derives and stores write-once to Drive; what a
dashboard or an API reads, and its fields, belong to the repository that serves it.** The earlier draft of this plan had a derived
"view file" and a consumer contract (NP7a); both are DROPPED, and nothing here says what a consumer reads. Any consumer can read the
facts-only Record, the cluster files and the receipts from the Drive, and apply the public rules (`config/news_sources.yaml`) and its own
private lists itself. `ArticleViewer` (NP5b) and `corroborate` (NP6b) stay as this repository's own compute-on-read code; no run here uses them
yet, and this plan adds no consumer for them. **This document builds nothing.**

## NP7b: the company-list rollback and edit rule (judge 100 N4; judge 101 B1)
The version 2 cluster run builds `PrivateCompanyFile` with `lowest_version=0` and no `used`, so it would accept an OLDER list than the one it
used before, and would not notice a list EDITED IN PLACE under the same version number (`VersionedFiles.latest` detects an edit only through
`used={version: sha}`). Fix:
1. The version 2 cluster file records `companies_sha256` beside `companies_version` (the SHA-256 of the list bytes; it sits in the private Drive
   file, never in git or a log). The run reads the previous file (it already does, for `previous`) and builds the list reader with
   `lowest_version` = that `companies_version` and `used={companies_version: companies_sha256}`. An older list stops the run with
   `company_list_rolled_back`; a list whose bytes differ from the recorded ones stops it with `company_list_damaged`. `PrivateCompanyFile.companies`
   also refuses when `latest` skipped a damaged newer version (`Picked.damaged` non-empty) instead of quietly using the older one.
2. The first version 2 file has no previous one, so it only records.
3. Adding `companies_sha256` changes format 2, which no file uses yet (version 2 has not been dispatched); the NP6a row Z15 and the parser are
   updated with it.
The materiality file has no reader in any run of this repository today (see "Found while planning"), so no rollback rule is planned for it now;
it gets one when a run starts to read it. Lane 1, two judges (the same code path as Z6), small.

## NP7c: the cutover, ingestion workflows only (documents and owner decisions)
1. **The owner's gate list before any schedule is enabled** (a runbook page that this plan names and the story will write; one owner for each fact):
   the outlet and resolver probes ran from a runner and their counts are acceptable; the resolve and read passes ran with `resolver_failing` and
   `reader_failing` not red; a company list, a discovery file and the other private files exist; the version 1 against version 2 clustering
   comparison (NP3c below) was reviewed, including `url_joins_unlike_title`; and the scheduled `data-cache sync --unreceipted raw/news` check exists
   and ran clean (judge 62 F-a: nothing runs it today, so a Record file with no receipt would pass silently).
2. **Order of enabling (judge 101 B2).** Every news workflow, fetch and promote included, is dispatch-only on main (`news-fetch`, `news-promote`,
   `news-resolve`, `news-read-pages`, `news-cluster`, `news-probe-outlets` have no `schedule:`; I checked), so nothing flows until the owner enables
   them, and a later stage reads what an earlier one wrote. The order, each step a lane 1 workflow change at the owner's go, one at a time, each
   first run watched: **fetch, promote, resolve, read-pages, cluster (algorithm 2), then staging cleanup** (`staging-cleanup.yml`: report only first,
   apply only after the owner reads the report). Groww's market-hours rule is untouched (none of these call Groww).
3. **Retire the version 1 cluster run only after the owner switches to version 2:** the scheduled version 1 run stops; the version 1 files stay
   forever (write-once) and `parse_cluster_file` keeps reading them. `cluster/entities.py` and the version 1 preparer can then be deleted (lane 1,
   with a test that old files still parse). Until then nothing is removed.
4. **Agentic's own collection (NP0 decision 7) is not touched by this repository.** Whether and when agentic stops collecting is for the
   owner, in agentic; this plan only provides the comparison data (NP3c).

## NP3c (kept separate, dispatch-only): the measurement the cutover needs
A read-only `news compare-clusterings` that clusters the same window with version 1 and version 2 in memory and writes nothing: counts of clusters,
size distribution, joins by URL, `url_joins_refused`, `url_joins_unlike_title`, and the number of articles tagged per company (no titles, no
symbols). And, with it, the recall question NP3b left open: how many tagged articles the broad feeds alone find against the targeted ones.
Owner-dispatched (it reads the Record and the private lists). A separate small story with its own plan paragraph; not designed further here.

## Found while planning (a decision for the orchestrator and the owner, not decided here)
**The read pass still reads newest first.** NP4's plan said the pass would prefer "material" headlines once NP5 existed. NP5 built `MaterialTerms`
and the tagger, but nothing in `reads/run.py` uses them: with a cap of 80 pages a pass, the pages read are the newest listed ones, not the material
ones, and the materiality file the owner would write has no effect on any run. Wiring it means the read pass loads the company list and the
materiality file (private, versioned, with the rollback rule above, and a decision whether a missing or unreadable file stops the pass or falls back
to newest first). That is an ingestion change, lane 1, and its own story; I have not planned it. Reasoning only: until it exists, the cap of 80
spends reads on whatever came last.

## Decisions I am making (the judge should overrule what is wrong)
- NP7b records the list's SHA in the cluster file, not in git. The cost is one more field in a file nobody has written yet.
- No rollback rule for materiality until a run reads it.
- `url_joins_unlike_title` and the URL rule are not touched until the measurement (agreed with the orchestrator).

## Said plainly
- Nothing in NP1 to NP7 has run against real feeds: no outlet probe, no resolver call, no page read, and no company list exists yet. Every rate,
  size and run-time figure in these plans is reasoning only until the owner dispatches the first runs.
- The privacy line holds: no title, URL, symbol or company name is written to git or a log by anything here.

## Contract rows planned (docs/RECORD_CONTRACT.md, appended to the NP6a section)
A version 2 run stops on an older company list (`company_list_rolled_back`) and on a list edited in place (`company_list_damaged`); the first file
only records; the recorded SHA is of the bytes used; a skipped damaged newer version is a stop, not a fallback; the new field is in the file and in
the parser.

## Size and order
NP7b about 60 lines plus tests; NP7c documents; NP3c its own story. Order: NP7b and NP3c in parallel (neither waits on the other), NP7c last
(owner decisions).
