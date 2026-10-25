"""What carries a number in a checkout (story O12): the series' files and the numbered addendum headings in them."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from fno.numbering.categories import AddendumCategory, Category

ADDENDUM_HEADING = re.compile(r"^#{2,3} Addendum ([1-9]\d*)\b", re.MULTILINE)
FENCED = re.compile(r"^```.*?^```", re.MULTILINE | re.DOTALL)  # a quoted heading in a code block is not a section


@dataclass(frozen=True)
class NumberedItem:
    number: str
    name: str  # the file name; for an addendum, the file it is in
    where: str  # repository path, for the finding lines


def misnamed_files(root: Path, category: Category) -> list[str]:
    """Files that start like the series but do not follow `<prefix>_<n>_<slug>.md` (`response_07_x.md`, `review_7.md`):
    they would escape the check, so they are findings."""
    folder = root / category.folder
    starts = sorted(folder.glob(f"{category.prefix}_*")) if folder.is_dir() else []
    return [p.relative_to(root).as_posix() for p in starts if not category.file_number(p.name)]


def numbered_items(root: Path, category: Category) -> list[NumberedItem]:
    folder = root / category.folder
    files = sorted(p for p in folder.glob("*.md") if category.file_number(p.name)) if folder.is_dir() else []
    if isinstance(category, AddendumCategory):
        return [item for path in files for item in _addenda(root, category, path)]
    return [NumberedItem(category.file_number(p.name), p.name, p.relative_to(root).as_posix()) for p in files]


def _addenda(root: Path, category: AddendumCategory, path: Path) -> list[NumberedItem]:
    report = category.file_number(path.name)
    where = path.relative_to(root).as_posix()
    headings = ADDENDUM_HEADING.findall(FENCED.sub("", path.read_text(encoding="utf-8")))
    return [NumberedItem(f"{report}.{k}", path.name, where) for k in headings]
