"""One SHA-256 receipt of a Drive file (story O9): where the bytes are, what they hash to, and who wrote them when."""

from __future__ import annotations

from dataclasses import dataclass

FIELD_SEPARATOR = "\t"


@dataclass(frozen=True)
class Receipt:
    path: str  # the Drive path, area included (e.g. `data/intraday/...`)
    sha256: str
    size: int
    written_at: str  # UTC, ISO 8601 with offset
    writer: str  # the job or command that wrote the file
    run_id: str

    def to_text(self) -> str:
        fields = (self.sha256, str(self.size), self.written_at, self.writer, self.run_id)
        return FIELD_SEPARATOR.join(fields) + "\n"

    @classmethod
    def from_text(cls, path: str, text: str) -> Receipt:
        sha256, size, written_at, writer, run_id = text.rstrip("\n").split(FIELD_SEPARATOR)
        return cls(path, sha256, int(size), written_at, writer, run_id)
