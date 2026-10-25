"""The fleet port (stories MS-P1i and MS-P1j): one session's run of every driver on every road. The acceptance
harness (i) plants faults through it on the fake fleet, and the real fleet (j) must pass the same harness."""

from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from typing import Protocol, runtime_checkable

from .accounts import FillResult
from .records import DecisionRecord
from .seal import Seal


class RunMode(StrEnum):
    RECORD = "record"  # the paper record: Drive store, receipts pushed
    REPLAY = "replay"  # a recorded session again: fixed clock, local store, nothing pushed


@dataclass(frozen=True)
class SessionRun:
    session: date
    mode: RunMode
    status: str  # "" when it ran; SCHOOL_OFF_LINE when the switch is off (then nothing below is set)
    decisions: tuple[DecisionRecord, ...] = ()  # one per scheduled (road, driver version), sealed before any fill
    decisions_seal: Seal | None = None
    fills: tuple[FillResult, ...] = ()  # every fill of the session, account entries first
    warnings: tuple[str, ...] = ()  # lines the run must make loud (a card mismatch, counts not pushed); exit 1

    def __post_init__(self):
        if self.status and (self.decisions or self.decisions_seal or self.fills or self.warnings):
            raise ValueError("a run that did not run records nothing")
        if self.decisions and self.decisions_seal is None:
            raise ValueError("decisions are sealed")


@runtime_checkable
class FleetRunner(Protocol):
    def run(self, session: date, mode: RunMode) -> SessionRun: ...
