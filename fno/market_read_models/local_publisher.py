"""A ReadModelPublisher writing to a folder (story P6): tests and local runs. Each publication is written to its own
folder under a temporary name and renamed into place; only then does `current.json` move to it (one atomic rename),
so a failure part-way leaves the previous publication current."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from .publication import Publication, hashes
from .publisher import PublishFailed, ReadModelPublisher

CURRENT_FILE = "current.json"
PUBLICATIONS = "publications"


class LocalFolderPublisher(ReadModelPublisher):
    name = "local folder"

    def __init__(self, folder: Path):
        self.folder = Path(folder)

    def publish(self, publication: Publication) -> int:
        target = self.folder / PUBLICATIONS / publication.publication_id
        added = 0
        try:
            if not target.exists():
                self._write_folder(target, publication)
                added = len(publication.records)
            elif self.stored(publication.publication_id) != hashes(publication):
                raise PublishFailed(f"{publication.publication_id} exists with different pages")
            self._write_json(self.folder / CURRENT_FILE, {"publication_id": publication.publication_id,
                                                         "day": publication.day.isoformat()})  # fmt: skip
        except OSError as exc:
            raise PublishFailed(f"{publication.publication_id}: {exc}") from exc
        return added

    def stored(self, publication_id: str) -> dict[str, str]:
        return {
            key: r["payload_sha256"]
            for key, r in self._read_folder(self.folder / PUBLICATIONS / publication_id).items()
        }

    def current(self) -> dict[str, dict]:
        pointer = self.folder / CURRENT_FILE
        if not pointer.is_file():
            return {}
        publication_id = json.loads(pointer.read_text(encoding="utf-8"))["publication_id"]
        return self._read_folder(self.folder / PUBLICATIONS / publication_id)

    def _write_folder(self, target: Path, publication: Publication) -> None:
        partial = target.with_name(f".{target.name}.part")
        shutil.rmtree(partial, ignore_errors=True)
        partial.mkdir(parents=True)
        try:
            for page_key, record in publication.records.items():
                self.write_record(partial / f"{page_key}.json", record)
            partial.rename(target)
        finally:
            shutil.rmtree(partial, ignore_errors=True)

    def write_record(self, path: Path, record: dict) -> None:
        path.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")

    @staticmethod
    def _read_folder(folder: Path) -> dict[str, dict]:
        return {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted(folder.glob("*.json"))}

    @staticmethod
    def _write_json(path: Path, value: dict) -> None:
        partial = path.with_name(f".{path.name}.part")
        partial.write_text(json.dumps(value), encoding="utf-8")
        partial.replace(path)
