"""The checks on every paired row before anything is scored (story F9a criteria 1-2). A row is refused, with its day
and unit, when the two decisions used different packs or snapshots, or a snapshot that is not the day's execution
snapshot in E3's run log (both checked on scored rows); when the unit is not the one the rotation schedules; or when
it names a role that only exists inside a bundle. The rotation (S1 `role_value_schedule`): the k-th row of a book
version from the common start (k from 0) ablates unit k mod n, in identifier order; rows before the common start are
pilot rows and never move the cycle. Every row is a day the book committed a real decision, a no-trade included, so
every row advances the cycle and a day without a row does not."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from datetime import date

from .role_set import RoleSet
from .rows import SCORED, PairedRow


class RowRefused(ValueError):
    pass


def _refuse(row: PairedRow, why: str) -> RowRefused:
    return RowRefused(f"{row.book} {row.day} unit {row.unit!r}: {why}")


def check_unit(row: PairedRow, role_set: RoleSet) -> None:
    if row.unit in role_set.unit_ids:
        return
    bundle = role_set.bundle_of(row.unit)
    if bundle:
        raise _refuse(row, f"the role belongs to the declared bundle {bundle!r} and is evaluated only as that bundle")
    raise _refuse(row, f"not a registered unit of {row.book} version {row.version}")


def check_hashes(row: PairedRow, run_log_snapshots: Mapping[date, str]) -> None:
    if row.real_packs_sha256 != row.shadow_packs_sha256:
        raise _refuse(row, "the real and the shadow decision used different packs")
    if row.real_snapshot_id != row.shadow_snapshot_id:
        raise _refuse(row, "the real and the shadow decision were valued on different snapshots")
    logged = run_log_snapshots.get(row.day)
    if row.real_snapshot_id != logged:
        raise _refuse(row, f"snapshot {row.real_snapshot_id!r} is not the run log's execution snapshot ({logged})")


def check_rotation(rows: Sequence[PairedRow], role_set_of: Callable[[str], RoleSet], common_start: date) -> None:
    position: dict[str, int] = {}
    for row in (r for r in rows if r.day >= common_start):
        units = role_set_of(row.version).unit_ids
        k = position.get(row.version, 0)
        if row.unit != units[k % len(units)]:
            raise _refuse(
                row, f"the rotation schedules {units[k % len(units)]!r} for this day (row {k} of the version)"
            )
        position[row.version] = k + 1


def checked(rows: Sequence[PairedRow], role_set_of: Callable[[str], RoleSet],
            run_log_snapshots: Mapping[date, str], common_start: date) -> list[PairedRow]:  # fmt: skip
    """The book's rows, all checked; the first refusal stops the report (a damaged record is never scored)."""
    for row in rows:
        check_unit(row, role_set_of(row.version))
        if row.status == SCORED:  # an unavailable or unscored shadow has no pack or snapshot to compare
            check_hashes(row, run_log_snapshots)
    check_rotation(rows, role_set_of, common_start)
    return list(rows)
