# Judge 88: NP4a page fetcher (code), round 1 at 3f56dbc: PASS

**Lane 1 (the first code that requests outside sites' pages; it widens the shared allowlist rule); judge #1.** Branch `story/NP4a-page-fetcher`, frozen SHA 3f56dbc. Reviewed `git diff origin/main...3f56dbc`: `news/pages/*` (380 lines), `SourceRules.may_fetch`, `news-probe-outlets.yml`, rows H1 to H11.

## Gates (locked venv; strong evidence)
1721 passed; ruff is clean; contract plants all `ok`.

## The attack points (strong evidence unless marked)
- **Host gate at every hop.** Redirects are followed by hand (at most 5), and every hop goes back through `_admit`:
  - https only, no userinfo, no port, a plain host;
  - `may_fetch`;
  - the per-host stop;
  - the address check;
  - robots.txt.
- A hop that leaves the rules is `redirect_refused`. A robots.txt fetch may not change host.
- **`may_fetch`** now requires every listed ancestor and the alias's main domain to allow fetching.
- **Plants (each one undone; all fail tests):**

| Plant | Result |
|---|---|
| address check removed | 3 failed |
| host not stopped on 401/403/429/503 | 8 failed |
| no size cap | 3 failed |
| no spacing | 2 failed |
| robots.txt may change host | 1 failed |
| multicast allowed | 3 failed |
| `may_fetch` checks the nearest listed outlet only | 7 failed |
| port allowed | 2 failed |

- **Address check (`is_reachable`), probed with 21 addresses on Python 3.13, the version CI uses.**
  - Refused, correctly: loopback v4 and v6, RFC 1918, CGNAT, NAT64, IPv4-mapped 127/8, 6to4 of 127/8 and 10/8, Teredo, 0.0.0.0, broadcast, 198.18/15, 240/4, 192.0.0/24, link-local (the runner's 169.254 metadata range included), ULA, multicast, 2001:db8::/32.
  - **Accepted, and should not be (minor; reasoning only on reachability):**
    - IPv4-compatible `::127.0.0.1` and `::a00:1` (`::/96`). That is the same "an embedded IPv4 we cannot vouch for" reason NAT64 is refused for.
    - Deprecated site-local `fec0::1`.
    - ORCHIDv2 `2001:20::1`.
  - Modern Linux does not route these, and every name is a listed public outlet, so this is not blocking. Refuse `::/96`, `fec0::/10` and `2001:20::/28` for consistency, with tests.
- **The decoded-byte cap.** The lock pins urllib3 2.8.0, whose `read(amt)` returns at most `amt` decoded bytes, so `iter_content(65536)` stops a gzip bomb at the cap. The implementer's real requests-plus-gzip test confirms it.
- **Pacing and stop.** `RequestSpacer` is reused across hosts and robots.txt requests. A 401, 403, 429 or 503 stops that host for the run.
- **Output.** Codes only; `Page.__repr__` hides the URL and the body. The probe prints a domain and a fixed code, which is acceptable because the allowlist is public (owner decision H aside).
- **The workflow.** Dispatch only; `contents: read`; no secret; no commit; `timeout-minutes: 30`.
- **The refusing-outlet probe** (`--include-refusing`) is opt-in: one GET each, through every guard except the `fetch` flag. That is the NP0 2d / NP4 plan re-probe (judge 84 PASS); it sends one request and evades nothing.

## Notes (not blocking)
- **No total time per page.** `timeout=20` bounds each socket read, not the page. A trickling server could hold one page for a long time. Only the workflow's 30 minutes bounds the probe. NP4b's read pass needs a wall-clock budget (the plan's 900 s per run).
- **DNS time-of-check-to-time-of-use** (the name could resolve differently between the check and the connection) is stated in the docstring as a known gap. It is acceptable for listed public outlets and GET only.
- `requests.Session` honours proxy variables from the environment (`trust_env`). That is harmless on runners; say so, or set `trust_env = False`.

## Hard lines
No order path, no secret, no Groww call, nothing requested until the owner dispatches the probe, nothing committed by the workflow.

## Verdict: PASS round 1 at 3f56dbc. The address refinements and NP4b's per-run time budget are requested.
