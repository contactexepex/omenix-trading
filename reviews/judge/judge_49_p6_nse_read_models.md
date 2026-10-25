# Judge 49: story P6, NSE market read models for the Screener and Markets

**Verdict: FAIL.** There is 1 should-fix finding and 3 minor findings. **Criterion 4 is BLOCKED BY THE OWNER** (no
`FNO_DB_URL`), not failed.
- **My rebuild of 12 Oct from the archived raw files** reproduces the builder's comparison exactly: 8 of 9 example
  blocks have 0 differences.
- **The 9th (sectors, 826 differences)** is NSE's 23:20 IST rewrite of the index file. I traced its cause and it is
  as claimed. But A11 (judge 48 PASS) now keeps NSE's later version, and P6 does not read it yet, so criterion 1 is
  not met.

**What I judged**
- **Repository:** trading at dd98f6e.
- **Claims:** `reviews/claude/response_50_2026-10-13-p6-nse-read-models.md`.
- **Story:** `docs/stories/P-publishing.md`, P6.

## Checks run by the judge

```
$ python -m pytest -q tests/market_read_models                 50 passed (the Postgres tests ran on a throwaway PostgreSQL 16)
$ (full suite at 46fe709: 1215 passed; ruff and imports clean)
$ python -m fno market compare --day 2026-10-12                (rebuilt from the archived NSE files in Drive)
  getScreenerSummaryIndia_india: 0 difference(s)
  getScreenerStocksIndia_india: 0      …_high: 0      …_gainers: 0
  getFnoScreenerSummary_india: 0       getFnoScreenerRows_india: 0      …_index_options: 0
  getOverviewIndicesIndia_india: 0
  getIndiaSectors_india: 826 difference(s)
```

**The sectors differences, traced:**
- Of the 18 sector indices in the example, exactly two are absent from our archived index file (`fc847998…`):
  **Nifty Capital Goods** and **Nifty Telecommunications**.
- Both are among the 21 indices NSE added in its rewrite at 23:20:10 IST (`e8e8f6ec…`). I verified both versions
  against NSE in judge 48.
- The 826 differences are those two missing rows shifting every later position.

**My schema plants:**

| Plant | Result |
|---|---|
| An extra top-level field in the stocks block, through a real `market publish --day 2026-10-12 --local` | **refused**: "ScreenerStocksTableIndia: … 'extra_judge' was unexpected". Nothing written; "the previous publication stays current". The alert line reports `FNO_SLACK_BOT_TOKEN` not set in my environment, as expected. |
| An extra key inside the row builder (`stock_rows.py`) | Never reaches the payload, because the block maps only `STOCK_KEYS`. A weak plant, not a gap. |

## Criteria

| # | Criterion | Judge's evidence | Result |
|---|---|---|---|
| 1 | For 12 Oct every built block equals the W11 example field by field | 8 of 9 blocks equal (my rebuild). Sectors: 2 indices missing because the build reads the first version of a file NSE rewrote (finding 1). | **NOT MET** (cause understood; fix available) |
| 2 | Every payload validates against the pinned schema; a planted extra or missing field fails the run | My extra-field plant was refused in a real run; the builder's 4 plants are tested | MET |
| 3 | Publishing is atomic per session | Local: temporary folder, rename, then the pointer, tested with a failing adapter. Postgres: one transaction, tested on a real throwaway server (a failing third insert rolls back; a second publish adds no rows; a changed payload under the same ID is refused). | MET |
| 4 | A real publish to Azure with the publisher role; a dashboard-role read returns the same payloads | No `FNO_DB_URL` in this environment (owner step). The owner steps are listed in the claims. | **BLOCKED BY THE OWNER** |
| 5 | New raw datasets complete in Drive with fingerprints, coverage 0 missing and 0 damaged | My compare read them from Drive. The builder's coverage shows 254 of 254 for both datasets. I did not re-run coverage. | MET (on the builder's coverage plus my successful rebuild from those files) |
| 6 | Size, lint, imports, tests; no US block | Largest P6 file 167 lines; full suite green; six India blocks only | MET |

## Finding 1 (should fix): the build must read NSE's latest version through A11

- **The situation:** A11 (judge 48 PASS) archives NSE's rewrite and provides `VersionedRawStore`. Its story says
  "publishing can use NSE's latest version". P6 still reads the raw first version, so 12 Oct's sectors block lacks
  two indices that NSE publishes.
- **Expected:**
  - Wire P6's raw reader to A11's latest reader in the composition root. That is one line, behind the existing
    `RawFileStore`.
  - Re-run the comparison and show `getIndiaSectors_india: 0 difference(s)`.
- **A point to decide (reasoning only):** publishing should read the latest version, and research the
  point-in-time version. Write that rule into P6's story.

## Minor findings

1. **The pin is behind the dashboard.**
   - The examples file differs from `main` (W11 added the 13 states' examples in d7c982a). The contract version is
     still 2.4.0 and the schemas are unchanged.
   - **Expected:** re-pin and extend `market compare` to the 13 new examples. They use real queries (`x-query`), so
     they also check P6's rows against the route's own semantics.
2. **The 52-week high and low cover a shorter window after a dropped history.**
   - When a demerger has no ex-date trade, the sessions before it are dropped, as claimed and as the orchestrator
     accepted. `y1` is then null; the test checks it, and I read the code.
   - But `h` and `l` are still computed over the remaining sessions (`stock_rows.py:55`, `year` = what is left).
     They are labelled 52-week but cover fewer sessions.
   - The dashboard's TMPV has the same issue (judge 42 addendum 3).
   - **Expected:** apply the same principle. Null when fewer than 250 sessions remain, or a stated contract rule for
     partial windows.
3. **The "special pre-open price" wording.** As judge 42 addendum 3 says, NSE's special pre-open session applies to
   stocks with derivatives. For INDIAGLYCO and DCMSRIND the ex-date open is the normal pre-open auction price. The
   method is fine; the wording should say so.

## Claims vs reality

| Claim | Result |
|---|---|
| 8 blocks equal; sectors differ only by the two rewritten indices | **True** (my rebuild and trace) |
| KOTAKBANK published `y1` 4.24, `h` 453.2 | Consistent with my judge 42 addendum 2 (2,126.90 × 0.2 = 425.38) |
| The demerger rule applies "as claimed" (sessions before a no-trade ex-date dropped, figures null) | **True for the period changes; partial for 52-week** (minor 2) |
| The schema refuses a planted extra field and nothing publishes | **True** (my real run) |
| Atomic publishing on real Postgres | **True** (tests run against a real server) |

## Addendum: round 2 (response 50, addendum 1)

**Verdict on P6: PASS. Criterion 4 is still BLOCKED BY THE OWNER** (`FNO_DB_URL`).

**Checks:** P6 tests 61 passed. I rebuilt 12 Oct from Drive (`market compare`) against the new pin: **21 India
examples**.

| Result | Blocks |
|---|---|
| 0 differences | 18 of 21, including the sectors' `.indices` (the 826 are gone) |
| Remaining | summary 7, oversold 1, filters 1, sectors 5 (in `.industries`) |

**The should-fix is ACCEPTED.**
- Publishing reads A11's latest version, and the root also covers the reference lists.
- The rule "publish latest, research point in time" is written into the story.
- The real rebuild shows Nifty Capital Goods and Nifty Telecommunications.

**The remaining 14 differences are the examples' error, not P6's (strong evidence; two cases checked against NSE by
hand):**

| Stock | NSE facts (bhavcopies; symbol change) | P6 publishes | My hand value |
|---|---|---|---|
| TMPV (TATAMOTORS until 24 Oct 2025) | Ex-date 14 Oct 2025: previous close 660.75, open 400.00, factor 1.6519. TATAMOTORS on 7 Oct 2025 (250 sessions back): 698.05. 12 Oct close 284.45. | `y1` −32.69% | 284.45 / (698.05 / 1.6519) − 1 = **−32.69%** |
| HEGAM (HEG until 22 Sep 2026) | HEG 4 Sep 2026 close 728.25, 7 Sep open 260.00, factor 2.8010. HEG 7 Oct 2025: 510.75. HEGAM 12 Oct close 231.29. | `y1` +26.84% | 231.29 / (510.75 / 2.8010) − 1 = **+26.84%** |

- **The cause:** the examples break a renamed stock's history at its rename, so they show null or partial-year
  figures. P6 joins the history through NSE's `symbolchange.csv`, and the summary counts and industry averages move
  with those rows.
- **Correction to my own judge 42 addendum 3:** I called HEGAM "a new listing (14 sessions)". That was wrong. HEG
  was renamed HEGAM on 22 Sep 2026, and its demerger (7 Sep) is filed under the new symbol.
- **Criterion 1, now MET:** every remaining difference is traced to the example's missing join. P6's figures are the
  correct ones by NSE's own files.
- **For design (routed):** the 33 and 34 fetch must join renames through `symbolchange.csv`. The examples then equal
  P6's figures.

**Minors 1-4: ACCEPTED.**

| Minor | What changed |
|---|---|
| 1 | New pin (only the examples file changed; schemas byte-identical). All 21 examples are compared through a port of the dashboard's `screener_route.py` by their own `x-query`. |
| 2 | A history cut by an action without a price makes `h`, `l` and `va` null. A later listing keeps its range, which is right because no earlier session exists. |
| 3 | TMPV is joined, as above. |
| 4 | Pre-open wording fixed. |

**Remaining risk (the builder's own, agreed; reasoning only):**
- A rename with an unlisted price change inside the 0.55-1.8 jump band would pass unnoticed.
- The jump check still guards every joined series, and the 12 Oct build passed it.

## Addendum 2: criterion 4 (runs 38438666957 and 38439360415; response 50, addendum 4)

**Criterion 4: PARTLY.**
- **Proven, strong evidence:** the publish to Azure as the publisher role, the read-back, and the idempotence.
- **Not yet done:** the criterion's second half, "a read with the **dashboard role** returns the same payloads". The
  only read-back is as `fno_writer`. The claims say the owner's `dashboard_app` read "should show these".
- **So P6 does not close yet:** it needs one owner command. I cannot run it myself, because the judge never connects
  to the real Azure server.

**What I checked:**
- **The run log** (job 115439222087, `market-publish`, head ec21fe2, 17:26-17:31 UTC):
  - "published 6 blocks as nse-2026-10-12-40630e1cd4ec to Azure Postgres (fno schema) (6 rows added)";
  - "read back 6 pages … every payload SHA-256 equals the built records";
  - six hashes, and the database-check step succeeded.
  - **No secret in the log:** `FNO_DB_URL` and the other secrets appear as `***`.
- **My own rebuild:** `python -m fno market publish --day 2026-10-12 --local` gives the **same publication ID**
  (`nse-2026-10-12-40630e1cd4ec`) and **all six payload SHA-256 values equal** the Azure read-back
  (`2b472f04…`, `4c1121a6…`, `4ed30070…`, `2bf88cac…`, `cfb05842…`, `e4d8d13b…`). The published bytes are what the
  code builds from the archived files.
- **A second run adds nothing:** run 38439360415 (from a later commit) reports "(0 rows added)" and the same ID, and
  the ID is named by content.
- **The TLS root cause is plausible and the fix is sound (some evidence):**
  - Root cause: libpq bundled with `psycopg[binary]` points "system" roots at a missing build path.
  - Fix: pinned Azure roots with `verify-full`, always overriding the URL.
  - I did not re-run the TLS reproduction. The builder's tests run on a throwaway TLS server.
  - Failure classes are printed without host or user.

**Expected to close P6:**
- The owner runs the dashboard-role read-back (response 50, addendum 2's command) as `dashboard_app`.
- The output is committed redacted, like X1's evidence: page keys and payload SHA-256 only.
- The six hashes above must appear. P6 is then PASS.

## Addendum 3: the dashboard-role read (response 50, addendum 5, 3a21070)

**Criterion 4: MET. P6: PASS.**
- **The evidence:** the owner's `dashboard_app` query returns 6 page keys of the current publication.
- **My check:** their SHA-256 values equal, string for string (my `diff` of the two sorted lists is empty):
  - the publishing run's six values;
  - my own local rebuild of 12 Oct (addendum 2).
- **No secret was shared:** the password was typed at psql's hidden prompt.
- **Closing #84 is correct.**
