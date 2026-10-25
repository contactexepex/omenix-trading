"""Composition root of `fno/school/accounts/` (story MS-P1d): one E1 paper account per driver version under
`journal/school/`, its brake lifted by the monthly review file, mirrored to Drive's private `paper` area through E2c's
`PrivateFiles` (the desk's own, under repository paths, so school files never share a Drive name with the desk's)."""

from pathlib import Path

from ...config import ROOT
from ..settings import SchoolSettings
from .names import school_root
from .reviews import REVIEWS_FILE, ReviewFile
from .school_accounts import AccountSync, SchoolAccounts


def build_account_sync(root: Path = ROOT) -> AccountSync:
    from ...desk.wiring import build_private_files

    return build_private_files(root)


def build_account_port(cfg: dict, settings: SchoolSettings, root: Path = ROOT,
                       sync: AccountSync | None = None) -> SchoolAccounts:  # fmt: skip
    """`sync` None keeps the accounts local (tests, replays); the fleet passes `build_account_sync()`."""
    return SchoolAccounts(school_root(root), settings.account_rs, settings.brake_rs, cfg["charges"],
                          ReviewFile(Path(root) / REVIEWS_FILE), sync)  # fmt: skip
