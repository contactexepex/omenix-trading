"""A Book 3 strategy against its constitution (story D5 criterion 3), at registration and again at C4. The spec is in
D1's playbook format, so its structure code, expiry kind and expiry window are its own fields. The playbook format has
no underlying (every version is a NIFTY option strategy) and accepts only monthly expiries today, so a non-NIFTY or a
weekly spec cannot be written at all; the expiry check stays as the second guard for when D1 adds another kind. The
planned holding is at most the expiry window's far end minus the days before expiry at which the time exit falls."""

from __future__ import annotations

from .constitution import EXPIRY, Constitution


def planned_holding_days(spec) -> int:
    expiry = spec.structure.expiry
    return expiry.max_days - expiry.exit_days_before_expiry


def constitution_problems(spec, constitution: Constitution) -> list[str]:
    structure = spec.structure
    problems = []
    if structure.code not in constitution.structures:
        problems.append(f"structure {structure.code} is not in the constitution's {sorted(constitution.structures)}")
    if structure.expiry.kind != EXPIRY:
        problems.append(f"expiry {structure.expiry.kind!r}: only {EXPIRY!r} expiries are allowed")
    if planned_holding_days(spec) > constitution.max_holding_days:
        problems.append(f"planned holding up to {planned_holding_days(spec)} days, over the constitution's "
                        f"{constitution.max_holding_days}")  # fmt: skip
    return problems
