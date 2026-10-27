# Judge 99: NP6a grouper version 2 (code), round 1 at 7323c3f: PASS

**Lane 1; judge #1.** Branch `story/NP6a-grouper-v2`, frozen SHA 7323c3f. Reviewed `git diff origin/main...7323c3f`: `cluster/{prepare,url_identity,assign,cluster,matcher}.py`, `cluster_record/{grouping,cluster_file,run,report,wiring}.py`, `resolve/effective_url.py`, `news-cluster.yml`, rows Z1 to Z15. Plan: NP6 (judge 96, with condition C1).

## Gates (locked venv; strong evidence)
1958 passed; ruff is clean; contract plants all `ok`.

## The three points asked (strong evidence)
- **The narrowed no-I/O test is fair.** It now allows exactly the module `urllib.parse`; every other `urllib` import keeps its top name and is forbidden. I added each of these to `cluster/url_identity.py` (after the `__future__` import), and each **fails** the test:
  - `import urllib.request`;
  - `from urllib import request`;
  - `import urllib`;
  - `from urllib.request import urlopen`.

  `urllib.parse` only splits strings.
- **The company list fails closed.**
  - Only `company_list_missing` falls back to version 0 with no bar movement.
  - Any other refusal stops the run with its code (`GroupingBlocked`), and any store error is `company_list_unavailable`.
  - A damaged resolution file is `resolution_unreadable`.
  - Plants: an invalid list falling back silently → 3 failed; a store error falling back silently → 1 failed.
- **The workflow input.** `algorithm` is a `choice` of "1" or "2" (default "1"), passed through env and quoted (`--algorithm "${ALGORITHM:-1}"`). Version 1's behaviour and bytes are unchanged unless "2" is dispatched.

## URL identity (some evidence; the story says "a guess")
- Plants: any URL counted as an identity → 7 failed; `utm_` not stripped → 2 failed.
- **Where the guess is weakest (reasoning only):**
  - any remaining non-tracking query makes a URL an identity, so a home page with `?ref=rss` would join everything resolved to it;
  - so does any two-segment section path (`/markets/stocks`).
- `url_joins_unlike_title` (C1) is the early warning, and the story requires the v1/v2 comparison before NP7. I recommend that the comparison treat any `url_joins_unlike_title > 0` as a reason to inspect, and that the rule refuse a URL whose only query parameters are `ref`-like.

## Hard lines
No order path, no secret, no Groww call, no request. Writes only new format-2 files in a new folder, through the existing write-once path. No symbol or name is printed or stored.

## Verdict: PASS round 1 at 7323c3f. The URL-rule note is recommended for the comparison before NP7.
