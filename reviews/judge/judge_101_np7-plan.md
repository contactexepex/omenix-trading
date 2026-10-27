# Judge 101: NP7 cutover and read-contract plan (plan doc), round 1 at f69aef7: FAIL

**Lane 1 plan, sole judge (judge #1).** Branch `story/NP7-plan`, frozen SHA f69aef7: one file, `docs/stories/NP7-cutover-and-read-contract.md` (92 lines). The orchestrator's check is not evidence here; I checked the claims against `main`.

## (2) NP7b, the rollback pin: required, B1 (strong evidence, code)
- The plan pins only `lowest_version` (from the previous cluster file's `companies_version`) and explicitly declines "a hash of the list bytes per file".
- But `VersionedFiles.latest(lowest_version, used)` (`news/versioned.py:50-69`) detects a version **edited in place** only through `used`, a map of version to SHA-256: "a version edited in place is skipped loudly" needs that map.
- With `lowest_version` alone, `companies-v3.json` edited in place (same number, other content) is accepted, and the run **silently regroups**. That is exactly the harm NP7b exists to stop, and it is not "damage", because the edited file is valid.
- **Fix:** record `companies_sha256` in the version 2 cluster file (and `materiality_sha256` in the view header). Pass `used={version: sha}` with `lowest_version`, so an edited list is refused or skipped like the feed list. The list's hash is a private file's digest, safe to keep in the private Drive file.

## (3) The cutover order: required, B2 (strong evidence, code)
- On `main` every news workflow is dispatch-only: `news-fetch`, `news-promote`, `news-cluster`, `news-resolve`, `news-read-pages`, `news-probe-outlets`, and `staging-cleanup` (each has 0 `schedule:` blocks).
- The plan's order, "resolve, read-pages, then the cluster run with algorithm 2, then views", omits **news-fetch and news-promote**. Without them no article reaches the Record, so the later steps have nothing to work on. It also omits the staging cleanup, which can trash news polls and must come after promote with a report-only first run.
- **Fix:** give the whole order (fetch, then promote, then resolve, read-pages, cluster v2, views, then staging-cleanup report-only and then apply), each with its gate.
- **Gate list, recommended additions:**
  - the scheduled `data-cache sync raw/news --unreceipted` check (judge 62 F-a), so a Record file without a receipt is caught during cutover;
  - the S1 cleanup's first report-only run.

## (1) View snapshot against judging on read: acceptable, with one addition
- A write-once **derived** snapshot labelled with its inputs does not contradict "judgements are computed on read". The Record keeps only facts, and every snapshot is a dated reading of them; the next run reflects a rule edit. One implementation for every consumer is the right call.
- **Missing from the header (recommended; reasoning only):** the version of the **code** that judged. A tagger or view-rule change, such as NP5a's possessive fix, changes the output with no list or rule-file version bump, so two snapshots could differ with identical labels. Add the commit SHA (`GITHUB_SHA`, public) or a view-rules version.
- Overlapping 48 h windows mean each article is in about 48 snapshots. The plan's size estimate already counts this (about 40 MB a day), and the cadence decision is deferred to real numbers, which is right.

## (4) Company-tagged clusters only: an owner decision, cost understated
- For an F&O trader, market-wide news matters: RBI policy, crude, rupee, FII flows (NP0's broad queries).
- Unless the text names a company or one of the index aliases ("Nifty", "Bank Nifty"; NP3a), such a story is **dropped** from the view.
- A missing company list (version 0) yields an empty view.
- State both, and add a "market-wide" bucket (broad-query items, or a minimum origin count) as an owner option, rather than presenting "tagged only" as costless. The "counts add up" row should also report the clusters dropped.

## What holds
- The plan says plainly that the dashboard's fields and access path are unconfirmed, and NP7a waits for them.
- Agentic's cutover is out of this repository.
- The version 1 files stay readable forever.
- The privacy line holds: view files live in the private Drive; logs and codes carry no titles or URLs.

## Verdict: FAIL round 1 at f69aef7. B1 (pin the list's SHA-256, not just its number) and B2 (the full enabling order) required; (1) the code version and (4) the cost statement recommended.
