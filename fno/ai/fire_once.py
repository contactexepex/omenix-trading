"""Fire once, even across a crash (story F1t, O1 builder's point 3; reused by F2's role routines). A fire log names each
routine to fire on a day. Before any trigger is called, every entry to fire is written as `firing` and the log is
committed and pushed; only then is each trigger called, and its result written. A container that dies after a call
but before the result was recorded leaves a `firing` entry: the rerun never calls that trigger again and marks it
`fire_unknown` (a routine that did start still publishes its sealed answer, which is judged as usual). A container
lost before the first commit fired nothing. Entries keep `fno/ai`'s fire-log fields (`fired`, `session`, `reason`),
so the audit plan reads them alike; `fired` is True, False, or None for `fire_unknown`."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime
from pathlib import Path

FIRING, FIRED, NOT_FIRED, FIRE_UNKNOWN = "firing", "fired", "not_fired", "fire_unknown"
UNKNOWN_REASON = "the container stopped during the fire (between the trigger call and its record): not fired again"
NOT_PUSHED = "the fire log could not be pushed before firing ({error}): nothing was fired"

Commit = Callable[[Sequence[Path], str], object]  # commits and pushes these paths; raises when it cannot
FireOne = Callable[[str], dict]  # fires one routine: {"fired": True, "session": ...} or {"fired": False, "reason": ...}


class FireLogRefused(ValueError):
    """The fire log on disk is not one this module wrote."""


class FireOnceLog:
    def __init__(self, root: Path, path: str, commit: Commit, clock: Callable[[], datetime]):
        self.root, self.file, self.commit, self.clock = Path(root), Path(root) / path, commit, clock

    def read(self) -> dict[str, dict]:
        if not self.file.is_file():
            return {}
        log = json.loads(self.file.read_text(encoding="utf-8"))
        if not isinstance(log, dict) or not all(isinstance(e, dict) and "state" in e for e in log.values()):
            raise FireLogRefused(f"{self.file} is not a fire log (every entry needs a state)")
        return log

    def fire(self, planned: Mapping[str, dict], fire_one: FireOne, message: str) -> dict[str, dict]:
        """`planned`: name -> entry; an entry with `"fire": True` is to be fired, any other is final as given (a
        `not_fired` with its reason). The first call commits the `firing` log, fires and writes the results; a later
        call fires nothing and only turns leftover `firing` entries into `fire_unknown`. The caller commits the file
        after this returns."""
        log = self.read()
        if log:
            return self._settle_leftovers(log)
        log = {name: self._planned(entry) for name, entry in planned.items()}
        self._write(log)
        to_fire = [name for name, entry in log.items() if entry["state"] == FIRING]
        try:
            self.commit((self.file,), f"{message}: about to fire {', '.join(to_fire) or 'none'}")
        except Exception as failed:  # noqa: BLE001 - no trigger is called: each entry says so, never `firing`
            reason = NOT_PUSHED.format(error=type(failed).__name__)
            log = {n: e | {"state": NOT_FIRED, "fired": False, "reason": reason} if n in to_fire else e
                   for n, e in log.items()}  # fmt: skip
            self._write(log)
            return log
        for name in to_fire:
            log[name] = self._fired(log[name], name, fire_one)
            self._write(log)
        return log

    def _fired(self, entry: dict, name: str, fire_one: FireOne) -> dict:
        """A trigger that raised may or may not have started its routine: `fire_unknown`, never fired again."""
        try:
            result = fire_one(name)
        except Exception as failure:  # noqa: BLE001 - whatever went wrong, the fire's outcome is unknown, not "not fired"
            return entry | {"state": FIRE_UNKNOWN, "fired": None, "reason": f"{type(failure).__name__}: {failure}"}
        return self._result(entry, result)

    def _planned(self, entry: dict) -> dict:
        base = {k: v for k, v in entry.items() if k != "fire"}
        if entry.get("fire"):
            return base | {"state": FIRING, "fired": None, "fired_at": self.clock().isoformat()}
        return base | {"state": NOT_FIRED, "fired": False}

    @staticmethod
    def _result(entry: dict, result: dict) -> dict:
        fired = bool(result.get("fired"))
        return entry | result | {"state": FIRED if fired else NOT_FIRED, "fired": fired}

    def _settle_leftovers(self, log: dict[str, dict]) -> dict[str, dict]:
        leftovers = [name for name, entry in log.items() if entry["state"] == FIRING]
        for name in leftovers:
            log[name] = log[name] | {"state": FIRE_UNKNOWN, "fired": None, "reason": UNKNOWN_REASON}
        if leftovers:
            self._write(log)
        return log

    def _write(self, log: dict[str, dict]) -> None:
        self.file.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.file.with_name(f".{self.file.name}.tmp")
        temporary.write_text(json.dumps(log, sort_keys=True, indent=1) + "\n", encoding="utf-8")
        temporary.replace(self.file)
