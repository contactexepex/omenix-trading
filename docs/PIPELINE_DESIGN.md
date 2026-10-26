# Ingestion pipeline design: staging → promotion → system-of-record

**Status: DRAFT / proposal (owner + Claude, 27 Oct 2026); Phase 1 built on branch `story/P1-staging-promotion`
(see "Phase 1 as built").** This is the owning document for the multi-source ingestion architecture; everywhere else
links here. It is refined with the owner and implemented incrementally (each phase through the gate + judge).

## Why

Today ingestion fetches each source and archives it write-once to Drive, with a SHA-256 receipt in GitHub. We want
three more things:

1. **More sources, more reliability** — fetch the same facts (prices, filings, news) from several free sources so a
   single flaky source does not create a gap, and so corroboration raises confidence.
2. **Never let a fetcher corrupt the record** — a fetched file must *prove* itself before it becomes a source of
   truth the forecasting engine trusts.
3. **Safe to run in a public repo** — no business logic, no secrets in the repo; even an abused workflow must not be
   able to poison the system-of-record.

The answer to all three is a **two-stage pipeline with a quality gate between fetch and record.**

## The three zones (bronze → silver → gold)

| Zone | What it holds | Who writes it | Mutable? |
|---|---|---|---|
| **Staging** (landing) | Every raw fetch, from every source, tagged with source + fetch time | the fetchers | append-only, overwritable by a newer fetch of the same thing |
| **Record** (system-of-record) | Only files that passed the quality gate | the **promotion gate only** | **write-once** (first promotion wins; receipts prove it) |
| **Derived** | Tables/features built from the record (RV, flows, panels) | derived-step jobs | write-once |

Staging and Record are **separate Drive areas**. A fetcher can only write Staging. Nothing but the promotion gate
writes Record. This is the core rule: **ingestion never commits or overrides the system-of-record directly.**

## Flow

```
            fetchers (per source)                 promotion gate                  consumers
  NSE ─┐                                    ┌─ freshness check                 ┌─ forecasting /
  NSDL ─┤                                    ├─ schema / parse check            │  price-prediction
  BSE  ─┼─►  STAGING (Drive)  ───────────►  ├─ cross-source agreement  ──►  RECORD (write-once) ──►  engine (separate repo)
  news ─┤     raw + source + seen_at         ├─ authority / signature          │  + SHA-256 receipts
  Yahoo ┘                                    ├─ dedup (news clusters)           └─ backtesting
                                             └─ promote only what passes
```

- **Fetchers** run as GitHub Actions (NSE, NSDL, BSE, news, Yahoo — no key needed, public-safe) and, for Groww only,
  as a scheduled session (key off GitHub). Each writes **only to Staging**.
- **The promotion gate** is a separate set of GitHub Actions. It reads Staging, applies the checks below, and writes
  the passing files to the write-once Record. It needs **no broker key** (it only processes already-fetched data), so
  it is fully public-repo-safe.

## Promotion checks (what makes a file "good enough" to become a record)

Applied per dataset; a file is promoted only if it passes all that apply:

1. **Freshness** — the data's own timestamp is within the dataset's expected window (e.g. an EOD file is for the
   session it claims; a quote is from today).
2. **Schema / parse** — it parses into the expected columns/types; no truncation; row counts in range.
3. **Cross-source agreement** — where two+ sources cover the same fact (e.g. NIFTY close from NSE and Yahoo), they
   must agree within tolerance; the **authoritative source wins** on conflict (NSE/NSDL/BSE over Yahoo/Google).
4. **Authority / signature** — prefer the official/signed source; a scraped source is a cross-check, never the primary
   record when an authoritative one exists.
5. **Idempotency** — if the Record already holds this file (same SHA), skip; a different SHA is a *revision*, handled
   by the existing revision path, not an overwrite.
6. **Dedup (news)** — see below.

A file that fails is left in Staging with a reason and alerted to #fno-desk; it never reaches the Record. **Garbage
cannot become a record** — this is the security property and the data-quality property at once.

## News: dedup and credibility

Goal: the same story from several sources should count as **one story with higher credibility**, not as several
independent signals.

- Fetch headlines/articles from multiple free sources (Google News RSS, publisher RSS/sites).
- In the promotion gate, **cluster** articles that refer to the same event (title/entity/time similarity + URL
  canonicalisation), keeping the list of sources per cluster.
- Store **one cluster record** with: the canonical story, its sources, first-seen time per source, and a credibility
  signal = number of independent sources corroborating it.
- The forecasting engine consumes the cluster (one story, with its corroboration weight) — so the same news across
  sources raises credibility but is not double-counted. The final weighting into a forecast is **application-side**;
  ingestion's job is to link and store the clusters, not to score the forecast.
- We will study `contactexepex/agentic-stock-prediction`'s existing news dedup and mirror a proven approach here.

## Source catalogue (free only)

| Source | Datasets | Role | Mechanism | Confidence on reliability |
|---|---|---|---|---|
| NSE archives | F&O, index close, participant-OI, equity/delivery, circulars, filings, corp actions | **primary** | Actions (have) | strong |
| NSDL | FPI daily flows | **primary** | Actions (have) | strong |
| Groww | 15-min NIFTY marks, candles, 3pm chain | **primary** (intraday) | **routine** (key off GitHub) | strong, but snapshot not full depth |
| BSE (bseindia.com) | BSE filings / announcements, BSE prices | cross-check / secondary | Actions (new) | some — scraping, brittle |
| Google News RSS + publisher feeds | market/company news | news (clustered) | Actions (new) | some — headline-level |
| Yahoo Finance (unofficial) | EOD OHLC cross-check | **cross-check only** | Actions (new) | weak — unofficial, ToS, thin for F&O |

Not pursued (honest): **free, reliable trade-level / full bid-ask / historical depth for NSE F&O does not exist** —
the broker feed (Groww) is the only realistic source, and it is snapshot. Google Finance has no public API.

## Security (public repo)

- Fetchers hold **no broker key** (Groww runs as a routine with the key in its session env, never in GitHub).
- Fetchers can write **only Staging**; the write-once Record is written **only** by the promotion gate — so an abused
  public workflow can at worst drop garbage in Staging, which the gate rejects.
- Actions pinned to full SHAs; no third-party actions; fork PRs require approval and cannot reach secrets (no
  `pull_request` triggers); the record scan blocks committing any secret/PII.
- GitHub masks secrets in logs; code prints exception class names only, never credential-bearing text.

## GitHub Actions vs routines

- **Actions:** all non-Groww fetchers + the entire promotion/validation/dedup pipeline (no key needed).
- **Routines (scheduled sessions):** only the Groww fetchers (key off GitHub), per the "no broker key in GitHub" rule.

## System-of-record contract (for the forecasting engine)

The engine (separate repo) reads the Record through the verified Drive cache. The Record guarantees: write-once,
schema-valid, freshness-checked, authoritative-source-preferred, with a SHA-256 receipt per file in GitHub. News is
delivered as deduped clusters with corroboration counts. *(To be firmed up with the engine's needs.)*

## Open decisions (owner)

1. **Promotion tolerances** — exact freshness windows and cross-source agreement tolerances per dataset.
2. **Where the forecasting engine lives** — a third repo? That fixes the Record contract.
3. **BSE / Yahoo / news priority** — which new source first.
4. **Public-repo history** — rewrite to a clean root (hide old forecast/desk code + committer PII) — owner's call.

## Incremental build plan (each phase: gate + judge)

1. **Staging/Record split** *(built, see below)* — introduce the Staging Drive area + a `RawFileStore` variant that writes Staging; move
   existing fetchers to write Staging; add a minimal promotion gate that promotes what already passes (freshness +
   schema + idempotency). *(foundation)*
2. **News source + dedup** — Google News RSS + a couple of publisher feeds → Staging; promotion-gate clustering/dedup;
   store clusters + corroboration. *(first new source; where dedup matters)*
3. **BSE filings** — second filings source into Staging + cross-check in the gate.
4. **Yahoo EOD cross-check** — corroborate NSE closes; authoritative-source-wins on conflict.
5. **Harden + document** — finalise the Record contract with the forecasting engine.

## Phase 1 as built (staging/record split, `fno/ingestion/promotion/`)

**Scope.** The dated NSE datasets the librarian already archives (`participant-oi`, `index-close`, `fo-bhavcopy`,
`cm-bhavcopy`, `security-delivery`, `participant-volume`, `fii-stats`). The reference-list snapshots and the other
workflows are not moved yet.

**Additive, not a reroute.** The 13 live workflows still fetch straight into the Record (Drive `raw` area). Phase 1 adds
the second path beside them: `python -m fno stage <dataset>` and `python -m fno promote <dataset>`, run by hand through
the new dispatch-only workflow `pipeline-staging.yml` (no schedule). Switching a live workflow from "fetch to Record" to
"stage, then promote" is a separate, deliberate change per workflow, after the gate has promoted real files for a
while; it needs the owner's go-ahead. Both paths write the Record through the same write-once store, so they cannot
disagree silently: a different file for a recorded path raises a conflict, it never overwrites.

**Staging layout (Drive area `staging`).** `<source>/<fetch time UTC>/<archive path>`. Each fetch is a new write-once
object (the Drive store cannot overwrite a raw file), so "a newer fetch replaces an older one" means the gate reads the
newest copy first; the old copies stay. The source tag and fetch time are in the path. A fetch whose bytes equal the
newest staged copy is not staged again.

**The fetcher cannot write the Record.** The stager is wired (`promotion/wiring.py`) with an `AreaStore` on `staging`
only; it holds no reference to the Record. `tests/ingestion/promotion/test_wiring_cli.py` asserts every Drive path it
writes starts with `staging/`.

**The gate (`PromotionGate`).** For one archive path, it takes the staged copies of the authoritative source (`nse`),
newest first, and:
1. a copy equal to the Record's file: `already recorded` (idempotent, nothing written);
2. else runs every `PromotionCheck` (freshness, schema); a copy that fails any is skipped with its reasons;
3. the newest passing copy is written to the Record (`promoted`), unless the Record holds other bytes: then `differs
   from record` (a revision for the existing revision path; never written);
4. no staged copy: `not staged`; every copy failing: `rejected` (left in Staging).
`promote` commits the manifest rows it wrote and posts every non-promoted file to #fno-desk (first five named).

**Checks built.** *Freshness*: a file cannot be for a session after its fetch day (IST), and a daily run also requires
the fetch within `--max-lag-days` of the session (default 7, `DEFAULT_MAX_LAG_DAYS`; `--backfill` lifts the lag limit;
the default is a placeholder until the owner sets the tolerance, open decision 1). *Schema*: the dataset's own content
check, the same function the librarian and the coverage check use, so row-count and layout rules live in one place.
Cross-source agreement, authority ranking and news dedup arrive with the phases that bring a second source.

**Not in Phase 1 (stated, not hidden).** No second source exists yet, so the gate promotes only `nse` copies. Staging
copies are never deleted (no retention rule yet). Staging has no receipts: it is not a record.
