"""A book's action on one common opportunity, read from its D3 record (story S3, expected design 1). Scoreboard A
removes the account (S1 `scoreboard_a_standardisation`: no cash, slot or margin limits), so a valid candidate refused
only by an account limit is a take; a refusal by the rule that judges the trade alone is the book's own skip; bad data
and a wrongly opened account are operations faults, not judgement, so they are not observed."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from ..constants import Decision
from ..playbook.decision_validity import BLOCKED

TAKE, SKIP, NOT_OBSERVED = "take", "skip", "not observed"
TRADE_ACTION = "trade"
# Rules that look at the book's state, not the trade (allocation.py:18, fno/risk/caps.py, rules.py:45-47, 82-84, and
# manager.py:58's "inputs" check, an account limit only with its "already open" reason: the same trade held).
ACCOUNT_LIMIT_RULES = frozenset(
    {"max_open_trades", "margin_room", "bucket_cap", "open_risk_cap", "new_risk_per_day", "drawdown_brake",
     "stress_loss", "exposure_limit", "inputs"}
)  # fmt: skip
INPUTS_RULE, ALREADY_OPEN = "inputs", "is already open in"  # fno/risk/manager.py:19 and :58
OPERATIONS_RULES = frozenset({"paper_account"})  # an account opened with the wrong capital trades nothing
UNPROVEN_PREFIX = "unproven:"  # allocation.py:72-77, the open-trade limit of a version with few completed trades
INPUT_NOT_USABLE = "refused, input not usable"  # fno/risk/manager.py:66


@dataclass(frozen=True)
class Action:
    kind: str
    reason: str
    record: Mapping | None = None


def _failed(record: Mapping) -> list[Mapping]:
    risk = record.get("risk") or {}
    return [v for v in risk.get("verdicts", ()) if not v.get("ok", True)]


def _not_chosen(record: Mapping) -> Action:
    failed, reason = _failed(record), record["decision"]["reason"]
    if any(v.get("reason", "").startswith(INPUT_NOT_USABLE) for v in failed):
        return Action(NOT_OBSERVED, "risk input not usable", record)
    rules = {v["rule"] for v in failed}
    if rules & OPERATIONS_RULES:
        return Action(NOT_OBSERVED, "paper account refused", record)
    limits = [v for v in failed if _account_limit(v)]
    if reason.startswith(UNPROVEN_PREFIX) or (failed and len(limits) == len(failed)):
        refusals = "; ".join(f"{v['rule']}: {v.get('reason', '')}" for v in limits) or reason
        return Action(TAKE, f"account limit only ({refusals})", record)  # the original refusal, listed (review 120)
    trade_rules = sorted({v["rule"] for v in failed if not _account_limit(v)})
    return Action(SKIP, "refused by " + ", ".join(trade_rules) if trade_rules else reason, record)


def _account_limit(verdict: Mapping) -> bool:
    if verdict["rule"] == INPUTS_RULE:
        return ALREADY_OPEN in verdict.get("reason", "")
    return verdict["rule"] in ACCOUNT_LIMIT_RULES


def action_of(record: Mapping) -> Action:
    """The take, skip or not-observed reading of one opportunity's record. A C4 block reads "no trade" in
    `decision.action` even when `decision.outcome` reads "chosen" (decision_record.py:76-79), so the action decides."""
    decision = record["decision"]
    if decision["action"] == TRADE_ACTION:
        return Action(TAKE, "chosen", record)
    blocked = decision["reason"].startswith(f"{BLOCKED}:")  # C4 refused the trade itself
    if decision["outcome"] == Decision.NOT_CHOSEN and record.get("structure") and not blocked:
        return _not_chosen(record)
    return Action(SKIP, decision["reason"], record)
