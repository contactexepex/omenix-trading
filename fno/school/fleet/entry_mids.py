"""An entry's mids (story 3.4's slippage against mid): the quotes witnessed in the position's own sealed decision
record, read back from the decisions file of the session it opened in. Never a later snapshot, never a guess."""

from ..constants import SLOT_1500, RecordKind
from ..contracts.dashcam import DashcamStore
from ..contracts.decisions import OpenPosition
from ..contracts.records import DecisionRecord
from ..contracts.snapshot import ContractKey


class EntryNotSealed(LookupError):
    """The position's opening session has no sealed decision for its road and driver: a ledger without its record."""


class DashcamEntryMids:
    def __init__(self, dashcam: DashcamStore):
        self.dashcam = dashcam

    def __call__(self, position: OpenPosition) -> dict[ContractKey, float]:
        seal = self.dashcam.find(position.opened, SLOT_1500, RecordKind.DECISIONS)
        records = () if seal is None else self.dashcam.read(seal)
        record = next((r for r in records if isinstance(r, DecisionRecord) and r.road == position.road
                       and r.decision.driver_id == position.driver_id), None)  # fmt: skip
        if record is None:
            raise EntryNotSealed(f"{position.position_id}: no sealed decision on {position.opened}")
        return {w.key: w.quote.mid for w in record.witnessed if w.quote.mid is not None}
