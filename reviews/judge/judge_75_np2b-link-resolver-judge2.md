# Judge 75: NP2b link resolver (code, lane 1), judge #2 of 2

Frozen SHA `3cc0c62` (branch `story/NP2b-link-resolver`; NP1 and NP2a are on main). I read the story first, then
reviewed `git diff origin/main 3cc0c62`:
- `fno/ingestion/news/resolve/*`;
- the lock and requirements changes;
- the tests, rows L1-L7 and their plants.

I also read the library itself: the `googlenewsdecoder==0.2.1` wheel was downloaded, its SHA-256 matched the lock's
second hash (`a7adec...497a`), and it was unpacked and read, never imported from its own folder. I judged this
independently of judge #1.

**Gates:** this checkout has no httpx, so `tests/ingestion/news/resolve/test_adapter.py` fails to collect here. In a
scratch venv built from `requirements.lock` with `--require-hashes --only-binary=:all:`, everything installed and
**1437 passed**. ruff check and format are clean; imports clean (524 files); code size passed; contract plants all ok
in that venv.

**My plants (6 of 6 killed):**

| Plant | Tests failed |
|---|---|
| hook allows any host | 5 |
| hook not installed | 1 |
| links not checked before sending | 2 |
| `accept` keeps the service's own links | 4 |
| no interval floor | 2 |
| guard built from every feed kind | 3 |

## What reaches the network (your first ask): no host off the allowed domain

- **Every request the library makes goes through `self.client`.** The page GET (manual hops, `follow_redirects=False`)
  and the batch POST (`follow_redirects=True`) both use it (`decoder.py:75,95`). httpx 0.28.1 runs the request hooks
  at the top of every redirect iteration, before `_send_single_request` (I read `Client._send_handling_redirects`).
  So `egress_hook` sees every hop.
- **The hook with real `httpx.Request`s refuses:**
  - a look-alike suffix (`news.example.com.evil.test`), another host, `http:` and `wss:`;
  - punycode (the decoded host is non-ASCII), `[::1]` and `127.0.0.1`.
- **`allows_link` refuses:** a protocol-relative link, a line break in the host, a zero-width character, userinfo and
  `:443`.
- **An empty guard allows nothing.**

## Findings

1. **F1 (must fix): the pacing floor does not hold when the service pushes back.**
   - `googlenewsdecoder` sleeps `interval` only after a *successful* page request. On a failed one it `continue`s
     before the sleep (`decoder.py:147-155`).
   - Reproduced with the real `GoogleDecoder` on a `MockTransport` that answers 503: 10 links gave **10 page requests
     and zero sleeps**.
   - So in a block, rate limit or changed protocol, the adapter sends its requests back-to-back. That is the moment
     the floor exists for, and it breaks the adapter's own rule "at least `interval_seconds` between page requests"
     (`decoder_adapter.py:79`) and the plan's floor.
   - Fix: enforce the spacing on our side. For example, a request hook that waits until `interval` has passed since
     the previous request, or one link per `decode_google_news_urls` call with our own sleep (each call then makes its
     own POST, so that costs the batching). Add a test with a failing transport and a plant.
2. **F2 (must fix, text): "the exact checked string is sent" is not what happens.**
   - The library does not send our link. `article_id` takes the last path segment, and `params_page_url` builds its
     own `https://<the service host>/rss/articles/<id>?hl=&gl=&ceid=` from a host fixed in `_parse.py`, copying
     `hl`, `gl` and `ceid` from our link. It POSTs to a fixed batch URL.
   - The adapter comment (`decoder_adapter.py:133`) and the story's "Defence in depth" say the exact checked string is
     what is sent. The real protection is the hook, which holds, plus the library's own host check on hops
     (`next_google_hop`).
   - Correct the wording. Say also that the library itself only ever addresses one fixed host, which narrows the
     egress beyond our guard.

## Should fix (not blocking)

- **The hook checks scheme and host only.** `https://news.example.com:8443/` and `https://evil.test\@news.example.com/`
  pass, which means another port, or a username sent, on the allowed host. Egress stays on the domain, but
  `clean_https_link` already refuses both. Refusing `request.url.port not in (None, 443)` and userinfo in the hook
  would make the two layers agree.
- **The allowed domain is the whole registrable domain** of the wrapper feed. That includes user-content subdomains of
  the service's parent company. The POST follows redirects, so a hop there would be allowed. Consider allowing only
  the wrapper feed's own host plus the hosts the library is known to use. Reasoning only: the redirects seen in
  agentic's data stay on one host.

## Supply chain (your third ask)

- `requirements.lock` adds exactly the stated pins, all with hashes: googlenewsdecoder 0.2.1, selectolax 0.4.13,
  httpx 0.28.1, httpcore 1.0.9, h11 0.16.0, h2 4.4.1, hpack 4.2.0, hyperframe 6.1.0, anyio 4.15.1, socksio 1.0.0 and
  typing-extensions 4.16.0. The only other change is two "via" comments. `requirements-groww.lock` adds the same set.
- **The library itself:** about 600 lines in four files. Its imports are `httpx`, `selectolax` and the standard
  library. It does no file, subprocess or `eval` work, and the async module is unused.
- **Two cautions:**
  - `socksio`, and `proxy=` support, mean that a `*_PROXY` environment variable would route through a proxy
    (`trust_env`). The runners set none.
  - The library's own messages quote the URL. The adapter never keeps them, as stated.
- `tests/test_pinned_installs.py` passes in the venv.

**Verdict: FAIL** (round 1, `3cc0c62`). F1 is a real pacing defect against a third party's unofficial endpoint; F2 is a
wrong statement about what is sent.
