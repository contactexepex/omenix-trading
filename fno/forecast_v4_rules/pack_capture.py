"""The post-release capture (story G7b completion, part b2): one session's pack-derived v4 rows, written once to Drive
before 15:10 IST. Inputs come through `PackInputs`, this module's own interface, so it does not depend on the pack's
file format (G10's). Rows: raw implied (V2, V3), premium-adjusted implied (V1, V2, V3; V1's ratio by wording W3's
switch), V5's option-implied probability, V4's and V5's base rates and their two rule forecasters; and V4's and V5's
frozen terms. Every pack-reading row names the released pack's SHA-256 and passes G10's binding guard; the base
rates read no pack and name none. Nothing is written on a `system_late` day, and nothing from 15:10:00 IST (checked
before every write). A rerun skips a row already written the same (`Record.same_as`, `made_at` aside); a different
row for the day is refused."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import date, datetime

from ..constants import (
    V1_RV_1S,
    V2_RV_5S,
    V3_RV_20S,
    V4_BASELINE_BASE_RATE,
    V4_BASELINE_OPTION_IMPLIED_PROB,
    V4_BASELINE_PREMIUM_ADJUSTED,
    V4_BASELINE_RAW_IMPLIED,
    V4_DAY_A,
    V4_RV_BELOW_WEEKLY_IV,
    V5_INSIDE_STRADDLE,
)
from ..forecast_v4.terms import V4_DEADLINE
from ..models import IST
from ..v4_pack.guard import check_pack_binding
from ..v4_pack.model import ChainQuote
from .baselines import BaseRate, Ewma, Value
from .constants import V4_BASELINE_PREMIUM_ADJUSTED_INTRADAY, V4_RULE_V4_EWMA_CHI2, V4_RULE_V5_EWMA_LOGNORMAL
from .drive_records import live_bytes, live_path, read_live
from .implied import ImpliedBaselines, IvPoint, first_session_of_month
from .intraday_series import RATIO_CLOSE_PROXY, RATIO_INTRADAY
from .live_quotes import TwoSided
from .option_probabilities import option_implied_probability, v4_ewma_chi2, v5_ewma_lognormal
from .option_terms import OptionTerms, OptionTermsRule, Void
from .records import BASELINE, LIVE, RULE, SLOT_REPORTED, VERSION, Record, record
from .series import Outcome

TERMS_FOLDER = "v4/terms"
PACK_FORECASTERS = {  # (forecaster, question) -> (kind, slot); every one reported only (V3-V5) or a baseline
    (V4_BASELINE_RAW_IMPLIED, V2_RV_5S): (BASELINE, SLOT_REPORTED),
    (V4_BASELINE_RAW_IMPLIED, V3_RV_20S): (BASELINE, SLOT_REPORTED),
    (V4_BASELINE_PREMIUM_ADJUSTED, V1_RV_1S): (BASELINE, SLOT_REPORTED),
    (V4_BASELINE_PREMIUM_ADJUSTED, V2_RV_5S): (BASELINE, SLOT_REPORTED),
    (V4_BASELINE_PREMIUM_ADJUSTED, V3_RV_20S): (BASELINE, SLOT_REPORTED),
    (V4_BASELINE_PREMIUM_ADJUSTED_INTRADAY, V1_RV_1S): (BASELINE, SLOT_REPORTED),  # W3's yardstick A
    (V4_BASELINE_PREMIUM_ADJUSTED_INTRADAY, V2_RV_5S): (BASELINE, SLOT_REPORTED),  # for part f's V2 series
    (V4_BASELINE_PREMIUM_ADJUSTED_INTRADAY, V3_RV_20S): (BASELINE, SLOT_REPORTED),  # for part f's V3 series
    (V4_BASELINE_OPTION_IMPLIED_PROB, V5_INSIDE_STRADDLE): (BASELINE, SLOT_REPORTED),
    (V4_BASELINE_BASE_RATE, V4_RV_BELOW_WEEKLY_IV): (BASELINE, SLOT_REPORTED),
    (V4_BASELINE_BASE_RATE, V5_INSIDE_STRADDLE): (BASELINE, SLOT_REPORTED),
    (V4_RULE_V4_EWMA_CHI2, V4_RV_BELOW_WEEKLY_IV): (RULE, SLOT_REPORTED),
    (V4_RULE_V5_EWMA_LOGNORMAL, V5_INSIDE_STRADDLE): (RULE, SLOT_REPORTED),
}
READS_NO_PACK = frozenset({V4_BASELINE_BASE_RATE})
YARDSTICKS = {RATIO_CLOSE_PROXY: V4_BASELINE_PREMIUM_ADJUSTED, RATIO_INTRADAY: V4_BASELINE_PREMIUM_ADJUSTED_INTRADAY}
RISK_NEUTRAL = f"{VERSION} risk-neutral, not a real-world probability"  # protocol 3.1's label for V5's baseline
NOT_TODAY = "{day} is not today ({today}): a live row is made on its own day only"
NOT_RELEASED = "{day} is {label}: no pack was released, so nothing is written (the day is out for everyone)"
PAST_DEADLINE = "{now:%H:%M:%S} IST is at or after the {deadline:%H:%M} deadline: {path} and later rows not written"
CHANGED_ROW = "{path}: a different row is already written for this day"


@dataclass(frozen=True)
class PackInputs:
    """The released pack's fields this capture reads, and the release record's label and SHA-256 kept apart from the
    loaded pack's (filled from G10's `ReleasedPacks` by the wiring)."""

    day: date
    release_label: str  # A or system_late, from the release record
    release_sha256: str  # the release record's pack_sha256 ("" on a system_late day)
    pack_sha256: str  # the SHA-256 of the pack bytes this capture read
    iv30: IvPoint | None  # a fraction (the pack holds points)
    spot: float
    chain: Sequence[ChainQuote]
    future_expiry: date
    future: TwoSided | None
    v4_expiry: date | None
    listed: Sequence[date] | None  # NSE's listed expiries known before the day (`ListedExpiries.listed`)


class CaptureRefused(RuntimeError):
    """Not the day's own run, a system_late day or past the deadline: nothing more written (O1 alerts a refusal)."""


class ChangedRow(RuntimeError):
    """A different row or terms already written for the day: rows never change, so this is a failure."""


def terms_path(question: str, day: date) -> str:
    return f"{TERMS_FOLDER}/{question}/{day:%Y}/{day.isoformat()}.json"


def terms_bytes(terms: OptionTerms | Void, pack_sha256: str) -> bytes:
    return json.dumps({**asdict(terms), "pack_sha256": pack_sha256}, sort_keys=True, default=str).encode("utf-8")


def digest(*parts) -> str:
    return hashlib.sha256("|".join(repr(p) for p in parts).encode()).hexdigest()


class PackForecasts:
    """One day's pack-derived values and records."""

    def __init__(self, implied: Mapping[str, Mapping[str, ImpliedBaselines]], ewma: Ewma, terms: OptionTermsRule,
                 base_outcomes: Mapping[str, list[Outcome]], method: str):  # fmt: skip
        """`implied[measure][question]`: V1's, V2's and V3's baselines on their stored ratios, per W3 yardstick
        (`close_proxy`: B, `intraday`: A); `ewma`: the close-proxy EWMA; `base_outcomes`: V4's and V5's live outcomes;
        `method`: the hash of the deciding files (criterion 21)."""
        self.implied, self.ewma, self.rule, self.base_outcomes = implied, ewma, terms, base_outcomes
        self.method = method

    def terms(self, p: PackInputs) -> dict[str, OptionTerms | Void]:
        return {
            V4_RV_BELOW_WEEKLY_IV: self.rule.v4(p.day, p.spot, p.chain, p.v4_expiry),
            V5_INSIDE_STRADDLE: self.rule.v5(p.day, p.spot, p.chain, p.future_expiry, p.future, p.listed),
        }

    def values(self, p: PackInputs, terms: dict) -> dict[tuple[str, str], tuple[Value, str]]:
        """Each row's value and the SHA-256 of what it read."""
        s2, v4, v5 = self.ewma.variance(p.day), terms[V4_RV_BELOW_WEEKLY_IV], terms[V5_INSIDE_STRADDLE]
        out, close = {}, self.implied[RATIO_CLOSE_PROXY]
        for question in (V2_RV_5S, V3_RV_20S):
            out[(V4_BASELINE_RAW_IMPLIED, question)] = (close[question].raw(p.day, p.iv30),
                                                        digest(p.pack_sha256, p.iv30))  # fmt: skip
        for measure, forecaster in YARDSTICKS.items():
            for question, implied in self.implied[measure].items():
                ratio = implied.ratio.at(first_session_of_month(p.day, implied.sessions))
                out[(forecaster, question)] = (implied.premium_adjusted(p.day, p.iv30),
                                               digest(p.pack_sha256, p.iv30, ratio))  # fmt: skip
        for question in (V4_RV_BELOW_WEEKLY_IV, V5_INSIDE_STRADDLE):
            known = [o for o in self.base_outcomes[question] if o.resolved_on < p.day]
            out[(V4_BASELINE_BASE_RATE, question)] = (
                BaseRate(known).forecast(p.day),
                digest(sorted((o.day, o.value, o.resolved_on) for o in known)),
            )
        out[(V4_BASELINE_OPTION_IMPLIED_PROB, V5_INSIDE_STRADDLE)] = (option_implied_probability(v5), digest(v5))
        out[(V4_RULE_V4_EWMA_CHI2, V4_RV_BELOW_WEEKLY_IV)] = (v4_ewma_chi2(v4, s2), digest(v4, s2))
        out[(V4_RULE_V5_EWMA_LOGNORMAL, V5_INSIDE_STRADDLE)] = (v5_ewma_lognormal(v5, s2), digest(v5, s2))
        return out

    def records(self, p: PackInputs, made_at: str) -> tuple[dict[tuple[str, str], Record], dict]:
        terms, rows = self.terms(p), {}
        for (forecaster, question), (value, inputs) in self.values(p, terms).items():
            kind, slot = PACK_FORECASTERS[(forecaster, question)]
            sha = "" if forecaster in READS_NO_PACK else p.pack_sha256
            rows[(forecaster, question)] = record(p.day, question, value.status, value.value, sha,
                                                  self._version(forecaster, question), label=LIVE, kind=kind,
                                                  slot=slot, method_sha256=self.method, inputs_sha256=inputs,
                                                  made_at=made_at)  # fmt: skip
        return rows, terms

    def _version(self, forecaster: str, question: str) -> str:
        if forecaster == V4_BASELINE_OPTION_IMPLIED_PROB:
            return RISK_NEUTRAL
        measure = next((m for m, f in YARDSTICKS.items() if f == forecaster), None)
        return VERSION if measure is None else f"{VERSION} ratio {measure}"


def capture_pack(forecasts: PackForecasts, inputs: PackInputs, clock: Callable[[], datetime],
                 get: Callable[[str], bytes | None], put: Callable[[str, bytes], None]) -> list[str]:  # fmt: skip
    """Writes the day's rows and terms write-once; returns the paths written or already the same."""
    now = clock()
    if inputs.day != now.astimezone(IST).date():
        raise CaptureRefused(NOT_TODAY.format(day=inputs.day, today=now.astimezone(IST).date()))
    if inputs.release_label != V4_DAY_A:
        raise CaptureRefused(NOT_RELEASED.format(day=inputs.day, label=inputs.release_label))
    rows, terms = forecasts.records(inputs, now.isoformat())
    for (forecaster, _), row in rows.items():
        check_pack_binding(forecaster, row.day, row.pack_sha256, inputs.release_sha256)
    writes = [(live_path(f, q, inputs.day), live_bytes(row, V4_DAY_A), row) for (f, q), row in rows.items()]
    writes += [(terms_path(q, inputs.day), terms_bytes(t, inputs.pack_sha256), None) for q, t in terms.items()]
    for path, data, row in writes:
        _write(path, data, row, clock, get, put)
    return [path for path, _, _ in writes]


def _write(path: str, data: bytes, row: Record | None, clock, get, put) -> None:
    now = clock()
    if now.astimezone(IST).time() >= V4_DEADLINE:
        raise CaptureRefused(PAST_DEADLINE.format(now=now.astimezone(IST), deadline=V4_DEADLINE, path=path))
    held = get(path)
    if held is None:
        put(path, data)
    elif held != data and (row is None or not read_live(held)[0].same_as(row)):
        raise ChangedRow(CHANGED_ROW.format(path=path))


def store_refit_ratios(implied: Mapping[str, Mapping[str, ImpliedBaselines]], day: date,
                       sessions: Sequence[date]) -> list[str]:  # fmt: skip
    """Judge 598 SF1: on the month's refit day, every measure's and question's ratio is stored, whatever the day's
    release (it reads no pack: the EOD proxy, the closes and A16/A16b rows from before the day); any other day
    stores none. Returns one line per stored ratio."""
    if day not in sessions or first_session_of_month(day, list(sessions)) != day:
        return []
    return [f"premium ratio {measure} {question} for {day:%Y-%m}: {by_question.ratio.at(day)}"
            for measure, baselines in implied.items() for question, by_question in baselines.items()]  # fmt: skip
