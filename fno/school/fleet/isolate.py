"""Each driver isolated (story MS-P1j): one driver's failure or slowness never stops another. An exception is named by
its class only (a message could carry a contract or a price) and sealed as that driver's `unavailable: driver_error`;
a driver past its time limit is `unavailable: deadline`. A thread past its limit cannot be stopped in Python: it is
left to finish on its own and its result is discarded [reasoning only: a pure rule driver has no side effects]."""

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from dataclasses import dataclass
from typing import Generic, TypeVar

from ..constants import UnavailableReason

T = TypeVar("T")


@dataclass(frozen=True)
class Isolated(Generic[T]):
    value: T | None
    failed: UnavailableReason | None = None
    error_class: str = ""


def isolated(work: Callable[[], T], seconds: float) -> Isolated[T]:
    pool = ThreadPoolExecutor(max_workers=1)
    future = pool.submit(work)
    try:
        return Isolated(future.result(timeout=seconds))
    except FutureTimeout:
        return Isolated(None, UnavailableReason.DEADLINE)
    except Exception as failure:  # noqa: BLE001 - every driver failure is sealed, never raised
        return Isolated(None, UnavailableReason.DRIVER_ERROR, type(failure).__name__)
    finally:
        pool.shutdown(wait=False, cancel_futures=True)
