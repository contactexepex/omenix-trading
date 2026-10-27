# NP4b: reading the pages (extractors, the read file, the read pass)

Lane 1, two judges (it requests outside pages once dispatched and writes the Record). Plan: [NP4](NP4-page-reads.md) (judge 84).
Built on [NP4a](NP4a-page-fetcher.md) (the guarded fetcher, merged), [NP2c](NP2c-resolve-pass.md) (resolution files) and
[NP2d](NP2d-wrapper-index.md) (the wrapper index). Contract rows Y1 to Y13. **Nothing runs until the owner dispatches the
workflow; it has no schedule.**

## What it does
`python -m fno news read-pages [--apply] [--limit N]` is one pass over the **Record**:
1. newest day first over the last 3 days of the articles manifest, it picks the articles worth a page read: a Google News article
   in the wrapper index that has a resolution file (the page is the resolved URL), or any other article (its own canonical link);
   an unresolved Google News article is not read (`unresolved`), a URL on a host that is not a fetchable listed outlet is not
   requested at all (`unlisted`), and an article already read is skipped (`already`);
2. fetches each page through the NP4a fetcher (allowlist at every hop, global addresses only, robots.txt, 1.5 s apart, a host stops
   on a refusal), at most **80 pages** a run;
3. measures it (`reads/extract.py`): JSON-LD first, OpenGraph/meta as the fallback, both with the already locked `selectolax` (no new
   package; NP4 plan decision 1);
4. with `--apply`, writes `news/reads/<key[:2]>/<key>.json` through the shared write-once writer (file, receipt, `reads.csv` row).
   Without `--apply` it is the probe: it fetches and extracts and writes nothing.

## The read file: facts and hashes, no text
`format` (2 since NP10), `key`, `host`, `access` (`full` for a measured body of 300 or more characters, `partial`, `paywalled`), `extractor`,
`body_chars`, `body_sha256`, `published_at`, `modified_at`, up to 5 `authors`, `provider`, `summary_extract` (NP10). **No article body and no HTML; the page snippet of NP10
(owner decision E1 = YES, 28 Oct 2026) is the only page text**: `to_bytes` refuses a file over 6,000 bytes (Y10). The
body is measured and dropped (the snippet is the first three sentences, 600 characters at most); the strings kept are single-line and capped. The cost, said plainly (reasoning only): NP5's
wire-agency detection can use only the byline, the JSON-LD provider and the outlet, not a dateline in the first sentences.

## Bounds and alerts
- **Run budget** (judge 88): the clock is checked before every page; past `BUDGET_SECONDS` (900) the rest are counted as
  `budget_stopped` and alerted (Y5). The fetcher's 20 s timeout is per read, so this is what keeps the job inside its limit.
- At most 400 Record files read to choose the pages (`unexamined`, alerted, Y6).
- **A reader that gets nothing is loud** (the lesson of NP2c's judge 82): nothing read of three or more pages, or under half of ten or
  more, is red and alerted (Y8). Pages an outlet asks us not to read (`robots_disallowed`, `host_stopped`, `host_not_allowed`) are not
  faults. One or two failures are not a failing reader.
- A page with no facts, or a refused one, writes nothing and is tried again on the next pass until it leaves the look-back.

## Round 2 (judge 89)
- **One hostile page cannot stop the run (F1, Y14):** a JSON-LD nested 200,000 deep raised `RecursionError`, which escaped and made
  the same page come first again for three days. Each block is skipped on any parse failure and any extractor failure is counted
  (`extract_error`) while the run goes on.
- **A total deadline per fetch (F2, Y15, Y16):** the library's timeout is per read, so a server that drips 12 bytes every 0.5 s held a
  1-second timeout for 6 s and could hold a fetch until the job was killed. The fetcher now owns a deadline for hops, robots.txt and the body
  together (`fetch(url, seconds)`, at most 60 s, and the pass hands each fetch what the run has left); the body is read with `read1`, which
  returns what has arrived, so the deadline is checked between drips; a fetch that runs out stops its host. Not covered: the
  name lookup itself, which the system bounds.
- Names in a three-byte script now fit (the file is UTF-8, 4,000 bytes, Y18); `news` command start-up no longer imports the HTML parser
  (`reads/limits.py`); the list-depth limit is tested (Y17).

## Said plainly
- Whether a GitHub runner can read these outlets is unmeasured; run `news-probe-outlets` first (NP4a). Until it is dispatched, no
  page has been requested.
- JSON-LD coverage on the outlets omenix reads is unmeasured (agentic's mix: 70% JSON-LD, reasoning only for this one).
- `full` means the page's JSON-LD carried a long body; a page without JSON-LD body text is `partial` however long it is.
- The pass does not choose "material" headlines (NP5 does); until then it is newest first.
