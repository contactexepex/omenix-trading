"""Corporate actions from NSE's own list (story P6; judge 42), read and classified by the share-basis change they
imply:

- A split or consolidation ("Face Value Split ... From Rs 5/- Per Share To Re 1/- Per Share") has the ratio old face
  value / new face value; a bonus a:b (a new shares for b held) the ratio (a + b) / b.
- A demerger has no ratio in NSE's list (the ex-date price is exchange-discovered), nor does another scheme of
  arrangement, an amalgamation or a capital reduction. A bonus of preference shares ("Scheme Of Arrangement - Bonus
  NCRPS") is another security and changes no equity price, like a dividend.
- Dividends, buy-backs, interest, distributions and rights issues change no price here."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date, datetime
from math import prod

from fno.shared.fo_bhavcopy import BadFile

FACE_VALUE = re.compile(r"From\s+R[es]+\.?\s*([\d.]+)\s*/-.*?To\s+R[es]+\.?\s*([\d.]+)\s*/-", re.IGNORECASE)
BONUS = re.compile(r"^\s*Bonus\s+(\d+)\s*:\s*(\d+)", re.IGNORECASE)
DEMERGER = "demerger"
PREFERENCE_BONUS = "bonus ncrps"  # preference shares: another security
HISTORY_BREAKS = ("arrangement", "amalgamation", "capital reduction")
EX_DATE_FORMAT = "%d-%b-%Y"
KIND_RATIO, KIND_DEMERGER, KIND_BREAK, KIND_NONE = "ratio", "demerger", "break", "none"


@dataclass(frozen=True)
class CorporateAction:
    symbol: str
    ex_date: date
    subject: str
    kind: str  # ratio (split, bonus), demerger, break (no ratio anywhere) or none (no price change)
    factor: float | None = None  # a ratio action's divisor of earlier prices

    @property
    def changes_shares(self) -> bool:
        return self.kind != KIND_NONE


def classify(subject: str) -> tuple[str, float | None]:
    """(kind, factor) of an action's description in NSE's list."""
    text = subject.strip().lower()
    if text.startswith(DEMERGER):
        return KIND_DEMERGER, None
    if PREFERENCE_BONUS in text:
        return KIND_NONE, None
    if any(word in text for word in HISTORY_BREAKS):
        return KIND_BREAK, None
    factor = prod(float(old) / float(new) for old, new in FACE_VALUE.findall(subject))
    factor *= prod((int(new) + int(held)) / int(held) for new, held in BONUS.findall(subject))
    return (KIND_RATIO, factor) if factor != 1.0 else (KIND_NONE, None)


def read_corporate_actions(data: bytes, filename: str) -> list[CorporateAction]:
    """Every action in NSE's corporate-actions list (JSON from its website), classified."""
    try:
        records = json.loads(data.decode("utf-8"))
        return [_action(r) for r in records if r.get("exDate") not in (None, "-")]
    except (ValueError, KeyError, TypeError, AttributeError) as exc:
        raise BadFile(f"{filename}: not NSE's corporate-actions list ({exc})") from exc


def _action(record: dict) -> CorporateAction:
    ex_date = datetime.strptime(record["exDate"], EX_DATE_FORMAT).date()
    return CorporateAction(record["symbol"], ex_date, record["subject"], *classify(record["subject"]))
