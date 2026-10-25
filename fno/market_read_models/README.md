# NSE market read models (story P6)

The India blocks of the dashboard's Screener (33) and Markets overview (34) that the W11 contract assigns to publisher
`fno` (exepex/trading), built from NSE's own daily files archived in Drive, validated against the pinned contract
(`contracts/omenix-dashboard/`) and published all at once per session.

| Page key | W11 endpoint | Stored as (W11 2.4) | Served by the route |
|---|---|---|---|
| `screener_summary` | `/markets/india/screener/summary` | the served payload (all, n500, fno, ours) | as stored |
| `screener_stocks` | `/markets/india/screener/stocks` | `ScreenerStocksTableIndia` (every row) | filtered, sorted, paged (Markets movers are pages) |
| `fno_screener_summary` | `/markets/india/fno/screener/summary` | the served payload | as stored |
| `fno_screener_rows` | `/markets/india/fno/screener/rows` | `FnoScreenerTable` (every row) | paged (Markets index options: four rows) |
| `overview_indices` | `/markets/india/overview/indices` | the served payload | as stored |
| `overview_sectors` | `/markets/india/overview/sectors` | the served payload | as stored |

The NIFTY option chain for screen 32 (story P9, W13's contract `blocks-chain.yaml`, `blocks-chain-history.yaml`)
publishes in the same publication, one pointer and one run status for both screens:

| Page key | W13 endpoint | Pages |
|---|---|---|
| `chain_underlying` | `/markets/india/fno/chain/underlying` | one |
| `chain_expiries` | `/markets/india/fno/chain/expiries` | one |
| `chain_rows:<expiry>` | `/markets/india/fno/chain/rows?expiry=&strikes=` | one per expiry with every strike; the route serves near and band (`chain_route.py`) |
| `chain_history` | `/markets/india/fno/chain/history` | one |
| `chain_contract:<code>` | `/markets/india/fno/chain/contracts/{code}/history` | one per contract in scope |
| `chain_sources` | `/markets/india/fno/chain/sources` | one |

Computed as W13's examples were (`chain_expiries.py`, `chain_history.py`, `chain_math.py`): NIFTY contracts of the
next three calendar months within 10% of the day's NIFTY, both legs per strike; IV by Black-Scholes from the close
only when the contract traded, searched within 1%-200% (else no IV, Greeks or chance); Greeks and prices from
`fno/analytics.py`; history from 1 Jun 2026, at most six months (`chain_session.py`).

The F&O screens' pages (story P2, `docs/stories/W3-fno-screens.md`) publish in the same publication:

| Page key | Contract schema | Source |
|---|---|---|
| `weather` | `FnoWeather` (P2a) | M1's records (`WeatherRecords`), NIFTY's committed closes; published only from a live record M1 scored, never a level, a `reaches` colour or the US cue (`weather_block.py`, `weather_parts.py`) |
| `weather_history` | `FnoWeatherHistory` (P2a, 2.10.0) | every M1 record up to the session, oldest first: colour, label and the two chances beside the usual chances, with the counts (`weather_history_block.py`) |
| `forecast_history` | `FnoForecastHistory` (P2, 2.10.0) | G4's daily score reports: each v3 question's running score per forecaster, one point per report, live and back-fill apart, one back-fill file per series (`forecast_history_block.py`) |
| `forecast_lab` | `FnoForecastLab` (P2b, 2.10.0) | G4's latest report (live mode only) and the session's committed forecast records: v3's five questions with today's values, the scores, Book 2 and Book 3 against Book 1 (G1's primary family), each forecaster's coverage; v4 listed as a draft (`forecast_lab_block.py`) |

"ours" (the companies the stock tool follows) is counted and tagged here over the NSE rows, from the stock tool's list
(W11 input `FollowedCompaniesIndia`, orchestrator decision of 13 Oct 2026, judge 40): a close uses the latest list dated
on or before it (`followed.py`). Until the stock tool publishes the list (K5-proposed), lists are recorded in
`research/data/followed-companies/india/<as_of>.json`; without a list for a close, the run stops.

How each figure is computed follows the contract's own examples (dashboard `design/mockups/33-screener/fetch_nse.py`,
`_platform/screener_data.py`, `_platform/markets_data.py`): one year and a week of capital-market and index files, three
months of F&O files, the same formulas (returns 1, 5, 21, 63, 250 sessions back; Wilder RSI 14; ATM IV by
Black-Scholes on the spot with the B1 solver, rate `risk_free_rate`). Past prices and volumes are put on today's share basis from NSE's corporate-actions list (`corporate_actions.py`,
judge 42): a split or bonus divides earlier prices by NSE's stated ratio (KOTAKBANK 5:1 on 14 Jan 2026); a demerger by
the previous close / the ex-date open (the pre-open auction's price: NSE's special pre-open session for stocks with
derivatives, the normal pre-open auction for the others; without an ex-date trade, or for a scheme with no ratio, only
the sessions from the ex-date are used, and every figure whose window reaches past the cut is null: changes, 52-week
high and low, volume average); bonus preference shares, dividends,
buy-backs and rights change nothing (price returns). NSE's range list leaves out some symbols (ETFs such as
BANKNIFTY1): a symbol with a one-session close ratio outside 0.55-1.8 and no share-count action in the list gets its own
list looked up (`market look-up`, run by `market daily`), archived per symbol; the jump only chooses where to look, the
ratio is NSE's. A symbol needing a lookup that is not archived stops the build. A renamed stock keeps its sessions under
the old symbol (NSE's `symbolchange.csv`, archived daily; `symbol_changes.py`): NSE lists corporate actions under the
current symbol, so without the join TMPV (TATAMOTORS until 24 Oct 2025) and HEGAM (HEG until 22 Sep 2026) lose both
their year and their demerger adjustment. Publishing reads NSE's latest version of every file (A11's revisions,
`build_versioned_reader()`); research reads the version available at its decision time. Other deliberate differences: sessions come from
NSE's calendar, never weekdays (the examples once skipped the 1 Feb 2026 Sunday Budget session), and an index absent
from a session's file carries its own last date in `as_of` instead of passing an older close off as the day's.

Modules: `nse_files.py` (readers, also the archive's content checks), `chain_*.py` (the option chain, P9),
`run_status.py` (P7), `wiring.py` (this package's composition root), `symbol_changes.py`, `stock_rows.py`, `fno_rows.py`, `index_rows.py`,
`session_rows.py` (reads one session's archived files; a missing file stops the build), `blocks.py` (one builder class
per block, pure), `contract.py` (the pin, validation, drift), `contract_examples.py` and `screener_route.py` (the comparison), `publication.py` (stored rows, validated as stored and as
served), `publisher.py` (`ReadModelPublisher`), `local_publisher.py`, `postgres_publisher.py` (the Azure `fno` schema,
tables in `db/fno/migrations/`), `market_run.py` (one session, all or nothing, alerts), `cli.py`.

Commands:
- `python -m fno market daily [--day D]`: the routine. Archives the session's F&O, index, capital-market and delivery
  files, any newer NSE version of them (A11 revisions), the reference lists and the symbol changes to Drive (with
  manifest rows, committed), then builds, validates and publishes to
  Azure (`FNO_DB_URL`, the fno publisher role; environment settings only). Run it the next morning (for example 07:30
  IST): NSE rewrites some evening files late (the 12 Oct 2026 index file gained two indices at 23:20 IST).
  It runs in GitHub Actions (`.github/workflows/market-publish.yml`, daily at 07:10 IST for the previous session, or
  dispatched with a `day`), never in an AI session: Claude's cloud containers cannot reach Postgres on port 5432.
  After publishing it reads back what the store holds for the publication as the publisher role and checks every
  page's SHA-256 against the built records, printing only counts and hashes. A publication is named by its content
  (`nse-<day>-<12 hex of the pages' hashes>`), so a second run of the same day adds no rows.
- `python -m fno market publish --day D [--local FOLDER]`: one session from the archived files.
- `python -m fno market compare --day 2026-10-12`: the built blocks against every pinned W11 India example, field by
  field; a paged example is served from our stored table by its own query (`x-query`) with the contract's route
  semantics (`screener_route.py`, ported from the dashboard's reference).
- `python -m fno market contract-check`: the pinned contract against the dashboard's published files.

Any failure (a missing file, a schema break, a refused publish) stops the run before anything is visible, prints the
reason and alerts #fno-desk; the previous publication stays current. Never an order function; research data only.
