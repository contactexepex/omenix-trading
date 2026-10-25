"""What the public-record scan (story O5) looks for: one `RecordPattern` per kind of value that must never be committed.

A pattern returns where each value starts in a file's text, and the value, so the scanner can drop allow-listed ones and
name the line; the values themselves are never printed or stored, only the pattern's name. Patterns never match across
a line break.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from collections.abc import Iterable, Iterator
from functools import lru_cache


@lru_cache(maxsize=1)
def lowered(text: str) -> str:
    """The text in lower case, made once per file for all its patterns (the scanner runs every pattern on one text in
    turn; a 60 MB data file was lowered ten times)."""
    return text.lower()


class RecordPattern(ABC):
    """One kind of value that must not appear in a committed record."""

    name: str

    @abstractmethod
    def values_in(self, text: str) -> Iterator[tuple[int, str]]:
        """The start offset and the value of every value of this kind in the text."""


class RegexPattern(RecordPattern):
    """Values matched by a regular expression (the whole match, or its `value` group when it has one).

    `required`: lower-case substrings at least one of which every match contains; a text without any of them is
    skipped without running the regex (a 20 MB data file then costs milliseconds instead of a second).
    """

    def __init__(self, name: str, regex: str, flags: int = 0, required: Iterable[str] = ()):
        self.name = name
        self._regex = re.compile(regex, flags)
        self._required = tuple(required)

    def values_in(self, text: str) -> Iterator[tuple[int, str]]:
        if self._required:
            lower = lowered(text)
            if not any(word in lower for word in self._required):
                return
        group = "value" if "value" in self._regex.groupindex else 0
        for match in self._regex.finditer(text):
            if self.is_real(match.group(group)):
                yield match.start(group), match.group(group)

    def is_real(self, value: str) -> bool:
        """Extra check on a regex match (a subclass narrows it, e.g. by a checksum)."""
        return True


# Placeholders written in docs and examples instead of a real secret: `$VAR`, `${VAR}`, `<your key>`, `***`, `...`
PLACEHOLDER = re.compile(
    r"^[$<{*.]|^(?:x+|changeme|redacted|placeholder|none|null|true|false|password|pass|pwd|secret)$", re.IGNORECASE
)


class SecretValuePattern(RegexPattern):
    """A regex whose matched value is a secret unless it is a placeholder."""

    def is_real(self, value: str) -> bool:
        return not PLACEHOLDER.search(value)


# A secret's name (not part of a longer name), then `:` or `=` (optional quotes), or the word "is" before a value that
# holds a digit (so "GROWW_API_KEY is required" passes and "GROWW_API_KEY is ab12..." does not)
SECRET_NAME = r"(?<![A-Za-z0-9_])(?:{names})(?![A-Za-z0-9_])"
SECRET_SEPARATOR = r"(?:[\"']?[ \t]*[:=][ \t]*[\"']?|[ \t]+is[ \t]+(?=[^\s\"'`,;]*\d))"
# The value: at least `short` characters with a digit in them, or at least `long` characters of any kind
SECRET_VALUE = r"(?P<value>(?=[^\s\"'`,;]*\d)[^\s\"'`,;]{{{short},}}|[^\s\"'`,;]{{{long},}})"


class SecretAssignmentPattern(SecretValuePattern):
    """A value written next to a secret's name: `GROWW_API_KEY=...`, `"access_token": "..."`, `API secret is ...`.
    Placeholders pass."""

    def __init__(
        self,
        name: str,
        secret_names: Iterable[str],
        lengths: tuple[int, int],
        flags: int = 0,
        required: Iterable[str] = (),
    ):
        names = sorted(secret_names, key=len, reverse=True)
        short, long = lengths
        regex = (
            SECRET_NAME.format(names="|".join(names)) + SECRET_SEPARATOR + SECRET_VALUE.format(short=short, long=long)
        )
        super().__init__(name, regex, flags, required or [n.lower() for n in names])


# Verhoeff checksum tables (UIDAI's check digit for Aadhaar numbers)
_VERHOEFF_D = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], [1, 2, 3, 4, 0, 6, 7, 8, 9, 5], [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
    [3, 4, 0, 1, 2, 8, 9, 5, 6, 7], [4, 0, 1, 2, 3, 9, 5, 6, 7, 8], [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2], [7, 6, 5, 9, 8, 2, 1, 0, 4, 3], [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
    [9, 8, 7, 6, 5, 4, 3, 2, 1, 0],
]  # fmt: skip
_VERHOEFF_P = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], [1, 5, 7, 6, 2, 8, 3, 0, 9, 4], [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
    [8, 9, 1, 6, 0, 4, 3, 5, 2, 7], [9, 4, 5, 3, 1, 2, 6, 8, 7, 0], [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5], [7, 0, 4, 6, 9, 1, 3, 2, 5, 8],
]  # fmt: skip


def verhoeff_valid(digits: str) -> bool:
    """True when the last digit is the Verhoeff check digit of the others."""
    check = 0
    for i, digit in enumerate(reversed(digits)):
        check = _VERHOEFF_D[check][_VERHOEFF_P[i % 8][int(digit)]]
    return check == 0


class AadhaarPattern(RegexPattern):
    """Twelve digits (first 2-9, optionally grouped 4-4-4) whose Verhoeff check digit is right, so that only about
    one random 12-digit number in ten is taken for an Aadhaar number."""

    def __init__(self, name: str):
        super().__init__(name, r"(?<![\w.,])[2-9]\d{3}([ -]?)\d{4}\1\d{4}(?![\w.,])")

    def is_real(self, value: str) -> bool:
        return verhoeff_valid(re.sub(r"\D", "", value))
