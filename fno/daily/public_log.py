"""Story O1-status-only (judge 443): the public form of a step's inputs and result. `journal/runs/<date>.json` is
committed, so it holds status, never data. Every leaf, at any depth and under any key, is judged by its type:
booleans and None stay; integers only under a count key (an integer can be money); floats never; a string only when it
is in the closed vocabulary below, otherwise its reason code: the producer's template it matches, a raised exception's
type, or `unlisted`. A command's printed lines and error output never reach it."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence

from ..constants import NO_DECISION_LATE, STEP_FAILED, STEP_NOT_LIVE, STEP_OK, STEP_REFUSED
from .quote_parts import ADOPTED, EARLIER, RESTARTED, STARTED

UNLISTED = "unlisted"
RAISED = "raised:{kind}"
COMMAND = {STEP_OK: "command:ok", STEP_REFUSED: "command:nothing_written"}  # else "command:exit_<code>"
COUNT_KEYS = frozenset({"exit_code", "marked_contracts", "open_positions", "rows", "n"})
DROPPED_KEYS = frozenset({"lines", "stderr"})  # a command's own output: the private full log only
# status words that hold a space, or that a command step writes as its `status` or `how`
NOT_FILLED = "not filled"  # E3's fills outcome, a literal in fno/desk/daily_steps.py (a test pins it)
WORDS = frozenset({STEP_OK, STEP_FAILED, STEP_REFUSED, STEP_NOT_LIVE, NO_DECISION_LATE, STARTED, RESTARTED, ADOPTED,
                   EARLIER, NOT_FILLED})  # fmt: skip
VOCABULARY = tuple(re.compile(pattern) for pattern in (
    r"(?=[0-9]*[a-f])([0-9a-f]{7,40}|[0-9a-f]{64})",  # commit and file hashes: never digits alone (judge 448)
    r"\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}(:\d{2}(\.\d+)?)?([+-]\d{2}:\d{2}|Z)?)?",  # ISO dates and times
    r"\d{4}-\d{2}-\d{2}-r\d+",  # D3 run ids
    r"[a-z]+_\d{8}_\d{6}",  # quote snapshot ids
    r"(?!.*\d{3})[A-Za-z][A-Za-z0-9_:-]*",  # ids and words: a letter first, no run of 3 digits (strikes, amounts)
))  # fmt: skip
EXCEPTION = re.compile(r"([A-Z][A-Za-z0-9]+): ")  # "OSError: ...", as `Alerted` and the desk record a raise
FIELD_NAME = re.compile(r"[a-z][a-z0-9_]*")  # a key that names a field (`sha256`, `marked_contracts`)
PLACEHOLDER = re.compile(r"\{[^{}]*\}")
LITERAL = re.compile(r"[A-Za-z]")


class TemplateRefused(ValueError):
    """A template without a literal piece would match every text: it can never be a code."""


class ReasonRegistry:
    """Each template is matched by its whole literal skeleton (anchored, each placeholder `.*?`), never by a prefix: a
    template that starts with a placeholder ("{done} applied, ...") would otherwise match every text."""

    def __init__(self, common: Sequence[tuple[str, str]], by_step: Mapping[str, Sequence[tuple[str, str]]]):
        self.common = [self._compiled(code, template) for code, template in common]
        self.by_step = {step: [self._compiled(c, t) for c, t in pairs] for step, pairs in by_step.items()}

    def code(self, step: str, text: str) -> str:
        matching = self.matching(step, text)
        if matching:
            return matching[0]
        raised = EXCEPTION.match(text)
        return RAISED.format(kind=raised.group(1)) if raised else UNLISTED

    def matching(self, step: str, text: str) -> list[str]:
        """Every code whose template matches `text` (the registry's tests require at most one)."""
        return [code for code, skeleton in (*self.by_step.get(step, ()), *self.common) if skeleton.fullmatch(text)]

    def codes(self, step: str) -> list[str]:
        return [code for code, _ in (*self.by_step.get(step, ()), *self.common)]

    @staticmethod
    def _compiled(code: str, template: str) -> tuple[str, re.Pattern]:
        literals = PLACEHOLDER.split(template)
        if not any(LITERAL.search(piece) for piece in literals):
            raise TemplateRefused(f"{code}: {template!r} has no literal piece")
        return code, re.compile(".*?".join(re.escape(piece) for piece in literals), re.DOTALL)


class PublicResult:
    def __init__(self, registry: ReasonRegistry, counts: Iterable[str] = COUNT_KEYS):
        self.registry, self.counts = registry, frozenset(counts)

    def public(self, step: str, value: object, key: str = "") -> object:
        if isinstance(value, Mapping):
            kept = [(k, v) for k, v in value.items() if k not in DROPPED_KEYS]
            public = {self._key(str(k), n): self.public(step, v, str(k)) for n, (k, v) in enumerate(kept)}
            return public | self._command_reason(value, public)
        if isinstance(value, list | tuple):
            return [self.public(step, item, key) for item in value]
        if value is None or isinstance(value, bool):
            return value
        if isinstance(value, int):
            return value if key in self.counts else None
        if isinstance(value, str):
            return value if self._listed(value) else self.registry.code(step, value)
        return None  # a float, or anything else: never public

    @staticmethod
    def _command_reason(result: Mapping, public: Mapping) -> dict:
        """A command's last line is its own text: unless it is a listed message, its code comes from its status and
        exit code (O1's codes)."""
        if not isinstance(result.get("exit_code"), int) or public.get("reason") != UNLISTED:
            return {}
        code = result["exit_code"]
        return {"reason": COMMAND.get(result.get("status"), f"command:exit_{code}")}

    @classmethod
    def _key(cls, key: str, position: int) -> str:
        """Keys are judged too (judge 448): a field name, a book or an id stays; any other key, a contract symbol for
        one, becomes `unlisted:<position>`, unique within its dict."""
        return key if FIELD_NAME.fullmatch(key) or cls._listed(key) else f"{UNLISTED}:{position}"

    @staticmethod
    def _listed(text: str) -> bool:
        return text in WORDS or any(pattern.fullmatch(text) for pattern in VOCABULARY)
