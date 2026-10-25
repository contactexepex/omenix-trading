"""Single-writer lock per paper account (story E1, moved from the removed old E4; clean-slate design section 5).

`with AccountLock(root, book):` holds an exclusive operating-system lock (`flock`) on
`journal/<book>/account/.lock` and writes a lease inside it: the holder (host, process ID, process start time), the
start and the expiry. Rules:

- The lock is taken without waiting: a second writer gets `AccountBusy` at once and must exit without writing.
- A clean exit empties the lease and releases the lock.
- A crashed holder loses its `flock` with its process, but its lease stays in the file. The next writer takes over
  only when that lease has expired **and** its holder is gone; never while the holder is alive (checked by process ID
  and start time on the same host, so a reused process ID is not mistaken for the holder).
- The lock file is never deleted (deleting it would let two writers lock two different files).

Scope (stated, not hidden): an operating-system lock protects one machine. Two cloud containers each have their own
checkout, so between containers the guard is git itself (a push from a stale checkout is rejected) together with
fill-ID idempotency in `PaperAccount`. Linux and macOS only (`fcntl`).
"""

from __future__ import annotations

import fcntl
import json
import os
import socket
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from ..models import now_utc
from .paths import account_folder, file_in_account

LOCK_FILE = ".lock"
UNKNOWN_HOST = "unknown"  # holder of a lease that could not be read
DEFAULT_LEASE_SECONDS = 600.0  # one desk write takes seconds; a crashed holder blocks its book for at most this long


class AccountBusy(RuntimeError):
    """Another writer holds this book's account, or a crashed writer's lease has not expired yet."""


@dataclass(frozen=True)
class Holder:
    host: str
    pid: int
    started: str  # the process's start time as the kernel reports it; tells a live holder from a reused process ID


@dataclass(frozen=True)
class Lease:
    book: str
    holder: Holder
    start: str  # ISO time, UTC
    expiry: str  # ISO time, UTC

    def expired(self, now: datetime) -> bool:
        return now >= datetime.fromisoformat(self.expiry)

    @classmethod
    def from_text(cls, text: str) -> Lease | None:
        """The lease in the lock file; None when the file is empty (released cleanly). A lease that cannot be read
        (a crash while writing it) is treated as held by an unknown process until the default lease expires."""
        if not text.strip():
            return None
        try:
            data = json.loads(text)
            return cls(data["book"], Holder(**data["holder"]), data["start"], data["expiry"])
        except (ValueError, KeyError, TypeError):
            return None


def process_start(pid: int) -> str:
    """The process's start time in clock ticks since boot (Linux `/proc/<pid>/stat` field 22); "" if unknown."""
    try:
        stat = Path(f"/proc/{pid}/stat").read_text()
    except OSError:
        return ""
    return stat.rsplit(")", 1)[1].split()[19]


def this_holder() -> Holder:
    return Holder(socket.gethostname(), os.getpid(), process_start(os.getpid()))


def holder_alive(holder: Holder) -> bool:
    """True when the holder's process still runs on this host. A holder on another host cannot be checked: it counts
    as alive until its lease expires."""
    if holder.host != socket.gethostname():
        return True
    try:
        os.kill(holder.pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        pass  # exists, owned by another user
    return not holder.started or process_start(holder.pid) == holder.started


class AccountLock:
    """Exclusive writer lock on one book's account. Use as a context manager; `held` says whether it is held now."""

    def __init__(self, root: Path, book: str, lease_seconds: float = DEFAULT_LEASE_SECONDS):
        self.book = book
        self.lease_seconds = lease_seconds
        folder = account_folder(root, book)
        folder.mkdir(parents=True, exist_ok=True)
        self.path = file_in_account(folder, LOCK_FILE)
        self.recovered_from: Lease | None = None  # the crashed holder's lease this lock took over, if any
        self._fd: int | None = None

    @property
    def held(self) -> bool:
        return self._fd is not None

    def __enter__(self) -> AccountLock:
        self.acquire()
        return self

    def __exit__(self, *exc) -> None:
        self.release()

    def acquire(self) -> None:
        if self.held:
            raise AccountBusy(f"{self.book}: this lock object already holds the account")
        fd = os.open(self.path, os.O_RDWR | os.O_CREAT, 0o644)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            os.close(fd)
            raise AccountBusy(f"{self.book}: another writer holds the account ({self.path})") from None
        try:
            self._check_previous_lease(fd)
        except BaseException:
            os.close(fd)  # closing releases the flock; the previous lease stays untouched
            raise
        self._fd = fd
        self._write_lease()

    def renew(self) -> None:
        """Extend the lease (a long run calls this before its lease would expire)."""
        if not self.held:
            raise AccountBusy(f"{self.book}: cannot renew a lock that is not held")
        self._write_lease()

    def release(self) -> None:
        if self._fd is None:
            return
        os.ftruncate(self._fd, 0)  # empty lease = released cleanly
        os.fsync(self._fd)
        os.close(self._fd)  # also releases the flock
        self._fd = None

    def _check_previous_lease(self, fd: int) -> None:
        if os.fstat(fd).st_ino != os.stat(self.path).st_ino:
            raise AccountBusy(f"{self.book}: the lock file was replaced while locking; try again")
        text = os.pread(fd, 1 << 16, 0).decode("utf-8", errors="replace")
        lease = Lease.from_text(text)
        now = now_utc()
        if lease is None and text.strip():  # unreadable lease: assume a holder until the default lease has passed
            written = datetime.fromtimestamp(os.fstat(fd).st_mtime, UTC)
            lease = Lease(
                self.book, Holder(UNKNOWN_HOST, 0, ""), written.isoformat(), _plus(written, self.lease_seconds)
            )
        if lease is None:
            return
        if lease.holder.host != UNKNOWN_HOST and holder_alive(lease.holder):
            raise AccountBusy(f"{self.book}: lease holder {lease.holder} is still alive")
        if not lease.expired(now):
            raise AccountBusy(f"{self.book}: a crashed writer's lease runs until {lease.expiry}; not taken over yet")
        self.recovered_from = lease

    def _write_lease(self) -> None:
        now = now_utc()
        lease = Lease(self.book, this_holder(), now.isoformat(), _plus(now, self.lease_seconds))
        data = json.dumps(asdict(lease)).encode()
        os.ftruncate(self._fd, 0)
        os.pwrite(self._fd, data, 0)
        os.fsync(self._fd)


def _plus(moment: datetime, seconds: float) -> str:
    return (moment + timedelta(seconds=seconds)).isoformat()
