"""The chain route's strike sets (story P9, W13: "the route picks the strikes"): one stored page per expiry holds every
strike within 10% ("all"); the route serves "near" (the 21 strikes around the ATM strike) and "band" (within 5% of
NIFTY) from it. Used here to check our stored pages against W13's examples, as the dashboard's route serves them."""

from __future__ import annotations

NEAR_EACH_SIDE = 10  # "near": the ATM strike and 10 either side
BAND = 0.05  # "band": strikes within 5% of NIFTY (the 3 pm band)
ALL = "all"


def strikes_view(stored: dict, strikes: str, spot: float, atm: float) -> dict:
    """The served ChainRows for a strike set, from the expiry's stored page (all strikes); `spot` from the underlying
    block, `atm` from that expiry's summary in the expiries block."""
    rows = stored["rows"]
    if strikes == "near":
        i = next(n for n, r in enumerate(rows) if r["strike"] == atm)
        rows = rows[max(0, i - NEAR_EACH_SIDE) : i + NEAR_EACH_SIDE + 1]
    elif strikes == "band":
        rows = [r for r in rows if abs(r["strike"] - spot) <= spot * BAND]
    return {**stored, "strikes": strikes, "rows": rows}
