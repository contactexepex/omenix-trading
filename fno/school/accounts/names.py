"""Where a driver version's paper account lives (story MS-P1d). E1's `PaperAccount` takes the three books or a shadow
version `shadow:<name>-v<n>`; a school account is `shadow:school-<code>-v<version>` under the school's own root
`journal/school/` (so its files are `journal/school/journal/shadow/school-<code>-v<version>/account/`, git-ignored),
never the desk's `journal/shadow/`, which the desk's marking and scorecards read."""

import re
from pathlib import Path

from ...books.account import EQUITY_HISTORY_FILE
from ...books.account import POSITIONS_FILE as E1_POSITIONS_FILE
from ...books.paths import account_folder
from ...constants import CASH_LEDGER_FILE, JOURNAL_FOLDER, SHADOW_PREFIX

SCHOOL_FOLDER = "school"  # <repo>/journal/school is the school's PaperAccount root
POSITIONS_FILE = "school_positions.jsonl"  # the school's position records beside E1's ledger
_DRIVER_ID = re.compile(r"(?P<code>[A-Z0-9]+)@(?P<version>[1-9][0-9]*)")


def school_root(repository: Path) -> Path:
    return Path(repository) / JOURNAL_FOLDER / SCHOOL_FOLDER


def account_name(driver_id: str) -> str:
    """`CS1@1` -> `shadow:school-cs1-v1`; any other form of driver ID is refused, never guessed."""
    found = _DRIVER_ID.fullmatch(driver_id)
    if found is None:
        raise ValueError(f"driver ID {driver_id!r} is not <code>@<version> (capitals and digits, version from 1)")
    return f"{SHADOW_PREFIX}school-{found['code'].lower()}-v{found['version']}"


def account_files(root: Path, driver_id: str) -> list[Path]:
    """The files a school account is made of, as E2c's private files mirror them (the lock is local only)."""
    folder = account_folder(root, account_name(driver_id))
    return [folder / name for name in (CASH_LEDGER_FILE, E1_POSITIONS_FILE, EQUITY_HISTORY_FILE, POSITIONS_FILE)]
