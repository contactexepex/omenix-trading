"""One driver version against its matched controls (story MS-INS, part d): for each control (N0, RC1 and REF of the
road), both measures, on the common road-days h's counting rule gives that pair, batched at the pair's frozen hold."""

from collections.abc import Collection, Mapping

from ...contracts.decisions import DriverCard
from ..contracts import Measure, PairedRow
from .holds import pair_batch
from .series import RoadDay, paired_series
from .shapes import is_seller
from .status import paired_row
from .values import RoadSlot

Slots = Mapping[str, Mapping[RoadDay, RoadSlot]]  # each driver's road-slots, by driver ID
Common = Mapping[tuple[str, str], Collection[RoadDay]]  # the counted road-days of each (driver, control)


def compare(driver: DriverCard, controls: Collection[DriverCard], cards: Collection[DriverCard], slots: Slots,
            common: Common, rules_sha256: str) -> tuple[PairedRow, ...]:  # fmt: skip
    """A row per control and measure on its counted road-days; a pair with none gives no row (criterion 9). `cards`
    are every card in force, for RC1's hold (its twins')."""
    rows = []
    for control in controls:
        pair = (driver.driver_id, control.driver_id)
        if not common.get(pair):
            continue
        batch = pair_batch(driver, control, cards)
        for measure in Measure:
            series = paired_series(slots.get(pair[0], {}), slots.get(pair[1], {}), common[pair], measure)
            rows.append(paired_row(*pair, measure, series, batch, rules_sha256, is_seller(driver)))
    return tuple(rows)
