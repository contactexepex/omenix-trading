# NP4: reading the article pages of listed outlets (PLAN)

PLAN for the orchestrator's check and one judge before any code. Lane 1 for the code that follows (it requests pages from outside
sites and writes the Record). Plan: [NP0](NP0-news-port-plan.md) sections 2d and 2e, amended below where measuring the dependency
changed the answer. Not built; nothing is requested.

## What NP4 is for
The feed gives a headline and a snippet. A page read adds what the dashboard and the later steps (NP5 wire detection, NP6
clustering) need and the feed does not carry: whether the page is free or paywalled, its real publication and modification time,
its byline and provider, and a content hash. **No article body and no HTML is ever stored** (NP0 section 2e).

## Decisions I am making, with reasons (the judge should overrule what is wrong)
1. **No new dependency in NP4a and NP4b: JSON-LD and OpenGraph/meta only, parsed with `selectolax`, which NP2b already
   hash-locked.** NP0 planned `trafilatura` as well. I measured its cost: a dry install adds **15 packages** over our
   locked set (babel, courlan, dateparser, htmldate, jusText, lxml, lxml_html_clean, python-dateutil, pytz, regex, six, tld, tzdata, tzlocal,
   trafilatura; counted with a dry install into a clean environment: 46 packages against 31 without it. judge 84 found my first count of 11 was short) to a public repo's supply chain. Agentic's own
   numbers (NP0 section 0, strong evidence): JSON-LD produced the text in 422 of about 600 reads (70%), trafilatura in 92 (15%), the
   description of a paywalled page in 82 (14%). Since NP4 stores no body, the main use of trafilatura (body text for key sentences) is
   not needed to store any fact above; **trafilatura becomes an optional NP4c** that the owner can ask for after seeing the real
   JSON-LD coverage. (Reasoning plus the agentic counts.)
2. **Split in two stories.** NP4a: `PageFetcher` and the outlet probe (requests, no parsing). NP4b: extractors, the read file, the
   read pass and its dispatch-only workflow. NP4a alone makes the first outside request, so it goes through the judges before
   anything can parse a page.
3. **The read file stores facts and hashes, no text** (decision 4 of NP0 asked whether to keep up to three key sentences of at most 40
   words, as agentic does). I recommend building without them first: they are the only article-derived text and the only
   copyright question. The cost (reasoning only): NP5's wire-agency detection also reads a dateline or attribution in the lede
   ("(Reuters) -"); without the lede it can use only the byline, the JSON-LD provider and the outlet. I will measure how many of the
   wire stories that loses once real reads exist, then the owner decides. **Owner decision wanted, not blocking NP4a.**
4. **robots.txt.** NP0 does not mention it, and agentic did not read it (I checked its fetch code: allowlist, redirects, 4 MB,
   20 s). I propose honouring it, **fetched through the same `PageFetcher`** (same guards, spacer and per-host stop, cached for the
   run; a redirect to another host makes it unreadable): one extra request per host per run, a `Disallow` for our User-Agent or `*` on the path means that page
   is not read (code `robots_disallowed`), an unreadable robots.txt means not read this run. That is the polite reading of
   "respect bot protection" and costs about one request a host. **Owner decision wanted; default: honour it.**

## NP4a: the page fetcher and the outlet probe
- `PageFetcher.fetch(url) -> Page(code, final_url, content_type, body)` (interface); adapter `HttpsPageFetcher` over `requests`.
  Built from the **public** allowlist (`SourceRules`): a host is fetched only when `may_fetch(host)`.
  **Correction (judge 84 F1): NP1 does not do what I wrote.** `may_fetch` looks at the nearest listed entry only, so a
  separately listed child of a `fetch: false` outlet (reproduced: `a.example.com` false, `in.a.example.com` listed true) is fetchable
  today. NP4a changes `may_fetch` to walk every listed ancestor: a host is fetchable only if its nearest entry is `fetch: true` AND
  no listed ancestor (alias included) is `fetch: false`. A row and a plant pin it (a listed child of a `fetch: false` parent is
  never fetched); the 112 shipped entries are checked against the new rule in a test and the owner sees any outlet it changes.
- Every request and **every redirect hop** (followed by hand, at most 5): https only; no credentials, no port; host passes
  `may_fetch`; otherwise the read stops with `redirect_refused`. Never a hop to an unlisted host (agentic's rule, ported).
- Resolve the host first and connect only if **every** resolved address (IPv4 and IPv6) is `is_global` (`blocked_address`),
  at every hop (judge 84 F2: a plain private/reserved test lets carrier-grade NAT `100.64.0.0/10` through; I measured
  `100.64.0.1` as `is_private False`, `is_reserved False`, `is_global False`). Also refused: IPv4-mapped IPv6 whose IPv4 is not global,
  and the NAT64 range `64:ff9b::/96` (Python calls it global, but it embeds an IPv4 address we cannot vouch for). Plant: a redirect
  that resolves to `100.64.x.x` is refused. A check-then-connect gap remains (a name could change its answer between the check and
  the connection). Pinning the connection to the checked address would close it but needs a custom adapter that keeps SNI and
  certificate checks; I do not build that now: the names are the 112 public outlets and we send only a GET (reasoning only), and I
  will do it if a judge shows a realistic path.
- Limits: 4 MB of **decoded** bytes (streamed and counted after decompression, so a small gzip bomb is `too_large` too; nothing kept), 20 s timeout, `Content-Type` html or xhtml only, one polite
  User-Agent that says who we are, TLS verification always on, no cookies kept, `Accept-Encoding` as `requests` sends it.
- **Pacing:** at least 1.5 s between ANY two page requests across hosts (NP2b's `RequestSpacer`, reused, not copied) and a per-host
  stop for the run: a 401, 403, 429, 503 or a challenge page stops that host for the run (the outlet is not retried), others go on.
- **The outlet probe** `news probe-outlets`: one GET of the front page of each fetchable listed outlet (and, only with `--include-refusing`, once each of the outlets marked `fetch: false`), counts and per-outlet
  outcome (the allowlist is public, so naming an outlet is not private; no URL beyond the host, no page content). Dispatch-only
  workflow, run once by the owner **from a GitHub runner**, because agentic's `fetch: false` list was measured from another network
  (NP0 2d). Its result goes to the owner before any outlet is changed; the allowlist file is never edited by a job.

## NP4b: extraction and the read file
- `Extractor` strategy; `JsonLdExtractor` (schema.org `NewsArticle`/`Article`: `datePublished`, `dateModified`, `author`,
  `publisher`, `isAccessibleForFree`, `articleBody` length and hash) and `MetaExtractor` (OpenGraph/`article:` and `description`
  for a paywalled page). Page text is untrusted: parsed, measured, discarded; no `eval`, no template, no shell, no network in a parser.
- **Read file** `news/reads/<key[:2]>/<key>.json`, write-once through `WriteOnceWriter` (NP2c), receipt and `reads.csv`: final host,
  access outcome (`full`, `partial`, `paywalled`, `blocked`, `failed`), extractor, body characters, body SHA-256, published and
  modified times, byline names, provider, and the fetch code. Facts only; a size cap in the writer and a plant make "no body stored" a
  test, not a promise.
- **Which articles:** from the resolution files (NP2c) and publisher items' own links, host on the allowlist with `fetch: true`,
  newest first, at most 80 pages and 900 s per run, the NP2c pattern (3-day look-back, a read cap, counts-only line, `expiring`).
  Until NP5 exists there is no "material" priority; newest first. Dispatch-only workflow, `apply` input default false.

## What I cannot promise (said plainly)
- Whether GitHub runners reach the outlets agentic reached is unmeasured (that is the probe). Evidence from another network says
  125 of about 1,500 reads were blocked (8%, strong evidence for that network only).
- JSON-LD coverage on omenix's outlets is unmeasured; 70% is agentic's number on its own mix.
- Half of agentic's material headlines came from outlets not on the allowlist (`skipped_unlisted` 793 of about 1,500): those get a
  tier from the host but no page read, by design.
- Paywalled pages give only their description; the dashboard shows what the feed gave.
- Tests use synthetic pages and a fake transport; no real outlet is requested by a test.

## Rows and tests promised
Contract rows for: allowlist-only at every hop; private-address refusal; size and type caps; 1.5 s across hosts; per-host stop;
redirects by hand; no body stored; write-once read file; dispatch-only workflows; probe is read-only. Each with a plant.

| # | Story | Lines (est.) |
|---|---|---|
| NP4a | `PageFetcher`, guard, pacing, `news probe-outlets`, workflow | ~350 |
| NP4b | extractors, read file, read pass, workflow | ~400 |
| NP4c | `TrafilaturaExtractor` (optional, owner's call, 15 packages) | ~150 |
