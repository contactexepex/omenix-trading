"""The decision record (story D3, design 5, 12.6, 13.1 item 3, 13.5): one record per evaluated opportunity, plus one
for the day's "no trade" opportunity, in one format for all three books. A record holds what was seen (the live
values, and by hash every input the run read), what was expected, what was decided and why, the rejected
alternatives, and the three-book fields; a field a book does not have is present and null. `served` lists every
component the decision used (D6 compares it with the registered version; a missing component leaves it unscored)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date

from ..books.versions import DecisionFacts
from ..constants import BOOK1_RULES, BOOK2_HYBRID, BOOK3_AI, Decision
from .decision_validity import BLOCKED, ValidityResult
from .outcomes import DayEvaluation, Outcome

SCHEMA_VERSION = 1
KIND = "decision_record"
NO_TRADE_ID = "no_trade"
HEADER = ("code_commit", "config_sha256", "inputs_sha256", "registry_commit", "strategy_file_sha256")
THREE_BOOK = (
    "book", "version_id", "common_pack_sha256", "private_pack_sha256", "rule_default", "chosen_action", "reason",
    "authority_check", "strategy_id", "strategy_spec_sha256", "model_served", "session_id", "served", "judge",
    "owner_override", "forecasts",
)  # fmt: skip
BODY = (
    "schema_version", "kind", "run_id", "opportunity_id", "mode", "header", "features", "rule_result", "structure",
    "expected", "risk", "validity", "decision", "alternatives", "corrects",
)  # fmt: skip
FIELDS = BODY + THREE_BOOK
# Null where a book has no such thing (D3 criterion 6); every other three-book field must be filled.
NULLABLE = {
    BOOK1_RULES: {"authority_check", "strategy_id", "strategy_spec_sha256", "model_served", "session_id"},
    BOOK2_HYBRID: {"strategy_id", "strategy_spec_sha256"},
    BOOK3_AI: {"rule_default", "authority_check"},
}
NON_EMPTY = {BOOK2_HYBRID: ("rule_default", "chosen_action", "reason", "authority_check")}  # text, never ""
PER_OUTCOME = ("book", "chosen_action", "reason", "rule_default")  # set per record, not by the run
# Book 3's day record ("no trade" for the day) names no strategy; each of its opportunity records does (F6, 16 Oct)
DAY_RECORD_NULLABLE = {BOOK3_AI: {"strategy_id", "strategy_spec_sha256"}}
LINKS = {"version_id", "judge", "owner_override", "forecasts"}  # filled when they exist (D6, C4/F4, F4, G3)
# The owner never overrides a paper decision (owner, 16 Oct 2026, DESK_DECISIONS row 229 item 4): null in every book
ALWAYS_NULL = ("owner_override",)


class RecordError(ValueError):
    """A decision record that does not match its schema; the message names the field."""


def _action(outcome: Outcome) -> str:
    return "trade" if outcome.decision in (Decision.CHOSEN, Decision.SHADOW_TRADE) else "no trade"


def _expected(outcome: Outcome) -> dict:
    plan, candidate = outcome.opportunity.strategy.evaluation_plan, outcome.candidate
    low, high = plan["expected_range"]
    return {
        "mean_rs": plan["expected_net_per_opportunity"], "source": plan["expected_net_source"], "unit": plan["unit"],
        "range_low": low, "range_high": high, "p10_rs": None, "p90_rs": None,  # not in the playbook format yet
        "worst_rs": -round(candidate.max_loss, 2) if candidate else None,  # the trade's modelled maximum loss
    }  # fmt: skip


def _summary(outcome: Outcome) -> dict:
    return {"opportunity_id": outcome.opportunity.opportunity_id, "mode": outcome.opportunity.mode,
            "decision": str(outcome.decision), "reason": outcome.reason}  # fmt: skip


class RecordBuilder:
    """Turns one evaluated day into its records; everything the run knows besides the outcomes comes in `context`."""

    def __init__(
        self, book: str, run_id: str, context: Mapping[str, object],
        validity: Mapping[str, ValidityResult] | None = None,
    ):  # fmt: skip
        self.book, self.run_id, self.context, self.validity = book, run_id, dict(context), dict(validity or {})

    def _blocked(self, outcome: Outcome) -> ValidityResult | None:
        result = self.validity.get(outcome.opportunity.opportunity_id)
        return result if result is not None and not result.ok else None

    def _action(self, outcome: Outcome) -> str:
        return "no trade" if self._blocked(outcome) else _action(outcome)

    def _reason(self, outcome: Outcome) -> str:
        blocked = self._blocked(outcome)
        return f"{BLOCKED}: {blocked.reason}" if blocked else outcome.reason

    def build(self, evaluation: DayEvaluation, strategy_files: Mapping[str, str]) -> list[dict]:
        outcomes = evaluation.outcomes
        records = [self._opportunity(o, outcomes, strategy_files) for o in outcomes]
        return [*records, self._day(evaluation)]

    def _base(self, opportunity_id: str, mode: str, strategy_file_sha: str | None) -> dict:
        header = {key: self.context[key] for key in HEADER if key != "strategy_file_sha256"}
        return {
            "schema_version": SCHEMA_VERSION, "kind": KIND, "run_id": self.run_id, "opportunity_id": opportunity_id,
            "mode": mode, "header": {**header, "strategy_file_sha256": strategy_file_sha}, "corrects": None,
            **{key: self.context.get(key) for key in THREE_BOOK if key not in PER_OUTCOME},
            "book": self.book,
        }  # fmt: skip

    def _opportunity(self, outcome: Outcome, outcomes: Sequence[Outcome], files: Mapping[str, str]) -> dict:
        strategy, opportunity_id = outcome.opportunity.strategy, outcome.opportunity.opportunity_id
        record, c4 = outcome.record(), self.validity.get(opportunity_id)
        action, reason = self._action(outcome), self._reason(outcome)
        candidate = "built" if outcome.candidate else outcome.reason
        base = self._base(outcome.opportunity.opportunity_id, outcome.opportunity.mode, files[strategy.file_name])
        return {
            **base, "features": record["features"],
            "rule_result": {"fired": not record["unmet_conditions"], "unmet_conditions": record["unmet_conditions"]},
            "structure": record["trade"], "expected": _expected(outcome), "risk": record["risk"],
            "validity": {"c4": c4.record if c4 else None, "candidate": candidate},
            "decision": {"action": action, "outcome": record["decision"], "reason": reason},
            "alternatives": [_summary(o) for o in outcomes if o is not outcome],
            "rule_default": action if self.book != BOOK3_AI else None, "chosen_action": action, "reason": reason,
        }  # fmt: skip

    def _day(self, evaluation: DayEvaluation) -> dict:
        chosen = [o.opportunity.opportunity_id for o in evaluation.chosen if not self._blocked(o)]
        reason = f"chosen: {chosen}" if chosen else "no opportunity was chosen today"
        action = "trade" if chosen else "no trade"
        return {
            **self._base(NO_TRADE_ID, "book", None), "features": {}, "rule_result": None, "structure": None,
            "expected": None, "risk": None, "validity": None,
            "decision": {"action": action, "outcome": action, "reason": reason},
            "alternatives": [_summary(o) for o in evaluation.outcomes],
            "rule_default": action if self.book != BOOK3_AI else None, "chosen_action": action, "reason": reason,
        }  # fmt: skip


def run_context_of(record: Mapping) -> dict:
    """The run's context (hashes, links, `served`) as a stored record carries it: what a replay rebuilds with."""
    header = {key: record["header"][key] for key in HEADER if key != "strategy_file_sha256"}
    return {**header, **{key: record[key] for key in THREE_BOOK if key not in PER_OUTCOME}}


def validate_record(record: Mapping) -> None:
    """RecordError unless the record has exactly the schema's fields, its version, every three-book field filled
    except where its book has none (criterion 6), and no owner override in any book."""
    if record.get("schema_version") != SCHEMA_VERSION or record.get("kind") != KIND:
        raise RecordError(f"schema_version must be {SCHEMA_VERSION} and kind {KIND!r}")
    missing, unknown = sorted(set(FIELDS) - set(record)), sorted(set(record) - set(FIELDS))
    if missing or unknown:
        raise RecordError(f"fields missing {missing}, unknown {unknown}")
    if record["book"] not in NULLABLE:
        raise RecordError(f"book: unknown {record['book']!r}")
    allowed_null = NULLABLE[record["book"]] | LINKS
    if record["opportunity_id"] == NO_TRADE_ID:
        allowed_null |= DAY_RECORD_NULLABLE.get(record["book"], set())
    empty = [key for key in THREE_BOOK if record[key] is None and key not in allowed_null]
    if empty:
        raise RecordError(f"{record['book']} must fill {empty}")
    overridden = [key for key in ALWAYS_NULL if record[key] is not None]
    if overridden:
        raise RecordError(f"{overridden} must be null: the owner never overrides a paper decision")
    blank = [key for key in NON_EMPTY.get(record["book"], ()) if not record[key]]
    if blank:  # story D4 criterion 7: Book 2's AI action carries its reason and the envelope's verdict
        raise RecordError(f"{record['book']} must give a non-empty {blank}")
    served = record["served"]
    if not isinstance(served, Mapping) or not served or not all(isinstance(v, str) and v for v in served.values()):
        raise RecordError("served: every component the decision used, as non-empty text")
    if set(record["header"]) != set(HEADER):
        raise RecordError(f"header must hold exactly {HEADER}")


def decision_facts(record: Mapping, commit: str) -> DecisionFacts:
    """What D6 needs from a committed record: its book, day, ID, the commit that holds it and every served component."""
    day = date.fromisoformat(record["run_id"][:10])
    return DecisionFacts(
        record["book"], day, f"{record['run_id']}/{record['opportunity_id']}", commit, record["served"]
    )
