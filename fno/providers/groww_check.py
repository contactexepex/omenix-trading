"""`python -m fno groww-check`: proves the Groww data connection works, without printing any secret.

Prints the field names Groww returns for a chain leg and a quote, so the parsers can be checked against reality.
"""

from __future__ import annotations

from . import get_provider
from .groww import _payload

CHECK_UNDERLYING = "NIFTY"


def groww_check_lines(cfg: dict, underlying: str = CHECK_UNDERLYING) -> list[str]:
    provider = get_provider("groww", cfg)  # GW1: the sign-in alert and A16's quiet windows, as every reader by hand
    api = provider.api
    lines = ["signed in to Groww (token obtained)"]
    expiries = provider.expiries(underlying)
    lines.append(f"{underlying} expiries: {', '.join(str(d) for d in expiries[:4])}")
    raw = api.get_option_chain(exchange=api.EXCHANGE_NSE, underlying=underlying, expiry_date=expiries[0].isoformat())
    chain = provider.chain(underlying, expiries[0])
    atm = chain.atm_strike()
    lines.append(
        f"chain {expiries[0]}: spot {chain.spot:,.2f}, {len(chain.strikes())} strikes, at the money {atm:,.0f}"
    )
    legs = _payload(raw).get("strikes", {})
    atm_legs = legs.get(str(int(atm))) or legs.get(str(atm)) or next(iter(legs.values()), {})
    call = (atm_legs or {}).get("CE") or {}
    lines.append(f"chain leg fields: {sorted(call)}")
    symbol = call.get("trading_symbol")
    if symbol:
        quote = _payload(api.get_quote(trading_symbol=symbol, exchange=api.EXCHANGE_NSE, segment=api.SEGMENT_FNO))
        lines.append(f"quote {symbol} fields: {sorted(quote)}")
        lines.append(f"quote bid/ask: {quote.get('bid_price')} / {quote.get('offer_price')}")
    return lines
