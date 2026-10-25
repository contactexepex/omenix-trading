"""Book 3's constitution (story D5; design 12.3; the owner's answers of 16 Oct 2026): `book3/constitution-v<n>.yaml`,
committed before Book 3's first counted decision, its SHA-256 a D6 component (`constitution`) and a D3 `served` key.
Allowed keys only. NIFTY monthly options, the nine defined-risk structure codes C4 accepts (or a subset), a planned
exit at most 21 calendar days after entry, the packs as the only sources. The owner's risk limits and the scoring
protocol are references, never numbers, so Book 3 can change neither: a number in their place is refused."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import yaml

from ..constants import BOOK3_FOLDER, STRUCTURES, STRUCTURES_ONE_SIDE

DEFINED_RISK_CODES = frozenset((*STRUCTURES, *STRUCTURES_ONE_SIDE))  # C4 fixes every one's maximum loss at entry
UNDERLYING, EXPIRY = "NIFTY", "monthly"
SOURCES = ("common_pack", "private_pack")
RISK_REFERENCE, SCORING_REFERENCE = "risk.profiles.books", "research/evaluation/PROTOCOL.md"
KEYS = ("version", "underlying", "expiry", "structures", "max_holding_days", "sources", "risk", "scoring")
COMPONENT = "constitution"  # its D6 component and D3 `served` key
FILE = "constitution-v{version}.yaml"


class ConstitutionError(ValueError):
    pass


@dataclass(frozen=True)
class Constitution:
    version: int
    structures: frozenset[str]
    max_holding_days: int
    sha256: str


def parse_constitution(raw: bytes, where: str) -> Constitution:
    data = yaml.safe_load(raw.decode("utf-8")) or {}
    if not isinstance(data, dict) or set(data) != set(KEYS):
        raise ConstitutionError(f"{where}: the keys must be exactly {KEYS}")
    fixed = {"underlying": UNDERLYING, "expiry": EXPIRY, "risk": RISK_REFERENCE, "scoring": SCORING_REFERENCE}
    wrong = [f"{key} must be {value!r}" for key, value in fixed.items() if data[key] != value]
    structures = set(data["structures"] or ())
    if not structures or not structures <= DEFINED_RISK_CODES:
        wrong.append(f"structures must be defined-risk codes from {sorted(DEFINED_RISK_CODES)}")
    if not isinstance(data["max_holding_days"], int) or not 1 <= data["max_holding_days"] <= 21:
        wrong.append("max_holding_days must be a whole number of days, 1 to 21 (design 12.3: up to 3 weeks)")
    if list(data["sources"] or ()) != list(SOURCES):
        wrong.append(f"sources must be {list(SOURCES)}")
    if wrong:
        raise ConstitutionError(f"{where}: " + "; ".join(wrong))
    return Constitution(int(data["version"]), frozenset(structures), data["max_holding_days"],
                        hashlib.sha256(raw).hexdigest())  # fmt: skip


class ConstitutionFiles:
    def __init__(self, root: Path):
        self.folder = Path(root) / BOOK3_FOLDER

    def by_sha256(self) -> dict[str, Constitution]:
        """Every constitution version, by the hash of its bytes (the one D6 names is the one in force)."""
        found = {}
        for path in sorted(self.folder.glob("constitution-v*.yaml")) if self.folder.is_dir() else ():
            constitution = parse_constitution(path.read_bytes(), str(path))
            if path.name != FILE.format(version=constitution.version):
                raise ConstitutionError(f"{path}: the file name must match its version")
            found[constitution.sha256] = constitution
        return found
