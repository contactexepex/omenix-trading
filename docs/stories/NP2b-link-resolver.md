# NP2b: the link resolver (BUILT, awaiting two judges; stacked on NP2a)

Lane 1, **two judges** (an outside service, a new dependency, requests to a third party). Plan: [NP0](NP0-news-port-plan.md) section 2b.
Owner answers (27 Oct 2026, relayed by the orchestrator): **B** following and decoding news links is permitted under the carried-over
rules; **C** use a ready-made library if suitable, behind the interface. This story writes **nothing** (the resolution file and the
pass are NP2c) and is called by nothing yet; it is dispatch-free code plus its tests.

## What it adds
- `fno/ingestion/news/resolve/`: `model.py` (`LinkResolver`, `Resolved`, five fixed codes), `guard.py` (`EgressGuard`,
  `guard_from_feeds`), `accept.py`, `decoder_adapter.py` (`GoogleNewsDecoderResolver`, `egress_hook`), `wiring.py` (the composition
  root: `build_link_resolver(feeds)`). 191 lines in all.
- Dependencies, hash-locked by `ops/relock.sh` (uv 0.11.32, as SEC1 requires): `googlenewsdecoder==0.2.1` and `selectolax>=0.4.12,<1.0`;
  the lock gained httpx 0.28.1 with h2, hpack, hyperframe, httpcore, h11, anyio, socksio and typing-extensions. Only the "via" comments
  of two existing entries changed.
- Contract rows **L1 to L6**, plants run; 57 offline tests (a fake library, and a REAL `httpx.Client` on a mock transport for the hook).

## Vetting of the library (owner: "use it if suitable")
- Maintained: releases through 18 Oct 2026 (0.2.2); I pin 0.2.1 (20 Sep 2026), the version agentic uses on real data (14 failures in 1,533
  reads there, strong evidence). 0.2.2 is nine days old; a bump is a separate, reviewed change.
- Small: about 600 lines in four files; I read `decoder.py` and the imports. It does one page request per link (to get a signature),
  then one POST per batch of ten to a "batchexecute" endpoint. **It drives an unofficial endpoint of the news service**, so it can break
  without notice; the mitigation is the interface plus a fixed code per link, and a one-class swap for our own adapter.
- Dependencies are the widely used httpx family plus `selectolax` (a C extension with wheels for 3.13). `selectolax` 1.0 removed the
  module the library imports, hence `<1.0`.
- It follows redirects itself, so a request hook on its client is the only place that sees every hop (`egress_hook`).

## Decisions and why
- **No news-service host name in the code (the orchestrator's decision (a)).** The allowed domain is the registrable domain of each
  wrapper-kind feed in the private feed list, read at run time (`guard_from_feeds`), so `tests/ingestion/news/test_privacy.py` stays
  untouched. A guard built from no wrapper feed allows nothing.
- **Defence in depth:** the link is checked (`clean_https_link` plus the allowed domain) before anything is requested, the exact
  checked string is what is sent, the hook refuses everything else at every hop, and the result is kept only through `accept`.
- **Fixed codes, never messages:** the library's messages can quote the link; `decode_failed`, `bad_result`, `refused_link`, `error`,
  `resolved` are all a caller sees. An exception from the library costs only its batch of ten (`error`); the caller (NP2c) counts codes
  and must alert when `error` or `decode_failed` dominates (the S1b rule: undecidable is loud).
- **Pacing:** the library sleeps a whole number of seconds after each page request; the floor is 2 s (the plan's floor is 1.5 s).
  Spacing between batches and the 80-per-pass cap belong to the pass (NP2c).

## What is NOT established (said plainly)
- Whether the endpoint works from a GitHub runner today: not probed. A read-only probe command is NP2c's first step, so the first real
  call is a counts-only line, not a surprise.
- I have not read the library's `_parse.py` line by line; the tests use a fake for it. Reasoning only: it is parsing, not network.
- `registrable_domain` is "last two labels, three when those are a public suffix" with the curated suffix list of NP1, not the full
  Public Suffix List.

## Judges: please try to break
1. A link or redirect hop that reaches a host off the allowed domains (try encodings, a line break inside the host, a port, userinfo, a
   look-alike such as `<domain>.evil.example`, a protocol-relative link).
2. A result that is kept but should not be. 3. Anything in the dependency change beyond the pins listed above.
