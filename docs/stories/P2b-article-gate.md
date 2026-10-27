# P2b: the article gate — staged news polls into the write-once Record (PLAN)

PLAN for the orchestrator's review before any code. Lane 1 (it writes the Record: write-once data, receipts, the privacy
rule). Design and invariants: [P2-news-dedup.md](P2-news-dedup.md) (merged, double-PASSed); the fetcher it reads from is P2a
(merged). Pattern: [P1-staging-record-split.md](P1-staging-record-split.md). **This step PROMOTES to the Record**, so the
write-once and privacy invariants apply in full. It is built and tested offline only: the first real promotion is the owner's
go-live step, and the workflow is `workflow_dispatch` only with no cron.

## What passes and what stays in Staging

A staged poll (raw feed bytes) is read in this order; the first failure leaves the poll in Staging with ONE fixed reason code
and counts toward an alert (never a title, URL or message):

| Level | Check | Code |
|---|---|---|
| poll | larger than 5 MB | `poll_too_large` |
| poll | contains a DOCTYPE or ENTITY declaration (XML expansion attacks; a feed needs neither) | `unsafe_xml` |
| poll | does not parse as XML, or has no RSS/Atom/RDF root | `not_a_feed` |
| poll | parses but has no items | `no_items` |
| item | no title | `item_missing_title` |
| item | no link and no guid | `item_missing_link` |
| item | any field over 20,000 characters | `item_too_long` |

An item with no usable publication time is **not** rejected: it is kept with `time_source=seen` (design N6). There is no age
check at all. Parsing uses the standard library's `xml.etree` only after the DOCTYPE/ENTITY refusal (no new dependency, which
would touch the hash-locked requirements).

## What it writes (the Record, private Drive `raw` area; the gate is the only writer)

- **Article file** `news/articles/<key[:2]>/<key>.json`: the fixed fields of the design (key, source name, title, the feed's short
  summary, canonical URL for publisher items, published time, `time_source`, first `seen_at`). Sharded by the first two hex
  characters of the key so a path depends on the key alone: finding an existing article needs no index and no date.
- **Same key, same fixed fields** (seen_at and feed id excluded): a no-op. **Same key, different fixed fields** (a live blog, a
  correction): the first file stays the record and the later version is written write-once to
  `news/revisions/<key[:2]>/<key>/<sha8 of the version>.json`. It reuses the revision *pattern* of P1 (`RevisionSink`) but
  NOT its archive: the A11 revision index and the standard manifest carry NSE-style URL columns, which would break invariant 1.
  A small news revision writer implements the same interface.
- **Manifest** `research/data/manifests/news/articles.csv`: `date,article_id,status,sha256,size_bytes` (`status` = recorded or
  revision), a row only after Drive accepted the file (file first). Hash ids only. **Receipts**: one SHA-256 receipt per Drive
  file under `receipts/`, as the data-store rule requires.
- **The key** is the design's D2 key by item kind. The kind (publisher or Google News wrapper) comes from the feed list: the
  private `feeds-vN.json` gets an optional `kind` per feed (default `publisher`, `wrapper` for Google News), so no host name is
  written in the code (the tree-scan test forbids it). P2b adds that field and its validation to the feed-list parser.
- **Canonicalisation** is the D3 allow-list; **time parsing** accepts RFC 822 and RFC 3339, a zone-less time is read as UTC and
  flagged `time_source=assumed_utc`, and an unparseable one becomes `seen`.

## Reconciliation and alerts

For every poll the gate checks `items = recorded + revisions + no-ops + rejected-by-code` and writes that line (counts only)
to the run log; the run exits 1 and alerts #fno-desk on any rejection code. A plant that skips an item makes the sum fail.
A poll that failed stays in Staging and is never pruned. Reprocessing is idempotent (the same poll gives all no-ops), so the
command takes `--from YYYY-MM-DD` like `promote` and may be re-run; the same stuck poll is therefore re-alerted on each run
(the existing P1 gap, not new).

## Order of work (each its own judged round, one in flight)

1. **P2b1, pure functions, no I/O:** the parser and poll/item checks, the key, the canonicaliser, the time parser, the article
   file format. Tests on synthetic feeds; plants on every check.
2. **P2b2, the writer:** the gate over Staging, the Record writer, the revision writer, the manifest and receipts, the
   reconciliation, `python -m fno news promote`, `news-promote.yml` (dispatch only), the master privacy test extended to this
   layer (marker headline, URL and query through parse, key, article file, revision, manifest, receipt, logs and alerts, including
   the failure paths and DEBUG logging), and the wiring test that the gate writes only to the Record areas and reads only Staging.

## Risks, said plainly

- **Receipt volume.** One receipt per article file is the project rule. Reasoning only, assumptions: 10 feeds, perhaps 300 new
  articles a day, is 300 receipt files and 300 manifest rows a day in the public repository (about 110,000 a year). Ask: is that
  acceptable, or should receipts for news be batched per run? Batching would change the design's "one file per key".
- **XML from the open web** is untrusted: the DOCTYPE refusal and the size cap are the defence; the plan has no entity expansion.
- **Time handling** is the commonest source of silent errors: zone names, zone-less times, future times. A future time is
  accepted and flagged, never rejected (no age or range check at the gate).
- **Google News fallback key** (no guid) depends on the title and summary being stable across polls; if Google edits a title the
  item gets a new key and clustering merges the two. Accepted by the design.

## Deferred to the owner's go-live

The first real promotion, the `news-promote` schedule, and the answer on receipt volume. Gates per step: full suite, ruff,
imports, numbers, size (350 lines), record scan, mutation plants for every invariant, two judges.
