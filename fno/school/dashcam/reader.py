"""Reading a sealed file back through the verified Drive cache (story O9, rule 4): only a receipted file counts and
every byte is checked against the receipt's SHA-256 before it is used."""

from typing import Protocol

from ...storage.drive_cache import DriveCache
from ..contracts.seal import StaleSeal

UNREADABLE = "{path} cannot be read back: {problems}"


class SlotFileReader(Protocol):
    def read(self, path: str) -> bytes:
        """The file's verified bytes; `StaleSeal` when it is missing, unreceipted or damaged."""


class VerifiedDriveReader:
    def __init__(self, cache: DriveCache, area: str):
        self.cache, self.area = cache, area

    def read(self, path: str) -> bytes:
        drive_path = f"{self.area}/{path}"
        folder = drive_path.rsplit("/", 1)[0]
        report = self.cache.sync(folder)
        local = self.cache.local(drive_path)
        problems = [problem for problem in report.problems if problem.startswith(f"{drive_path}:")]
        if problems or not local.is_file():  # another file's damage in the folder never blocks this one
            raise StaleSeal(UNREADABLE.format(path=path, problems="; ".join(problems) or "no receipt"))
        return local.read_bytes()
