"""The exact half of the devil's advocate (story LR1; T3 reuses it): AI text may only repeat numbers the code-built
lines hold. One tokenizer reads both texts the same way and compares whole number tokens, never substrings ("4" does
not match "40%", judge 167 addendum 1). Numbers written in words are refused so the token rule cannot be dodged."""

from __future__ import annotations

import re

NUMBER = re.compile(r"(?<![\w.])[+-]?\d+(?:[.,:-]\d+)*%?(?!\w)")  # 40%, -0.0042, 2026-10-16 and 10:41 are one token
NUMBER_WORDS = re.compile(
    r"\b(zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|"
    r"seventeen|eighteen|nineteen|twenty|half|double|twice|dozen)\b",
    re.IGNORECASE,
)
FORBIDDEN_FORMS = ("http://", "https://", "www.", "<@", "<!", "<#", "```")

SHA_LINE = "rule 1: the first line is not the SHA-256 of the committed lines"
FORM = "rule 2: {what}"
UNKNOWN_NUMBER = "rule 3: number {token} is not in the lines"
NUMBER_IN_WORDS = "rule 4: number written in words ({word})"


def number_tokens(text: str) -> set[str]:
    return set(NUMBER.findall(text))


def sha_failure(text: str, lines_sha256: str) -> tuple[str | None, list[str]]:
    """(the rule 1 failure or None, the lines after the SHA line)."""
    first, *rest = text.splitlines() or [""]
    return (None if first.strip() == lines_sha256 else SHA_LINE), rest


def form_failure(text: str, max_words: int) -> str | None:
    if len(text.split()) > max_words:
        return FORM.format(what=f"more than {max_words} words")
    found = next((f for f in FORBIDDEN_FORMS if f in text), None)
    return None if found is None else FORM.format(what=f"a link, mention or code block ({found})")


def number_failure(text: str, allowed: set[str]) -> str | None:
    """Rules 3 and 4: every number token is a whole token of the lines, and none is written in words."""
    unknown = sorted(number_tokens(text) - allowed)
    if unknown:
        return UNKNOWN_NUMBER.format(token=unknown[0])
    word = NUMBER_WORDS.search(text)
    return None if word is None else NUMBER_IN_WORDS.format(word=word.group(0))


class NumberCheck:
    """The four rules for an AI summary: the SHA line, size and form, numbers from the lines only, none in words."""

    def __init__(self, lines_text: str, lines_sha256: str, max_words: int):
        self.allowed, self.sha, self.max_words = number_tokens(lines_text), lines_sha256, max_words

    def first_failure(self, text: str) -> str | None:
        failure, body_lines = sha_failure(text, self.sha)
        body = "\n".join(body_lines)
        return failure or form_failure(body, self.max_words) or number_failure(body, self.allowed)
