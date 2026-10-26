# Ingestion pipeline design: staging → promotion → system-of-record

**Status: DRAFT / proposal (owner + Claude, 26 Oct 2026).** Not yet built. This is the owning document for the
multi-source ingestion architecture; everywhere else links here. It will be refined with the owner, then implemented
incrementally (each phase through the gate + judge). Phase 1's contract (claims, gap list, default freshness rule) is
`docs/stories/P1-staging-record-split.md`.

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

1. **Staging/Record split** *(built; see below)* — introduce the Staging Drive area + a `RawFileStore` variant that writes Staging; move
   existing fetchers to write Staging; add a minimal promotion gate that promotes what already passes (freshness +
   schema + idempotency). *(foundation)*
2. **News source + dedup** — Google News RSS + a couple of publisher feeds → Staging; promotion-gate clustering/dedup;
   store clusters + corroboration. *(first new source; where dedup matters)*
3. **BSE filings** — second filings source into Staging + cross-check in the gate.
4. **Yahoo EOD cross-check** — corroborate NSE closes; authoritative-source-wins on conflict.
5. **Harden + document** — finalise the Record contract with the forecasting engine.

## Phase 1 as built (staging/record split, `fno/ingestion/promotion/`)

Contract, claims and gap list: `docs/stories/P1-staging-record-split.md`. In short:

- **Additive.** The existing fetch-to-Record paths and workflows are unchanged. `python -m fno stage <dataset>` fetches
  NSE's files into the Drive `staging` area only; `python -m fno promote <dataset>` runs staged files through the gate
  into the write-once Record (Drive `raw` with its manifest row). The only new workflow, `pipeline-staging.yml`, is
  `workflow_dispatch` only. Switching a live workflow to stage-then-promote is a separate change, with the owner's go-ahead.
- **Datasets:** participant-oi, participant-volume, fii-stats, fo-bhavcopy, cm-bhavcopy. index-close and
  security-delivery stay on the direct path (no verified date in their files yet).
- **Staging layout:** `<source>/<fetch time UTC>/<archive path>`; a newer fetch is a new write-once copy beside the old
  one; identical bytes are not staged twice. Staging has no receipts (it is not a record) and no retention rule yet.
- **Only the gate writes the Record, by construction:** the Stager holds a `StagingArea` only; the Record store is given
  to `PromotionGate` only; a test asserts only `staging.py` and `gate.py` call `.put(` in the package.
- **Gate:** equal to the Record = skip; else the newest staged copy that passes every check is written; a passing copy
  that differs from the Record is reported as a revision, never written; failing copies stay in Staging with their reasons.
  `promote` commits its manifest rows and posts non-promoted files to #fno-desk.
- **Default checks (behavior-preserving, no number):** the dataset's content check (same function the librarian uses) and,
  where that check reads no date, `ContentDayCheck`: every row's date must equal the session the path claims, else the
  file is rejected (also if undated or unreadable).
- **Owner decision 1 seam:** `FreshnessCheck(max_lag_days)` is wired only when `config.yaml` sets
  `promotion.max_lag_days`; it ships `null` (no window). The owner's numbers plug in there, per dataset later.

