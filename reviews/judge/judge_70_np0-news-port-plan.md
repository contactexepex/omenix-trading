# Judge 70: NP0 news port plan (functional plan document), round 1 at 0e9401a: FAIL

**Lane 1, sole judge (judge #1).** Branch `story/NP0-news-port-plan`, frozen SHA 0e9401a. The change is one file, `docs/stories/NP0-news-port-plan.md` (`git diff --stat origin/main...0e9401a`). The orchestrator's prior approval is not evidence here; I re-derived everything.

## (1) Claims about omenix code: all correct (strong evidence, read at 0e9401a)
- `feeds.py:22-23`: `FEED_ID = ^feed-\d{2,3}$`, `MAX_FEEDS = 50`.
- `planner.py:25`: `UNCOMPARED = ("first_seen_at", "format")`. The migration trap is real: added fields would make every v1 file differ and be written again as a revision.
- `article_file.py:27,43`: `canonical_url` is "" for wrapper items.
- `cluster/entities.py`: `ENTITIES` has 22 entries.
- `codes.py:6,8`: 403/429 → `refused`; a non-feed answer → `block_page`.
- `nse_pacer.py:28`: `HOST_SPACING_SECONDS` holds only the two NSE hosts.
- `fno/ingestion/news/`: 2,025 lines.
- Wording nit: the news fetcher uses its own `NEWS_PACER = NsePacer()` (`news/session.py:16`), which reads the same `HOST_SPACING_SECONDS` table. "The shared host pacer" should say so. The one-entry plan works.

## (2) Claims about agentic: mostly confirmed; the cluster figures are not reproducible
I checked out agentic `f1b9bb6` read-only (HEAD, "india intraday 2026-10-27 08:46 UTC"), ran none of its code, and recounted with `python -I`.

**Exact matches:**
- 25,433 news rows, 21,793 of them Google News.
- 1,533 article rows.
- Access outcomes: 793 / 502 / 125 / 82 / 17 / 14.
- Extractors: jsonld 422, trafilatura 92, description 82, newspaper 4.
- 1,237 distinct clusters.
- `news_sources.yaml`: 112 domains (12 primary, 23 tier1, 77 tier2), 11 `fetch: false`, 227 lines; `india.yaml` 229 lines.
- `company_meta`: 20 companies; Mahindra has 7 exclusions.

**Not reproduced:** "32 clusters with 2 or more origins" and the flags 766 / 768 / 595 / 439 / 223.

| Counting method | ≥2 origins | no_vetted_origin | unread | low_tier_only | single_source | promotional_provider |
|---|---|---|---|---|---|---|
| Latest snapshot per cluster | 35 | 760 | 762 | 587 | 442 | 233 |
| First snapshot | 21 | 772 | 775 | 599 | 444 | 213 |
| Flag on any snapshot | 35 | 772 | 775 | 599 | 450 | 233 |

- Close, but no method matches, and the plan does not state its method.
- The conclusion ("corroboration is rare", about 2.6% to 2.8%) survives. The "strong" label does not, for these figures until the method is stated and recounted.
- **Day counts are inconsistent:** "5-27 Oct" contains only 17 news files (no 6, 17, 18, 20, 24 or 25 Oct). "About 1,500 a day" divides by 17 files; "about 67 a day" divides 1,533 by 23 days (there are 16 article files, about 96 a day). Use one denominator and say which.

## (3) Privacy and write-once: three required corrections

**N1 (required; strong evidence of the inconsistency, the decision is the owner's): the public allowlist contradicts the privacy model the plan itself uses.**
- Section 2c puts `config/news_sources.yaml` (112 outlet domains, tiers, `fetch` flags) in the **public** repository, as "public knowledge".
- But omenix keeps its feed list private and salted precisely so the public repo does not show what the owner reads (`feeds.py:1`: "feed ids and their URLs live in Drive, never in this repository").
- Section 3 also keeps domain names out of summaries "so the public repo does not show what the owner reads". A curated, tiered list of the outlets the owner reads and trusts is exactly that.
- Either keep the allowlist private (Drive, versioned like `feeds-vN.json`), or make "public allowlist" an explicit owner decision with this trade-off stated. It must not be presented as consistent with the privacy rule.
- The record scan does not block plain domain names (`record_scan/catalogue.py` matches credential URLs only). So "no domain names in run summaries or Slack" must be enforced by a marker test like N5, and the plan should say so.

**N2 (required; strong evidence, code): decoding must not change an article's identity.**
- Article keys depend on the kind (`keys.py:4-5`): a publisher item's key comes from its canonical URL, a wrapper item's from its guid (else time plus title).
- Section 1, "Duplication to remove" (2), says the wrapper special case in `Article` "goes away once links are decoded".
- If a decoded Google item switches to the publisher (URL) key, then:
  - the same story gets a **different key** depending on whether the decoder succeeded that run;
  - every Google article already in the Record would be recorded again under a new key.
- The plan must state that a wrapper item's key stays the wrapper key whatever the decoder returns. Only `source_url`, `url_status` and `tier` record the decode. The duplication item should be reworded accordingly.

**N3 (required; reasoning plus code): the "retry through revisions" has no input.**
- Section 2b and risk 1 promise that an `undecoded` item "a later run may" repair through the revision path. A revision is only written when the gate re-reads a staged poll that contains the item.
- But:
  - the gate reads only the polls in its `--from..--to` range;
  - the S1 staging cleanup (judge 66 PASS) trashes a poll after 7 days once every article in it is a NO_OP. An `undecoded` article already recorded *is* a NO_OP, so the poll is removed and nothing is left to retry from;
  - the resolver cap of 80 per run means every wrapper item beyond 80 in a run is first recorded undecoded.
- The plan must name the retry source, for example a separate resolver pass over `undecoded` Record files writing revisions.
  - Square it with S1 (an undecoded article must not count as "held" for cleanup, or retries must not need the poll).
  - Give the volume arithmetic: items per run against the cap of 80 and the run cadence.
- Also state that the dashboard must read the revision to get the URL, because the first file stays undecoded forever.

## (5) Promises the code cannot keep as written (required wording)
- 2d says "1.5 s between requests across hosts", but the pacer spaces per host only (`nse_pacer.py`, `_hosts`). Cross-host spacing is new code; say so.
- Section 5 says "0.5 s between outlet feeds", but every non-NSE host gets `DEFAULT_SPACING_SECONDS = 1.0` today. 0.5 s would *loosen* politeness. Drop it or justify it.

## (4) Evidence labels
Honest, except the cluster figures (above) and "strong" on the per-day rates. Elsewhere, "some evidence" and "reasoning only" are used where they should be (the decoder risk, the effort estimate, MinHash).

## Hard lines
None touched: a plan only, no orders, no Groww, no secrets. It correctly keeps the watchlist and queries private.

## Verdict: FAIL round 1 at 0e9401a. N1, N2 and N3, plus the wording in (5), are required; the counting method for the cluster figures and the day counts are requested.

## Addendum 1: round 2 at 6439195: PASS

Reviewed `git diff 0e9401a 6439195`: one file, 287 lines (under 500). Section 8 lists each finding with the check the author made.

**Cluster numbers and day counts: fixed.** The method is now stated (latest `as_of` per `cluster_id`) and the figures equal my recount: 35 / 760 / 762 / 587 / 442 / 233, and 21 by first-seen state. Rates are per day that has a file (17, 16 and 16 days).

**N1: fixed as an owner decision.** The allowlist's place is decision H, with the precedent stated (the same list is public in agentic). NP1 is not merged before the owner answers. The watchlist and queries are always private. A marker test for "no host name in summaries" is required of each story that prints one.

**N2: fixed.** The wrapper key is untouched and independent of resolution (sections 1 and 2b), and NP2a does not touch `keys.py`.

**N3: fixed by a better mechanism than the one I suggested, and I accept the reasoning (some evidence, reasoning plus code).**
- A re-poll rebuilds the item as unresolved. With the URL inside the article file, every re-poll would differ and record a false revision, unless the planner learned an asymmetric rule.
- The chosen mechanism is a separate write-once resolution file, plus a resolve pass over the Record's last 3 days that never needs staging. That cannot churn, leaves the planner alone, and makes S1's trashing irrelevant.
- `wrapper_link` stays uncompared, so a changed redirect token makes no revision.
- The second migration trap is real: `cluster_record/article_source.py:30` raises "unknown format" for anything but `FORMAT = 1`.
- Keeping tier, wire, promotional, tickers and priority (rule-file judgements) out of the article file is correct. They would cause mass false revisions whenever a rule file changed.

**Pacing wording: fixed.**

**Gaps in the new design (requested, not blocking for a plan; NP2a and NP2c must carry them):**
1. **Every Google article recorded before NP2a can never be resolved.** Format 1 has no `wrapper_link`, and nothing is back-filled. Section 3 says "not back-filled", but it should say plainly: their dashboard URL stays empty and their tier stays `unlisted` forever.
2. **The throughput margin is thin (reasoning only).** Nominal capacity is 80 per pass × 24 passes = 1,920 a day, against about 1,280 arrivals a day: 1.5 times the need.
   - The plan itself says scheduled runs arrive hours late. Below 16 passes a day, the 3-day window expires about (1,280 − 80 × passes) items a day for good.
   - NP2c must report `expired` and the backlog in counts, alert on `expired > 0`, and state the cadence it needs.

**Hard lines.** None touched; the plan keeps every story at `workflow_dispatch` until go-live, with two judges each.

**Verdict: PASS round 2 at 6439195.** Gaps 1 and 2 are for the NP2a/NP2c stories, and the doc wording for gap 1 is requested.
