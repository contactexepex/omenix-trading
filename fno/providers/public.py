"""Free public data: NSE website JSON endpoints and Yahoo Finance daily history.

These endpoints are unofficial and NSE may throttle or change them without notice.
"""

from __future__ import annotations

import contextlib
import time
from datetime import date, datetime
from functools import reduce
from math import gcd

import requests

from ..http_pacing import PacedSession
from ..models import IST, OptionChain, OptionQuote
from .base import Provider, is_index

NSE = "https://www.nseindia.com"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/option-chain",
}


class PublicData:
    """Thin HTTP client for the public NSE website."""

    def __init__(self, pause: float = 0.4):
        self.session = PacedSession()
        self.session.headers.update(HEADERS)
        self.pause = pause
        self._warmed = False

    def _warm(self) -> None:
        if not self._warmed:
            with contextlib.suppress(requests.RequestException):
                self.session.get(NSE + "/option-chain", timeout=15)
            self._warmed = True

    def nse_json(self, path: str, params: dict | None = None) -> dict:
        for attempt in range(3):
            resp = self.session.get(NSE + path, params=params, timeout=20)
            if resp.status_code == 200 and resp.text.strip():
                time.sleep(self.pause)
                return resp.json()
            self._warm()
            time.sleep(1.5 * (attempt + 1))
        resp.raise_for_status()
        raise RuntimeError(f"NSE returned an empty response for {path}")


def parse_nse_date(text: str) -> date:
    for fmt in ("%d-%b-%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unrecognised NSE date: {text}")


def infer_lot_size(rows: list[dict]) -> int | None:
    """Order-book quantities are always whole lots, so their GCD is the lot size."""
    qty = []
    for row in rows:
        for kind in ("CE", "PE"):
            leg = row.get(kind) or {}
            for key in ("buyQuantity1", "sellQuantity1"):
                v = leg.get(key)
                if isinstance(v, (int, float)) and v > 0:
                    qty.append(int(v))
    if len(qty) < 10:
        return None
    lot = reduce(gcd, qty)
    return lot if lot > 1 else None


def parse_nse_chain(payload: dict, underlying: str, expiry: date, fallback_lot: int) -> OptionChain:
    rec = payload["records"]
    spot = float(rec["underlyingValue"])
    ts = datetime.strptime(rec["timestamp"], "%d-%b-%Y %H:%M:%S").replace(tzinfo=IST)
    rows = [
        r
        for r in rec.get("data", [])
        if parse_nse_date(r.get("expiryDates") or r.get("expiryDate") or (r.get("CE") or r.get("PE"))["expiryDate"])
        == expiry
    ]
    quotes: dict[tuple[float, str], OptionQuote] = {}
    for row in rows:
        strike = float(row["strikePrice"])
        for kind in ("CE", "PE"):
            leg = row.get(kind)
            if not leg:
                continue
            quotes[(strike, kind)] = OptionQuote(
                strike=strike,
                kind=kind,
                ltp=float(leg.get("lastPrice") or 0),
                bid=float(leg.get("buyPrice1") or 0) or None,
                ask=float(leg.get("sellPrice1") or 0) or None,
                oi=float(leg.get("openInterest") or 0),
                oi_change=float(leg.get("changeinOpenInterest") or 0),
                volume=float(leg.get("totalTradedVolume") or 0),
                iv=float(leg.get("impliedVolatility") or 0) or None,
                symbol=leg.get("identifier"),
            )
    lot = infer_lot_size(rows) or fallback_lot
    return OptionChain(
        underlying=underlying.upper(),
        spot=spot,
        expiry=expiry,
        timestamp=ts,
        lot_size=lot,
        quotes=quotes,
        source="nse",
    )


class NSEProvider(Provider):
    name = "nse"

    def __init__(self, config: dict, client: PublicData | None = None):
        super().__init__(config)
        self.client = client or PublicData()

    def expiries(self, underlying: str) -> list[date]:
        data = self.client.nse_json("/api/option-chain-contract-info", {"symbol": underlying.upper()})
        return sorted(parse_nse_date(d) for d in data.get("expiryDates", []))

    def chain(self, underlying: str, expiry: date) -> OptionChain:
        return parse_nse_chain(
            self.chain_payload(underlying, expiry), underlying, expiry, self.fallback_lot_size(underlying)
        )

    def chain_payload(self, underlying: str, expiry: date) -> dict:
        """NSE's option-chain JSON for one expiry, as it came."""
        params = {
            "type": "Indices" if is_index(underlying) else "Equity",
            "symbol": underlying.upper(),
            "expiry": expiry.strftime("%d-%b-%Y"),
        }
        return self.client.nse_json("/api/option-chain-v3", params)
