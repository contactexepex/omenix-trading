# Judge 81: NP3b feed planner (code), round 1 at 0d6adbe: PASS

**Lane 1 (feed plan; privacy and outside-service pacing); judge #1.** Branch `story/NP3b-feed-planner`, frozen SHA 0d6adbe. Reviewed `git diff origin/main...0d6adbe`: `news/planning/*`, `news/pacing.py`, and the small P2 changes (`feeds.py`, `session.py`, `job.py`, `wiring.py`), rows D1 to D9.

## Gates (locked venv; strong evidence)
1582 passed; ruff and check_imports are clean; contract plants all `ok`.

## The attack points

- **D1, can a public poll-log id confirm a guessed name? No.**
  - Ids are `q-` + 8 hex of HMAC-SHA-256 keyed with the feed list's private salt. A fresh salt is `secrets.token_hex(16)` (128 bits); later plans keep the newest list's salt.
  - Without the salt, nobody can compute an id from a guessed company name.
  - Plant: an unsalted SHA-256 → 1 failed.
  - Residual (reasoning only): a feed list the owner wrote by hand keeps whatever salt the owner chose (at least 16 characters). If that was typed rather than random, it is weaker. Say in the story that a hand-written salt should be random.
- **D3 to D5.**
  - Plants: a collision ignored → 1 failed; a kind change allowed → 1 failed; no self-parse before write → 1 failed.
  - `FEED_ID` now uses `\A…\Z` (plant `^…$` → 2 failed).
  - The roughly 4-in-100,000 chance of an 8-hex collision within one plan is refused with a fixed code, not silently merged.
- **D6, URL encoding.**
  - `urlencode`, plus a test that a name cannot add a parameter (`&hl=evil`) or a fragment. That holds.
  - **Minor gap:** the test never checks that the query decodes back to itself. My plant pre-encoding spaces as `+` (which `urlencode` turns into `%2B`, a different search) passes all 627 news tests. Add `parse_qs(urlsplit(url).query)[param] == [query]`.
- **D7 and D8, pacing.**
  - A per-run `NsePacer` built from the feed list puts the search hosts 1.5 s apart; other hosts keep the 1.0 s default. `nse_pacer.py` is untouched.
  - The old `NEWS_PACER` was never attached to the pause log, so a per-run pacer loses no state.
  - Plants:

| Plant | Result |
|---|---|
| all hosts at 1.5 s | 1 failed |
| search hosts at 1.0 s | 2 failed |
| pacer not set in the job | 1 failed |

- **Privacy.**
  - The printed line is counts plus fixed codes (no query, company, URL or id), and an unexpected error prints only its type.
  - The salt is hidden from `repr` (`field(repr=False)`) and tested to be fresh and then kept.
  - Report-only is the default.
- **Cap.** `MAX_FEEDS` goes from 50 to 600. NP3's plan sized it, and the self-parse enforces it.

## Hard lines
No request is made by this change, no order path, no secret in a file, no Groww call.

## Verdict: PASS round 1 at 0d6adbe. Requested (not blocking): the D6 round-trip assert, and a story line that a hand-written salt must be random.
