"""Run status of every publish run (story P7): one row per product and run, `running` at the start, then `published`,
`failed` with a reason code, or `skipped`. The dashboard reads the latest row to say why F&O data is stale (judge 57).
Recording never hides the run's own result: a status write that fails returns a line saying so, and the run goes on."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path

from ..models import now_utc
from .db_errors import AUTHENTICATION, FIREWALL, NETWORK, PRIVILEGE, TLS

RUNNING, PUBLISHED, FAILED, SKIPPED = "running", "published", "failed", "skipped"
NOT_A_SESSION, ARCHIVE_INCOMPLETE, CONTRACT_CHANGED = "not_a_session", "archive_incomplete", "contract_changed"
SCHEMA_INVALID, PUBLISH_REFUSED, READ_BACK_MISMATCH = "schema_invalid", "publish_refused", "read_back_mismatch"
CRASHED, DATABASE_OTHER, FIGURES_NOT_COMPUTED = "crashed", "database_other", "figures_not_computed"
DATABASE_CODES = {  # a database failure class (db_errors) -> its reason code
    NETWORK: "database_network", FIREWALL: "database_firewall", TLS: "database_tls",
    AUTHENTICATION: "database_authentication", PRIVILEGE: "database_privilege",
}  # fmt: skip
NOT_RECORDED = "run status NOT recorded ({cause}); the run's own result above stands"
LOCAL_FILE = "run_status.jsonl"

START = """
insert into fno.run_status (product, run_id, session, started_at, result) values (%s, %s, %s, now(), 'running')
on conflict (product, run_id) do nothing
"""
FINISH = """
update fno.run_status set finished_at = now(), result = %s, reason_code = %s, reason = %s, publication_id = %s
where product = %s and run_id = %s and result = 'running'
"""


@dataclass(frozen=True)
class Outcome:
    result: str
    reason_code: str | None = None
    reason: str | None = None  # the line the run printed and alerted (never a credential: see db_errors)
    publication_id: str | None = None


def database_code(failure_class: str | None) -> str:
    return DATABASE_CODES.get(failure_class, DATABASE_OTHER) if failure_class else PUBLISH_REFUSED


class RunStatusRecorder(ABC):
    """Where run status rows go. Both methods return None, or a line saying the row was not recorded."""

    @abstractmethod
    def start(self, run_id: str, session: date) -> str | None: ...

    @abstractmethod
    def finish(self, run_id: str, outcome: Outcome) -> str | None: ...


class PostgresRunStatus(RunStatusRecorder):
    def __init__(self, url: str, connect: Callable, product: str):
        self._url, self._connect, self.product = url, connect, product  # the URL holds the credential

    def start(self, run_id: str, session: date) -> str | None:
        return self._execute(START, (self.product, run_id, session))

    def finish(self, run_id: str, outcome: Outcome) -> str | None:
        o = outcome
        return self._execute(FINISH, (o.result, o.reason_code, o.reason, o.publication_id, self.product, run_id))

    def _execute(self, statement: str, values: tuple) -> str | None:
        from psycopg import Error

        from .db_errors import described

        try:
            with self._connect(self._url) as connection:
                connection.execute(statement, values)
        except Error as exc:
            return NOT_RECORDED.format(cause=described(exc))
        return None


class LocalRunStatus(RunStatusRecorder):
    """JSON lines in a folder (local runs and tests): the same rows the table holds."""

    def __init__(self, folder: Path, product: str, clock: Callable[[], datetime] = lambda: now_utc()):
        self.file, self.product, self.clock = Path(folder) / LOCAL_FILE, product, clock

    def start(self, run_id: str, session: date) -> str | None:
        return self._append({"run_id": run_id, "session": session.isoformat(), "result": RUNNING})

    def finish(self, run_id: str, outcome: Outcome) -> str | None:
        return self._append({"run_id": run_id, **asdict(outcome)})

    def rows(self) -> list[dict]:
        """Each run's latest state, in start order."""
        latest: dict[str, dict] = {}
        lines = self.file.read_text(encoding="utf-8").splitlines() if self.file.is_file() else []
        for row in map(json.loads, lines):
            latest[row["run_id"]] = {**latest.get(row["run_id"], {}), **row}
        return list(latest.values())

    def _append(self, row: dict) -> str | None:
        try:
            self.file.parent.mkdir(parents=True, exist_ok=True)
            with self.file.open("a", encoding="utf-8") as out:
                out.write(json.dumps({"product": self.product, "at": self.clock().isoformat(), **row}) + "\n")
        except OSError as exc:
            return NOT_RECORDED.format(cause=type(exc).__name__)
        return None
