"""E8's own records (story E8 rules 1 and 12), private in Drive next to the paper accounts and never committed: each
exit alert's first delivery (its Slack time is the exit's order time T), and each fill or miss with the due mark, R,
the view, T and the snapshot's hash that the desk's own rows do not carry.

Every record is its own write-once file (judge 203 should-fix 2): `RawFileStore.put` refuses different bytes at an
existing path, so no write can ever replace newer content, and the same record written again by a rerun changes
nothing. Reads go through the step's read-only, time-capped store; writes go through the plain store, never
abandoned."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from datetime import datetime

from ...storage.raw_store import RawFileStore

ALERT_PATH = "{account}/alerts/{trade_id}.json"
FILL_PATH = "{account}/fills/{trade_id}-{kind}-{mark}.json"
NO_MARK = "unscheduled"  # a miss decided before any mark (owner away, contract expired)


@dataclass(frozen=True)
class TimingRecord:
    """One fill or miss as E8 applied it (rule 12): the order time T, R, the due mark and the copy priced from."""

    account: str
    view: str
    trade_id: str
    kind: str  # entry or exit
    reaction_minutes: int
    order_time: datetime  # T
    due_mark: datetime | None  # None: missed before any mark was due
    fill_mark: datetime | None  # the mark whose copy was priced (an exit may fill legs at later marks); None: no copy
    snapshot_id: str  # empty for a miss without a copy
    snapshot_sha256: str
    outcome: str
    reason: str

    def data(self) -> bytes:
        times = {
            name: moment.isoformat() if moment else None
            for name, moment in (
                ("order_time", self.order_time),
                ("due_mark", self.due_mark),
                ("fill_mark", self.fill_mark),
            )
        }
        fields = asdict(self) | times
        return (json.dumps(fields, indent=1, sort_keys=True) + "\n").encode()


def account_folder(account: str) -> str:
    return account.replace(":", "/")  # `shadow:<version>` becomes its own folder


class TimingLog(ABC):
    @abstractmethod
    def alert_time(self, account: str, trade_id: str) -> datetime | None:
        """When the trade's exit alert was first delivered; None while it has not been."""

    @abstractmethod
    def alerted(self, account: str, trade_id: str, delivered_at: datetime) -> None:
        """Keep an exit alert's first delivery."""

    @abstractmethod
    def record(self, record: TimingRecord) -> None:
        """Keep one fill or miss."""


class StoreTimingLog(TimingLog):
    def __init__(self, reader: RawFileStore, writer: RawFileStore):
        self.reader, self.writer = reader, writer

    def alert_time(self, account: str, trade_id: str) -> datetime | None:
        data = self.reader.get(ALERT_PATH.format(account=account_folder(account), trade_id=trade_id))
        return datetime.fromisoformat(json.loads(data)["delivered_at"]) if data else None

    def alerted(self, account: str, trade_id: str, delivered_at: datetime) -> None:
        body = {"account": account, "trade_id": trade_id, "delivered_at": delivered_at.isoformat()}
        path = ALERT_PATH.format(account=account_folder(account), trade_id=trade_id)
        self.writer.put(path, (json.dumps(body, indent=1, sort_keys=True) + "\n").encode())

    def record(self, record: TimingRecord) -> None:
        moment = record.fill_mark or record.due_mark
        mark = f"{moment:%Y%m%dT%H%M}" if moment else NO_MARK
        path = FILL_PATH.format(
            account=account_folder(record.account), trade_id=record.trade_id, kind=record.kind, mark=mark
        )
        self.writer.put(path, record.data())
