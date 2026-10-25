"""The recommender's fixed names (story REC1a): the two answers, the closed reason set in its priority order, the
evidence rungs and the record's kind. Apart from `fno/constants.py`, which is at the size limit (as the school's)."""

from enum import IntEnum, StrEnum

RECORD_KIND = "recommendation"
RECORD_SCHEMA_VERSION = 1  # a layout change is a new version, never an edit of a written record
RECOMMEND_STEP = "recommend"  # the O1 step and its `daily.live_from` key (REC1b)
WINDOW_SESSIONS = 60  # the evening check follows a day this many sessions; a monthly option closes in about 35 days


class RealMoneyAnswer(StrEnum):
    """Exactly two members: there is no "buy" (response 327 item 9: a green means eligible for review, never buy)."""

    DO_NOT_TRADE_REAL_MONEY = "do_not_trade_real_money"
    ELIGIBLE_FOR_YOUR_OWN_REVIEW = "eligible_for_your_own_review"


class PaperAnswer(StrEnum):
    PAPER_TRADE = "paper_trade"  # a recommendation: only a rung-3 version's trade (judge 620 S1)
    NO_TRADE = "no_trade"


class NoTradeReason(StrEnum):
    """The closed set, declared in priority order: with several true, the first wins (story section 1)."""

    DATA_CHECK_FAILED = "data_check_failed"
    STEP_PROBLEMS = "step_problems"
    NO_ESTABLISHED_VERSION = "no_established_version"
    QUOTE_GATE_FAILED = "quote_gate_failed"
    WEATHER_RED = "weather_red"
    RISK_CAP = "risk_cap"
    BRAKE = "brake"
    NO_CANDIDATE = "no_candidate"


REASON_TEXT = {
    NoTradeReason.DATA_CHECK_FAILED: "an input could not be read or its hash did not match, so nothing can be trusted",
    NoTradeReason.STEP_PROBLEMS: "a daily step failed or was refused today",
    NoTradeReason.NO_ESTABLISHED_VERSION: "no version has passed: none is established on forward paper results",
    NoTradeReason.QUOTE_GATE_FAILED: "today's quote capture or road quality gate failed",
    NoTradeReason.WEATHER_RED: "the market weather is red",
    NoTradeReason.RISK_CAP: "a risk cap or safety law refused the trade",
    NoTradeReason.BRAKE: "a drawdown brake or the daily stop holds",
    NoTradeReason.NO_CANDIDATE: "an established version exists, but it made no trade today",
}


# A day stopped by one of these is DO NOT TRADE for real money too, never ELIGIBLE (orchestrator, judge 654 m2)
BLOCKS_REAL_MONEY = frozenset({NoTradeReason.DATA_CHECK_FAILED, NoTradeReason.STEP_PROBLEMS,
                               NoTradeReason.QUOTE_GATE_FAILED, NoTradeReason.WEATHER_RED})  # fmt: skip


class EvidenceRung(IntEnum):
    """Confidence as a stated rule (story section 2), never a free number. Only ESTABLISHED is "proven"."""

    UNPROVEN = 0
    EXPLORATORY = 1
    WATCHING = 2
    ESTABLISHED = 3


class OutcomeSource(StrEnum):
    """Where an outcome came from. Only FORWARD can count; the others never raise a rung (story section 2)."""

    FORWARD = "forward"
    BACKTEST = "backtest"
    SIMULATOR = "simulator"
    REHEARSAL = "rehearsal"


class CandidateSourceName(StrEnum):
    """Where the day's candidates come from (orchestrator's ruling, 25 Oct): each is listed with its state."""

    DESK_BOOK1 = "desk:book1"
    SCHOOL = "school"


class SourceState(StrEnum):
    COMPLETE = "complete"
    UNAVAILABLE = "unavailable"  # the source step's status says why; never read as "no candidates"
