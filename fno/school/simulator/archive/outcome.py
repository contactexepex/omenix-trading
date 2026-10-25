"""What archiving a run came to, and the report lines that say so (story MS-SIM-e2; 7.8, "The limit lifts only for an
archived run"). `archived` is true only when every file of the run, the report text last, has a receipt on the remote
and a verified read-back from Drive; anything less says `local only, not archived` and names the problem."""

from dataclasses import dataclass, field

from ..practice.render import NOT_ARCHIVED, line
from .archive import ArchivedFile
from .names import receipts_folder

ARCHIVED = "archived: run {run}, {count} files, receipts {folder}, first receipt commit {commit}"
STOPPED = "archiving stopped after {done} of {total} files: {problem}"
REPORT_HEAD = "report text of run {run}; its files and receipts are listed in {folder}"


@dataclass
class ArchiveOutcome:
    run: str
    total: int  # the files the run has, the report text included
    files: list[ArchivedFile] = field(default_factory=list)
    problem: str | None = None

    @property
    def archived(self) -> bool:
        return len(self.files) == self.total > 0

    def status_lines(self) -> list[str]:
        """The report's first line(s): the archived line, or `local only, not archived` and why."""
        if self.archived:
            return [line(ARCHIVED.format(run=self.run, count=self.total, folder=receipts_folder(self.run),
                                          commit=self.files[0].commit))]  # fmt: skip
        lines = [line(NOT_ARCHIVED)]
        if self.problem:
            lines.append(line(STOPPED.format(done=len(self.files), total=self.total, problem=self.problem)))
        return lines


def report_head(run: str) -> str:
    """The archived report text's first line: it cannot hold its own receipt's commit, so it names the run."""
    return line(REPORT_HEAD.format(run=run, folder=receipts_folder(run)))
