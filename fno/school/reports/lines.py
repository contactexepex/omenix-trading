"""The words both sections share (story MS-P1g): the Paper label, the no-latency label and the NSE-terms line."""

from ..constants import NO_LATENCY_LABEL, NSE_TERMS_LINE, PAPER_LABEL
from ..contracts.roads import RoadDay

RUPEE = "Rs {amount:,.0f}"
SIGNED_RUPEE = "Rs {amount:+,.0f}"


def paper_title(title: str) -> str:
    return f"School pilot, {title} ({PAPER_LABEL}: no real money, no order)"


def footer() -> tuple[str, ...]:
    return NO_LATENCY_LABEL, NSE_TERMS_LINE


def road_status_line(days: tuple[RoadDay, ...]) -> str:
    parts = [f"{d.road.code} open" if d.status.open else f"{d.road.code} closed ({d.status.closed_by})" for d in days]
    return "Roads: " + "; ".join(parts) if parts else "Roads: none (not a trading day)"
