# Data-use map: what we collect, and what reads it (21 Oct 2026)

Owner, 21 Oct 2026: "we have the data but the system doesn't use it". One row per data source we collect, the history on
hand, and the forecaster or check that reads it, **from the code** (imports and file constants found by `grep` on `main`
at about c02a6a27, not from story texts). "Dashboard only" means the market read models (`fno/market_read_models/`)
publish it to a screen and nothing that forecasts or decides reads it. Histories come from the committed manifests
(`research/data/manifests/`), receipts (`receipts/`) and committed tables; Drive may hold more than the repository
shows.

Readers, by package: v2 rule forecasters `fno/forecast/`; v4 rule forecasters `fno/forecast_v4_rules/`; the weather
`fno/weather/` (M1); the range forecaster `fno/price_ranges/` and its price distribution `fno/price_distribution/`
(G13), reported by `fno/forecast_lab/` (FL1); Book 1's desk `fno/books/`, `fno/desk/`; checks `fno/checks/` (C3, C4)
and the risk manager `fno/risk/` (C2); the research engine `fno/research_engine/`; the weekly post-mortem
`fno/learning/`.

## Used by a forecaster, a decision or a check

| Source (owner story) | History on hand | Read by (code) |
|---|---|---|
| F&O bhavcopy, legacy and UDiFF (A1, A13) | 2019-01-01 to 2024-07-05 (1,366 files) and 2024-01-01 to 2026-10-21 (696 files) | the NIFTY panel `fno/research_data/panel_reader.py` → v2 forecasters (`fno/forecast/wiring.py`, `baseline_wiring.py`), v4 rules (`fno/forecast_v4_rules/series.py`), range forecaster (`fno/price_ranges/bhavcopy_chains.py`, `closes.py`), research engine (`fno/research_engine/cycles.py`, `features.py`), desk packs (`fno/desk/pack_wiring.py`), risk (`fno/risk/` FutureQuote) |
| Index closes incl. India VIX close (A10, O6) | 2017-01-02 to 2026-10-21 (2,429 sessions; `warmup_closes.csv`) | `CLOSES_FILE` in v2 forecasters, v4 rules, weather (`fno/weather/wiring.py`), AI books' packs (`fno/ai/close_archive.py`), range forecaster and price distribution, post-mortem (`fno/learning/`) |
| 3 pm NIFTY chain, Groww (A4, A4b) | repository markers 14-21 Oct 2026 (5 sessions); raw quotes in Drive only | Book 1's desk (`fno/books/book1_market.py`, `fno/desk/snapshot.py`, `pack_snapshot.py`, fills in `fno/desk/owner_timing/`), v2 live pack (`fno/forecast/live_pack.py`), checks (`fno/checks/validity_evidence.py`), price distribution (`fno/price_distribution/sources.py`), research engine live features (`fno/research_engine/live_features.py`) |
| 3 pm NIFTY chain, NSE (O6) | markers 14-21 Oct 2026 (5 sessions) | price distribution (`fno/price_distribution/sources.py`, `NSE_DATASET`), v2 capture (`fno/forecast/capture.py`), health (`fno/health/expectations.py`) |
| 15-minute NIFTY marks (A16) | 3 sessions (16, 19, 21 Oct; 78 slot files) | E8 fills (`fno/desk/owner_timing/mark_levels.py`, `mark_snapshots.py`), v4 rules' realised variance (`fno/forecast_v4_rules/wiring.py` via `INTRADAY_FOLDER`, `RvTable`), post-mortem health (`fno/learning/`) |
| Groww 15-minute and 1-minute NIFTY candles (A16b) | 1,684 sessions 2020-2025 (`research/data/intraday/rv-candle/`); option candles 2,548 contracts (E8a study) | candle realised variance (`fno/intraday/candle_rv_table.py`) → v4 rules and v4 scoring (`fno/forecast_scoring/v4/wiring.py`); option candles only in the E8a study (`research/`) |
| Events: RBI, Budget, elections (A6) | 61 rows, 2019-02-01 to 2026-12-04 (hand-kept) | research engine feature F3 (`fno/research_engine/event_features.py`), desk packs (`fno/desk/reference_inputs.py`), weather drivers (descriptive only, `fno/weather/drivers.py`) |
| NSE SPAN margins and the stress factor (A14, A14c) | SPAN files 2020-01-02 to 2026-10-21 (1,689); `margins.csv`; k rows from 14 Oct | risk manager (`fno/risk/margins.py`, `stress_factor.py`), C4's margin check (`fno/checks/validity_margin.py`) |
| NSE session calendar (A7) | 2019-2026 (`research/data/calendar/nse_sessions.csv`) | nearly every job (trading-day and session logic) |

## Collected, but no forecaster, decision or check reads it

| Source (owner story) | History on hand | Read by today | Why not, and when it can be tested |
|---|---|---|---|
| **Global cues: US 10-year, Brent, USD/INR (RBI, FBIL), S&P 500 and Nasdaq 100 (A17)** | 2007-01-02 to 2026-10-20 (about 4,950-5,060 days each); US index closes in Drive only | weather drivers, **descriptive only** ("never an input to the probabilities", `fno/weather/drivers.py`) | No forecaster takes an overnight cue. **Testable now**: 19 years of daily history; the overnight US move vs NIFTY's next-session range can be back-tested at once (a G-story or GR1 input) |
| **India VIX full history, OHLC (A15)** | 2010-07-19 to 2026-09-30 (4,019 days) | none (`fno/vix_history/` read only by its own CLI) | The forecasters use the VIX close from index closes (2017 on). **Testable now**: 16 years for a longer VIX-regime study (e.g. range width by VIX level since 2010) |
| **Participant-wise OI, FII/DII/pro/client (A8)** | 2019-01-01 to 2026-10-21 (1,935 sessions) | none: `build_point_in_time_participant_oi` (`fno/composition.py`) has no caller | Waits on A8's release-time measurement (20 measured release days) so a live reader knows when each day's file is public. **History testable now** with a conservative rule (use day t's file from t+1 only) |
| **FII/DII cash and NSDL FPI daily flows (P8)** | 6 sessions (13-21 Oct 2026) | dashboard only (`fno/market_read_models/flows_block.py`) | Too little history to test anything. **Testable after A23** (flow history back-fill, 2019 on if a source holds it) |
| 3 pm BANKNIFTY, FINNIFTY, MIDCPNIFTY chains (A4c) | 2 sessions (19, 21 Oct) | none (no reader of `banknifty_*` quote files; the range forecaster's BANKNIFTY uses bhavcopy closes and chains) | Started 19 Oct. Testable for BANKNIFTY implied ranges after about 60 sessions (mid-January 2027) |
| NSE and SEBI circulars (A20b) | from 21 Oct 2026 (first runs) | none | Event data; needs months to form a "rule-change week" flag, and a reader story; low priority for index ranges [reasoning] |
| F&O ban list and market lots (A20a) | ban list from 22 Oct, lots from 21 Oct (1 day each) | none (C4's lot rule reads its own config) | The ban list is stock-level, not index; lots could replace config values once a story wires it. Nothing to test on index ranges |
| Capital-market bhavcopy, delivery, corporate actions, EQUITY_L, Nifty 500, symbol changes (P6) | CM bhavcopy and delivery 2025-10-01 on (259 sessions); lists from 12 Oct 2026 | dashboard only (the screener, `fno/market_read_models/session_rows.py`); EQUITY_L also by A12's coverage | Stock-level; could feed breadth (BR1) or heavyweight moves; testable now for the last year [reasoning] |
| Company filings: results and shareholding XBRL, announcements, board meetings (A12) | announcements and board-meeting lists 2005-2026 (7,963 days); 25,363 results and 9,762 shareholding files | none (`fno/filings/` has no outside reader) | Heavyweight results dates (board meetings) could join the event window; **testable now** for result-week range widening [reasoning] |
| NSE contract master | not captured (NSE archives it; A20a decision) | — | Read directly when needed (e.g. BANKNIFTY has no weekly options, 21 Oct) |
| News (A19), macro calendar (A20c), pre-open data (A22) | not on `main` (A19 with its builder; A20c and A22 paused, owner scope freeze 21 Oct) | — | — |

## What this shows

- Forecasts and decisions read four inputs: the bhavcopy panel, index closes (with the VIX close), the 3 pm chains and
  intraday realised variance, plus events (one feature) and margins (risk only).
- Long histories lying unused today: global cues (19 years), India VIX OHLC (16 years), participant OI (8 years),
  filings and board meetings (20 years). Each can be back-tested now, before any live wiring, against the
  existing scored baselines (the v4 scores and FL1's range scores).
- Flows have no usable history (6 sessions); A23 is the fix.

Method: `grep` of imports and file constants across `fno/` (tests excluded), per data package, then each forecaster
package's imports; every path above can be opened to check. A file listed under "read by" reads the data directly or
through the named wiring constant.
