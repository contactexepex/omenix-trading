"""Which files decide G14's values (story G14, amendment 1 section 3b): the files of this package that make records,
scores or the gap table, and every `fno` module they import, directly or through others, found by walking the imports
(never a hand list). Files that only wiring reaches are starts too (`OUTSIDE_STARTS`: A16b's candle table, judge 596
S2; the session calendar, the second self-review); the wiring files themselves are hashed without following their
imports, which reach the whole app (`WIRING`). Shared modules that other
stories change are recorded, not checked, as v4's freeze records `fno/constants.py`
(`fno/forecast_scoring/v4/freeze_check.py`, `RECORDED_NOT_CHECKED`; not imported here, so the walk stays small). One
list for each record's method hash and for `FREEZE_v5_v1.md`. Fail closed (judge 596 addendum 2): `SHARED` is the one
exclusion list; any other walked file is byte-checked, and a new file joins `SHARED` only by a judged change."""

from __future__ import annotations

import ast
import hashlib
from pathlib import Path

PACKAGE = "fno/forecast_v5_v1"
OUTSIDE_STARTS = (  # input-path files no package module imports: wiring reaches them
    "fno/intraday/candle_rv_table.py",  # A16b's file layout and columns (the reader's table class)
    "fno/forecast_v4/sessions.py",  # which days are scored sessions (the trailing day, HAR's refits)
    "fno/storage/trading_days.py",
)
RECORD_STARTS = (f"{PACKAGE}/history.py", f"{PACKAGE}/capture.py", f"{PACKAGE}/records.py", *OUTSIDE_STARTS)
FREEZE_STARTS = (*RECORD_STARTS, f"{PACKAGE}/method.py", f"{PACKAGE}/report.py", f"{PACKAGE}/gap.py")
WIRING = (  # pick the reader, the folders and the inputs: hashed, their imports not followed (they reach the whole app)
    f"{PACKAGE}/wiring.py",
    "fno/forecast_v4_rules/wiring.py",
    "fno/forecast_v4_rules/pack_wiring.py",
)
SHARED = (
    # changed by other stories almost daily (125 commits in the 10 days to 24 Oct 2026)
    "fno/constants.py",
    "fno/constants_channels.py",
    "fno/constants_operations.py",
    "fno/models.py",
    # reached only because W8's reader imports one label, BACKFILLED, from global_cues/table.py (judge 615 S1; 10
    # commits in 10 days, none on G14's value path); the label's value is pinned by a test instead
    "fno/global_cues/table.py",
    "fno/global_cues/collection.py",
    "fno/global_cues/source.py",
    "fno/storage/row_log.py",
    "fno/storage/raw_store.py",
)


def _module_file(root: Path, dotted: str) -> str | None:
    """The repository path of an `fno` module (or of the module part of `fno.x.y.Name`), None for anything else."""
    parts = dotted.split(".")
    for k in range(len(parts), 0, -1):
        for candidate in (Path(*parts[:k]).with_suffix(".py"), Path(*parts[:k], "__init__.py")):
            if (root / candidate).is_file():
                return candidate.as_posix()
    return None


def _imports(root: Path, relative: str) -> set[str]:
    """The `fno` files one file imports."""
    package = Path(relative).parent.parts
    found = set()
    for node in ast.walk(ast.parse((root / relative).read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            base = list(package[: len(package) - node.level + 1]) if node.level else []
            module = ".".join(base + ([node.module] if node.module else []))
            names = [module] + [f"{module}.{alias.name}" for alias in node.names]
        else:
            continue
        found |= {f for name in names if name.startswith("fno") and (f := _module_file(root, name))}
    return found


def walk(root: Path, starts: tuple[str, ...]) -> list[str]:
    """Every file reached from `starts` (included), sorted."""
    seen, todo = set(), list(starts)
    while todo:
        relative = todo.pop()
        if relative not in seen:
            seen.add(relative)
            todo.extend(_imports(root, relative))
    return sorted(seen)


def checked(root: Path, starts: tuple[str, ...]) -> list[str]:
    """The walk without the shared modules: the files whose bytes are hashed."""
    return [f for f in walk(root, starts) if f not in SHARED]


def recorded(root: Path, starts: tuple[str, ...]) -> list[str]:
    """The walk's shared modules: listed, not hashed."""
    return [f for f in walk(root, starts) if f in SHARED]


def freeze_files(root: Path) -> list[str]:
    """What `FREEZE_v5_v1.md` byte-checks: every file of this package (wiring and cli included), the walk from
    `FREEZE_STARTS` minus `SHARED`, and v4's two wiring files (the start set only limits which imports are followed;
    judge 596 addendum 2)."""
    package = {p.relative_to(root).as_posix() for p in (root / PACKAGE).glob("*.py")}
    return sorted(package | set(checked(root, FREEZE_STARTS)) | set(WIRING))


def method_sha256(root: Path) -> str:
    """Each record's method hash: SHA-256 over the paths and bytes of the checked files and the wiring, in path
    order."""
    digest = hashlib.sha256()
    for relative in sorted({*checked(root, RECORD_STARTS), *WIRING}):
        digest.update(f"{relative}\n".encode())
        digest.update((root / relative).read_bytes())
    return digest.hexdigest()
