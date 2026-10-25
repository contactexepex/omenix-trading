"""Merges Drive folders that share one name in one folder into one (story DR1-0; owner, 23 Oct 2026: "DR1 merges,
judged"). Two runs creating a folder at the same moment can each make one (22 Oct: two `data/daily_runs/full`), and
from then on every path through that name is refused (RawFileConflict).

Choice by verified content, never by time (owner, 23 Oct): the folder kept is the one holding the most files whose
bytes match their receipts; a tie is refused, so a person decides. The other copies' items are moved into it (same-named
subfolders merged the same way); two files with one name, or a folder and a file with one name, are refused before
anything moves. Nothing is deleted: each emptied copy is renamed `<name>.merged-<day>` and stays where it was, so it
can be checked and removed by hand. Afterwards every receipt under the path is read back through the path-based store.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import date

from .drive_items import DriveItem, DriveItems
from .raw_store import RawFileStore
from .receipts import ReceiptFolder

MERGED_NAME = "{name}.merged-{day:%Y-%m-%d}"
TIE = "{path}: {count} copies hold {verified} verified file(s) each; a person decides which one is kept"
CLASH = "{path}: both copies hold {name!r}; nothing is moved (a person decides)"
NOT_VERIFIED = "{path}: receipt not matched after the merge ({why})"


@dataclass(frozen=True)
class Move:
    item: DriveItem
    from_folder: str
    to_folder: str
    path: str  # the item's Drive path, for the printed plan


@dataclass
class MergePlan:
    path: str
    kept: DriveItem | None = None
    emptied: list[DriveItem] = field(default_factory=list)
    moves: list[Move] = field(default_factory=list)
    refusals: list[str] = field(default_factory=list)

    @property
    def needed(self) -> bool:
        return bool(self.emptied)


class FolderMerge:
    def __init__(self, items: DriveItems, receipts: ReceiptFolder, store: RawFileStore):
        """`store` reads by path afterwards (the check every reader depends on)."""
        self.items, self.receipts, self.store = items, receipts, store

    def plan(self, path: str) -> MergePlan:
        plan = MergePlan(path)
        _, copies = self.items.copies(path)
        copies = [item for item in copies if item.folder]
        if len(copies) < 2:
            return plan
        counts = {item.id: self._verified(item, path) for item in copies}
        best = max(counts.values())
        winners = [item for item in copies if counts[item.id] == best]
        if len(winners) > 1:
            plan.refusals.append(TIE.format(path=path, count=len(winners), verified=best))
            return plan
        plan.kept = winners[0]
        plan.emptied = [item for item in copies if item is not plan.kept]
        for copy in plan.emptied:
            self._plan_moves(copy.id, plan.kept.id, path, plan)
        return plan

    def apply(self, plan: MergePlan, day: date) -> list[str]:
        """Carries out a plan without refusals; returns the problems found reading back every receipt."""
        if plan.refusals or not plan.needed:
            return list(plan.refusals)
        for move in plan.moves:
            self.items.move(move.item, move.from_folder, move.to_folder)
        for number, copy in enumerate(plan.emptied):
            name = MERGED_NAME.format(name=copy.name, day=day) + (f"-{number + 1}" if number else "")
            self.items.rename(copy, name)
        return self.check(plan.path)

    def check(self, path: str) -> list[str]:
        problems = []
        for receipt in self.receipts.under(path):
            try:
                data = self.store.get(receipt.path)
            except Exception as failure:  # noqa: BLE001 - every unreadable receipt is named, none stops the check
                problems.append(NOT_VERIFIED.format(path=receipt.path, why=type(failure).__name__))
                continue
            if data is None or hashlib.sha256(data).hexdigest() != receipt.sha256:
                why = "missing" if data is None else "other bytes"
                problems.append(NOT_VERIFIED.format(path=receipt.path, why=why))
        return problems

    def _plan_moves(self, source: str, target: str, path: str, plan: MergePlan) -> None:
        present = {}
        for item in self.items.children(target):
            present.setdefault(item.name, []).append(item)
        for item in self.items.children(source):
            item_path = f"{path}/{item.name}"
            same = present.get(item.name, [])
            if not same:
                plan.moves.append(Move(item, source, target, item_path))
            elif item.folder and len(same) == 1 and same[0].folder:
                self._plan_moves(item.id, same[0].id, item_path, plan)
            else:
                plan.refusals.append(CLASH.format(path=path, name=item.name))

    def _verified(self, folder: DriveItem, path: str) -> int:
        count = 0
        for item in self.items.children(folder.id):
            item_path = f"{path}/{item.name}"
            if item.folder:
                count += self._verified(item, item_path)
                continue
            receipt = self.receipts.read(item_path)
            if receipt is not None and hashlib.sha256(self.items.content(item)).hexdigest() == receipt.sha256:
                count += 1
        return count
