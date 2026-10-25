"""The common market pack (story E2, design 13.5 step 1): the day's market observations, session and events, each
admitted only if available by the cutoff, the common opportunity set, and the provenance to rebuild it. It holds no
book's decisions, positions, P&L, findings or memory: its inputs read market data only, and the finished pack is
refused if it names any book or any journal path."""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, time
from pathlib import Path
from typing import Protocol

from ..constants import BOOKS, JOURNAL_FOLDER
from ..models import IST
from ..playbook.loader import Playbook
from ..quotes.recorder import RECORDED_SESSION_KINDS
from .opportunity_set import OpportunitySet
from .pack_inputs import CommonInput
from .pack_items import PackError, admit, canonical_json, sha256_hex

SCHEMA_VERSION = 2  # E2b: no per-contract quote items (owner "8 A")
FUTURE_PREFIX = "future:"
SESSION_ITEM, SNAPSHOT_INPUT = "session", "a4_snapshot"  # SessionInput's item and SnapshotInput's provenance key
FORBIDDEN = (*BOOKS, f"{JOURNAL_FOLDER}/")  # a book's name or journal path never appears in the common pack


class PlaybookState(Protocol):
    def load(self) -> Playbook: ...


@dataclass(frozen=True)
class CommonPack:
    day: date
    body: dict

    @property
    def data(self) -> bytes:
        return canonical_json(self.body)

    @property
    def sha256(self) -> str:
        return sha256_hex(self.data)

    @classmethod
    def read(cls, day: date, path: Path) -> CommonPack:
        """A written pack, refused if its bytes are not the canonical form of its body (an edited file)."""
        data = Path(path).read_bytes()
        pack = cls(day, json.loads(data))
        if pack.data != data:
            raise PackError(f"{path} is not a pack as written: refused")
        return pack


def require_snapshot_on_session_day(day: date, body: dict) -> None:
    """A recorded session day without its canonical A4 snapshot is refused, not packed: the store is write-once, so an
    empty pack would freeze the day with no quotes even after the recorder commits (judge 72). A closed day, or a
    muhurat-only evening the recorder never records, still gets its session-only pack."""
    session = next((item["value"] for item in body["items"] if item["name"] == SESSION_ITEM), None)
    if session in RECORDED_SESSION_KINDS and body["provenance"].get(SNAPSHOT_INPUT, {}).get("snapshot_id") is None:
        raise PackError(f"no canonical A4 snapshot for {day.isoformat()} ({session} session): nothing written")


def require_market_only(data: bytes) -> None:
    text = data.decode("utf-8")
    found = [word for word in FORBIDDEN if word in text]
    if found:
        raise PackError(f"the common pack would contain book data ({found}); it holds market data only")


class CommonPackBuilder:
    def __init__(self, inputs: Sequence[CommonInput], opportunities: OpportunitySet, playbook: PlaybookState):
        self.inputs, self.opportunities, self.playbook = tuple(inputs), opportunities, playbook

    def build(self, day: date, cutoff: time) -> CommonPack:
        moment = datetime.combine(day, cutoff, tzinfo=IST)
        batches = {source.name: source.collect(day) for source in self.inputs}
        items, refused = admit((i for b in batches.values() for i in b.items), moment)
        monthly = sorted(
            date.fromisoformat(i.name.removeprefix(FUTURE_PREFIX)) for i in items if i.name.startswith(FUTURE_PREFIX)
        )
        playbook = self.playbook.load()
        body = {
            "schema_version": SCHEMA_VERSION,
            "kind": "common_market_pack",
            "day": day.isoformat(),
            "cutoff": moment.isoformat(),
            "provenance": {name: batch.provenance for name, batch in sorted(batches.items())},
            "items": [item.record() for item in items],
            "refused": list(refused),
            "opportunities": self.opportunities.build(playbook, day, monthly),
        }
        require_snapshot_on_session_day(day, body)
        pack = CommonPack(day, body)
        require_market_only(pack.data)
        return pack
