# NP4a: the page fetcher and the outlet probe

Lane 1, two judges (it makes requests to outside sites once dispatched, and widens the shared allowlist rule). Plan:
[NP4](NP4-page-reads.md) (passed by judge 84, with F1 and F2 now built). Contract rows H1 to H11. It stores nothing and
writes no Record file; NP4b adds extraction and the read file. **Nothing runs until the owner dispatches the probe workflow;
no workflow calls the fetcher yet.**

## What it is
- `HttpsPageFetcher` (`pages/fetcher.py`), behind `PageFetcher`. Every request and every redirect hop (by hand, at most 5) must be:
  plain https (no credentials, no port); a listed outlet that allows automated reads; a host not stopped earlier in the run;
  allowed by robots.txt; resolving only to global addresses. Then at least 1.5 s since any earlier page request (NP2b's
  `RequestSpacer`, reused), one polite User-Agent, no cookies, TLS verification on, 20 s timeout, 4 MB of **decoded** bytes, html or
  xhtml only. A 401, 403, 429 or 503 stops that host for the run. Every outcome is a fixed code; a `Page` never prints its URL or body.
- **The allowlist rule is stricter (judge 84 F1)**: `SourceRules.may_fetch` now needs every listed domain a host sits under to
  allow it. A listed child of a `fetch: false` outlet was fetchable before; the 112 shipped entries are unchanged by the new rule
  (a test pins the 101 fetchable and 11 refusing).
- **Addresses (judge 84 F2)**: every address the name resolves to must be `is_global`, at every hop, robots.txt included. Also
  refused: IPv4-mapped IPv6 with a non-global IPv4, NAT64, IPv4-compatible `::/96`, site-local `fec0::/10`, ORCHIDv2 `2001:20::/28` (judge 88) and multicast (Python calls multicast ranges global; the test found it).
- **robots.txt** is honoured (owner's default): fetched through the same method, once per host per run; absent or a client error means no
  restriction; a server error, a network failure, a redirect to another host or an oversized file means the host's pages are not
  read this run; a refusal stops the host.
- **`news probe-outlets [--include-refusing]`** and the dispatch-only, read-only, secret-free workflow `news-probe-outlets.yml`: one
  front-page request per listed outlet (101 fetchable; 11 refusing ones only when asked). It prints a counts line and one
  `domain: code` line per outlet into the run log; the allowlist is public. It edits nothing: the owner reads the result first.

## Said plainly
- The address check and the connection are two steps; a name could change its answer between them. The names are the listed
  public outlets and only GET is sent; connection pinning is not built (reasoning only).
- Whether a GitHub runner reaches these outlets is unmeasured until the owner dispatches the probe.
- `--include-refusing` sends one polite request to outlets whose operators were found to refuse bots from agentic's network. It is
  a one-time report for the owner, still through robots.txt and every other guard; no job changes the allowlist.
- robots.txt is part of the fetcher, so a probe also reads each outlet's robots.txt: about 2 requests per outlet at 1.5 s apart, about
  5 minutes for the fetchable set.
- **No per-page wall-clock limit here** (judge 88): the 20 s timeout is per read. The run-wide time budget belongs to the caller; NP4b's
  read pass must cap its total fetch time (the plan's 900 s) and pin it with a plant. The session ignores proxy settings in the
  environment (`trust_env` off, H16), so no hop can bypass the guards.
