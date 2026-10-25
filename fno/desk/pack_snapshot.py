"""The day's canonical 3 pm snapshot exactly as the common pack recorded it (story E2e): the snapshot ID the pack names
under its provenance (`a4_snapshot`), read by that ID from the pack's dataset, its quote file and its sidecar each
checked against the SHA-256 the pack recorded, and parsed from those verified bytes. The day's `.canonical` marker is
never followed (judge 309: a marker naming a later capture must not change what a decision reads). Every reader of the
cutoff market (Book 1's inputs, each book's sheet, each decider's re-check) takes it from here."""

from __future__ import annotations

from datetime import date

from ..quotes.recorder import DATASET, QuoteSnapshotRecorder
from ..research_data.quote_snapshots import CutoffSnapshot, parse_snapshot
from ..storage.raw_store import RawFileStore
from .common_pack import SNAPSHOT_INPUT, CommonPack
from .pack_items import sha256_hex

NOT_THE_PACK_S = "the canonical snapshot of {day} is not the one its common pack records ({why})"
FILES = (("csv", ".csv", "csv_sha256"), ("sidecar", ".meta.json", "meta_sha256"))


class NotThePacksSnapshot(ValueError):
    """The stored snapshot is missing or differs from the one the common pack recorded."""


def canonical_snapshot(day: date, common: CommonPack, quotes: RawFileStore) -> CutoffSnapshot:
    recorded = common.body["provenance"].get(SNAPSHOT_INPUT, {})
    snapshot_id = recorded.get("snapshot_id")
    if not snapshot_id:
        raise NotThePacksSnapshot(NOT_THE_PACK_S.format(day=day, why="the pack names no snapshot"))
    dataset = recorded.get("dataset") or DATASET
    verified = {}
    for kind, suffix, key in FILES:
        data = quotes.get(QuoteSnapshotRecorder.path(day, f"{snapshot_id}{suffix}", dataset))
        if data is None or sha256_hex(data) != recorded.get(key):
            raise NotThePacksSnapshot(NOT_THE_PACK_S.format(day=day, why=f"snapshot {snapshot_id}: {kind}"))
        verified[kind] = data
    return parse_snapshot(day, verified["csv"], verified["sidecar"])
