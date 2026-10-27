# Judge 80: NP3b feed plan (code, lane 1), judge #2

Frozen SHA `0d6adbe` (branch `story/NP3b-feed-planner`, main `67470c7` with NP3a merged). Reviewed
`git diff origin/main 0d6adbe`:
- `news/planning/*` and `news/pacing.py`;
- the P2 changes in `feeds.py`, `job.py`, `session.py` and `wiring.py`;
- the story, rows D1-D9 and their plants.

**Gates** (in the venv from `requirements.lock`, `--require-hashes`): 1582 passed; ruff check and format clean; imports
clean (549 files); code size passed; contract plants all ok.

**My plants (8 of 8 killed):**

| Plant | Tests failed |
|---|---|
| id unkeyed (plain SHA-256) | 2 |
| collision check off | 1 |
| kind-conflict check off | 1 |
| self-parse off | 2 |
| `pace_for` not called | 2 |
| a fresh salt instead of the newest list's | 1 |
| `FEED_ID` with `^...$` instead of `\A...\Z` | 2 |
| query not URL-encoded | 2 |

## The points asked

- **The id cannot be confirmed without the salt (D1).** `planned_feed_id` is `q-` plus 8 hex of
  `HMAC-SHA256(salt, kind \0 normalise_query(query))` (`query_id.py:21-24`). The salt is the newest list's own; only
  the first list gets `secrets.token_hex(16)` (`wiring.py:22-24`). The unkeyed plant is caught.
- **The guards:**
  - two queries on one id raise `FEED_PLAN_COLLISION`;
  - an id with another kind in any earlier version raises `FEED_PLAN_KIND_CONFLICT`;
  - the bytes are parsed with `parse_feed_list` before they are returned (`FEED_PLAN_INVALID`).

  Each one is killed by a plant.
- **Privacy of what is printed:** the only outputs are the fixed `LINE` (counts) and `STOPPED` (a fixed code, or
  `unexpected` with a class name). A grep finds no other `out` or `print` in `planning/`. The salt is never printed
  or logged: `FeedList.salt` and `DiscoveryPlan.search_url` and `publisher_feeds` are `repr=False`. The logged list
  SHA-256 is of the whole file, so it includes the salt.
- **URL encoding:** names and queries go through `urlencode` (plant killed).
- **`fno/shared/nse_pacer.py` is untouched** (empty diff). The per-run pacer is a new
  `NsePacer(spacing={wrapper hosts: 1.5})`. Like the old `NEWS_PACER`, it is never `attach`ed to the committed pause
  log or to alerts, so no private host can be published. Publisher hosts keep the default 1.0 s.
- **The 50 to 600 cap:** the existing feed tests pass unchanged. The widened `FEED_ID` uses `\A...\Z`, so a trailing
  line break is refused (plant killed). Discovery's publisher feeds must still be `feed-NN`.

## Notes (not blocking)

- If the discovery `search.url` already carries `query_param` in its own query string, `_search_url` appends a second
  copy. Refusing a `search.url` whose query has that parameter would make the result unambiguous.
- A query dropped from the plan frees its id, and a new query that collides with it (same kind, about 2^-32 per pair)
  would inherit its staged history. That is negligible; the story could say so in one line.

**Verdict: PASS** (`0d6adbe`).
