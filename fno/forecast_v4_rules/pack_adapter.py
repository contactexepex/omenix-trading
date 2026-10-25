"""From G10's released pack to the capture's `PackInputs` (story G7b completion, part b2): the release record's label
and SHA-256 kept apart from the bytes read, IV30 from volatility points to a fraction, the future as a live-quote
candidate (its last trade time, else its day volume, for A4's traded-today rule) and the pack's own `v4_expiry`, never
recomputed. A `system_late` day has no pack: its inputs carry the label only, and the capture writes nothing."""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from datetime import date

from ..constants import V4_DAY_A
from ..v4_pack.model import FutureQuote, Pack
from ..v4_pack.release import ReleaseRecord
from .implied import IvPoint
from .live_quotes import TwoSided
from .pack_capture import PackInputs

POINTS_PER_UNIT = 100.0  # the pack's IV30 is in volatility points (G1's unit)


def future_quote(future: FutureQuote) -> TwoSided | None:
    """None when the provider's quote failed (no bid and no ask): V5 then voids itself (`no_future_quote`)."""
    if future.bid is None and future.ask is None:
        return None
    traded = None if future.volume is None else future.volume > 0
    return TwoSided(future.bid, future.ask, future.last_trade_time, traded)


def pack_inputs(release: ReleaseRecord, pack: Pack | None, pack_bytes: bytes,
                listed: Sequence[date] | None) -> PackInputs:  # fmt: skip
    """`pack`/`pack_bytes`: the released pack as read and verified (`ReleasedPacks`), None/b"" on a system_late day."""
    if release.label != V4_DAY_A or pack is None:
        return PackInputs(release.day, release.label, release.pack_sha256, "", None, 0.0, (), release.day, None, None,
                          listed)  # fmt: skip
    iv30 = IvPoint(pack.iv30.value / POINTS_PER_UNIT, pack.iv30.flagged)
    return PackInputs(release.day, release.label, release.pack_sha256, hashlib.sha256(pack_bytes).hexdigest(), iv30,
                      pack.spot.value, pack.chain, pack.future.expiry, future_quote(pack.future), pack.v4_expiry,
                      listed)  # fmt: skip
