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
3. **Safe to run in a public repo** — no business logic, no secrets in the repo; no outsider writes Drive
   through a fork or a pull request (fork pull requests cannot read secrets). See "Security" for what protects the
   Record, and for the paths that remain (a bad merged change, a dependency that was malicious when locked).

The answer to all three is a **two-stage pipeline with a quality gate between fetch and record.**

## The three zones (bronze → silver → gold)

| Zone | What it holds | Who writes it | Mutable? |
|---|---|---|---|
| **Staging** (landing) | Every raw fetch, from every source, tagged with source + fetch time | the fetchers | append-only: a newer fetch is a new copy beside the old |
| **Record** (system-of-record) | Only files that passed the quality gate | the **promotion gate only** (target: today the live workflows also write it) | **write-once** (first promotion wins; receipts prove it) |
| **Derived** | Tables/features built from the record (RV, flows, panels) | derived-step jobs | write-once |

Staging and Record are **separate subfolders** (`staging/`, `raw/`) of the one shared Drive folder. In the new
stage-then-promote path a fetcher writes only Staging and nothing but the promotion gate writes the Record: this is the
core rule, **enforced in code only** (accepted owner decision, 26 Oct 2026; see "Security"). It is not yet true of the
live workflows: see "Phase 1 as built".

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
  as a scheduled session (key off GitHub). In the new path each writes **only to Staging** (code level; the live workflows still write the Record directly).
- **The promotion gate** is a separate set of GitHub Actions. It reads Staging, applies the checks below, and writes
  the passing files to the write-once Record. It needs **no broker key** (it only processes already-fetched data).

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

A file that fails is left in Staging with a reason and alerted to #fno-desk; it does not reach the Record through the
gate. This is a **data-quality** property: the gate checks format and identity, **not authenticity**, so a well-formed
forged file is not detected, and any job holding the shared credential can also write the Record directly (see
"Security").

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
- **Accepted owner decision (26 Oct 2026): one shared Drive folder, one shared credential, separation in code only.**
  Staging and the Record are subfolders of the same Drive folder, and the 13 of the 14 workflow files that write
  Drive use the same owner Drive credential (full Drive scope; `participant-oi-watch.yml` holds none). The owner chose not to pursue credential, account or repository isolation (cost and
  complexity). So a fetcher's credential **can** write the Record: an abused or wrongly changed workflow **could**
  overwrite or delete it. This design does not claim otherwise.
- What does and does not protect the Record, honestly. **No outsider reaches Drive through a fork or a pull request:**
  fork pull requests cannot read secrets and no workflow uses a `pull_request` trigger. **Supply chain is narrowed, not
  closed (story SEC1):** every workflow installs from a hashed lock (`requirements.lock`, installed with `--require-hashes` and
  `--only-binary=:all:`), so a new release of a dependency is not picked up and no package is built on the runner. What
  stays open: a dependency that was already malicious when locked; the lock tool `uv` (the root of trust for the hashes);
  `pip` itself from `actions/setup-python`; the runner image; the cloud container's own setup script; and the Groww
  routine session, whose source-only packages (`clint`, `args`) are built at install time with unhashed build
  requirements. `ops/relock.sh` regenerates the locks; the diff of every bump is reviewed.
  Against a bad change that reaches `main` the protection is **process**: the lane review (`docs/JUDGE.md`; lane 2 has
  no judge), the **public-record scan** on every commit and the **quality gates** (tests, lint, size and number checks).
  GitHub reports `main` as protected, but direct pushes are accepted (every session and the contents-write workflows
  push to it), so the review is process, not a technical block; the rule's exact settings are not readable from here.
  Drive files are write-once in our code, every Record file has a SHA-256 receipt in GitHub, and readers that go through the
  verified cache check the receipt on each read (`storage/drive_cache.py`; the coverage check, the librarian and the
  gate read `raw/` directly), so a changed file is detected when read (a change that also
  rewrites the receipt is not caught by that alone).
- Residual risk, stated plainly: the shared token has **full Drive scope**, so it covers the owner's whole Drive, not
  only `raw/`; anyone who can merge to `main` or is a repository admin can reach it; a dependency that was already malicious
  when locked, or any other open root listed above, can use it; and recovery is limited (Drive's trash and version history only, no separate backup of the
  Record). Receipts detect a changed file, they do not restore it. A **forged but well-formed** staged file is not
  detected by the gate, and a fetcher's credential could also delete the genuine staged copy; cross-source checks
  (Phase 4) or re-fetching from the authoritative source at promotion would narrow this, and are not built.
- Actions pinned to full SHAs; no third-party actions; fork PRs require approval and cannot reach secrets (no
  `pull_request` triggers); the record scan blocks committing any secret/PII.
- GitHub masks secrets in logs; code prints exception class names only, never credential-bearing text.

## GitHub Actions vs routines

- **Actions:** all non-Groww fetchers + the entire promotion/validation/dedup pipeline (no key needed).
- **Routines (scheduled sessions):** only the Groww fetchers (key off GitHub), per the "no broker key in GitHub" rule.

## System-of-record contract (for the forecasting engine)

The engine (separate repo) reads the Record through the verified Drive cache. The Record is meant to guarantee (target;
see "Security" for what holds today): write-once, schema-valid, freshness-checked, authoritative-source-preferred, with a SHA-256 receipt per file in GitHub. News is
delivered as deduped clusters with corroboration counts. *(To be firmed up with the engine's needs.)*

## Open decisions (owner)

1. **Promotion tolerances** — exact freshness windows and cross-source agreement tolerances per dataset.
2. **Where the forecasting engine lives** — a third repo? That fixes the Record contract.
3. **BSE / Yahoo / news priority** — which new source first.
4. **Public-repo history** — rewrite to a clean root (hide old forecast/desk code + committer PII) — owner's call.

## Incremental build plan (each phase: gate + judge)

1. **Staging/Record split** — introduce the Staging Drive area and a staging-only writer; a minimal promotion gate that
   promotes what already passes (the librarian's rules, schema, identity, idempotency). *(foundation; built for 5
   datasets, see below.)* Moving each existing fetcher to write Staging is **not done**: one workflow at a time, with
   the owner's go-ahead.
2. **News source + dedup** — Google News RSS + a couple of publisher feeds → Staging; promotion-gate clustering/dedup;
   store clusters + corroboration. *(first new source; where dedup matters)*
3. **BSE filings** — second filings source into Staging + cross-check in the gate.
4. **Yahoo EOD cross-check** — corroborate NSE closes; authoritative-source-wins on conflict.
5. **Harden + document** — finalise the Record contract with the forecasting engine.

## Phase 1 as built

The owning document for Phase 1 (what it does, claims, gap list, evidence) is `docs/stories/P1-staging-record-split.md`.
Three facts matter for the rest of this design:

- Only five datasets can go stage-then-promote (participant-oi, participant-volume, fii-stats, fo-bhavcopy,
  cm-bhavcopy), by hand, through the dispatch-only workflow `pipeline-staging.yml`. All live workflows still write the
  Record directly.
- "Only the gate writes the Record" holds **in code** (the new `stage` command can reach Staging only). It is **not** a
  credential boundary, by the owner's accepted decision (Security section): one shared credential writes both areas.
  `staging/` is a subfolder of the shared Drive folder (`promotion/wiring.py`: `AreaStore(build_owner_drive(env),
  "staging")`), the Record is `raw/` in the same folder.
- The shipped freshness rule is the date-identity check (a file's own date must be its session); a numeric window is the
  owner's decision 1 and is off unless `promotion.max_lag_days` is set in `config.yaml`.
