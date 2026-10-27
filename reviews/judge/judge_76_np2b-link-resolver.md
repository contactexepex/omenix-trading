# Judge 76: NP2b link resolver (code), round 1 at 3cc0c62: FAIL

**Lane 1, two judges; this is judge #1.** Branch `story/NP2b-link-resolver`, frozen SHA 3cc0c62. Reviewed `git diff origin/main...3cc0c62`: `fno/ingestion/news/resolve/` (199 lines), the locks, tests, contract rows L1 to L7.

**Disclosure.** I first wrote a PASS. My commit was refused by the record scan: a test link with a userinfo part looked like an e-mail address, and the scan sent its alert to #fno-desk, so this was a false positive and the value was never committed. In that time judge #2's FAIL (judge 75) landed on `main`. I did not adopt its finding blindly. I re-read the library source and confirmed it myself (B1 below). I had missed it in my first read.

## Gates (strong evidence)
- **Default environment:** ruff and check_imports are clean, but the resolve tests fail to collect (`httpx` is not installed), and contract plants L5 and L6 report "tests fail without the plant".
- **Locked environment:** in a fresh venv built with `pip install --require-hashes --only-binary=:all: -r requirements.lock`, as CI does, **1437 passed** and the contract plants are all `ok`.
- The story must say that the gates need the lock reinstalled first.

## B1 (required; strong evidence, read in the library at the locked hash): a failed page request is not paced
- I downloaded `googlenewsdecoder-0.2.1-py3-none-any.whl`, whose SHA-256 `a7adecb3…` equals the lock, and read it as data.
- In `decoder.py`, `decode_google_news_urls` does this when a page request fails:

  ```python
  params = self.get_decoding_params(art_id, source_url)
  if not params["success"]:
      results[i] = params
      continue                      # <- skips the sleep below
  ...
  if interval:
      time.sleep(interval)
  ```

- So the 2-second floor only applies after a **successful** page request. A failed one (each can follow up to 3 hops on the service host) goes straight to the next link.
- The adapter opens a new decoder per batch of ten, so after a failed batch the next one starts at once.
- **The worst case is the realistic one.** When the service is blocking us (429 or its "sorry" page), every link fails, and the resolver sends about 10 × 3 page requests per batch with no pause, batch after batch.
- That breaks NP0 section 2b (at least 1.5 s between requests to the service) and its polite-stop rule.
- **The adapter has no stop on a refusal either.** A 429 is just `decode_failed`, and the run goes on to the next links and batches. NP0 2a/2b and P2 say a refusal stops the host (`SourceCoolingOff`).
- **Fix (one way):**
  - enforce the spacing in our own request hook, sleeping until at least the interval has passed since the previous request, so every request is paced (GET, redirect hop and POST), whatever the library does;
  - stop the whole run on a 429 or a redirect to the "sorry" page, seen in a response hook.
  - Pin both with the mock-transport tests and plants.

## What holds (strong evidence)
- **One client.** The library sends every request through one `httpx.Client` (`self.client`), so the request hook sees all of them. I checked that httpx 0.28.1 fires the request hook on a redirect hop: a mock POST that redirected off the allowed host was refused at the hop, and only the allowed host was contacted.
- **Attacks on `EgressGuard(["svc.example"]).allows_link`, all refused:**
  - a look-alike host with the allowed name as a left-hand label;
  - a suffix match without the dot (`evilsvc.example`);
  - a protocol-relative link;
  - a userinfo part in front of an off-domain host;
  - a port;
  - `%2e` in the host;
  - line breaks, U+200B and non-ASCII.
  - Upper case is allowed, correctly.
- **My plants (locked venv, each one undone; all fail tests):**

| Plant | Result |
|---|---|
| hook not installed | 1 failed |
| hook allows http | 1 failed |
| a result on the service's own domain kept | 3 failed |
| non-ASCII link allowed | 2 failed |
| suffix match without the dot | 1 failed |
| interval floor removed | 1 failed |
| publisher feeds added to the allowed domains | 2 failed |

- **Dependencies:** `requirements.lock` only gains anyio, googlenewsdecoder, h11, h2, hpack, httpcore, httpx, hyperframe, selectolax, socksio and typing-extensions. No existing pin changed. `requirements-groww.lock` gains the same set, because it is compiled from `requirements.txt` too (`ops/relock.sh:37`).

## Also required (text)
- "The exact checked string is what is sent" is untrue. The library extracts the article id and requests its own fixed URLs on the service host (`RSS_ARTICLE_URL`, `BATCHEXECUTE_URL` in `_parse.py`), copying only `hl`, `gl` and `ceid` from our query.
- The hook is the real control, and the pre-check is defence in depth. Say so.

## Hard lines
No order path, no secret, no Groww call, no write; nothing calls this code yet. Politeness to an outside service is a carried-over rule, and B1 breaks it.

## Verdict: FAIL round 1 at 3cc0c62. B1 (pace every request and stop on a refusal) and the docstring correction are required.

## Addendum 1: round 2 at 356b149: PASS

Reviewed `git diff 3cc0c62 356b149`. The lock is unchanged. Gates were run in a fresh venv installed from `requirements.lock`.

**Gates (strong evidence).** 1454 passed; ruff and check_imports are clean; contract plants all `ok`, L1 to L12.

**B1 fixed (strong evidence).**
- **Pacing.** `RequestSpacer` is a request hook on the library's one client, so every request waits at least 1.5 s after the previous one, a failed one included. The library's own wait is off (`interval=None`). With a fake clock, four requests gave three sleeps of 1.5 s.
- **The stop.** `PushbackStop` (a response hook) plus `stopped_hook` (a request hook) stop the run at the first 429, 503 or "sorry" page, and every later batch returns `paused` without starting a decoder.
- **Checked on httpx 0.28.1:** the response hook fires on a **redirect response**. A POST that redirected to the "sorry" path set the stop, and the sorry hop itself was never requested (only the first path was contacted).
- **Plants (each one undone; all fail tests):**

| Plant | Result |
|---|---|
| pacer not hooked | 2 failed |
| stop not observed | 4 failed |
| stopped hook removed | 4 failed |
| 503 not a stop | 2 failed |
| sorry only via the location header | 1 failed |
| no early pause per batch | 1 failed |
| hook ignores userinfo and port | 2 failed |
| library interval set to 0 | 1 failed |
| 1.5 s floor removed | 1 failed |

**Docstring fixed.** It now states that the library requests only its own fixed URLs and that the hooks are the real controls.

**Notes (not blocking).**
- 403 is not a stop. `PUSHBACK_STATUSES = (429, 503)` follows NP0's list for this service, but omenix's own refusal set is `(403, 429)` (`nse_pacer.REFUSAL_STATUS_CODES`). Requests are now paced, so a run of 403s cannot hammer the service; adding 403 would match P2's rule. I recommend it.
- "One instance is one run." `build_link_resolver` makes a new resolver on every call. NP2c must build it once per run, or the stop and the pacer reset between calls. Pin that in NP2c.
- An explicit `:443` is normalised away by httpx before the hook sees it, as the story says. `clean_https_link` already refuses it before the link is handed over.

**Verdict: PASS round 2 at 356b149.**
