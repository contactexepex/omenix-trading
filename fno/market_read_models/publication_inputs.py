"""Which archived copies each publication read (story P8, judge 66): NSE and NSDL serve only their latest flows day, so
the archive keeps a copy per day fetched and a session's figures may come from more than one. The contract's stored row
has no field for this, so it is kept in the repository: one CSV row per publication, page and dataset, giving the
number of copies, the newest one's filing day and the SHA-256 of the full list (`<session> <filed on> <sha256>` lines,
sorted). The list itself is the flows reader's on the publication's session, re-made from the append-only archive and
checked against that SHA-256. A re-run that publishes the same ID adds nothing."""

from __future__ import annotations

import csv
import hashlib
import io
from collections.abc import Callable
from pathlib import Path

from .flows_block import FlowsCopy
from .publication import Publication

FIELDS = ("publication_id", "page_key", "dataset", "copies", "newest_filed_on", "copies_sha256")
LINE = "    {page_key} read {copies} {dataset} copies, newest filed {newest_filed_on}, list SHA-256 {copies_sha256}"
RECORDED = "publication inputs: {rows} row(s) added to {path}"
ALREADY = "publication inputs: {publication_id} already recorded"


def copies_sha256(copies: list[FlowsCopy]) -> str:
    lines = sorted(f"{c.session.isoformat()} {c.filed_on.isoformat()} {c.sha256}" for c in copies)
    return hashlib.sha256("\n".join(lines).encode()).hexdigest()


def input_rows(publication: Publication) -> list[dict]:
    rows = []
    for page_key, copies in sorted(publication.inputs.items()):
        for dataset in sorted({c.dataset for c in copies}):
            used = [c for c in copies if c.dataset == dataset]
            rows.append({
                "publication_id": publication.publication_id, "page_key": page_key, "dataset": dataset,
                "copies": str(len(used)), "newest_filed_on": max(c.filed_on for c in used).isoformat(),
                "copies_sha256": copies_sha256(used),
            })  # fmt: skip
    return rows


class PublicationInputsFile:
    def __init__(self, path: Path, commit: Callable[[str], str] | None = None):
        self.path, self.commit = Path(path), commit

    def record(self, publication: Publication) -> list[str]:
        """The lines to print: one per dataset read, then what was written (and committed, when a commit is given)."""
        rows = input_rows(publication)
        lines = [LINE.format(**row) for row in rows]
        if not rows:
            return lines
        if publication.publication_id in {r["publication_id"] for r in self.rows()}:
            return [*lines, ALREADY.format(publication_id=publication.publication_id)]
        self._append(rows)
        lines.append(RECORDED.format(rows=len(rows), path=self.path.name))
        return [*lines, self.commit(f"market publish {publication.day}")] if self.commit else lines

    def rows(self) -> list[dict]:
        return list(csv.DictReader(io.StringIO(self.path.read_text()))) if self.path.is_file() else []

    def _append(self, rows: list[dict]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        new = not self.path.is_file()
        with self.path.open("a", newline="") as out:
            writer = csv.DictWriter(out, fieldnames=FIELDS, lineterminator="\n")
            if new:
                writer.writeheader()
            writer.writerows(rows)
