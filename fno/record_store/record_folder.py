"""The records, kept in git (story DR1): `receipts/records/<dataset>/<yyyy>/<mm>/<session>.<level>.json`, a small
pointer to the chosen version (path and SHA-256) with every check's result; never a data value. Publishing is a push
to main, the one atomic step there is (first push wins), so two certifiers can never both make a record."""

from __future__ import annotations

import json
from pathlib import Path

from .models import Record, StagedVersion
from .publisher import Published, RecordPublisher


def encode(document: dict) -> bytes:
    return (json.dumps(document, indent=1, sort_keys=True) + "\n").encode()


class RecordFolder:
    def __init__(self, folder: Path, publisher: RecordPublisher | None = None):
        """`publisher`: puts a record on origin's main (None: records stay local, e.g. a dry run)."""
        self.folder, self.publisher = Path(folder), publisher

    def file_for(self, dataset: str, session: str, level: str) -> Path:
        year, month, _ = session.split("-")
        return self.folder / dataset / year / month / f"{session}.{level}.json"

    def chosen(self, dataset: str, session: str, level: str) -> StagedVersion | None:
        file = self.file_for(dataset, session, level)
        return chosen_in(file.read_bytes()) if file.is_file() else None

    def write(self, record: Record) -> StagedVersion:
        """Writes once (locally) and returns the version the record names: this one, or an earlier record's."""
        held = self.chosen(record.dataset, record.session, record.level)
        if held is None:
            file = self.file_for(record.dataset, record.session, record.level)
            file.parent.mkdir(parents=True, exist_ok=True)
            temporary = file.with_name(f".{file.name}.part")
            temporary.write_bytes(encode(record.to_document()))
            temporary.replace(file)
        return self.chosen(record.dataset, record.session, record.level)

    def publish(self, dataset: str, session: str, level: str) -> Published | None:
        """None when records stay local; else whether origin's main holds this record (also on a rerun)."""
        if self.publisher is None:
            return None
        return self.publisher.publish(self.file_for(dataset, session, level), f"{dataset} {session} {level}")


def chosen_in(data: bytes) -> StagedVersion:
    return StagedVersion(**json.loads(data)["chosen"])
