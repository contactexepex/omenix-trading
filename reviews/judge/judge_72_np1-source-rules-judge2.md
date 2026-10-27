# Judge 72: NP1 news source rules (code, lane 1), judge #2 of 2

Frozen SHA `1d1bfed` (branch `story/NP1-source-rules`). I read the story first, then reviewed
`git diff $(merge-base) 1d1bfed`:
- `config/news_sources.yaml`;
- `fno/ingestion/news/sources/{model,loader,rules,labels}.py`;
- the tests, the contract rows O1-O8 and their plants.

The branch does not touch `reviews/` or `numbers/`. The "deleted judge_70" seen in `git diff origin/main` comes only
from the branch being older than main. I judged this independently of judge #1.

**Gates (cleared `__pycache__`):** 1287 passed; ruff check and format clean; imports clean (511 files); code size
passed; contract plants all ok.

**My plants (6 of 6 killed):**

| Plant | Tests failed |
|---|---|
| no dot boundary | 1 |
| `fetch` ignored | 3 |
| no host-shape check | 3 |
| lookup also tries the bare TLD | 1 |
| unknown keys accepted | 1 |
| a non-bool flag accepted | 1 |

## Limit, said plainly: the port is NOT compared with agentic `f1b9bb6`

I asked to attach `contactexepex/agentic-stock-prediction` read-only to compare the two files. The session's
permission check denied it, and I did not work around that. What I could check is the file's own numbers, read with a
duplicate-key-aware loader:
- 112 domains: 12 primary, 23 tier1, 77 tier2;
- 11 `fetch: false`;
- 8 wires;
- no duplicate keys;
- top-level sections `domains`, `wires`, `promotional`.

That it matches agentic's file line for line is **not established by me**. Judge #1, or anyone with access, should diff
it, or the owner can grant access. The values are public outlet names and tiers, and the record scan passed. I found no
private value by reading.

## Your question 1: a host that should be unlisted but finds an outlet

None found that matters. The following are all unlisted or `may_fetch` False:
- `reuters.com%2e`, `xn--reuters.com`, `reuters.com:443`, a host with credentials before it (a user name and an at-sign, then `reuters.com`);
- `1.2.3.4`, `[::1]`, `reuters.com/x`;
- `notreuters.com`, `reuters.com.evil.example`;
- `.reuters.com`, `a..reuters.com`, `-a.reuters.com`.

`www.` under every `fetch: false` domain stays False.

Two lenient forms are accepted: `REUTERS.COM.` and `reuters.com..` (all trailing dots stripped), and a host wrapped in
tabs or newlines (`.strip()`). Both name the same real host, so neither widens anything. A Kelvin sign `K` lowercases
to ASCII `k`, but IDNA maps it the same way, so the host is the same one too.

## Findings (your questions 2 and 3: mistakes and abuse through the config file alone)

1. **F1 (must fix): a domain listed twice silently overrides itself, which can turn `fetch: false` into fetchable.**
   `yaml.safe_load` keeps the last of two identical keys without a word. I reproduced it: `a.example.com` with
   `fetch: false`, then the same key again without it, gives `may_fetch` True. This is exactly "a mistake the loader
   accepts", and it flips the one safety property this story exists for. In a 112-entry file a re-added domain is a
   realistic slip.

   Fix: load with a `SafeLoader` subclass whose mapping constructor refuses a duplicate key at any level. Add a test
   and a plant. It is about 6 lines.
2. **F2 (should fix): a public suffix can be listed, which allows every host beneath it.**
   - The `DOMAIN` pattern accepts `co.in` and `github.io`. I reproduced it: `may_fetch("anything-at-all.co.in")` and
     `may_fetch("evil.github.io")` are both True.
   - The file's own rule is "never unknown or dubious sites". One entry would open a whole country suffix or a free
     hosting platform.
   - Two judges review the file, so this needs a deliberate or careless commit (reasoning only on how likely that is).
   - Fix: refuse a listed domain that is a public suffix. The clean way is the Public Suffix List as a pinned, hashed
     dependency. The cheap way is a short refuse-list of second-level suffixes plus the shared-hosting suffixes, with
     its limits stated.
3. **F3 (should fix): a name that normalises to the empty string claims every unlabelled item.** `names: ["."]` passes
   `_strings` (`"."` is not blank), and `normalise_label` turns it into `""`. Then `domain_of_label(None)` and
   `domain_of_label("")` return that outlet, so every item with no label would get its tier. Reproduced. Fix: refuse a
   name whose normalised form is empty, and have `domain_of_label` return None for an empty label before the lookup.
4. **F4 (should fix): a `same_as` alias of a `fetch: false` outlet is fetchable.** It is one outlet with two hosts, and
   one host refuses bots. The loader accepts `b same_as a` where `a` has `fetch: false` and `b` does not, and
   `may_fetch(b)` is then True. Reproduced. The shipped pairs (`bbc.co.uk` to `bbc.com`, `economictimes.com` to
   `economictimes.indiatimes.com`) are fetchable on both sides, so nothing live is affected. Fix: refuse a `fetch`
   mismatch across `same_as`, or let the alias inherit the main domain's `fetch`.
5. **F5 (should fix): two wires can claim one name.** `_wire_name` keeps the last one, silently. Outlet labels already
   get this check (`_check_labels`); wires do not. Reproduced: `X` and `Y` both naming "Reuters" gives `Y`.

## Notes (not blocking)

- `opinion_unless_path: "/news"` also counts `/newsletter/...` as news. It is a prefix rule, inherited. A trailing `/`
  in the config, or a check at a path boundary, would be exact.
- `promotional.text` accepts any pattern that compiles, including `(a+)+$`. NP5 will run these against untrusted feed
  text; NP5 should bound them, for example with a timeout or a match on short text only.
- A stale comment in the YAML header says "extract: optional extractor order (default jsonld, trafilatura,
  newspaper)", but `newspaper` is removed.
- **"NOT established" section:** honest on the probe origin, the tiers and the breadth. It should add that the port's
  fidelity to `f1b9bb6` rests on the builder alone until a judge diffs it.

**Verdict: FAIL** (round 1, `1d1bfed`). F1 is the blocker, a 6-line fix plus a test. F2 to F5 are small and
strengthen the same "a typo is an error" promise.

## Addendum 1: round 2 (final) on `df3fe62`

`git diff 1d1bfed df3fe62 -- fno config docs tests`:
- `UniqueKeyLoader`;
- `is_public_suffix` (a two-label national-suffix rule plus a curated hosting list);
- empty-label refusals and lookups;
- the `same_as` alias inheriting `fetch: false`;
- `_check_wires`;
- `opinion_unless_path` must be `/.../`;
- non-ASCII refused before lower-casing.

`NP0-news-port-plan.md` in the range is already on main (judge 70 PASS at `6439195`), so it is not part of this change.

**Gates (cleared `__pycache__`):** 1311 passed; ruff check and format clean; imports clean (511 files); code size
passed; contract plants all ok. Largest file: `loader.py`, 204 lines.

**My round-1 reproductions, re-run:**

| Finding | Now |
|---|---|
| F1: repeated key | refused (`fetch` repeated inside one outlet: "repeated key 'fetch'"). A list as a key, and a YAML merge-key trick, are also refused. |
| F2: public suffix | `co.in`, `gov.uk`, `com.au`, `edu.au`, `co.jp`, `github.io` refused |
| F3: empty label | refused when loading, and `domain_of_label(None)` returns None |
| F4: alias of a `fetch: false` outlet | not fetchable |
| F5: two wires, one name | refused |

**Plants (7 of 7 killed):**

| Plant | Tests failed |
|---|---|
| duplicate-key check off | 2 |
| suffix check off | 9 |
| alias bypass | 2 |
| empty-label lookup | 2 |
| wire check off | 2 |
| ASCII check off | 2 |
| `/.../` check off | 4 |

**Port fidelity:** the orchestrator, not a judge, diffed the file against `f1b9bb6`. The story says so plainly
(lines 46-48). I still have no access to that repository, so this remains unverified by me.

## Notes (not blocking; reasoning only on likelihood)

- **A separately listed child of a `fetch: false` parent is fetchable.** The loader accepts `a.example.com`
  `fetch: false` plus `in.a.example.com` with no `fetch`, and `lookup` finds the child first. It is the F4 pattern by
  another route. Nothing in the shipped file is nested, so nothing live is affected. Consider refusing it, or
  inheriting the parent's `fetch` the way the alias now does, before NP4 re-probes.
- **The curated suffix list is what the story says it is.** `substack.com` and `ltd.uk` still load. `nic.in` is
  refused, which is the safe direction. The listed `finance.yahoo.com` and `news.yahoo.com` are single-organisation
  hosts.

**Verdict: PASS** (`df3fe62`).
