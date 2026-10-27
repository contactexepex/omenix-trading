# Judge 73: NP2a article format 2 (code), round 1 at 20c8c32: FAIL

**Lane 1, two judges; this is judge #1.** Branch `story/NP2a-article-format-2`, frozen SHA 20c8c32, stacked on NP1 df3fe62. Reviewed `git diff df3fe62 20c8c32`. I wrote this without reading judge #2.

## What holds (strong evidence)
- **Gates:** ruff and check_imports are clean; 1348 passed; contract plants all `ok`, including F1 to F8.
- **Scope matches the PASSED plan (judge 70 addendum 1):**
  - the article file gains only `source_domain` and `wrapper_link`;
  - no tier, wire, promotional flag, tickers, priority or resolved URL;
  - `keys.py` is untouched, so the wrapper key is unchanged (attack 4: nothing changes a key);
  - `wrapper_link` is in `UNCOMPARED`;
  - `article_from_bytes` reads formats 1 and 2 and replaces the cluster reader's refusal of anything but the current format.
- **The P2 test reversal is disclosed and correct** (`test_canonical_times_keys.py`): the link is now kept, but only as `wrapper_link`, never as `canonical_url`.
- **Format 1 against format 2** (attack 1): a v1 file equal on the shared fields is a NO_OP against its v2 twin. My plant comparing on the key only → 8 failed.
- **`https_host`** (attack 3) refuses: credentials, a non-443 port, a `%0a` host, an IPv6 literal, a scheme that is not https.

## B1 (required; strong evidence, reproduced): two files of the SAME format are compared only on their shared keys
- `same_version` (`planner.py`) compares `a.keys() & b.keys()` in every case. Its own docstring says "Two files of one format differ in any field", but:
  - `{"format": 2, "key": "k"}` against a complete format-2 file → **same version (NO_OP)**;
  - a format-2 file without `title` against a format-2 file with a different title → **same version**.
- That is attack 2: different articles judged "the same version". Only a damaged but valid-JSON held file triggers it today.
  - The writer and S1 are protected by the manifest SHA (`manifest.has` and the RECORDED conflict).
  - But the planner is the one definition of the rule, and it says NO_OP.
- **Fix:**
  - when the formats are equal, compare every field except `UNCOMPARED`;
  - when they differ, require the older file to hold every field its format defines, and compare the shared fields;
  - anything else is "damaged" and differs.
  - Pin it with a test and a plant.

## B2 (required; strong evidence, reproduced): `wrapper_link` is stored raw, not as the checked URL
- `source_facts` checks `https_host(link)` and then stores `link.strip()` as given. `urlsplit` silently removes `\n`, `\r` and `\t` before parsing, so the check passes while the stored value keeps them. Stored values I produced:

| Input | Stored `wrapper_link` |
|---|---|
| `https://a.example\n/x` | `https://a.example\n/x` |
| `https://news.example/a\nb` | `https://news.example/a\nb` |
| `https://a.example/x y` | `https://a.example/x y` (a space) |
| `https://a.example:443/x` | `https://a.example:443/x` (a port, which NP0 2b says a URL must not have) |
| `HTTPS://A.EXAMPLE/x` | upper-case scheme kept |

- The Record is write-once, so a malformed link stored now stays forever. NP2c's resolver would then have to be the only guard.
- **Fix:**
  - keep the link only when it contains no whitespace or control character and has no explicit port;
  - store it with a lower-case scheme and host.
  - Pin the table above as tests and plant one case.

## Minor (not blocking)
- `article_from_bytes` accepts `"format": true`, because `True in (1, 2)`. Use `type(x) is int`. A JSON `1.0` is accepted the same way.
- An IP address (`1.2.3.4`) is accepted as a `source_domain`. It is a fact, so this is harmless, but NP5 must not give it a tier (`lookup` returns unlisted; fine).
- The NP1 `fullmatch` condition (judge 71 addendum 2) is inherited here. It does not bite via `urlsplit().hostname`, which already drops `\n`, but it must be fixed in NP1 before this merges.

## Hard lines
No order path, no secret, no Groww call, no request, and no change to an existing Record file (only new writes are format 2).

## Verdict: FAIL round 1 at 20c8c32. B1 and B2 are required, both small.
