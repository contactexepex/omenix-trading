"""NSE Clearing's SPAN risk-parameter file (story A14): the NIFTY parts a one-expiry option structure's margin needs.

The file is a zip holding one SPAN 4 XML file (`nsccl.<YYYYMMDD>.<i1..i5|s>.spn`, about 50 MB). It is read in one
pass, keeping only the symbol's index (`phyPf`), futures (`futPf`), options (`oopPf`) and its combined-commodity
definition (`ccDef`). Each option has a risk array: its loss per unit, in rupees, for one bought unit under 16 price
and volatility scenarios (the two extreme ones already weighted).

The margin method is modelled exactly only when the file's own definition says so, so anything else is refused
(`BadSpanFile`, a `BadFile`): a zero short-option minimum, unit adjustment rates and contract value factors, and one
16-value risk array per option. Story A14c reads history too: with `allow_short_option_minimum` (never A14's daily job,
which must keep refusing a method change), one GROSS minimum rate per short unit is read, as 2020's files charged
(`nsccl.20200407.i1`: Rs 405 a short unit, about 5% of the index). Spread charges exist only between different expiries,
which a one-expiry structure never has. Scanning risk is summed over scan tiers (on a weekly expiry day the expiring
series has a tier of its own); a one-expiry structure lies in one tier, so its scanning risk is that tier's, which the
calculator checks.
"""

from __future__ import annotations

import io
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass
from datetime import date, datetime
from xml.etree.ElementTree import Element

from ..constants import NIFTY_SYMBOL, OPTION_CALL, OPTION_PUT, SPAN_BOD_CREATED_BEFORE
from ..fo_bhavcopy import BadFile
from ..models import IST

SCENARIOS = 16
CREATED_FORMAT = "%Y%m%d%H%M"
SHORT_OPTION_MINIMUM_METHOD = "GROSS"  # SPAN charges the minimum on every short unit, hedged or not
KEPT_PARTS = ("phyPf", "futPf", "oopPf", "ccDef")  # a portfolio is named by `pfCode`, a definition by `cc`
OPTION_KINDS = {"C": OPTION_CALL, "P": OPTION_PUT}

Contract = tuple[float, str]  # (strike, "CE" or "PE"), as the structures name a contract


class BadSpanFile(BadFile):
    """Not a SPAN file, or one whose margin method for the symbol is not the one modelled: no margin from it."""


@dataclass(frozen=True)
class SpanOption:
    price: float
    risk: tuple[float, ...]  # loss of one bought unit in each of the 16 scenarios, rupees


@dataclass(frozen=True)
class SpanFile:
    name: str
    created: datetime  # the file's own `<created>` stamp, IST
    underlying: float  # the index's price in the file (its last close for a beginning-of-day file)
    monthly_expiries: tuple[date, ...]  # the futures' expiries
    series: dict[date, dict[Contract, SpanOption]]  # options by expiry and contract
    scan_tiers: tuple[tuple[date, date], ...]  # (first, last) expiry of each scan tier
    short_option_minimum: float = 0.0  # rupees per short unit (SPAN's GROSS minimum); 0 in every file since 2020

    def tiers_holding(self, expiry: date) -> int:
        return sum(first <= expiry <= last for first, last in self.scan_tiers)

    def deadline(self, day: date) -> datetime:
        """A14's point-in-time rule: a beginning-of-day file counts for `day` only if written before 09:00 IST."""
        return datetime.combine(day, SPAN_BOD_CREATED_BEFORE, tzinfo=self.created.tzinfo)

    def written_in_time(self, day: date) -> bool:
        return self.created < self.deadline(day)


def read_span_file(data: bytes, filename: str, symbol: str = NIFTY_SYMBOL,
                   allow_short_option_minimum: bool = False) -> SpanFile:  # fmt: skip
    """The symbol's parts of a zipped SPAN file; BadSpanFile when it is damaged or outside the modelled method."""
    created, parts = _parse(_unzip(data, filename), filename, symbol)
    history = allow_short_option_minimum
    minimum = _check_method(parts["ccDef"], filename, history)
    try:
        return SpanFile(filename, created, _underlying(parts["phyPf"], filename), _expiries(parts["futPf"]),
                        _series(parts["oopPf"], filename), _scan_tiers(parts["ccDef"], filename, history),
                        minimum)  # fmt: skip
    except BadSpanFile:
        raise
    except (TypeError, ValueError) as exc:  # an unreadable date or risk value
        raise BadSpanFile(f"{filename}: unreadable value ({exc})") from exc


def _unzip(data: bytes, filename: str) -> bytes:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            members = [m for m in archive.namelist() if m.endswith(".spn")]
            if len(members) != 1:
                raise BadSpanFile(f"{filename}: expected one .spn file, found {members}")
            return archive.read(members[0])
    except (zipfile.BadZipFile, KeyError, EOFError) as exc:
        raise BadSpanFile(f"{filename}: not a readable zip ({exc})") from exc


def _parse(xml: bytes, filename: str, symbol: str) -> tuple[datetime, dict[str, Element]]:
    created, parts = None, {}
    try:
        for _, element in ET.iterparse(io.BytesIO(xml), events=("end",)):
            if element.tag == "created" and created is None:
                created = element.text
            elif element.tag in KEPT_PARTS:
                if (element.findtext("pfCode") or element.findtext("cc")) != symbol:
                    element.clear()  # another symbol: free its memory
                elif element.tag in parts:
                    raise BadSpanFile(f"{filename}: more than one {element.tag} for {symbol}")
                else:
                    parts[element.tag] = element
    except ET.ParseError as exc:
        raise BadSpanFile(f"{filename}: not valid XML ({exc})") from exc
    missing = [part for part in KEPT_PARTS if part not in parts]
    if missing or created is None:
        raise BadSpanFile(f"{filename}: no {', '.join(missing or ['created'])} for {symbol}")
    return _created(created, filename), parts


def _created(text: str, filename: str) -> datetime:
    try:
        return datetime.strptime(text.strip(), CREATED_FORMAT).replace(tzinfo=IST)
    except ValueError as exc:
        raise BadSpanFile(f"{filename}: unreadable created stamp {text!r}") from exc


def _number(element: Element, tag: str, filename: str) -> float:
    try:
        return float(element.findtext(tag))
    except (TypeError, ValueError) as exc:
        raise BadSpanFile(f"{filename}: missing or unreadable <{tag}>") from exc


def _scan_tiers(definition: Element, filename: str, history: bool) -> tuple[tuple[date, date], ...]:
    """The scan tiers; a history read (story A14c) takes a file without `scanTiers` (2020's) as one tier, as SPAN
    scans a combined commodity with no tiers defined."""
    tiers = tuple((_day(t.findtext("sPe")), _day(t.findtext("ePe"))) for t in definition.iterfind("scanTiers/tier"))
    if not tiers and history and definition.find("scanTiers") is None:
        return ((date.min, date.max),)
    if not tiers:
        raise BadSpanFile(f"{filename}: no scan tier")
    return tiers


def _check_method(definition: Element, filename: str, allow_minimum: bool) -> float:
    """The short-option minimum per short unit (0 unless allowed); anything not modelled is refused by name."""
    if any(_number(rate, "val", filename) != 1 for rate in definition.findall("adjRate")):
        raise BadSpanFile(f"{filename}: an adjustment rate other than 1 is not modelled")
    tiers = definition.find("somTiers")
    rates = [] if tiers is None else [_number(rate, "val", filename) for rate in tiers.iter("rate")]
    if tiers is None or not rates:
        raise BadSpanFile(f"{filename}: no short-option minimum definition")
    if all(rate == 0 for rate in rates):
        return 0.0
    if not allow_minimum:
        raise BadSpanFile(f"{filename}: a short-option minimum charge is not modelled")
    if len(rates) != 1 or definition.findtext("somMeth", "").strip() != SHORT_OPTION_MINIMUM_METHOD or rates[0] < 0:
        raise BadSpanFile(f"{filename}: only one GROSS short-option minimum rate is modelled, found {rates}")
    return rates[0]


def _underlying(index: Element, filename: str) -> float:
    prices = [_number(phy, "p", filename) for phy in index.findall("phy")]
    if len(prices) != 1 or not prices[0] > 0:
        raise BadSpanFile(f"{filename}: the index needs one positive price, found {prices}")
    return prices[0]


def _day(text: str | None) -> date:
    return datetime.strptime((text or "").strip(), "%Y%m%d").date()


def _expiries(futures: Element) -> tuple[date, ...]:
    return tuple(sorted(_day(fut.findtext("pe")) for fut in futures.findall("fut")))


def _series(options: Element, filename: str) -> dict[date, dict[Contract, SpanOption]]:
    if _number(options, "cvf", filename) != 1:
        raise BadSpanFile(f"{filename}: a contract value factor other than 1 is not modelled")
    found = {}
    for series in options.findall("series"):
        if _number(series, "cvf", filename) != 1 or _number(series, "sc", filename) != 1:
            raise BadSpanFile(f"{filename}: series {series.findtext('pe')} is scaled, which is not modelled")
        found[_day(series.findtext("pe"))] = dict(_option(opt, filename) for opt in series.findall("opt"))
    return found


def _option(option: Element, filename: str) -> tuple[Contract, SpanOption]:
    kind, arrays = OPTION_KINDS.get(option.findtext("o") or ""), option.findall("ra")
    if kind is None or len(arrays) != 1:
        raise BadSpanFile(f"{filename}: an option needs a kind C or P and one risk array")
    risk = tuple(float(value.text) for value in arrays[0].findall("a"))
    if len(risk) != SCENARIOS:
        raise BadSpanFile(f"{filename}: a risk array has {len(risk)} scenarios, not {SCENARIOS}")
    contract = (_number(option, "k", filename), kind)
    return contract, SpanOption(_number(option, "p", filename), risk)
