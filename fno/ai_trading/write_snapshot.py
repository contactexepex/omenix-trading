"""The decider's write paths as they were just before `decide()` (story F1t, agreed with F6): every file's bytes and
every folder. A refused or failed decision puts each path back exactly (changed files rewritten, new files and new
folders removed), so nothing half-written (a registry row, a spec file, a ledger row) can be committed later. The
snapshot, not `HEAD`, is the reference: `research/ledger.csv` is shared with the research factory, so a change made
before `decide()` by anyone is kept. The daily run is one thread, so nothing else writes these paths meanwhile.
`OutsideSnapshot` does the same for the rest of the checkout (except the paths it is told to leave alone: the write
paths, and folders the run's children write in parallel): a decider may write nowhere else, and anything it wrote out
there is found and put back (to its state before `decide()`, else `HEAD`), so no later step commits it."""

from __future__ import annotations

import os
import shutil
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class WriteSnapshot:
    root: Path
    paths: tuple[str, ...]
    files: dict[str, bytes]  # repository path -> bytes
    folders: frozenset[str]

    @classmethod
    def take(cls, root: Path, paths: Sequence[str]) -> WriteSnapshot:
        root = Path(root)
        files, folders = {}, set()
        for found in _under(root, paths):
            name = found.relative_to(root).as_posix()
            if found.is_dir():
                folders.add(name)
            else:
                files[name] = found.read_bytes()
        return cls(root, tuple(paths), files, frozenset(folders))

    def changed(self) -> list[str]:
        """Every path under the write paths that differs from the snapshot (new, changed or removed), sorted."""
        now = {p.relative_to(self.root).as_posix(): p for p in _under(self.root, self.paths) if p.is_file()}
        differing = {name for name, path in now.items() if self.files.get(name) != path.read_bytes()}
        return sorted(differing | (set(self.files) - set(now)))

    def restore(self) -> list[str]:
        """Puts every write path back to the snapshot; returns what it changed."""
        changed = self.changed()
        for name in changed:
            path = self.root / name
            if name in self.files:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(self.files[name])
            else:
                path.unlink()
        new_folders = [p for p in _under(self.root, self.paths) if p.is_dir()]
        for folder in sorted(new_folders, key=lambda p: len(p.parts), reverse=True):
            if folder.relative_to(self.root).as_posix() not in self.folders and folder.exists():
                shutil.rmtree(folder)
        return changed


def _under(root: Path, paths: Sequence[str]) -> list[Path]:
    found = []
    for name in paths:
        target = root / name
        if target.is_file():
            found.append(target)
        elif target.is_dir():
            found += [target, *target.rglob("*")]
    return found


def is_under(root: Path, path: Path, paths: Sequence[str]) -> bool:
    """True when `path` is one of `paths` or inside one of them (no `..` or link can escape); a relative `path` is the
    repository's, never the current directory's."""
    resolved = (Path(root) / path).resolve()
    return any(resolved == (Path(root) / p).resolve() or resolved.is_relative_to((Path(root) / p).resolve())
               for p in paths)  # fmt: skip


class Worktree(Protocol):
    def changed(self) -> set[str]:
        """Every path git status lists (untracked included), relative to the root."""

    def at_head(self, path: str) -> bytes | None:
        """The file as `HEAD` holds it; None when `HEAD` has no such file."""


class GitWorktree:
    def __init__(self, root: Path):
        self.root = Path(root)

    def changed(self) -> set[str]:
        out = os.fsdecode(subprocess.run(["git", "status", "--porcelain=v1", "-z", "-uall"], cwd=self.root,
                                         capture_output=True, check=True).stdout)  # fmt: skip
        entries, paths, index = out.split("\0"), set(), 0
        while index < len(entries) and entries[index]:
            code, name = entries[index][:2], entries[index][3:]
            paths.add(name)
            index += 2 if "R" in code or "C" in code else 1  # a rename or copy (either column) carries its old name
        return paths

    def at_head(self, path: str) -> bytes | None:
        shown = subprocess.run(["git", "show", f"HEAD:{path}"], cwd=self.root, capture_output=True)
        return shown.stdout if shown.returncode == 0 else None


@dataclass(frozen=True)
class OutsideSnapshot:
    """Every changed file of the checkout outside the write paths, just before `decide()`: what the decider changes
    out there is found (a decider may write nowhere else) and put back, so no later step can commit it."""

    root: Path
    worktree: Worktree
    inside: tuple[str, ...]
    before: dict[str, bytes | None]  # path -> bytes before decide(); None: absent then

    @classmethod
    def take(cls, root: Path, worktree: Worktree, inside: Sequence[str]) -> OutsideSnapshot:
        outside = [p for p in worktree.changed() if not is_under(root, Path(root) / p, inside)]
        return cls(Path(root), worktree, tuple(inside), {p: _bytes(Path(root) / p) for p in outside})

    def changed(self) -> list[str]:
        now = {p for p in self.worktree.changed() if not is_under(self.root, self.root / p, self.inside)}
        return sorted(p for p in now | set(self.before) if _bytes(self.root / p) != self._reference(p))

    def restore(self) -> list[str]:
        changed = self.changed()
        for name in changed:
            reference, path = self._reference(name), self.root / name
            if reference is None:
                path.unlink(missing_ok=True)
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(reference)
        return changed

    def _reference(self, name: str) -> bytes | None:
        return self.before[name] if name in self.before else self.worktree.at_head(name)


def _bytes(path: Path) -> bytes | None:
    return path.read_bytes() if path.is_file() else None
