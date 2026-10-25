# Where the tool gets its data

Rewritten for the clean slate (12 Oct 2026). The old desk's source notes (Yahoo candles, intraday NSE scans, news
APIs and their prices) are in git history at commit `184ff7e9acca6fd1b47598f69fbac5bb1b3b5914`; a news source is
re-added only through an approved story with point-in-time rules.

## Historical research data (NSE archives, free)

| Data | Source (code) | Coverage | Notes |
|---|---|---|---|
| F&O daily file, current UDiFF format | `nsearchives.nseindia.com/content/fo/` (`fno/storage/raw_source.py`) | from 1 Jan 2024 | closing prices, OI, volumes per contract; no bid or ask |
| F&O daily file, old format `foDDMONYYYYbhav.csv.zip` | `.../content/historical/DERIVATIVES/YYYY/MON/` | up to 5 Jul 2024 | reader proven identical to the new format on 128 overlap days (5,793,044 rows; `research/2026-10-12-legacy-format/`) |
| Index closes `ind_close_all_DDMMYYYY.csv` (incl. India VIX) | `.../content/indices/` | 2017 on (2017-18 as warm-up only, story A10) | |
| Capital-market file `BhavCopy_NSE_CM_0_0_0_YYYYMMDD_F_0000.csv.zip` (UDiFF) | `.../content/cm/` | archived from 1 Oct 2025 (story P6) | EQ and BE rows feed the screener |
| Security-wise delivery `sec_bhavdata_full_DDMMYYYY.csv` | `.../products/content/` | archived from 1 Oct 2025 (P6) | delivery % |
| Equity corporate actions (splits, bonuses, demergers, dividends) | `www.nseindia.com/api/corporates-corporateActions?index=equities&from_date=…&to_date=…` (JSON) | one copy per day fetched, from 13 Oct 2026 (P6) | ex-date and NSE's text; splits and bonuses adjust past prices |
| Listed companies `EQUITY_L.csv`, Nifty 500 list `ind_nifty500list.csv` | `.../content/equities/`, `.../content/indices/` | one copy per day fetched, from 13 Oct 2026 (P6) | names and industries; replaced in place by NSE |
| Symbol changes `symbolchange.csv` | `.../content/equities/` | one copy per day fetched, from 13 Oct 2026 (P6, judge 49) | joins a renamed stock's sessions to its new symbol (TATAMOTORS → TMPV); replaced in place by NSE |
| F&O ban list `fo_secban.csv` | `.../content/fo/` (`FoBanListSource`, reader `fno/research_data/fo_masters.py`) | one copy per trading day, filed under the trade date it names, from 19 Oct 2026 (A20a, `fo-masters.yml`) | written about 18:12 IST the evening before; replaced in place by NSE; a stale copy is refused and alerted |
| F&O market lots `fo_mktlots.csv` | `.../content/fo/` (`FoLotSizeSource`) | one copy per trading day fetched, from 19 Oct 2026 (A20a) | lot per underlying and expiry month; replaced in place by NSE |
| F&O contract master `NSE_FO_contract_DDMMYYYY.csv.gz` | `.../content/fo/` | **not archived by us**: NSE keeps it dated (served for 1 Oct 2025 on 16 Oct 2026), so it is fetched by a back-fill only when a story needs it (A20a decision) | written about 17:32 IST on the session; every contract's lot, expiry, strike, limits |
| Participant-wise OI (FII, DII, pro, client) | `.../content/nsccl/fao_participant_oi_DDMMYYYY.csv` (`ParticipantOiSource`, parser `fno/research_data/participant_oi.py`) | every session 1 Jan 2019 to 12 Oct 2026 (1,929 files, checked 13 Oct 2026; SHA-256 in `tools/nse_raw_download/manifest_participant_oi.csv`) | published after the close; usable only from the next session's decision time until release times are measured (story A8, `research/data/participant_oi/`) |

The owner downloads these once with `tools/nse_raw_download/` and keeps them on Google Drive (current format 690 files,
old format 1,366, index closes 1,928; read through `fno/storage/google_drive.py`). Participant OI is uploaded from
NSE by the cloud itself (`python -m fno data-librarian participant-oi`, story A9). The raw-file library looks in the
local folder, then Drive, then NSE itself, and archives what it fetches to Drive when the owner's upload keys are set.

## Live market data

| Data | Source | Notes |
|---|---|---|
| NIFTY option chain and per-contract quote book at about 3 pm | Groww Trade API (`fno/providers/groww.py`), market data only | `quote_book` gives bid, ask, sizes and last trade time but **no quote timestamp**, so a quote's age is unknown; validity needs a trade today. Groww's expiry list refuses future years, so in late December the recorder takes expiries from NSE's latest daily file |
| Option chain (fallback, `chain` command) | NSE public website (`fno/providers/public.py`) | unofficial and can be throttled |

Groww credentials (`GROWW_API_KEY` and `GROWW_TOTP_SECRET`, or `GROWW_ACCESS_TOKEN`) live only in the environment or
`~/.trading.env`. Data calls work from a changing IP; Groww's static-IP rule covers order placement, which this tool
never does.

## Rules and notices (story A20)

| Data | Source (code) | Coverage | Notes |
|---|---|---|---|
| NSE circulars | `www.nseindia.com/api/circulars?fromDate=…&toDate=…` (JSON; `fno/circulars/feeds.py`) | every circular NSE lists for yesterday and today, hourly 08:00-22:00 IST, from the first run (A20b, `circulars.yml`) | listed with our first-seen time in Drive `data/circulars/list/`; NSE lists a circular once per department, merged into one row; the file of each F&O one (department "Futures & Options" or F&O words in the subject) in `data/circulars/files/nse/` |
| SEBI circulars | `www.sebi.gov.in/sebiweb/home/HomeAction.do?doListing=yes&sid=1&ssid=7&smid=0` (HTML) | its latest 25 circulars, hourly (A20b) | same table; the page of each F&O one (derivative, margin, lot size, position limit... in the title) in `data/circulars/files/sebi/`; a page with nothing seen before alerts as a possible gap |

## Politeness

`fno/http_pacing.py`: at most one request a second to each site; two refusals in a row ("too many requests" or
"forbidden") pause that site for 15 minutes instead of retrying into a longer block.

**NSE downloads (story A9b, `fno/storage/retry_policy.py`):** every NSE archive source (`NseArchiveSource`: the F&O,
index, participant-OI, SPAN, equity, flows, VIX, filings and corporate-action files) follows one policy, GET and HEAD
alike:

| Answer | What happens |
|---|---|
| 2xx | used at once (one request, no wait) |
| 404 | "not published" |
| no connection, timeout, 429, any 5xx | retried: at most 4 tries, waits of 5, 15 and 45 s; NSE's `Retry-After` stretches a wait |
| `Retry-After` over 120 s | stop at once (reasoning only: past two minutes NSE is blocking, not hiccuping; the pacer's 15-minute pause and the next scheduled run are the right retry) |
| 403, any other 4xx | refused at once, never retried (`RawFileRefused`): retrying a refusal invites a longer block |
| the site is in its 15-minute pause | stop at once, no wait |

A final failure is always `RawSourceUnavailable` (a refused file: its subclass `RawFileRefused`), naming the file, the
status and the tries; every command prints it as a named line, records it, or alerts; never a traceback or a silent
skip. A paused site stops a pass over many files (a sweep) with one line naming how many were not read. In `market
daily`, a session file NSE does not answer on its revision re-read is an archive problem and stops that day's
publication (NSE's latest version cannot be confirmed). Worst case per
file: 65 s of waits, or 3 x 120 s, plus up to 4 request timeouts of 60 s; A12's `filings archive --max-minutes` checks
its deadline before each file, so only the file in flight runs over (twice that for a truncated file's second
download).

`PublicData` (`fno/providers/public.py`: the option-chain fallback and A12's filing indexes on www.nseindia.com/api)
is not under this policy: it keeps its own three tries with a cookie warm-up. Safe today because its callers catch all
it raises (`NseLevelSource` records any failure; A12's indexes turn a list failure into that company's failure and a
cool-off into a stop). A new caller must do the same until it comes under this policy.
