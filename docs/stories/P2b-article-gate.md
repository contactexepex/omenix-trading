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
  NOT its archive: the A11 revision archive accepts only paths of an NSE dataset (`source_of` refuses any other) and records them
  in the standard manifest, which has a URL column; both are wrong for news (invariant 1).
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

## P2b1 as built (the pure functions)

- **Code:** `fno/ingestion/news/article/` (`xml_safety.py`, `parse_feed.py`, `raw_item.py`, `item_checks.py`, `canonical.py`,
  `times.py`, `normalise.py`, `keys.py`, `article_file.py`, `read_poll.py`), the gate codes in `news/codes.py`, and the optional
  `kind` per feed in `news/feeds.py` (default `publisher`, `wrapper` for Google News; any other value is refused, a file without
  the field still loads). No I/O, no clock, no network, no committed surface: it produces values and persists nothing.
- **Hostile XML:** the raw bytes are searched (case-insensitive, and again with NUL bytes removed so UTF-16 and UTF-32 cannot hide
  a declaration; a BOM or leading white space changes nothing) for a DOCTYPE or ENTITY declaration BEFORE the standard-library
  parser is called; a billion-laughs and an external-entity sample are refused with `unsafe_xml` and a test proves the parser is
  never reached. The size cap is pinned at 5 MB. Item fields over 20,000 characters are `item_too_long` (pinned).
- **Key:** `keys.py` implements D2 (publisher: canonical URL, else guid; wrapper: guid, else full time + normalised title and
  summary + source) with a separator that cannot occur in the parts. Tested: deterministic, 3,000 random distinct inputs give
  3,000 keys, two same-title items a minute apart give two keys, tracking-only differences give one key and a real parameter two.
  The writer-side collision test (two distinct items sharing a key must be surfaced, not hidden) is P2b2.
- **One bad item never costs the poll its others (judge 46 K1).** A link the standard library cannot parse (a bad port, a broken
  IPv6 host) is counted as `item_unreadable` and the rest of the poll is read; a wrapper item does not use its link, so it is kept.
  A time that overflows, or has a year outside 1990-2100, is no time (RFC 822 reads "01 Jan 0001", a feed's minimum-date default,
  as 2001, so on the RFC 822 path only the year as written is checked): the item is kept as `seen`. A fraction (`.1234`), a comma
  fraction or a basic `T1234` time is never read as a year, and `00010101T000000+0500` (no standalone year, overflows on conversion)
  is no time rather than an error. This is not an age check; nothing is rejected for its time.
- **Proof:** 75 offline tests on synthetic feeds; mutation plants on every check, the XML scan (declaration list, case, NUL view,
  cap), the parser's refusal order, the link choice, the tracking list, the zone rule, the separator, the key inputs, the fixed
  fields and the reconciliation count each fail a test. Two plants first survived because a test built its input from the constant
  it protected; the numbers are now pinned.

## P2b2 as built (the writer)

- **Code:** `fno/ingestion/news/record/` (`manifest.py`, `writer.py`, `gate.py`, `report.py`, `wiring.py`), `python -m fno news
  promote --from YYYY-MM-DD [--to]` (default `--to` today UTC, the day polls are staged under), and `news-promote.yml`
  (`workflow_dispatch` only, `--from` required, commits only the news manifest and `receipts/raw/news`). Additive changes to P1
  code: `StagingArea.children()` (a listing) and four fixed codes in `news/codes.py`. Tests edited with disclosure: the
  workflow-install count is sixteen and `news-promote.yml` joins `NOT_PACED` (it reaches Drive only, like `data-checks.yml`).
- **One outcome per article:** recorded (new key), no-op (same fixed fields; `first_seen_at` not compared), or revision (same
  key, different fields: the first file stays the record; the version is written once at `news/revisions/<key[:2]>/<key>/<sha8
  of the fixed fields>.json`, so a version seen in many polls is kept once). Two different items sharing a key surface as a
  revision row, never hidden. Order is Drive file, receipt (the `DataStore`), then manifest row; a failed Drive write leaves no row.
- **A stopped run is repaired with the bytes already held**, never new ones (a later poll has a later `first_seen_at`, and
  different bytes at the same path would be a conflict).
- **Reconciliation:** per poll, items = recorded + revisions + no-ops + failed + rejected-by-code; a mismatch is `not_reconciled`.
  Every refusal is a fixed code counted in the one printed line, which is also the alert text (exit 1, #fno-desk): item and poll
  codes, `feed_unknown` (a staged feed id not in the list: kind unknown, stays staged), `record_failed`, `record_conflict`.
  Revisions and no-ops are normal and do not alert. A failed poll stays in Staging and is re-read on every run.
- **Cost, measured by reasoning:** one Drive read per distinct article key per run (an in-run cache), plus one listing per
  feed per day; the manifest is read once per run and appended to.
- **Kinds (judge 48 S2):** each feed id's kind is read over EVERY valid version of the feed list (`kinds_ever_listed`), so a
  feed retired from the newest list keeps its kind and its staged polls stay promotable. An id given two kinds in two versions
  stops the run with `feed_kind_changed`; an unreadable old version is skipped.
- **Round 1 (judge 47):** a revision's own manifest row and receipt are now asserted on the first run (W1: a repair on a later
  poll had masked a missing row); a staged feed unknown to the list is reported only for polls inside `--from`..`--to`, so a
  retired feed stops failing later runs (W2, with S2 above); a revision name collision (same 8 hex characters, other fields) is a
  `record_conflict`, never a no-op.
- **Torn manifest line (judge 47 B):** the manifest is appended through `CsvRowLog`; a file that does not end in a new line
  stops the run before any write with the fixed code `manifest_broken` (the owner trims the torn line by hand; the
  missing-row repair then re-adds it). The load skips and counts rows that are not whole (5 cells, a 64-hex article id and SHA-256, a known status, a numeric size:
  `manifest_row_skipped`, alerted); a torn line is never truncated silently, because it means a crash the owner should see.
  The workflow keeps committing the good rows and receipts when the promotion exits 1 (pinned by a test), then fails the run.
- **Commit guard (follow-up P2b3, criteria of both judges):** the commit step runs `python -m fno news check-manifest <folder>`,
  which uses the loader's own rule (`well_formed`: `check_appendable` plus the per-row checks), never a second copy in YAML.
  It judges the FILE, never promote's exit code: a whole manifest with a mere rejection still commits its good rows. A broken
  one (a promote killed mid-write, for instance out of memory) is **loud**: the command alerts #fno-desk, the torn file is
  discarded from the working tree, the manifest is NOT committed and the step exits 1 (the run is red). **Receipts are still
  committed**: they keep the real evidence time of each Drive file (a receipt rewritten by a later repair would carry the later
  time), and a receipt without its row is harmless. Tested with real git against a bare origin.
- **The workflow also ends with the repo-standard failure alert** (`failure()`, fixed text and the run link), because a killed
  promote cannot alert by itself; a test pins it.
- **Healing is range-bound (runbook):** the rows of a killed run are re-added only by a later promote whose `--from`..`--to`
  covers those days (the idempotent re-promote); a plain daily run does not heal an older gap. The alert says so: "re-run the
  same --from..--to range" for a torn file (`manifest_broken`), and "fix by hand" for a not-whole row in a complete file
  (`manifest_row_skipped`); fixed texts, codes only. A last row that is whole but has no new line is also `manifest_broken`. The owner's schedule should cover recent days.
- **Follow-up, not blocking (judge 48):** `kinds_ever_listed` reads every feed-list version without checking each against the
  hashes in `feed_lists.csv`, so an edited version could change a kind silently. The list is private and write-once, the fetch job
  owns the ledger, and a wrong kind gives a duplicate, not a loss. Decide later whether to harden it.
- **Wiring (judge 48 S1):** `build_news_promotion` itself runs on a recording fake Drive: every write lands under
  `raw/news/articles|revisions`, every read under `staging/news`, `config/feeds` or `raw/news`, and a second process reads the
  Record back (all no-ops); plants that swap the writer, the reader or the gate onto the wrong area fail.
- **Proof:** 48 offline tests; plants that fail a test: the compared fields, the sha8 length, the missing-row repair, the
  file-before-row order, the manifest conflict check, the conflict catch, the unknown-feed check, the poll-reject count, and the
  reconciliation sum. The master privacy test runs a marker headline, host, path and query through the article file, manifest,
  receipts, report line and DEBUG logs, including a refused poll.

## Deferred to the owner's go-live

The first real promotion, the `news-promote` schedule, and the answer on receipt volume. Gates per step: full suite, ruff,
imports, numbers, size (350 lines), record scan, mutation plants for every invariant, two judges.
