# Judge 71: NP1 news source rules (code), round 1 at 1d1bfed: FAIL

**Lane 1, two judges; this is judge #1.** Branch `story/NP1-source-rules`, frozen SHA 1d1bfed. Reviewed `git diff origin/main...1d1bfed`: 13 files, all new except RECORD_CONTRACT and contract_plants. I wrote this without reading judge #2.

## Gates (strong evidence)
ruff and check_imports are clean; 1287 passed; contract plants all `ok`, including O1 to O8. The largest file is 152 lines. The code is pure: no request, no Drive, no clock.

## B1 (required; strong evidence, reproduced): a YAML mistake that makes `may_fetch` True for an outlet marked `fetch: false`
- `loader.py:32` uses `yaml.safe_load`, which **silently keeps the last value of a duplicate key**, and the loader has no duplicate check of its own.
- Probe (`load_source_rules` on a temporary file):

| YAML | Loader | `may_fetch("bseindia.com")` |
|---|---|---|
| `bseindia.com: {tier: primary, fetch: false, fetch: true}` | accepted | **True** |
| `bseindia.com: {tier: primary, fetch: false}` then `bseindia.com: {tier: primary}` | accepted | **True** |
| Same domain in two cases | refused (good) | — |

- Both accepted cases are your break-it targets 2 and 3 at once. A merge that appends a second entry, or a hand edit, re-enables requests to an outlet that refuses bot traffic, with no error.
- Fix: a `SafeLoader` subclass whose `construct_mapping` refuses a repeated key at any level. Pin it with a test and an O-row plant.

## Host attacks (break-it target 1)

**Refused correctly:**

| Input | Result |
|---|---|
| port | unlisted |
| `user@` | unlisted |
| `%75` | unlisted |
| `xn--reuters.com` | unlisted |
| `1.2.3.4` | unlisted |
| a path | unlisted |
| interior space | unlisted |
| `REUTERS.COM` and a trailing dot | match, as designed |

**Two documented claims are not exactly true (minor, not blocking):**
- **Non-ASCII.** `"marKetwatch.com"` (Kelvin sign) is **listed, tier1**, because `str.lower()` maps U+212A to ASCII `k` before the ASCII check. Requests' IDNA (UTS46) encodes it to the same `marketwatch.com`, so a request would reach the real outlet: no look-alike fetch (some evidence, `idna.encode` checked). It still contradicts "non-ASCII → unlisted". Check `isascii()` before `lower()`.
- **Whitespace.** Tab, newline, vertical tab and U+2028 at either end are stripped and the host matches (`"\nmarketwatch.com"` → tier1). Harmless for a host taken from `urlparse`, but the doc says "a space ... unlisted". Either refuse it or document it.

## Privacy (relation to judge 70 N1; I re-checked my own finding)
- This story adds the **public** allowlist that judge 70 (NP0, FAIL round 1, still open, unmerged) flagged as N1.
- A fact I had not weighed there: this exact list is **already public** in the owner's public `agentic-stock-prediction` repo (I cloned it anonymously at f1b9bb6). Republishing it here therefore adds little exposure (reasoning only).
- I now rate N1 as an owner decision with low marginal cost, not a blocker for this story. The story should say so in one line: "the same list is public in agentic; the owner accepts it here", or link the owner's decision.
- Process note for the orchestrator: NP1 cites NP0 as "orchestrator-approved", but NP0 is FAIL round 1 at the judge and not on `main`. NP0's N2 and N3 do not affect NP1's pure lookups.

## Hard lines
No order path, no secret, no Groww call, no request, no Drive.

## Verdict: FAIL round 1 at 1d1bfed. B1 required; the two host-doc mismatches and the privacy line requested.

## Addendum 1: round 2 at aa00a5c: PASS, on condition of a one-word fix (`fullmatch`)

Reviewed `git diff 1d1bfed aa00a5c`.

**Gates (strong evidence).** ruff and check_imports are clean; 1294 passed; contract plants O1 to O10 all `ok`.

**B1 fixed (strong evidence, my round-1 probe re-run).**
- `UniqueKeyLoader` refuses:
  - a repeated `fetch` (inline and block style);
  - a second `bseindia.com` entry;
  - a YAML merge key (`<<`), refused as unreadable.
- Accepted, and both harmless:
  - an alias reused for two outlets (each gets the same settings, which is visible in the file);
  - a repeated name inside a list.

**Host minors fixed.** The Kelvin sign, a tab, a space at either end and U+2028 are now unlisted; upper case and a trailing dot still match, as designed.

**One gap left (strong evidence, reproduced): `plain_host` still returns a host with a trailing newline.**
- `PLAIN_HOST.match` uses `$`, which in Python matches *before* a final `\n`.
- `plain_host("marketwatch.com\n")` returns `'marketwatch.com\n'`, not `""`, contradicting its docstring ("Whitespace anywhere ... make it ''").
- Lookups are still safe: `tier_of` gives `unlisted`, and `may_fetch` gives False.
- But `outlet_key` passes the newline through. Any later story that writes an outlet key into a line-based file (TSV, CSV, a receipt) inherits a line break.
- **Condition:** `PLAIN_HOST.fullmatch(cleaned)`, plus a test with `"marketwatch.com\n"` → `""`. The orchestrator can check it.

**Privacy.** The story now states the point and that the merge is held for owner decision H. That is consistent with judge 70's addendum.

**Verdict: PASS round 2 at aa00a5c, on condition of `fullmatch` plus its test. The merge stays held for decision H.**

## Addendum 2: superseded by df3fe62: PASS, the condition still open and widened to two places

Reviewed `git diff aa00a5c df3fe62`, which folds in judge 72's F1 to F5.

**Gates (strong evidence).** 1311 passed; contract plants O1 to O14 all `ok`.

**The new rules read correctly:**
- a public suffix is refused as an outlet domain: the 2-label `co.in`-style rule plus a curated hosting list, honestly stated as not the full Public Suffix List;
- `may_fetch` follows `same_as` to the main domain's `fetch: false`;
- empty labels are refused, and lookups return None for an empty label;
- two wires claiming one name or domain are refused;
- `opinion_unless_path` must be `/…/`.

**Condition from Addendum 1: NOT done, and it applies in two places (strong evidence, reproduced at df3fe62).**
- `rules.py:28` still uses `PLAIN_HOST.match`, so `plain_host("marketwatch.com\n")` returns `'marketwatch.com\n'`.
- `loader.py:77` uses `DOMAIN.match` in the same way: `build_source_rules({'domains': {'evil.com\n': {'tier': 'tier1'}}})` is **accepted**, so an outlet domain can carry a line break. A quoted YAML key can produce one.
- **Fix:** `fullmatch` in both places, plus two tests: a host with a trailing newline gives `""`, and a domain key with a trailing newline is refused.

**Verdict: PASS at df3fe62, on condition of `fullmatch` in `rules.py` and `loader.py` with their tests. The merge stays held for decision H.**
