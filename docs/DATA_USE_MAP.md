# Data-use map: what we collect

One row per data source this ingestion backend collects, with the history on hand. Histories come from the committed
manifests (`research/data/manifests/`), receipts (`receipts/`) and committed tables; Google Drive may hold more than
the repository shows. The forecasting, desk and dashboard consumers that once read these datasets have been removed;
this repository now only fetches and archives the data, write-once to Drive.

## What we collect

| Source (owner story) | History on hand |
|---|---|
| F&O bhavcopy, legacy and UDiFF (A1, A13) | 2019-01-01 to 2024-07-05 (1,366 files) and 2024-01-01 to 2026-10-21 (696 files) |
| Index closes incl. India VIX close (A10, O6) | 2017-01-02 to 2026-10-21 (2,429 sessions; `warmup_closes.csv`) |
| 3 pm NIFTY chain, Groww (A4, A4b) | repository markers from 14 Oct 2026; raw quotes in Drive only |
| 3 pm NIFTY chain, NSE public (O6) | markers from 14 Oct 2026 |
| 3 pm BANKNIFTY, FINNIFTY, MIDCPNIFTY chains (A4c) | from 19 Oct 2026 |
| 15-minute NIFTY marks (A16) | from 16 Oct 2026 (78 slot files a session) |
| Groww 15-minute and 1-minute NIFTY candles (A16b) | 1,684 sessions 2020-2025 (`research/data/intraday/rv-candle/`) |
| Events: RBI, Budget, elections (A6) | 61 rows, 2019-02-01 to 2026-12-04 (hand-kept) |
| NSE SPAN margins and the stress factor (A14, A14c) | SPAN files 2020-01-02 to 2026-10-21 (1,689); `margins.csv` |
| NSE session calendar (A7) | 2019-2026 (`research/data/calendar/nse_sessions.csv`) |
| Global cues: US 10-year, Brent, USD/INR (RBI, FBIL), S&P 500 and Nasdaq 100 (A17) | 2007-01-02 to 2026-10-20 (about 4,950-5,060 days each); US index closes in Drive only |
| India VIX full history, OHLC (A15) | 2010-07-19 to 2026-09-30 (4,019 days) |
| Participant-wise OI, FII/DII/pro/client (A8) | 2019-01-01 to 2026-10-21 (1,935 sessions) |
| FII/DII cash and NSDL FPI daily flows (P8) | from 13 Oct 2026 |
| FII derivative statistics (A23) | 2019 onward where the source holds it (flow-history back-fill) |
| NSE and SEBI circulars (A20b) | from 21 Oct 2026 (first runs) |
| F&O ban list and market lots (A20a) | ban list from 22 Oct, lots from 21 Oct 2026 |
| Capital-market bhavcopy, delivery, corporate actions, EQUITY_L, Nifty 500, symbol changes (P6) | CM bhavcopy and delivery from 2025-10-01 (259 sessions); lists from 12 Oct 2026 |
| Company filings: results and shareholding XBRL, announcements, board meetings (A12) | announcements and board-meeting lists 2005-2026 (7,963 days); 25,363 results and 9,762 shareholding files |
| NSE F&O contract master | not archived by us: NSE keeps it dated, fetched by a back-fill only when needed (A20a decision) |

Method: the histories above are read from the committed manifests, receipts and tables; every path can be opened to
check. Where the data comes from, with the exact sources and download policy: `docs/DATA_SOURCES.md`.
