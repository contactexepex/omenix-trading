"""Deterministic stand-ins for time, sleep, randomness and Slack, so the resilience tests never wait or call out."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta


class FakeClock:
    """A clock whose `sleep` advances it, usable as both the retry policy's clock and sleep."""

    def __init__(self) -> None:
        self.now, self.slept = 0.0, []

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.now += seconds


class WallClock:
    """A timezone-aware clock the breaker reads; `advance` moves it."""

    def __init__(self) -> None:
        self.at = datetime(2026, 10, 27, 9, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.at

    def advance(self, seconds: float) -> None:
        self.at += timedelta(seconds=seconds)


class SpyAlerts:
    def __init__(self) -> None:
        self.sent: list[str] = []

    def send(self, text: str) -> str:
        self.sent.append(text)
        return "spy"


def floor_jitter(low: float, high: float) -> float:
    return low  # the least jitter: the wait is exactly the floor


def top_jitter(low: float, high: float) -> float:
    return high  # the most jitter: the wait is twice the floor
