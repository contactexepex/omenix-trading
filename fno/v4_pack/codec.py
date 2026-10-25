"""The pack's stored form (story G10 part 2, section 1): canonical JSON (sorted keys, UTF-8, no spaces), whose SHA-256
of the stored bytes is the pack's identity. Reading checks the SHA, the format and that the bytes are canonical, so one
pack has exactly one identity; any field observed outside the 14:30-14:40 window is refused."""

from __future__ import annotations

import hashlib
import json
import math
from datetime import date, datetime

from ..constants import V4_DAY_A
from ..forecast_v4.terms import V4_CAPTURE_START, V4_PACK_WINDOW_END
from ..models import IST
from .model import FIELD_NAMES, ChainQuote, FutureQuote, Iv30, Level, Pack, VixLevel

PACK_LABELS = (V4_DAY_A,)  # a system_late day has no pack
OPTION_KINDS = ("CE", "PE")
MID = "mid"


class PackFormatError(ValueError):
    """Bytes that are not a valid canonical pack: nothing reads them."""


def pack_bytes(pack: Pack) -> bytes:
    """The bytes stored in Drive; the same pack always gives the same bytes."""
    return json.dumps(_encode(pack), sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")  # fmt: skip


def pack_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_pack(data: bytes, released_sha256: str) -> Pack:
    """The pack the release record names; refuses other bytes, a broken format or a non-canonical encoding."""
    if pack_sha256(data) != released_sha256:
        raise PackFormatError("the pack's bytes do not match the released SHA-256")
    try:
        pack = _pack(json.loads(data.decode("utf-8")))
    except (ValueError, TypeError, KeyError, AttributeError) as error:
        raise PackFormatError(f"not a v4 pack: {error}") from None
    if pack_bytes(pack) != data:
        raise PackFormatError("the pack's bytes are not in canonical form")
    return pack


def _encode(value):
    if isinstance(value, datetime):
        if value.tzinfo is None:
            raise PackFormatError("every time in a pack carries its offset")
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, tuple):
        return [_encode(item) for item in value]
    if type(value) in FIELD_NAMES:
        body = {name: _encode(getattr(value, name)) for name in FIELD_NAMES[type(value)]}
        if isinstance(value, ChainQuote) and value.mid is not None:
            body[MID] = value.mid
        return body
    if isinstance(value, float) and not math.isfinite(value):
        raise PackFormatError("a pack holds finite numbers only")
    return value


def _pack(body: dict) -> Pack:
    _keys(body, Pack)
    day = date.fromisoformat(body["day"])
    if body["label"] not in PACK_LABELS:
        raise PackFormatError(f"label {body['label']!r} is not A")
    seen = _Window(day)
    chain = tuple(_chain_quote(item, seen) for item in body["chain"])
    if not chain:
        raise PackFormatError("the chain is empty")
    spot = _keys(body["spot"], Level)
    vix = _keys(body["india_vix"], VixLevel)
    pack = Pack(day, _text(body["label"]), _text(body["source"]), _text(body["provider"]),
                _text(body["captured_from"]), _time(body["released_at"]),
                Level(_number(spot["value"]), seen(spot["observed_at"])), _future(body["future"], seen),
                VixLevel(_number(vix["value"]), seen(vix["observed_at"]), _time_or_none(vix["nse_time"])), chain,
                _iv30(body["iv30"], seen), _date_or_none(body["v4_expiry"]))  # fmt: skip
    if pack.future.expiry <= day:
        raise PackFormatError("the future's expiry is not after the day")
    return pack


def _future(body: dict, seen: _Window) -> FutureQuote:
    _keys(body, FutureQuote)
    sides = (_number_or_none(body[name]) for name in ("last", "bid", "ask"))
    volume = body["volume"]
    if volume is not None and (isinstance(volume, bool) or not isinstance(volume, int) or volume < 0):
        raise PackFormatError("the future's volume is a whole count or absent")
    quoted = seen(body["quoted_at"]) if body["quoted_at"] is not None else None
    return FutureQuote(date.fromisoformat(body["expiry"]), *sides, seen(body["observed_at"]),
                       _time_or_none(body["last_trade_time"]), volume, quoted)  # fmt: skip


def _chain_quote(body: dict, seen: _Window) -> ChainQuote:
    _keys({k: v for k, v in body.items() if k != MID}, ChainQuote)
    if body["kind"] not in OPTION_KINDS:
        raise PackFormatError(f"option kind {body['kind']!r} is not CE or PE")
    return ChainQuote(date.fromisoformat(body["expiry"]), _number(body["strike"]), body["kind"],
                      _number_or_none(body["bid"]), _number_or_none(body["ask"]), _number_or_none(body["last"]),
                      _time_or_none(body["last_trade_time"]), seen(body["observed_at"]))  # fmt: skip


def _iv30(body: dict, seen: _Window) -> Iv30:
    _keys(body, Iv30)
    if not isinstance(body["flagged"], bool) or not body["expiries"]:
        raise PackFormatError("iv30 needs a true/false flag and its expiries")
    expiries = tuple(date.fromisoformat(item) for item in body["expiries"])
    return Iv30(_number(body["value"]), body["flagged"], expiries, _text(body["method"]), seen(body["observed_by"]))


def capture_window(day: date) -> tuple[datetime, datetime]:
    """The day's capture window, 14:30:00-14:40:00 IST, both ends inside."""
    return datetime.combine(day, V4_CAPTURE_START, IST), datetime.combine(day, V4_PACK_WINDOW_END, IST)


class _Window:
    """Every observed time of a pack lies in its day's capture window, 14:30:00-14:40:00 IST."""

    def __init__(self, day: date):
        self.start, self.end = capture_window(day)

    def __call__(self, text: str) -> datetime:
        observed = _time(text)
        if not self.start <= observed <= self.end:
            raise PackFormatError(f"observed at {text}, outside the {V4_CAPTURE_START:%H:%M}-"
                                  f"{V4_PACK_WINDOW_END:%H:%M} window")  # fmt: skip
        return observed


def _keys(body: dict, kind: type) -> dict:
    if set(body) != set(FIELD_NAMES[kind]):
        raise PackFormatError(f"{kind.__name__} fields differ: {sorted(set(body) ^ set(FIELD_NAMES[kind]))}")
    return body


def _time(text: str) -> datetime:
    found = datetime.fromisoformat(text)
    if found.tzinfo is None:
        raise PackFormatError(f"{text} has no offset")
    return found


def _time_or_none(text: str | None) -> datetime | None:
    return None if text is None else _time(text)


def _number(value) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float) or not math.isfinite(value):
        raise PackFormatError(f"{value!r} is not a finite number")
    return float(value)


def _number_or_none(value) -> float | None:
    return None if value is None else _number(value)


def _text(value) -> str:
    if not isinstance(value, str) or not value:
        raise PackFormatError(f"{value!r} is not a non-empty text")
    return value


def _date_or_none(text) -> date | None:
    return None if text is None else date.fromisoformat(text)
