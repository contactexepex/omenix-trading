"""Where a practice run lives in Drive (story MS-SIM-e, 7.8). Every path is `school-practice/<run id>/<scenario>/...`,
under the same data store as the pilot's `school/` area but in its own folder, with its own receipt folder, so no
practice path can be mistaken for a pilot path and the pilot's readers never reach it.

The run id is short (a hash) and fixed by what the run read and ran: the window, the roads, the scenarios, the code
identity and the digest of its input receipts. The same run is the same id; new code or new captures make a new run, so
an archived run is never touched."""

import hashlib
import re
from collections.abc import Iterable
from datetime import date

PRACTICE_AREA = "school-practice"
REPORT_NAME = "report.txt"
RUN_ID_PATTERN = re.compile(r"\d{8}_\d{8}_[0-9a-f]{12}")
HASH_CHARS = 12


class BadRunId(ValueError):
    """A run id that could escape its folder or collide with another path."""


def run_id(first: date, last: date, roads: Iterable[str], scenarios: Iterable[str], code: str, inputs: str) -> str:
    """`20240304_20240306_<12 hex>`: the dates for the eye, the hash for everything else the run depended on."""
    basis = "|".join([",".join(sorted(roads)), ",".join(sorted(scenarios)), code, inputs])
    return f"{first:%Y%m%d}_{last:%Y%m%d}_{hashlib.sha256(basis.encode()).hexdigest()[:HASH_CHARS]}"


def checked(name: str) -> str:
    if not RUN_ID_PATTERN.fullmatch(name):
        raise BadRunId(f"not a practice run id: {name!r}")
    return name


def run_folder(name: str) -> str:
    return f"{PRACTICE_AREA}/{checked(name)}"


def file_path(name: str, scenario: str, relative: str) -> str:
    """`relative` is the file's place inside the scenario (dates and a name), never absolute and never up a level."""
    if not re.fullmatch(r"[a-z0-9]+", scenario) or relative.startswith("/") or ".." in relative.split("/"):
        raise BadRunId(f"not a practice file place: {scenario!r} {relative!r}")
    return f"{run_folder(name)}/{scenario}/{relative}"


def report_path(name: str) -> str:
    return f"{run_folder(name)}/{REPORT_NAME}"


def receipts_folder(name: str) -> str:
    """Where the run's receipts sit in the repository (exact paths are committed, never a glob)."""
    return f"receipts/data/{run_folder(name)}"
