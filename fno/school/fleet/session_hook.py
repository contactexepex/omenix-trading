"""A step the fleet runs after the session's outcomes are sealed and before its counts are committed (story MS-P1j;
the instructor's session run, MS-INS part e, agreed with its builder 23 Oct 2026). It can never stop the school's own
record: a failure or a time-out is one #fno-desk alert naming its class, and the counts are still written and
committed.

One committer per run (judge 523, orchestrator's ruling): the step's work runs on a thread under its time limit and
only reads and computes; it returns its writes, which run here, on the run's own thread, only when the work ended in
time. So a thread past its limit, which Python cannot stop, has written nothing and never can: what it returns later is
dropped with it, and the run's single counts commit takes only files this thread wrote."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

from ..constants import UnavailableReason
from .isolate import isolated

NOT_RUN = "school {name} not run for {session} ({why}); the session's own record and counts are unaffected"
NOT_WRITTEN = "school {name} not written for {session} ({why}); the session's own record and counts are unaffected"
TIME_LIMIT = "time limit"

Writes = Callable[[], object]  # the step's writes, run on the run's own thread


def nothing_to_prepare() -> None:
    """A step whose work reads nothing the run must fetch first."""


@dataclass(frozen=True)
class StagedSessionStep:
    """`prepare` runs on the run's thread before the work (e.g. one fetch of `main`, so the work never runs git);
    `work(session)` runs on the thread under `seconds` and returns its `Writes`."""

    name: str
    work: Callable[[date], Writes]
    alert: Callable[[str], object]
    seconds: float = 300.0
    prepare: Callable[[], object] = nothing_to_prepare

    def __call__(self, session: date) -> None:
        try:
            self.prepare()
        except Exception as failure:  # noqa: BLE001 - the school's record never stops for its step
            self.alert(NOT_RUN.format(name=self.name, session=session, why=type(failure).__name__))
            return
        done = isolated(lambda: self.work(session), self.seconds)
        if done.failed:
            why = TIME_LIMIT if done.failed is UnavailableReason.DEADLINE else done.error_class
            self.alert(NOT_RUN.format(name=self.name, session=session, why=why))
            return
        try:
            done.value()
        except Exception as failure:  # noqa: BLE001 - as above; named by class only
            self.alert(NOT_WRITTEN.format(name=self.name, session=session, why=type(failure).__name__))


def no_step(session: date) -> None:
    """A run with no step after its outcomes (a replay, the tests)."""
