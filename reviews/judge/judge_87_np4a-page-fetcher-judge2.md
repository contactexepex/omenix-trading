# Judge 87: NP4a page fetcher and outlet probe (code, lane 1), judge #2

Frozen SHA `3f56dbc` (branch `story/NP4a-page-fetcher`). The branch is older than main, which now has NP2d merged.
`git diff origin/main` therefore shows NP2d's lines as removed, so I reviewed `git diff $(merge-base) 3f56dbc`:
- `news/pages/{address,fetcher,robots,probe,model,cli,wiring}.py`;
- `sources/rules.py` (`may_fetch`);
- `news-probe-outlets.yml`;
- the tests, rows H1-H11 and their plants.

**Gates** (in the venv from `requirements.lock`, `--require-hashes`): 1721 passed; ruff clean; imports clean (571 files);
code size passed; contract plants all ok.

**My plants (8 of 8 killed):**

| Plant | Tests failed |
|---|---|
| address check off at a hop | 3 |
| multicast allowed | 4 |
| NAT64 allowed | 3 |
| robots.txt allowed to hop to another host | 1 |
| no host stop | 9 |
| `allow_redirects=True` | 1 |
| `may_fetch` reads only the nearest entry | 8 |
| robots verdict ignored | 11 |

## My plan findings, built

- **F1 (judge 84), the inheritance rule:** `may_fetch` now requires every listed suffix, and each one's alias, to allow
  fetching (`rules.py:69-77`). My reproduction, a listed `in.a.example.com` under an `a.example.com` with
  `fetch: false`, now gives **False**, and a sibling stays True. The shipped list is unchanged: 101 of 112 fetchable.
- **F2 (judge 84), the address rule:** `is_reachable` refuses `100.64.0.1`, `64:ff9b::7f00:1`, `::ffff:10.0.0.1`,
  `224.0.0.1`, `ff0e::1`, `::1`, `0.0.0.0` and `192.0.0.8`, and allows `8.8.8.8` and `2001:4860:4860::8888`.
  `all_global` asks this of **every** resolved address, and `_admit` runs it at **every** hop. The extra multicast
  refusal is right: Python calls some multicast ranges global.
- **Should-fixes:**
  - the 4 MB cap counts decoded bytes (`iter_content`);
  - robots.txt is read through the same `_follow`, with every guard, the spacer and the stop;
  - robots.txt is cached per host;
  - a cross-host robots redirect counts as unreadable (plant killed);
  - the robots token `fno-desk` matches the product token in our User-Agent.
- **The connection-pinning gap** is stated in the fetcher's docstring (lines 15-17), not built, as agreed.

## The other points asked

- **`news-probe-outlets.yml`:** dispatch-only, `contents: read`, no secrets in its environment, writes nothing, commits
  nothing. Hash-locked install.
- **`--include-refusing`** also asks the `fetch: false` outlets, once each, still through robots.txt and every other
  guard. That matches the allowlist header ("NP4 re-probes every listed domain"). The NP4 plan said "each fetchable
  listed outlet"; align its wording.
- **`NOT_PACED` gains the probe workflow: correct.** The probe uses the fetcher's own `RequestSpacer`, not the shared
  NSE pacer or its pause log. **21 to 22 installs: correct.**
- **The re-pointed plants** O1, O3 and O12 still fail tests (contract plants all ok).

## Should fix (not blocking)

1. **The probe prints only at the end.** `cmd_probe_outlets` builds the whole report, then prints. 112 outlets need up
   to about 224 requests (robots.txt plus the front page), each with a 20 s timeout. If a runner's traffic is
   silently dropped by many outlets, which is exactly what the probe exists to find, the 30-minute job timeout kills
   the run and the log holds **nothing**. Print each `domain: code` line as it completes, or raise the timeout above
   224 x 20 s plus spacing.
2. **The fetcher's docstring misstates its own order.** It lists the host stop (step 3) before robots.txt (step 4),
   while `_admit` checks the address before robots.txt. Robots.txt is fetched only after the address check passes,
   so the code is correct; it is the docstring's step order that is wrong. Align the text.

**Verdict: PASS** (`3f56dbc`), with the two should-fixes above.
