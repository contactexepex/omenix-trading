"""Engineering-standards enforcer (CLAUDE.md): no ``.py`` file and no class in ``fno/`` exceeds 350 lines.

The limit is inclusive (<= 350 passes); the current largest file, ``fno/shared/constants.py``, sits at exactly 350.
Restored in refactor stage 3. The judge also checks this (``docs/JUDGE.md``)."""

from __future__ import annotations

import ast
from pathlib import Path

MAX_LINES = 350
FNO = Path(__file__).resolve().parent.parent / "fno"


def _py_files() -> list[Path]:
    return sorted(p for p in FNO.rglob("*.py") if "__pycache__" not in p.parts)


def test_at_least_one_module_is_scanned() -> None:
    assert len(_py_files()) > 50  # sanity: the walk actually found the package


def test_no_python_file_exceeds_350_lines() -> None:
    offenders = []
    for path in _py_files():
        lines = len(path.read_text(encoding="utf-8").splitlines())
        if lines > MAX_LINES:
            offenders.append(f"{path.relative_to(FNO.parent)}: {lines} lines")
    assert not offenders, "files over 350 lines:\n" + "\n".join(offenders)


def test_no_class_exceeds_350_lines() -> None:
    offenders = []
    for path in _py_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                span = (node.end_lineno or node.lineno) - node.lineno + 1
                if span > MAX_LINES:
                    offenders.append(f"{path.relative_to(FNO.parent)}::{node.name}: {span} lines")
    assert not offenders, "classes over 350 lines:\n" + "\n".join(offenders)
