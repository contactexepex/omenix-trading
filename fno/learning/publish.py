"""Posting the weekly post-mortem (story LR1), once, to #fno-desk: the AI summary if it passes the exact number check
(else one line saying why it was dropped, plus one alert), the devil's advocate objections in their own labelled
section (or "advocate not run: <reason>"), then the code-built lines, which are posted in every case. The only module
that reads the AI's files, and only to post them: nothing the AI writes reaches a decision."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from ..advocate.numbers import NumberCheck
from ..advocate.port import Advocate, AdvocateResult, AdvocateSubject
from ..alerts.sender import AlertSender
from .report import PostMortemRecords, sha256_of
from .writer import FIRED_SUFFIX, LINE

PROSE_SUFFIX, POSTED_SUFFIX = "_prose.md", "_posted.json"
PROSE_WORDS = 150
SUMMARY_HEAD = "*Summary (AI-written from the lines below; every number checked against them)*"
OBJECTIONS_HEAD = "*Devil's advocate objections (AI; they change no number and decide no trade)*"
LINES_HEAD = "*The numbers (code-built, the source of truth)*"
NOT_FIRED = "routine not fired"
NO_PROSE = "no summary received"
DROPPED = "AI summary dropped: {reason}"


class Publisher:
    def __init__(self, records: PostMortemRecords, advocate: Advocate, alerts: AlertSender):
        self.records, self.advocate, self.alerts = records, advocate, alerts

    def publish(self, saturday: date) -> list[str]:
        lines_path = self.records.path(saturday)
        if not lines_path.is_file():
            return [LINE.format(saturday=saturday, result="no committed lines for the week; nothing posted")]
        if self.records.read_json(saturday, POSTED_SUFFIX) is not None:
            return [LINE.format(saturday=saturday, result="already posted (once per week)")]
        sha, lines_text = sha256_of(lines_path), lines_path.read_text(encoding="utf-8")
        summary, dropped, objections = self._parts(saturday, lines_path, lines_text, sha)
        message = [*summary, "", OBJECTIONS_HEAD, *objections.lines(), "", LINES_HEAD, lines_text]
        outcome = self.alerts.send("\n".join(message))
        out = [LINE.format(saturday=saturday, result=f"posted ({outcome})")]
        if dropped:
            out.append(self.alerts.send(LINE.format(saturday=saturday, result=DROPPED.format(reason=dropped))))
        self.records.write_json_once(saturday, POSTED_SUFFIX, {
            "lines_sha256": sha, "summary": dropped or ("posted" if summary[0] == SUMMARY_HEAD else summary[0]),
            "advocate": "ran" if objections.ran else objections.not_run, "slack": outcome,
        })  # fmt: skip
        return out

    def _parts(self, saturday: date, lines_path: Path, lines_text: str, sha: str):
        """(the summary block, the failed number-check rule or None, the objections)."""
        fired = self.records.read_json(saturday, FIRED_SUFFIX) or {"fired": False, "reason": NOT_FIRED}
        if not fired["fired"]:
            return [f"summary: {fired['reason']}"], None, AdvocateResult(not_run=fired["reason"])
        summary, dropped = self._summary(saturday, lines_text, sha)
        subject = AdvocateSubject(f"weekly post-mortem {saturday}", lines_path, sha)
        return summary, dropped, self.advocate.objections(subject)

    def _summary(self, saturday: date, lines_text: str, sha: str) -> tuple[list[str], str | None]:
        """(the summary block, the failed rule when the summary was dropped)."""
        path = self.records.path(saturday, PROSE_SUFFIX)
        if not path.is_file():
            return [f"summary: {NO_PROSE}"], None
        prose = path.read_text(encoding="utf-8")
        failure = NumberCheck(lines_text, sha, PROSE_WORDS).first_failure(prose)
        if failure:
            return [f"summary: {DROPPED.format(reason=failure)}"], failure
        return [SUMMARY_HEAD, *prose.splitlines()[1:]], None
