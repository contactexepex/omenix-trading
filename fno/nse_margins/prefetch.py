"""Day files read ahead, handed back in day order (story A14c's full run reads about 1,700 archived files).

Measured on 16 Oct 2026: one Drive download stream gave 0.41 MB/s (27-30 s per 12 MB file) and 16 parallel streams
were each as fast, so a one-at-a-time full run would take about 14 hours. At most `workers` downloads are in flight;
the caller still receives the files strictly in the order asked, so what it computes cannot change. Any download
error is raised at that day and stops the reading (fail closed); pending downloads are cancelled."""

from __future__ import annotations

import threading
from collections import deque
from collections.abc import Callable, Iterator, Sequence
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import date

from .job import DayFile


def per_thread(new_day_file: Callable[[], DayFile]) -> DayFile:
    """A day-file reader that builds its own reader (its own Drive session) once in each thread that calls it."""
    local = threading.local()

    def read(day: date) -> tuple[str, bytes | None]:
        if not hasattr(local, "day_file"):
            local.day_file = new_day_file()
        return local.day_file(day)

    return read


def in_order(day_file: DayFile, days: Sequence[date], workers: int) -> Iterator[tuple[date, tuple[str, bytes | None]]]:
    """Each day with its file, in the order of `days`, with up to `workers` downloads running ahead."""
    if workers < 1:
        raise ValueError(f"workers must be at least 1, not {workers}")
    pool = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="day-file")
    ahead: deque[tuple[date, Future]] = deque()
    upcoming = iter(days)
    try:
        for day in upcoming:
            ahead.append((day, pool.submit(day_file, day)))
            if len(ahead) == workers:
                break
        while ahead:
            day, future = ahead.popleft()
            found = future.result()  # a download error is raised here, at its own day
            following = next(upcoming, None)
            if following is not None:
                ahead.append((following, pool.submit(day_file, following)))
            yield day, found
    finally:
        pool.shutdown(wait=True, cancel_futures=True)
