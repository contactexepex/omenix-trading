"""The routine side of an AI book's decision (story F1t), what its routine runs; standard library only.

- `brief`: checks the fired pointer, the committed common pack's SHA-256 and the decision prompt's registered hash,
  then prints F1t's model rule, the prompt, `INPUT` and the input (common pack, own private pack, analyst cards).
  Nothing of the input is shown unless every check passes.
- `seal`: completes and checks the answer (refusals list what to fix), then publishes only the commitment.
- `reveal`: from `reveal_from`, publishes the answer and the salt.
The working files (pointer, salt, answer) stay in `.ai_decision/`, which is git-ignored."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from ..ai.run_timing import RunTiming
from ..ai.seal import Commitment, commitment_hash, new_salt
from ..ai.sealed_publish import ALREADY_SEALED, SealedPublisher, SealRefused
from ..ai.transport import PublishFailed
from ..desk.pack_items import canonical_json, sha256_hex
from ..desk.private_pack import ALLOWED_FOLDERS
from .answer import MODEL_RULE, check_answer, complete_answer, labels_of
from .figures import private_figures
from .paths import WORK_FOLDER, commitment_path, common_pack_path, reveal_path
from .pointer import DecisionPointer, parse_pointer
from .versions import DecisionRegistry

POINTER_FILE, SEALED_FILE = "pointer.txt", "sealed.json"
NO_COMMON_PACK = "no committed common pack for {day}: pull main and try again"
WRONG_COMMON_PACK = "the committed common pack for {day} is not the one fired"


class StepRefused(RuntimeError):
    """A step cannot run (wrong order, a wrong pack); the message says what to do."""


@dataclass
class DecisionSession:
    root: Path
    registry: DecisionRegistry
    publisher: SealedPublisher
    timing: RunTiming  # F8c's run timing, with its decision run name (agreed with F8c's owner, 16 Oct)
    out: Callable[[str], None] = print

    def brief(self, text: str) -> None:
        pointer = parse_pointer(text, self.registry)
        self.timing.start(pointer)
        prompt = self.registry.current(pointer.book).prompt_text(self.root)
        common = self._common_pack(pointer)
        self._save(POINTER_FILE, text)
        self.out(MODEL_RULE)
        self.out(prompt)
        self.out(f"INPUT (seal by {pointer.receipt_deadline:%H:%M:%S}; labels {_hash(labels_of(pointer))[:12]})")
        body = {
            "analyst_cards": pointer.analyst_cards,
            "common_pack": json.loads(common),
            "private_pack": pointer.private_pack,
        }
        self.out(json.dumps(body, sort_keys=True, indent=1, ensure_ascii=False))

    def seal(self, answer_file: Path) -> None:
        pointer = parse_pointer(self._load(POINTER_FILE), self.registry)
        version, labels = self.registry.current(pointer.book), labels_of(pointer)
        answer = complete_answer(json.loads(Path(answer_file).read_text(encoding="utf-8")), labels)
        public = [f for f in ALLOWED_FOLDERS[pointer.book] if not f.startswith("journal/")]
        private = private_figures(pointer.private_pack, self._common_pack(pointer).decode("utf-8"), public)
        check_answer(answer, labels, version.shape_check, private)
        path = commitment_path(pointer.day, pointer.book)
        if self.publisher.is_sealed(path):
            raise SealRefused(ALREADY_SEALED.format(path=path))
        salt = new_salt()
        self._save(SEALED_FILE, json.dumps({"answer": answer, "salt": salt}))  # kept before publishing: reveal needs it
        commitment = Commitment(pointer.book, pointer.day.isoformat(), pointer.version, _hash(labels),
                                commitment_hash(salt, answer))  # fmt: skip
        commit = self.publisher.commit(path, commitment, _message(pointer, "commitment (sealed answer)"))
        self.out(f"sealed: {pointer.book} {pointer.day} in commit {commit[:10]}; only the remote at "
                 f"{pointer.receipt_deadline:%H:%M:%S} decides whether it is on time")  # fmt: skip

    def reveal(self) -> None:
        pointer = parse_pointer(self._load(POINTER_FILE), self.registry)
        sealed = json.loads(self._load(SEALED_FILE))
        path = reveal_path(pointer.day, pointer.book)
        if pointer.reveal_from > self.publisher.clock():
            self.out(f"waiting until {pointer.reveal_from:%H:%M:%S} before revealing")
            self.publisher.wait_until(pointer.reveal_from)
        commit = self.publisher.reveal(
            path, sealed["answer"], sealed["salt"], _message(pointer, "reveal (answer and salt)")
        )
        self.out(f"already revealed: {path}" if commit is None else f"revealed in commit {commit[:10]}")
        self._time_run(pointer)

    def _time_run(self, pointer: DecisionPointer) -> None:
        """The run's timing for BG1's ledger; a failure is said and never raised (the reveal is already out)."""
        try:
            self.out(self.timing.publish(pointer, _message(pointer, "run timing")))
        except (PublishFailed, ValueError, OSError) as failed:
            self.out(f"timing NOT published ({failed}): the run's AI minutes will show as not captured")

    def _common_pack(self, pointer: DecisionPointer) -> bytes:
        path = self.root / common_pack_path(pointer.day)
        if not path.is_file():
            raise StepRefused(NO_COMMON_PACK.format(day=pointer.day))
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != pointer.common_pack_sha256:
            raise StepRefused(WRONG_COMMON_PACK.format(day=pointer.day))
        return data

    def _save(self, name: str, text: str) -> None:
        folder = self.root / WORK_FOLDER
        folder.mkdir(exist_ok=True)
        (folder / name).write_text(text, encoding="utf-8")

    def _load(self, name: str) -> str:
        path = self.root / WORK_FOLDER / name
        if not path.is_file():
            raise StepRefused(f"{name} missing: run the steps in order (brief, seal, reveal)")
        return path.read_text(encoding="utf-8")


def _hash(value: dict) -> str:
    return sha256_hex(canonical_json(value))


def _message(pointer: DecisionPointer, what: str) -> str:
    return f"F1t {pointer.book} {pointer.day}: decision {what}"
