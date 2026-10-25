"""The daily run's child commands (story O1): each of its own steps is an existing `python -m fno ...` command run
unchanged, so its rules, output and alerts stay the story's that built it. Behind an interface so tests use fakes."""

from __future__ import annotations

import contextlib
import os
import signal
import subprocess
import sys
import tempfile
from abc import ABC, abstractmethod
from collections.abc import Callable, Sequence
from pathlib import Path

from ..alerts.sender import NOT_SENT, SENT

UNSENT = NOT_SENT.split(":")[0]  # "alert NOT sent": a child's own unsent alert, printed for the routine's connector
ALERT_OUTCOMES = (SENT, UNSENT)  # a line a command's own alert left, sent or not


def alerted_in(printed: Sequence[str]) -> bool:
    """True when a command's whole output holds its own alert's outcome line, sent or not."""
    return any(outcome in line for line in printed for outcome in ALERT_OUTCOMES)


KEPT_LINES = 10  # the run log keeps the last lines a command printed (result lines; never a secret, O5's scan)


class Process(ABC):
    @abstractmethod
    def poll(self) -> int | None:
        """The exit code once the command has ended; None while it runs."""

    @abstractmethod
    def lines(self) -> list[str]:
        """The last `KEPT_LINES` non-empty lines it printed (read once, after it has ended)."""

    @abstractmethod
    def alerted(self) -> bool:
        """True when it sent an alert of its own, Slack up or down: read from its whole output, which `lines` is not
        (an unsent alert's text never reaches the committed run log)."""

    @abstractmethod
    def stop(self) -> None:
        """Ends a command that ran past its limit."""

    def errors(self) -> list[str]:
        """The last lines it wrote to its error output (tracebacks, library logs): the private full log only, never
        the committed run log (story O1-status-only)."""
        return []


class Processes(ABC):
    @abstractmethod
    def start(self, arguments: Sequence[str], hold: int | None = None) -> Process:
        """Starts `python -m fno <arguments>` in the repository and returns at once; `hold`, an open file the child
        inherits and keeps for its life (a 3 pm part's lock, story O1 F1)."""


class ChildProcess(Process):
    """Its whole output is read once when it ends or is stopped: every unsent-alert line in it is printed as written
    (judge 178 addendum 6: CLAUDE.md's 3 pm rules have the routine post those lines), the last lines are kept."""

    def __init__(self, popen: subprocess.Popen, output, report: Callable[[str], None] = print, error_output=None):
        self.popen, self.output, self.report, self.printed = popen, output, report, None
        self.error_output, self.written = error_output, None

    def poll(self) -> int | None:
        return self.popen.poll()

    def stop(self) -> None:
        """Kills the child's whole process group, so a git or Groww call it started dies with it (judge 178 add. 3
        note 8)."""
        with contextlib.suppress(ProcessLookupError):  # it ended on its own meanwhile
            os.killpg(self.popen.pid, signal.SIGKILL)
        self.popen.wait()
        self._read()

    def lines(self) -> list[str]:
        """The last result lines, never an unsent alert: its text goes to the routine only (it can hold what is meant
        for Slack alone, such as a Drive error's text), never into the committed run record."""
        return [line for line in self._read() if UNSENT not in line][-KEPT_LINES:]

    def alerted(self) -> bool:
        return alerted_in(self._read())

    def errors(self) -> list[str]:
        if self.written is None:
            self.written = _lines(self.error_output) if self.error_output is not None else []
        return self.written[-KEPT_LINES:]

    def _read(self) -> list[str]:
        if self.printed is None:
            self.printed = _lines(self.output)
            for line in self.printed:
                if UNSENT in line:
                    self.report(line)
        return self.printed


class ChildProcesses(Processes):
    """The commands run with this Python and the routine's environment (its settings, never printed)."""

    def __init__(self, root: Path, report: Callable[[str], None] = print):
        self.root, self.report = Path(root), report

    def start(self, arguments: Sequence[str], hold: int | None = None) -> Process:
        output = tempfile.TemporaryFile("w+", encoding="utf-8")  # noqa: SIM115 - open for the child's run, closed once read
        error_output = tempfile.TemporaryFile("w+", encoding="utf-8")  # noqa: SIM115 - the same; kept apart from stdout
        command = [sys.executable, "-m", "fno", *arguments]
        # its own process group, so `stop` ends everything it started
        popen = subprocess.Popen(command, cwd=self.root, stdout=output, stderr=error_output, text=True,
                                 start_new_session=True, pass_fds=() if hold is None else (hold,))  # fmt: skip
        return ChildProcess(popen, output, self.report, error_output)


def _lines(output) -> list[str]:
    """Every non-empty line of a finished child's output file, which is closed once read."""
    output.seek(0)
    lines = [line.rstrip() for line in output.read().splitlines() if line.strip()]
    output.close()
    return lines
