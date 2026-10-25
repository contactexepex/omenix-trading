"""A committer that adds and commits only the paths its writer owns inside a shared folder (story A16e): another
story's files in the same folder (A16b's `rv-candle/`) are never swept into its commits. It also names whatever is
staged in the checkout outside those paths, which its writer must refuse: another writer is mid-commit there, and a
staged file anywhere makes the pull's merge fail."""

from __future__ import annotations

from collections.abc import Sequence

from .manifest_commit import GitManifestRecorder


class OwnedPathsCommitter(GitManifestRecorder):
    def __init__(self, repository, folder, owned: Sequence[str], **options):
        """`owned`: names inside `folder`; a directory ends with "/" (`rv/`), a file does not (`heartbeat.json`)."""
        super().__init__(repository, folder, **options)
        self.owned = tuple(f"{self.folder}/{name}" for name in owned)

    def owns(self, path: str) -> bool:
        return any(_matches(name, path) for name in self.owned)

    def _paths(self) -> list[str]:
        """Only owned paths that exist or are tracked: Git refuses a whole `add` when one pathspec matches nothing
        (exit 128), and `rv/` does not exist before the first session's last mark."""
        listed = self._git("ls-files", "-z", "--cached", "--others", "--exclude-standard", "--", self.folder)
        present = [path for path in listed.stdout.split("\0") if path]
        return [name for name in self.owned if any(_matches(name, path) for path in present)]

    def foreign_staged(self) -> list[str]:
        """Everything staged in the whole checkout that is not an owned path, sorted."""
        staged = self._git("diff", "--cached", "--name-only", "-z").stdout.split("\0")
        return sorted(path for path in staged if path and not self.owns(path))


def _matches(name: str, path: str) -> bool:
    return path.startswith(name) if name.endswith("/") else path == name
