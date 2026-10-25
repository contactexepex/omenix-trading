"""The slot's running account view (story MS-P1j, requirement from MS-P1f): the account's own view at the slot plus the
trades already accepted for it this slot, before any of them fills. So the bucket, open-risk, new-risk and margin laws
add them up, and the quote gate (E4d) counts the displayed size they will take on their road.

An accepted trade enters as the position its fill would open, with its entry cash taken at the proposal's premium less
all its modelled costs: a lower credit (or a higher debit) than the fill can give, so the running caps are never
looser than the filled ones [reasoning only]."""

from dataclasses import replace

from ..contracts.decisions import Decision, OpenPosition
from ..contracts.safety import AccountView


def position_id(decision: Decision) -> str:
    """One position per (driver version, road, session): a driver opens at most one trade on a road at one slot."""
    return f"{decision.driver_id}:{decision.road}:{decision.session}"


def driver_of(position: str) -> str:
    """The driver version a `position_id` names (Judge K, judge 529: read beside the one place that builds it)."""
    return position.split(":", 1)[0]


def opened_position(decision: Decision, entry_net: float) -> OpenPosition:
    """The position a sealed trade opens: its one ID, its proposal's legs, lot and maximum loss, and its entry cash."""
    proposal = decision.proposal
    return OpenPosition(position_id(decision), decision.driver_id, decision.road, proposal.structure, proposal.legs,
                        proposal.lot, decision.session, entry_net, proposal.max_loss)  # fmt: skip


def accepted_position(decision: Decision) -> OpenPosition:
    return opened_position(decision, decision.proposal.net_premium - decision.proposal.costs)


def running_view(view: AccountView, accepted: tuple[Decision, ...]) -> AccountView:
    if any(decision.driver_id != view.driver_id for decision in accepted):
        raise ValueError(f"accepted trades of another driver in {view.driver_id}'s view")
    added = tuple(accepted_position(decision) for decision in accepted)
    return replace(view, open_positions=(*view.open_positions, *added),
                   opened_this_session=(*view.opened_this_session, *added))  # fmt: skip
