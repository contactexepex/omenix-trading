"""Which drivers are seller-shaped (story MS-INS, part d; ruling D): mostly small wins and a rare full loss, the payoff
shape whose descriptive bound can look positive falsely (the skewed-seller null). Read from the card's family; RC1
draws seller structures too, so it counts as one."""

from ...contracts.decisions import DriverCard

SELLER_FAMILIES = frozenset({"capped_seller", "weekly_seller", "width_ladder", "reference", "edge1_control", "random"})


def is_seller(card: DriverCard) -> bool:
    return card.family in SELLER_FAMILIES
