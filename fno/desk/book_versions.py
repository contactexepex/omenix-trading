"""Book 1's D6 version kept current (story E3, judge 80 follow-up a). Book 1's served playbook is the digest of the
versions it may trade on the day (`playbook_digest`), so any approval, pause or retirement changes it; D6 would then
mark every later Book 1 decision `unscored`. Before each day's decisions the daily run compares that digest with the
active D6 version and, when only the playbook changed, registers and commits a new version starting that day, before
any decision of the day is committed (D6 counts a version only if committed strictly before the decision).

Only the playbook component is renewed this way: its change is itself a committed registry row (an owner's status
change or the hard-loss rule). Any other component that differs (the config, say) is left for the owner to register:
the day's decisions stay unscored until then, and the line says so. No version at all is never created here: the owner
registers Book 1's first version (D6)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date

from ..books.version_registry import VersionError, VersionRegistry, VersionRow
from ..books.versions import GitHistory, Versions
from ..constants import BOOK1_RULES
from ..playbook.decision_run import playbook_digest
from ..playbook.loader import PlaybookLoader
from .daily_ports import Committer, VersionKeeper

PLAYBOOK = "playbook"
NONE_YET = "Book 1 has no registered version: the owner registers the first one (D6); its decisions stay unscored"
UNCHANGED = "Book 1 version {version} unchanged (served playbook {digest})"
REGISTERED = "Book 1 version {version} registered from {day}: served playbook {old} -> {new}"
REFUSED = "Book 1 version NOT renewed ({problem}): the owner registers it; decisions stay unscored until then"
REASON = "playbook status change: the versions Book 1 may trade on {day} changed (registered by the daily run, E3)"


class Book1Versions(VersionKeeper):
    def __init__(self, loader: PlaybookLoader, registry: VersionRegistry, history: GitHistory,
                 head: Callable[[], str], committer: Committer):  # fmt: skip
        self.loader, self.registry, self.history, self.head, self.committer = (
            loader, registry, history, head, committer)  # fmt: skip

    def keep(self, day: date) -> str:
        digest = playbook_digest(self.loader.load(), day)
        active = Versions(self.registry.rows(), self.history).active_version(BOOK1_RULES, day)
        if active is None:
            return NONE_YET
        if active.components.get(PLAYBOOK) == digest:
            return UNCHANGED.format(version=active.version_id, digest=digest[:12])
        version = f"{active.version_id.split('+')[0]}+{day:%Y%m%d}"
        components = {**active.components, PLAYBOOK: digest}
        try:  # D6 refuses e.g. a second version starting the same day (two status changes in one day)
            self.registry.append(VersionRow(BOOK1_RULES, version, day, self.head(), components, REASON.format(day=day)))
        except VersionError as problem:
            return REFUSED.format(problem=problem)
        self.committer.commit((self.registry.path,), f"D6: register {BOOK1_RULES} {version} (served playbook changed)")
        old = active.components.get(PLAYBOOK, "none")[:12]
        return REGISTERED.format(version=version, day=day, old=old, new=digest[:12])
