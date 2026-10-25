"""The numbered series (story O12): each category has its own number sequence and registry `numbers/<name>.csv`."""

from __future__ import annotations

import re
from dataclasses import dataclass

REGISTRY_FOLDER = "numbers"
SLUG = re.compile(r"^[a-z0-9]+(?:[-_][a-z0-9]+)*$")
WHOLE = r"[1-9]\d*"


@dataclass(frozen=True)
class Category:
    """Files `<folder>/<prefix>_<n>_<slug>.md`, numbered 1, 2, 3 ... in their own sequence."""

    name: str
    folder: str
    prefix: str

    @property
    def registry(self) -> str:
        return f"{REGISTRY_FOLDER}/{self.name}.csv"

    def valid_number(self, number: str) -> bool:
        return re.fullmatch(WHOLE, number) is not None

    def file_number(self, file_name: str) -> str | None:
        """The number in a file name of this series, or None for any other file (a README, a status note)."""
        found = re.fullmatch(rf"{self.prefix}_({WHOLE})_.+\.md", file_name)
        return found.group(1) if found else None

    def claimed_name(self, number: str, slug: str) -> str:
        """The registry row's name: the file to create."""
        return f"{self.prefix}_{number}_{slug}.md"

    def next_step(self, number: str, name: str) -> str:
        """What the claimant writes now, word for word."""
        return f"write {self.folder}/{name}"

    def key(self, number: str, name: str) -> object:
        """What ties a file to its registry row: its number and file name."""
        return number, name

    def keys_for_file(self, number: str, name: str) -> tuple[object, ...]:
        """The row keys a file can be registered under: its own name, or a reservation `<prefix>_<n>_*.md` made
        before the file's name was known (the orchestrator's reservations, 16 Oct 2026)."""
        return self.key(number, name), self.key(number, f"{self.prefix}_{number}_*.md")


@dataclass(frozen=True)
class AddendumCategory(Category):
    """`## Addendum <k>` sections inside the files of `folder`/`prefix`; number `<n>.<k>`, one sequence per file n."""

    def valid_number(self, number: str) -> bool:
        return re.fullmatch(rf"{WHOLE}\.{WHOLE}", number) is not None

    def claimed_name(self, number: str, slug: str) -> str:
        """The registry row's name: a short label (the section lives in an existing file)."""
        return slug

    def next_step(self, number: str, name: str) -> str:
        """The heading to write: only the addendum's own number (judge 307: "## Addendum 307.5" was read as 307.307)."""
        report, addendum = number.split(".")
        return f"write the heading '## Addendum {addendum}' in {self.folder}/{self.prefix}_{report}_*.md"

    def key(self, number: str, name: str) -> object:
        """A heading names no label, so its number alone ties it to its row."""
        return number

    def keys_for_file(self, number: str, name: str) -> tuple[object, ...]:
        return (number,)


CLAUDE_RESPONSE = Category("claude-response", "reviews/claude", "response")
CHATGPT_REVIEW = Category("chatgpt-review", "reviews/chatgpt", "review")
JUDGE_REPORT = Category("judge-report", "reviews/judge", "judge")
JUDGE_ADDENDUM = AddendumCategory("judge-addendum", "reviews/judge", "judge")

CATEGORIES: dict[str, Category] = {c.name: c for c in (CLAUDE_RESPONSE, CHATGPT_REVIEW, JUDGE_REPORT, JUDGE_ADDENDUM)}
# Each addendum series belongs to the file series whose reports it extends.
ADDENDUM_OF: dict[str, Category] = {JUDGE_ADDENDUM.name: JUDGE_REPORT}
