"""Story G11, every part of a v4 input checked before `brief` shows any of it (review of dfb26381): the fired text is
untrusted, and under v4 it carries the whole input, so each field must be the shape `v4_input.py` writes: known keys
only, numbers where numbers belong, ISO dates, a pack label of a few code characters (no free text reaches the model),
and Hybrid's envelope exactly the one its rules values and its registered widths give (`Envelope.span`), so an edited
envelope can never let a seal through. Standard library only: the routine runs it."""

from __future__ import annotations

import re
from datetime import date, datetime

from ..forecast_v4.terms import POINT_QUESTIONS
from .envelope import Envelope
from .pointer import PointerRefused, is_number, is_probability
from .v4_input import CHAIN_COLUMNS
from .versions import BookVersion

PACK_FIELDS = ["atm_by_expiry", "chain_near_spot", "future", "india_vix", "iv30", "label", "released_at", "spot"]
DERIVED_FIELDS = ["nifty_1430_change_pct_vs_previous_close", "trailing_rv20_points_with_1430_spot",
                  "vix_1430_change_vs_previous_close"]  # fmt: skip
ATM_FIELDS = ["call_mid", "expiry", "put_mid", "straddle_mid", "strike"]
LABEL = re.compile(r"[A-Za-z0-9_-]{1,8}")
NAME = re.compile(r"[a-z0-9_]{1,40}")  # a forecaster's registered name, or `primary_baseline`
KINDS = ("CE", "PE")


def check_v4_input(built: dict, questions: list[str], registered: BookVersion) -> None:
    """PointerRefused naming the first part that is not what the firer writes."""
    _pack(built["pack"])
    _closes(built["closes_before_day"])
    _exact(built["derived"], DERIVED_FIELDS, "derived")
    if not all(_number_or_null(v) for v in built["derived"].values()):
        raise PointerRefused("derived facts must be numbers or null")
    _history(built["history"], questions)
    if "rules" in built:
        _rules(built["rules"], questions, registered)


def _pack(pack) -> None:
    _exact(pack, PACK_FIELDS, "pack")
    if not isinstance(pack["label"], str) or not LABEL.fullmatch(pack["label"]):
        raise PointerRefused("pack.label must be a short code")
    _datetime(pack["released_at"], "pack.released_at")
    _positive(pack["spot"], "pack.spot")
    _positive(pack["india_vix"], "pack.india_vix")
    _exact(pack["future"], ["ask", "bid", "expiry", "last"], "pack.future")
    _date(pack["future"]["expiry"], "pack.future.expiry")
    _all_numbers_or_null([pack["future"][k] for k in ("ask", "bid", "last")], "pack.future")
    iv30 = pack["iv30"]
    _exact(iv30, ["expiries", "single_expiry", "value"], "pack.iv30")
    if not isinstance(iv30["single_expiry"], bool) or not _number_or_null(iv30["value"]):
        raise PointerRefused("pack.iv30 must be a number or null with a true/false single_expiry")
    _dates(iv30["expiries"], "pack.iv30.expiries")
    _list(pack["atm_by_expiry"], "pack.atm_by_expiry")
    for atm in pack["atm_by_expiry"]:
        _exact(atm, ATM_FIELDS, "pack.atm_by_expiry")
        _date(atm["expiry"], "pack.atm_by_expiry.expiry")
        _positive(atm["strike"], "pack.atm_by_expiry.strike")
        _all_numbers_or_null([atm[k] for k in ("call_mid", "put_mid", "straddle_mid")], "pack.atm_by_expiry")
    _chain(pack["chain_near_spot"])


def _chain(chain) -> None:
    _exact(chain, ["columns", "rows"], "pack.chain_near_spot")
    if chain["columns"] != CHAIN_COLUMNS:
        raise PointerRefused(f"pack.chain_near_spot.columns must be {CHAIN_COLUMNS}")
    _list(chain["rows"], "pack.chain_near_spot.rows")
    for row in chain["rows"]:
        if not isinstance(row, list) or len(row) != len(CHAIN_COLUMNS) or row[1] not in KINDS:
            raise PointerRefused("a chain row must be [strike, CE or PE, bid, ask, last]")
        _positive(row[0], "a chain row's strike")
        _all_numbers_or_null(row[2:], "a chain row")


def _closes(closes) -> None:
    _exact(closes, ["dates", "nifty", "vix"], "closes_before_day")
    _dates(closes["dates"], "closes_before_day.dates")
    for name in ("nifty", "vix"):
        _list(closes[name], f"closes_before_day.{name}")
        if len(closes[name]) != len(closes["dates"]) or not all(is_number(v) and v > 0 for v in closes[name]):
            raise PointerRefused(f"closes_before_day.{name} must be one number above 0 per date")


def _history(history, questions: list[str]) -> None:
    if not isinstance(history, dict) or not set(history) <= set(questions) & POINT_QUESTIONS:
        raise PointerRefused("history must hold only the day's point questions")
    for question, rows in history.items():
        _exact(rows, ["dates", "rv_s"], f"history.{question}")
        _dates(rows["dates"], f"history.{question}.dates")
        _list(rows["rv_s"], f"history.{question}.rv_s")
        rv_ok = all(v is None or (is_number(v) and v >= 0) for v in rows["rv_s"])
        if len(rows["rv_s"]) != len(rows["dates"]) or not rv_ok:
            raise PointerRefused(f"history.{question}.rv_s must be one number >= 0 (or null: void) per date")


def _rules(rules, questions: list[str], registered: BookVersion) -> None:
    _exact(rules, ["by_question", "envelope"], "rules")
    by_question = rules["by_question"]
    _exact(by_question, sorted(questions), "rules.by_question")
    for question, by_name in by_question.items():
        kind = (lambda v: is_number(v) and v > 0) if question in POINT_QUESTIONS else is_probability
        unit = "variance above 0" if question in POINT_QUESTIONS else "probability in [0, 1]"
        if not isinstance(by_name, dict) or not all(isinstance(n, str) and NAME.fullmatch(n) for n in by_name):
            raise PointerRefused(f"{question}: rules must name registered forecasters")
        if not all(v is None or kind(v) for v in by_name.values()):
            raise PointerRefused(f"{question}: a rule's value must be a {unit} or null")
    spans = {q: [v for v in by_question[q].values() if v is not None] for q in questions}
    expected = Envelope.span(spans, registered.envelope_width, registered.point_envelope_width).as_json()
    if rules["envelope"] != expected:
        raise PointerRefused("rules.envelope is not the one its rules values and the registered widths give")


def _exact(value, keys: list[str], where: str) -> None:
    if not isinstance(value, dict) or sorted(value) != sorted(keys):
        raise PointerRefused(f"{where} must hold exactly {', '.join(sorted(keys))}")


def _list(value, where: str) -> None:
    if not isinstance(value, list):
        raise PointerRefused(f"{where} must be a list")


def _dates(values, where: str) -> None:
    _list(values, where)
    for value in values:
        _date(value, where)


def _date(value, where: str) -> None:
    try:
        date.fromisoformat(value)
    except (TypeError, ValueError):
        raise PointerRefused(f"{where} must hold YYYY-MM-DD dates") from None


def _datetime(value, where: str) -> None:
    try:
        datetime.fromisoformat(value)
    except (TypeError, ValueError):
        raise PointerRefused(f"{where} must be an ISO time") from None


def _positive(value, where: str) -> None:
    if not (is_number(value) and value > 0):
        raise PointerRefused(f"{where} must be a number above 0")


def _number_or_null(value) -> bool:
    return value is None or is_number(value)


def _all_numbers_or_null(values, where: str) -> None:
    if not all(_number_or_null(v) for v in values):
        raise PointerRefused(f"{where} must hold numbers or null")
