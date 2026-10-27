# NP2c: the resolve pass

Lane 1, two judges (it makes real requests to an outside service once the owner dispatches it, writes the Record, and adds a
workflow). Plan: [NP0](NP0-news-port-plan.md) section 2b ("Where it runs and how a failed item is retried"); built on
[NP2a](NP2a-article-format-2.md) (`wrapper_link` in the article file) and [NP2b](NP2b-link-resolver.md) (the resolver, merged,
with the 403 stop). Contract rows V1 to V12 in `docs/RECORD_CONTRACT.md`. **Nothing runs until the owner dispatches the
workflow; the workflow has no schedule.**

## What it does
`python -m fno news resolve [--apply] [--limit N]` is one pass over the **Record**, not over Staging:
1. reads the articles manifest of the last **3 days** (`LOOKBACK_DAYS`), newest day first;
2. skips the articles that already have a resolution (the `resolved.csv` manifest, no read);
3. reads the article files (read only), keeps those of kind wrapper with a `wrapper_link`, up to **80** (`CAP`, never raised by
   `--limit`); the rest of the wrapper articles are counted as `backlog`;
4. asks the resolver **once** with those links (V1: one resolver per run, so its stop on a 429/503/403/sorry page and its 1.5 s
   spacing are never reset; the wiring builds it once from the private feed list);
5. with `--apply`, writes each success as `news/resolved/<key[:2]>/<key>.json` through the shared write-once writer
   (`news/write_once.py`, extracted from the cluster writer: file, receipt, then the `resolved.csv` row; other bytes at the
   name are a conflict, never an overwrite). **Without `--apply` it is the probe**: it asks the resolver (real, paced,
   capped requests) and writes nothing.

A failure writes nothing and is counted by its fixed code; the link is asked again on the next pass until it leaves the
look-back. A service that pushes back (`paused`) is not red: those links wait. Staging is never read, so the staging cleanup
trashing a promoted poll after 7 days loses nothing the pass needs (pinned by a test that deletes the staged polls).

## The resolution file
Facts only, no time (the same answer is the same bytes): `format`, `key`, `url`, `host`, `claimed_domain` (what the feed said),
`host_agrees` (same registrable domain as the claim), `resolver` (the locked library version). The article key never depends on
it. The reader's rule (NP7): the effective source URL is the resolution's if present, else the publisher link, else none.

## Bounds and alerts (said plainly)
- At most 80 links resolved and **600 article files read** per pass (`unexamined` counts the rest). Reading is the cost: with
  the cap reached or everything resolved a pass still reads unresolved publisher articles of the look-back (up to 600) because the
  manifest does not say which are wrapper articles. This is bounded, not free (about 2 minutes at 0.2 s a Drive read, reasoning only).
- `expiring` counts unresolved wrapper articles on the **last day** of the look-back (failed or left out by the cap), about to be
  left unresolved for good. It is counted again on every pass of that day (not a unique count). It alerts #fno-desk but does not
  turn the run red; red only for what needs fixing by hand (an unreadable article, a conflict, a failed write, a torn manifest).
- Throughput margin: about 53 links an hourly pass are needed to keep up with ~1,280 a day at 1.5 s apart, against a cap of 80
  (reasoning only; it also assumes the service answers). Nothing is lost silently: the line shows `backlog` and `expiring`.
- Articles recorded before NP2a have no `wrapper_link` and stay unresolved for good (no back-fill).
- The endpoint is unofficial and has not been called from a runner yet: the first probe is the owner's dispatch of this
  workflow without `apply`; its counts-only line is the evidence (strong evidence only after that run).

## The workflow `news-resolve.yml`
`workflow_dispatch` only, inputs `apply` (default false), `limit`, `dry_run`; the `news-record` concurrency group (serial with
promote and cluster); the shared commit guard (`ops/commit_news_record.sh`) for `resolved.csv` and the receipts; the public-record
scan on (O5); no Slack token in code paths other than the alert sender. It makes no Groww call and is not subject to the Groww
hours rule; it does call the search service, which is paced and capped as above.
