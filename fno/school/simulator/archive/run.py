"""Archiving one practice run (story MS-SIM-e2): every record file, then the report text last, each saved, receipted
and read back from Drive before the next. The first file that cannot be archived or verified stops the run, so what
exists is the leading part of the list and the outcome says `local only, not archived` with the reason (a run that
failed half-way is reported partial, never as archived)."""

from collections.abc import Iterable

from .archive import PracticeArchive
from .files import RunFile
from .names import report_path
from .outcome import ArchiveOutcome

COMMIT_WHAT = "practice run {run}: {path}"


def archive_run(archive: PracticeArchive, run: str, files: Iterable[RunFile], report_text: str) -> ArchiveOutcome:
    everything = [*files, RunFile(report_path(run), report_text.encode("utf-8"))]
    outcome = ArchiveOutcome(run, len(everything))
    for file in everything:
        try:
            archived = archive.archive(run, file.path, file.payload, COMMIT_WHAT.format(run=run, path=file.path))
            archive.verify(archived)
        except Exception as error:  # noqa: BLE001 - any store, push or read-back failure is one named stop
            outcome.problem = f"{type(error).__name__}: {error}"
            break
        outcome.files.append(archived)
    return outcome
