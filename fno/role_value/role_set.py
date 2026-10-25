"""A book version's evaluated units (story F9a; S1 `role_value_schedule`): each registered AI role, or each declared
bundle of roles that cannot be separated, with an identifier. A role inside a bundle is never a unit on its own, and
the mandatory control roles (data, risk, cost and validity checks, the meters) are never units."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

CONTROL_ROLES = frozenset({"data_checks", "risk_manager", "cost_accountant", "hard_validity", "cusum", "stop_rule"})


class RoleSetError(ValueError):
    pass


@dataclass(frozen=True)
class Unit:
    unit_id: str
    roles: tuple[str, ...]

    @property
    def is_bundle(self) -> bool:
        return len(self.roles) > 1


@dataclass(frozen=True)
class RoleSet:
    book: str
    version: str
    units: tuple[Unit, ...]  # in identifier order: the rotation's order

    @classmethod
    def of(cls, book: str, version: str, units: Mapping[str, Sequence[str]]) -> RoleSet:
        built = tuple(Unit(uid, tuple(roles)) for uid, roles in sorted(units.items()))
        roles = [role for unit in built for role in unit.roles]
        controls = sorted(set(roles) & CONTROL_ROLES | set(units) & CONTROL_ROLES)
        if controls:
            raise RoleSetError(f"{book} v{version}: control roles are never evaluated units: {', '.join(controls)}")
        if len(roles) != len(set(roles)) or not all(unit.roles for unit in built):
            raise RoleSetError(f"{book} v{version}: each role belongs to exactly one unit, and no unit is empty")
        return cls(book, version, built)

    @property
    def unit_ids(self) -> tuple[str, ...]:
        return tuple(unit.unit_id for unit in self.units)

    def bundle_of(self, role: str) -> str | None:
        """The bundle a role belongs to, when it is bundled; None for a role that is its own unit or unknown."""
        for unit in self.units:
            if unit.is_bundle and role in unit.roles:
                return unit.unit_id
        return None


class RoleSets(ABC):
    @abstractmethod
    def role_set(self, book: str, version: str) -> RoleSet:
        """The units registered for one book version; RoleSetError when the version registers none."""
