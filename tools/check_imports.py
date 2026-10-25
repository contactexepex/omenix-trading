"""Clean-slate criterion 1: every runnable Python file imports only `fno` modules that exist.

Parses (AST) every .py file under fno/, tests/, tools/ and research/, resolves absolute and relative imports, and
reports any import of an `fno` module that is not in this checkout. Files listed in ARCHIVAL are historical studies
that run only at their pinned commit (see their README) and are skipped. Exit code 0 when clean, 1 otherwise.

    python tools/check_imports.py
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCANNED = ("fno", "tests", "tools", "research")
# Historical studies that import the removed old desk; runnable only at the commit named in their README.
ARCHIVAL = frozenset({"research/2026-10-12-backtest/replay.py"})


def runnable_files(root: Path = ROOT) -> list[Path]:
    files = (p for folder in SCANNED for p in (root / folder).rglob("*.py") if "__pycache__" not in p.parts)
    return sorted(p for p in files if p.relative_to(root).as_posix() not in ARCHIVAL)


def imported_modules(path: Path, root: Path = ROOT) -> list[str]:
    """Absolute dotted names of every module (and `from` target) the file imports."""
    names = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"), filename=str(path))):
        if isinstance(node, ast.Import):
            names += [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                package = list(path.relative_to(root).parts[:-1])
                base = package[: len(package) - node.level + 1]
                module = ".".join(base + ([node.module] if node.module else []))
            else:
                module = node.module or ""
            names.append(module)
            names += [f"{module}.{alias.name}" for alias in node.names]  # may be a submodule or just a name
    return names


def _exists(dotted: str, root: Path) -> bool:
    path = root.joinpath(*dotted.split("."))
    return path.with_suffix(".py").is_file() or (path / "__init__.py").is_file()


def missing_fno_imports(path: Path, root: Path = ROOT) -> list[str]:
    """`fno` imports of this file that do not resolve to a module, or to a name inside an existing module or package."""
    missing = []
    for name in imported_modules(path, root):
        if (name != "fno" and not name.startswith("fno.")) or _exists(name, root):
            continue
        parent, attr = name.rsplit(".", 1)
        if _exists(parent, root) and (not _is_package(parent, root) or _defined_in_init(parent, attr, root)):
            continue  # `from fno.x import name`: a name inside an existing module or package
        if not any(name.startswith(m + ".") for m in missing):  # report a missing module once, not each name from it
            missing.append(name)
    return missing


def _is_package(dotted: str, root: Path) -> bool:
    return (root.joinpath(*dotted.split(".")) / "__init__.py").is_file()


def problems(root: Path = ROOT) -> list[str]:
    return [f"{path.relative_to(root)}: imports missing module {name}"
            for path in runnable_files(root) for name in missing_fno_imports(path, root)]  # fmt: skip


def _defined_in_init(package: str, attr: str, root: Path) -> bool:
    init = root.joinpath(*package.split(".")) / "__init__.py"
    tree = ast.parse(init.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name == attr:
            return True
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == attr for t in node.targets):
            return True
        if isinstance(node, (ast.Import, ast.ImportFrom)) and any((a.asname or a.name) == attr for a in node.names):
            return True
    return False


def main() -> int:
    found = problems()
    print("\n".join(found) if found else f"clean: {len(runnable_files())} files, {len(ARCHIVAL)} archival skipped")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
