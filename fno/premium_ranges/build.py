"""One day's premium-range record (story sections "The rule" and "Sealing, files, timing"), built from G13's own 3 pm
record of that day (A4's canonical chain, valued by G13): every monthly contract with an IV is ranged; every other one
is counted by reason, never guessed."""

from __future__ import annotations

from collections import Counter
from datetime import date

from ..price_distribution.constants import OK
from .constants import (
    DECAY_ONLY,
    EXPIRES_BY_NEXT,
    LIVE,
    NO_ATM_IV,
    NO_CHANGE,
    NO_DISTRIBUTION,
    NO_IV,
    RULE,
    SCHEMA,
)
from .rule import ContractInputs, decay_only, no_change, rule_range

DIGITS = 4


def _points(value: float | None) -> float | None:
    return None if value is None else value / 100


def _reason(expiry: dict, step_days: int) -> str | None:
    if expiry["days"] <= step_days:
        return EXPIRES_BY_NEXT
    if (expiry.get("distribution") or {}).get("status") != OK:
        return NO_DISTRIBUTION
    return None if expiry.get("atm_iv_points") else NO_ATM_IV


def _row(expiry: dict, contract: dict, inputs: ContractInputs, step_days: int) -> dict:
    ranges = {RULE: rule_range(inputs, step_days), DECAY_ONLY: decay_only(inputs, step_days),
              NO_CHANGE: no_change(inputs)}  # fmt: skip
    return {"expiry": expiry["expiry"], "strike": inputs.strike, "side": inputs.side, "mid": inputs.mid,
            "iv_points": contract["iv_points"], "delta": contract.get("delta"), "days": inputs.days,
            **{name: [round(v, DIGITS) for v in values] for name, values in ranges.items()}}  # fmt: skip


def premium_rows(g13_record: dict, step_days: int) -> tuple[list[dict], Counter]:
    rows, not_ranged = [], Counter()
    rate = g13_record["rate"]
    for expiry in (g13_record.get("valuation") or {}).get("expiries", []):
        contracts = expiry.get("contracts", [])
        reason = _reason(expiry, step_days)
        if reason is not None:
            not_ranged[reason] += len(contracts)
            continue
        for c in contracts:
            if c.get("iv_points") is None:
                not_ranged[NO_IV] += 1
                continue
            inputs = ContractInputs(c["strike"], c["kind"], c["price"], c["iv_points"] / 100, expiry["forward"],
                                    _points(expiry["atm_iv_points"]), expiry["days"], rate)  # fmt: skip
            rows.append(_row(expiry, c, inputs, step_days))
    return rows, not_ranged


def premium_record(g13_record: dict, next_session: date, method_sha256: str, made_at: str | None) -> dict:
    day = date.fromisoformat(g13_record["day"])
    step_days = (next_session - day).days
    rows, not_ranged = premium_rows(g13_record, step_days)
    return {"schema": SCHEMA, "label": LIVE, "underlying": g13_record["underlying"], "day": day.isoformat(),
            "next_session": next_session.isoformat(), "step_days": step_days, "source": g13_record.get("source"),
            "g13_method_sha256": g13_record["method_sha256"], "g13_inputs_sha256": g13_record.get("inputs_sha256"),
            "method_sha256": method_sha256, "made_at": made_at, "rule": RULE, "rows": rows,
            "not_ranged": dict(sorted(not_ranged.items()))}  # fmt: skip
