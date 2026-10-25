"""Where the packs are written (story E2): `journal/packs/<date>/common.json` and
`journal/<book>/packs/<date>/private.json`, each beside a `.sha256` file in `sha256sum` form, so `sha256sum -c`
checks it. Written once: the same bytes again are accepted (idempotent rerun), different bytes are refused, and each
file appears whole or not at all (written to a temporary file, then renamed). Committing is the daily run's job."""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path

from ..constants import JOURNAL_FOLDER, PACKS_FOLDER
from .common_pack import CommonPack
from .pack_items import PackError
from .private_pack import PrivatePack

COMMON_FILE, PRIVATE_FILE = "common.json", "private.json"


class PackStore:
    def __init__(self, root: Path):
        self.root = Path(root)

    def common_path(self, day: date) -> Path:
        return self.root / JOURNAL_FOLDER / PACKS_FOLDER / day.isoformat() / COMMON_FILE

    def private_path(self, book: str, day: date) -> Path:
        return self.root / JOURNAL_FOLDER / book / PACKS_FOLDER / day.isoformat() / PRIVATE_FILE

    def write_common(self, pack: CommonPack) -> Path:
        return self._write(self.common_path(pack.day), pack.data, pack.sha256)

    def write_private(self, pack: PrivatePack) -> Path:
        return self._write(self.private_path(pack.book, pack.day), pack.data, pack.sha256)

    def _write(self, path: Path, data: bytes, sha256: str) -> Path:
        if path.exists():
            if path.read_bytes() != data:
                raise PackError(f"{path} already holds a different pack: packs are written once")
            return path
        path.parent.mkdir(parents=True, exist_ok=True)
        for target, content in ((path, data), (path.with_suffix(".sha256"), f"{sha256}  {path.name}\n".encode())):
            temporary = target.with_name(f".{target.name}.tmp")
            temporary.write_bytes(content)
            os.replace(temporary, target)
        return path
