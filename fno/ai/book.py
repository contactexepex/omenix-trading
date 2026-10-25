"""The book side of an AI book's forecast (stories F1 and G5; G11 step 7 for protocol v4), what its routine runs:

- `brief`: checks the fired text (a v2 pointer, or a v4 one carrying its whole input, `book_run.read_run`) and the
  versioned prompt's hash, and prints the prompt, then `INPUT` and the input. Nothing is shown unless every check
  passes.
- `seal`: completes and checks the answer (refusals name what to fix, so the model can fix it before the run's
  deadline: 15:15:00 under v2, 15:10:00 under v4), then publishes only the commitment. The salt and answer stay in the
  routine's private working folder.
- `reveal`: waits until the run's reveal time (15:15:10, or 15:10:10 under v4), at most `REVEAL_WAIT_CAP` per call,
  because the prompt runs it under a 10-minute Bash timeout and a v4 book seals about 25 minutes early (G11 C6):
  still early, it says so and ends, and the prompt runs it again. Then it publishes the answer and the salt, then the
  run's own timing (story F8c; `brief` noted its start), in a publish of its own, so a timing failure can never cost
  the reveal.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .answer import check_answer, complete_answer
from .book_run import BookRun, read_run
from .export import build_export
from .paths import WORK_FOLDER
from .run_timing import RunTiming
from .seal import Commitment, new_salt, reveal_text
from .transport import PublishFailed, SubmissionTransport
from .versions import version_by_label

POINTER_FILE, EXPORT_FILE, SEALED_FILE = "pointer.txt", "export.json", "sealed.json"
REVEAL_WAIT_CAP = 9 * 60  # seconds one `reveal` may sleep: inside the prompt's 600,000 ms Bash timeout
STILL_EARLY = "waiting until {at:%H:%M:%S} IST: run reveal again"


class BookStepRefused(RuntimeError):
    """A step cannot run (wrong order, already sealed); the message says what to do."""


@dataclass
class BookSession:
    root: Path
    transport: SubmissionTransport
    clock: Callable[[], datetime]
    sleep: Callable[[float], None]
    timing: RunTiming
    out: Callable[[str], None] = print

    def brief(self, text: str) -> None:
        run = read_run(text, lambda pointer: build_export(self.root, pointer, version_by_label(pointer.version)))
        self.timing.start(run)
        prompt = version_by_label(run.labels["version"]).prompt_text(self.root)
        self._save(POINTER_FILE, text)
        self._save(EXPORT_FILE, json.dumps(run.export, sort_keys=True))
        deadline = run.terms.receipt_deadline(run.day)
        late = f"; WARNING: already past {deadline:%H:%M:%S} IST" if self.clock() > deadline else ""
        self.out(prompt)
        self.out(f"INPUT (export_sha256 {run.labels['export_sha256']}){late}")
        self.out(json.dumps(run.export, sort_keys=True, indent=1))

    def seal(self, answer_file: Path) -> None:
        run = self._run()
        answer = complete_answer(json.loads(Path(answer_file).read_text(encoding="utf-8")), run.labels)
        checked = check_answer(answer, run.labels, run.envelope, run.questions)
        wrong = [f"{q}: {why}" for q, why in checked.problems.items() if why]
        if wrong:
            raise BookStepRefused("not sealed; fix and run seal again: " + "; ".join(wrong))
        path = run.terms.commitment_path(run.day, run.book)
        if self.transport.existing(path) is not None:
            raise BookStepRefused(f"{path} already exists: this book is sealed for {run.day} (written once)")
        salt = new_salt()
        self._save(SEALED_FILE, json.dumps({"answer": answer, "salt": salt}))  # kept before publishing: reveal needs it
        commitment = Commitment.of(answer, salt)
        commit = self.transport.publish(path, commitment.to_text(), _message(run, "commitment (sealed answer)"))
        self.timing.sealed(run)
        deadline = run.terms.receipt_deadline(run.day)
        when = "before" if self.clock() <= deadline else "AFTER"
        self.out(f"sealed: {run.book} {run.day} commitment {commitment.commitment_sha256[:12]} in commit "
                 f"{commit[:10]}, pushed {when} {deadline:%H:%M:%S} IST by this clock "
                 "(GitHub's push time decides)")  # fmt: skip

    def reveal(self) -> None:
        run = self._run()
        sealed = json.loads(self._load(SEALED_FILE))
        if any(sealed["answer"][k] != run.labels[k] for k in ("book", "day")):
            raise BookStepRefused("the sealed answer is not this run's (another day or book): seal this run first")
        self.timing.reveal_called(run)
        opens = run.terms.reveal_opens(run.day)
        wait = (opens - self.clock()).total_seconds()
        if wait > REVEAL_WAIT_CAP:
            self.out(f"waiting {REVEAL_WAIT_CAP} s of the {wait:.0f} s left before {opens:%H:%M:%S} IST")
            self.sleep(REVEAL_WAIT_CAP)
            self.out(STILL_EARLY.format(at=opens))
            return
        if wait > 0:
            self.out(f"waiting {wait:.0f} s until {opens:%H:%M:%S} IST before revealing")
            self.sleep(wait)
        path, text = run.terms.reveal_path(run.day, run.book), reveal_text(sealed["answer"], sealed["salt"])
        existing = self.transport.existing(path)
        if existing is not None:
            if existing != text:
                raise BookStepRefused(f"{path} already holds a different reveal (written once)")
            self.out(f"already revealed: {path}")
        else:
            commit = self.transport.publish(path, text, _message(run, "reveal (answer and salt)"))
            self.out(f"revealed: {run.book} {run.day} in commit {commit[:10]}")
        self._time_run(run)

    def _run(self) -> BookRun:
        text = self._load(POINTER_FILE)
        return read_run(text, lambda pointer: json.loads(self._load(EXPORT_FILE)))

    def _time_run(self, run: BookRun) -> None:
        """The run's timing for BG1's ledger; a failure is said and never raised (the reveal is already out)."""
        try:
            self.out(self.timing.publish(run, _message(run, "run timing")))
        except (PublishFailed, ValueError, OSError) as failed:
            self.out(f"timing NOT published ({failed}): the run's AI minutes will show as not captured")

    def _save(self, name: str, text: str) -> None:
        folder = self.root / WORK_FOLDER
        folder.mkdir(exist_ok=True)
        (folder / name).write_text(text, encoding="utf-8")

    def _load(self, name: str) -> str:
        path = self.root / WORK_FOLDER / name
        if not path.is_file():
            raise BookStepRefused(f"{name} missing: run the steps in order (brief, seal, reveal)")
        return path.read_text(encoding="utf-8")


def _message(run: BookRun, what: str) -> str:
    return f"F1/G5 {run.book} {run.day}: forecast {what}"
