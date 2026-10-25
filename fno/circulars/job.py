"""One run of A20b's job: read the circulars already listed (verified Drive cache), capture the feeds, commit the
receipts and the open-problem keys. An hourly job alerts once per episode: a new problem posts one line naming every
new problem, a known one posts nothing (the step still counts as having spoken), a cleared one posts one "recovered"
line. Any open problem makes the run exit 1, so O10's watcher records every failed run."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import date

from ..alerts.sender import SENT, AlertSender
from ..storage.manifest_commit import ManifestRecorder
from .capture import CircularCapture
from .episodes import OpenProblems
from .model import Problem

NOT_COMMITTED_MARK = " NOT committed"
SEEN_FAILED = "earlier circulars NOT read, nothing captured (a capture now would list them again): {error}"
ALERT = "Omenix F&O circulars {day}: NOT complete: {problems}. Run log: {where}"
ALREADY = "already alerted, still open: {keys}"
RECOVERED = "Omenix F&O circulars {day}: recovered: {keys}"
ABANDONED_SUFFIX = ":abandoned"


class CircularsJob:
    def __init__(self, seen: Callable[[], Sequence[dict]], capture: CircularCapture,
                 committers: Sequence[ManifestRecorder], state: OpenProblems, alerts: AlertSender,
                 spoken: Callable[[], None], where: str, out=print):  # fmt: skip
        self.seen, self.capture, self.committers, self.state = seen, capture, committers, state
        self.alerts, self.spoken, self.where, self.out = alerts, spoken, where, out

    def run(self, day: date) -> int:
        """0 when nothing is wrong; 1 while any problem is open (alerted once per episode)."""
        problems, before = self._problems(day), self.state.read()
        open_now = {p.key for p in problems if p.episode}
        settled = {p.key.removesuffix(ABANDONED_SUFFIX) for p in problems if not p.episode}  # not "recovered"
        cleared = sorted(before - open_now - settled)
        new = [p for p in problems if not p.episode or p.key not in before]
        for problem in problems:
            self.out(problem.text)
        sent = self._send(day, new, cleared)
        # Only a delivered line changes the state: an undelivered alert or recovery is tried again by the next run.
        still_alerted = before & open_now
        if sent:
            self.state.write(still_alerted | {p.key for p in new if p.episode})
        else:
            self.state.write(still_alerted | (before & set(cleared)))
        if problems and not new and sent:
            self.out(ALREADY.format(keys=", ".join(sorted(open_now))))
            self.spoken()  # known problems: the workflow's own failure line must stay quiet too
        unsaved = [line for line in self._commit(day) if NOT_COMMITTED_MARK in line]
        if unsaved:
            self.out(self.alerts.send(ALERT.format(day=day, problems="; ".join(unsaved), where=self.where)))
        return 1 if problems or unsaved else 0

    def _send(self, day: date, new: list[Problem], cleared: list[str]) -> bool:
        """One post for the run's new problems and recoveries; True when there was nothing to post or Slack took it."""
        lines = [ALERT.format(day=day, problems="; ".join(p.text for p in new), where=self.where)] if new else []
        lines += [RECOVERED.format(day=day, keys=", ".join(cleared))] if cleared else []
        if not lines:
            return True
        outcome = self.alerts.send("\n".join(lines))
        self.out(outcome)
        return outcome == SENT

    def _problems(self, day: date) -> list[Problem]:
        try:
            rows = self.seen()
        except (OSError, RuntimeError, ValueError) as exc:  # Drive (requests errors are OSError), a damaged part
            return [Problem("earlier-parts", SEEN_FAILED.format(error=exc))]
        return self.capture.run(day, rows)

    def _commit(self, day: date) -> list[str]:
        lines = [committer.commit(f"circulars {day}") for committer in self.committers]
        for line in lines:
            self.out(line)
        return lines
