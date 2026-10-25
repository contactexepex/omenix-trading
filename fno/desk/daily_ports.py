"""What the daily run depends on (story E3), each behind an interface so a fake can stand in for it in tests and a
real part can be swapped in the composition root: the common pack, the books' committed decisions, the execution
capture, C4's validity gate, the exit rules, the account writes across containers and the commits."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import TYPE_CHECKING, TypeVar

from ..checks.data_checks import CaptureRecord
from ..research_engine.ledger import GitFailed
from .common_pack import CommonPack
from .entries import EntryOrder
from .exit_rules import ExitRule
from .records import DeskJournal

if TYPE_CHECKING:
    from .daily_steps import StepOutcome

T = TypeVar("T")


@dataclass(frozen=True)
class CommittedDecision:
    """A book's decision run as committed: its run ID, when its commit happened, and the entry orders it decided."""

    book: str
    run_id: str
    commit: str  # the commit that holds the run
    committed_at: datetime  # its committer time (time zone aware)
    run: Path | None = None  # the run's folder (D3): its orders are built from it at the fill, C4's pass read there


class DayStep(ABC):
    """One of story O1's steps around the desk's own (weather, v4 forecasts, the quote parts, the card): run once at
    its place in `DAILY_RUN_STEPS`, recorded and committed by the daily run like any desk step."""

    @abstractmethod
    def run(self, day: date) -> StepOutcome:
        """What the step did: its inputs, its result (with `status` and `reason`) and the files to commit."""


class Waiter(ABC):
    @abstractmethod
    def until(self, moment: datetime) -> None:
        """Returns at `moment` (at once when it has passed)."""


class CommitFailed(Exception):
    """The committer could not commit and push (a refused file, a failed pull, a push rejected every time); the message
    names why, and `unpushed` says a local commit was left for the rerun to push. The daily run stops at that step with
    one alert (decision 44)."""

    def __init__(self, message: str, unpushed: bool = False):
        super().__init__(message)
        self.unpushed = unpushed


RUN_STOPS = (CommitFailed, GitFailed)  # what stops the whole run (decision 44), never one step's own failure


class StepInterrupted(Exception):
    """An unexpected error inside a step after it had written `written` trades to the accounts (`__cause__` is the
    error): the daily run fails the step and its alert says those trades stay (judge 570 minor 2)."""

    def __init__(self, written: int):
        super().__init__(f"{written} trades written before the error")
        self.written = written


@dataclass(frozen=True)
class OwnCommit:
    """This run's own earlier commit that may still be unpushed (a rejected push being recovered): its message and the
    SHA-256 of each file as recorded (None for a file that did not exist)."""

    message: str
    files: Mapping[str, str | None]  # path relative to the repository root -> SHA-256


class Committer(ABC):
    @abstractmethod
    def commit(self, paths: Sequence[Path], message: str, own_unpushed: OwnCommit | None = None) -> str:
        """Pulls, commits these paths and pushes; the commit ID. Raises `CommitFailed` when it cannot. Any unpushed
        commit other than `own_unpushed` is refused."""


class Packs(ABC):
    @abstractmethod
    def build(self, day: date) -> CommonPack:
        """Builds and writes the day's common pack (E2); `PackError` while the canonical snapshot is not committed."""

    @abstractmethod
    def stored(self, day: date) -> CommonPack | None:
        """The day's written common pack; None when none was written."""

    @abstractmethod
    def files(self, day: date) -> tuple[Path, ...]:
        """The day's written pack files, to commit."""


class VersionKeeper(ABC):
    @abstractmethod
    def keep(self, day: date) -> str:
        """Registers (and commits) a new D6 version of Book 1 when its served playbook changed; one line saying what."""


class DecisionSource(ABC):
    """On time is what the collector observes at the deadline (judge 82): the origin commit it pulled then."""

    @abstractmethod
    def observe(self) -> str:
        """Pulls now and returns the commit seen: the runs visible from it are the only ones collected."""

    @abstractmethod
    def committed(self, book: str, day: date, deadline: datetime) -> CommittedDecision | None:
        """The book's first original run (story D3b's run order) visible after `observe`, committed (committer time)
        before `deadline`; never a correction."""

    @abstractmethod
    def others(self, book: str, day: date, taken: str | None) -> list[dict]:
        """Every other run of the day in the same order, for the run log: run ID, commit and time, and for a
        correction what it corrects and why. Shown, never collected."""

    @abstractmethod
    def recorded(self, book: str, day: date, run_id: str, commit: str) -> CommittedDecision:
        """The run the decisions step recorded, read again for the fills; refused if it is not held by `commit`."""


class OrdersRefused(ValueError):
    """A committed run gives no orders (it does not replay under today's code, or decided a version whose exits code
    cannot enforce): that book's entries fail closed for the day; exits are unaffected (judge 84)."""


class OrderBuilder(ABC):
    """A committed decision run's entry orders (E5 for Book 1; F5 and F6 for the AI books), built at the fill."""

    @abstractmethod
    def orders(self, book: str, run: Path, decided_at: datetime) -> Sequence[EntryOrder]:
        """The orders the run decided (empty for "no trade"); `decided_at` is when the run was committed.
        `OrdersRefused` when it may give none."""


class ExecutionCapture(ABC):
    @abstractmethod
    def capture(self, day: date) -> CaptureRecord | None:
        """Takes one execution capture now (a second recorder capture, A4's rules), writes and commits its capture
        record; None when no capture could be taken."""


class ValidityGate(ABC):
    """C4's hard-validity checks on a committed decision (story C4, built apart)."""

    @abstractmethod
    def problems(self, decision: CommittedDecision, order: EntryOrder) -> list[str]:
        """Why this order may not be filled; empty only after a completed C4 pass."""


class ExitRules(ABC):
    @abstractmethod
    def rules(self, book: str) -> Mapping[str, Sequence[ExitRule]]:
        """Each open trade's exit rules, from its playbook version (by trade ID)."""


class AccountWriteRefused(RuntimeError):
    """An account write that could not be made durable (another container's work in the way, git refusing): that
    write's entries fail closed for the day, with an alert; the run goes on to every exit review (judge 84)."""


class AccountSync(ABC):
    @abstractmethod
    def write(self, book: str, apply: Callable[[DeskJournal], T], message: str) -> T:
        """Runs `apply` on the book's journal under its lock and makes the write durable across containers."""
