"""The files of a practice run, as the archive takes them (story MS-SIM-e2): the practice dashcam's record files of
every scenario, read from the run's home folder. Counts, accounts and marks are derived and carry no label, so they
are not archived (orchestrator, 23 Oct); the report reproduces them."""

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from ...dashcam.names import DASHCAM_FOLDER, SLOT_FILE_SUFFIX
from ..practice.dashcam import DASHCAM_HOME
from .names import file_path


@dataclass(frozen=True)
class RunFile:
    path: str  # under the data area, `school-practice/<run id>/<scenario>/<dates>/<slot>.<kind>.jsonl.gz`
    payload: bytes


def run_files(run: str, home: Path, scenarios: tuple[str, ...]) -> Iterator[RunFile]:
    """Every record file the scenarios wrote, in scenario then path order (the same order on a rerun)."""
    for scenario in scenarios:
        folder = Path(home) / scenario / DASHCAM_HOME / DASHCAM_FOLDER
        for file in sorted(folder.rglob(f"*.{SLOT_FILE_SUFFIX}")):
            yield RunFile(file_path(run, scenario, file.relative_to(folder).as_posix()), file.read_bytes())
