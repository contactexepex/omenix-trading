"""Which of a playbook version's exits code can enforce (stories D1 and E5, judge 84). Today the only machine-readable
exit is the structure's time exit (`exit_days_before_expiry`); the `profit`, `loss` and `event` exits are free text.
A version whose text exit is anything but exactly "none" (trimmed, any case) states a rule nobody would enforce: D1
refuses it `paper`, Book 1 never orders it, and its open trades still get the time exit, with an alert. "None" is the
whole value, never a prefix (judge 84: "none until day 10, then stop at 2x credit" states a stop); notes go in YAML
comments."""

from __future__ import annotations

from .schema import Strategy

TEXT_EXITS = ("profit", "loss", "event")
NO_EXIT = "none"


def unenforceable_exits(strategy: Strategy) -> list[str]:
    """The version's exits that code cannot apply, as "<kind>: <text>"; empty when only the time exit binds it."""
    written = {kind: str(strategy.exits.get(kind, "")) for kind in TEXT_EXITS}
    return [f"{kind}: {text}" for kind, text in written.items() if text.strip().lower() != NO_EXIT]
