"""The role sets as a file (story F9a): `agents/role_units.yaml`, by book and version, each unit's identifier with its
roles (one role: a separately evaluated role; several: a declared bundle). F2 writes the entries with each version."""

from __future__ import annotations

from pathlib import Path

import yaml

from .role_set import RoleSet, RoleSetError, RoleSets

ROLE_UNITS_FILE = "agents/role_units.yaml"


class RoleUnitsFile(RoleSets):
    def __init__(self, root: Path):
        self.path = Path(root) / ROLE_UNITS_FILE
        self._data: dict | None = None

    def role_set(self, book: str, version: str) -> RoleSet:
        if self._data is None:  # read once per report: every row asks for its version's units
            self._data = (yaml.safe_load(self.path.read_text(encoding="utf-8")) if self.path.is_file() else {}) or {}
        units = (self._data.get(book) or {}).get(str(version))
        if not units:
            raise RoleSetError(f"{ROLE_UNITS_FILE}: no units registered for {book} version {version}")
        return RoleSet.of(book, str(version), {uid: list(roles) for uid, roles in units.items()})
