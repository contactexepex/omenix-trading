# NP3b: the feed plan

Lane 1, two judges (it writes the private feed list that decides what omenix requests; privacy rule). Plan: [NP3](NP3-company-list-and-feed-planning.md)
sections 4 to 6 (passed by judge 77). Built on [NP3a](NP3a-company-list.md). Contract rows D1 to D9 in `docs/RECORD_CONTRACT.md`.

## What it does
`python -m fno news plan-feeds [--apply]` reads the owner's company list (`CompanyListSource`) and a private
`discovery-vN.json`, and writes the next `feeds-vN.json` in the private config area. **Nothing is requested.** The fetcher, Staging,
the gate and the poll log read the result as they read any feed list, so a new company list changes the plan at the next
`plan-feeds`, not the code. Without `--apply` it only reports; the printed line is counts and a fixed code, never a query,
a company, a URL or an id.

- `discovery-vN.json` (`planning/discovery.py`, versioned like every private file): the search service's address and
  parameters, the broad queries, the template for a company's own query (one `{name}` slot), and the hand-listed publisher
  feeds (`feed-NN` ids). Nothing in code names the service, a query or a company.
- `FeedPlanner` (`planning/planner.py`): pure. One feed per broad query, one per **targeted** company, plus the publisher
  feeds. A repeat of a query (case and spacing ignored) is planned once. The query is URL-encoded into the address (D6).
- **Ids** (`planning/query_id.py`, D1/D2): `q-` plus 8 hex of an HMAC-SHA-256, keyed with the feed list's private salt, over
  the kind and the normalised query. Same query, same id, however the list is ordered or extended; unguessable without the
  salt (feed ids are public in `polls.csv`). The first list gets a fresh random salt (never printed); later lists keep it.
  The salt and `normalise_query` are frozen.
- **Safety checks** (D3 to D5): two queries on one id are refused; an id an earlier list gave another kind is refused; the
  plan's bytes are parsed with the feed list's own checks before they are returned.
- **Three small changes to P2 code, each behaviour-preserving for existing feeds:** `FEED_ID` also accepts `q-<8 hex>` and
  now rejects a trailing line break (it used `$`; D9); `MAX_FEEDS` 50 to 600; the news session takes a per-run pacer built
  from the feed list (`news/pacing.py`: search hosts 1.5 s apart, all other hosts the default 1 s; D7, D8). `FeedList`
  carries its (private) salt, hidden from `repr`. `fno/shared/nse_pacer.py` is not touched and a test pins the NSE table.

## Said plainly
- **A collision of two queries on 8 hex characters** (32 bits; about 4 in 100,000 per plan at 600 feeds) stops the plan with
  `feed_plan_collision`; the owner rewords one query. With the salt frozen it cannot be worked around by re-hashing.
- **Load:** one request per planned feed per run at 1.5 s: 200 feeds take about 5 minutes. Staging volume against the cleanup limit
  is the NP3 plan's section 6 and is not decided here.
- **Recall of a broad-only plan is unmeasured (reasoning only)**; NP3c measures it. Nothing is requested before the owner's go-live.
- Dropped feeds (in the previous list, not in the plan) are counted in the line; their staged polls stay promotable because
  `kinds_ever_listed` keeps every id ever listed.
