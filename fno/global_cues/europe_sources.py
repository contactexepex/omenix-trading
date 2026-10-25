"""Official Euro Stoxx 50 and DAX closes, and Cboe's VIX (story A17e).

- STOXX (which calculates the Euro Stoxx 50 and the DAX) publishes a rolling three-month file per index without a
  login; its full history needs a licence, so history comes from Yahoo. STOXX's server sends an incomplete TLS chain
  (its intermediate certificate is missing), so the download trusts SSL.com's public intermediate, kept beside this
  module, on top of the usual bundle: that completes the chain the server should have sent and bypasses nothing.
- VIX from Cboe's delayed-quote history, A17's S&P 500 file layout (`CboeSp500Source`'s parser).

Values are private (Drive only, owner rule 50a79a43): an error never shows a level.
"""

from __future__ import annotations

import os
import tempfile
from datetime import date, datetime
from functools import cache
from pathlib import Path

import certifi
import requests

from .markets import CBOE_VIX, EURO_STOXX, FRANKFURT
from .source import TIMEOUT_SECONDS, CueRequest, CueValue, GlobalCueSource, checked, positive
from .us_index_sources import CboeSp500Source

STOXX_FILE = "https://www.stoxx.com/document/Indices/Current/HistoricalData/h_3m{symbol}.txt"
STOXX_HEADER = "Date;Symbol;Indexvalue;"
STOXX_INTERMEDIATE = Path(__file__).parent / "certs" / "sslcom_tls_issuing_rsa_ca_r1.pem"
CA_BUNDLE_VARIABLES = (
    "REQUESTS_CA_BUNDLE",
    "CURL_CA_BUNDLE",
)  # requests' own order; a proxy's bundle in cloud sessions
CBOE_VIX_FILE = "https://cdn.cboe.com/api/global/delayed_quotes/charts/historical/_VIX.json"


class StoxxSource(GlobalCueSource):
    unit, private, date_zone = "index points", True, FRANKFURT.zone
    max_age_days = 5  # a Thursday close on Tuesday after Good Friday and Easter Monday (STOXX and Xetra holidays)

    def __init__(self, cue: str, symbol: str, name: str, market=EURO_STOXX):
        self.cue, self.symbol, self.market = cue, symbol, market
        self.dataset = f"stoxx/indices/{symbol}-3m"
        self.publisher = f"STOXX Ltd. (calculates the {name}), three-month history file"
        self.first_value_date = date(2026, 7, 22)  # the oldest date of the first file read (21 Oct 2026)

    def requests(self, start: date, end: date) -> list[CueRequest]:
        return [CueRequest(f"h_3m{self.symbol}.txt", STOXX_FILE.format(symbol=self.symbol))]

    def download(self, session: requests.Session, request: CueRequest) -> bytes:
        try:
            bundle = _bundle_with_intermediate()
        except OSError as exc:  # one cue's failure, never the run's: the bundle could not be read or written
            raise requests.exceptions.SSLError(f"{self.cue}: no certificate bundle ({type(exc).__name__})") from exc
        response = session.get(request.url, timeout=TIMEOUT_SECONDS, verify=bundle)
        response.raise_for_status()
        return response.content

    def parse(self, data: bytes) -> list[CueValue]:
        lines = data.decode("utf-8", errors="replace").strip().splitlines()
        if not lines or lines[0].strip() != STOXX_HEADER:
            raise ValueError(f"{self.cue}: not STOXX's history file (header)")
        values = []
        for line in lines[1:]:
            day, symbol, level = (line.split(";") + ["", "", ""])[:3]
            if symbol.upper() != self.symbol.upper():  # its text may be a level after a layout change: never shown
                raise ValueError(f"{self.cue}: a row whose symbol is not {self.symbol.upper()}: layout changed")
            try:
                value_date = datetime.strptime(day, "%d.%m.%Y").date()
            except ValueError:
                raise ValueError(f"{self.cue}: a date cell is not DD.MM.YYYY: layout changed") from None
            values.append(CueValue(value_date, positive(level, day, True)))
        return checked(values, self.cue)

    def available_at(self, value_date: date) -> datetime:
        return self.market.available_at(value_date)


class CboeVixSource(CboeSp500Source):
    cue, dataset = "vix_us", "cboe/indices/vix-history"
    publisher = "Cboe Global Markets (owner of the VIX), delayed-quote history"
    first_value_date = date(2019, 1, 1)
    holiday_rows = True  # 31 US market holidays 2022-2026 have a row (tested 21 Oct 2026): readings skip them

    def requests(self, start: date, end: date) -> list[CueRequest]:
        return [CueRequest("vix-history.json", CBOE_VIX_FILE)]

    def available_at(self, value_date: date) -> datetime:
        return CBOE_VIX.available_at(value_date)


@cache
def _bundle_with_intermediate() -> str:
    """The usual trusted roots plus SSL.com's intermediate, as one file for this process."""
    named = next((os.environ[v] for v in CA_BUNDLE_VARIABLES if os.environ.get(v)), "")
    roots = Path(named if named and Path(named).is_file() else certifi.where()).read_text(encoding="utf-8")
    with tempfile.NamedTemporaryFile("w", suffix=".pem", delete=False, encoding="utf-8") as bundle:
        bundle.write(roots + "\n" + STOXX_INTERMEDIATE.read_text(encoding="utf-8"))
    return bundle.name
