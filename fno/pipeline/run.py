"""One pipeline run after a download step (story O6): find the batches, fire the routine for the new ones, save the
run summary in Drive and post one line to #fno-desk, plus one line per failure. Nothing fails silently: a failed
download, fire or Drive write makes the exit code 1, and every line printed is also what was posted."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from ..alerts.sender import AlertSender
from .batches import BatchFinder
from .dispatcher import BatchDispatcher
from .run_summary import RunSummary, RunSummaryStore

FAILURE_LINE = "Omenix F&O {job}: {dataset} {batch}: {outcome}: {detail}"
DRIVE_REFUSED = "Omenix F&O {job}: Drive refused the pipeline ({error}); nothing more fired, summary not saved{fix}"
SIGN_IN_FIX = ". If it names a sign-in: run tools/gdrive_oauth_setup.py and update the refresh-token secret"
DOWNLOAD_OK = "success"


class PipelineRun:
    def __init__(
        self,
        job: str,
        finder: BatchFinder,
        dispatcher: BatchDispatcher,
        summaries: RunSummaryStore,
        alerts: AlertSender,
        clock: Callable[[], datetime],
        log: Callable[[str], None] = print,
    ):
        self.job, self.finder, self.dispatcher, self.summaries = job, finder, dispatcher, summaries
        self.alerts, self.clock, self.log = alerts, clock, log

    def run(self, run_id: str, download: str, notes: tuple[str, ...] = ()) -> int:
        started = self.clock()
        try:
            report = self.dispatcher.dispatch(self.finder.batches())
            summary = RunSummary(
                self.job, run_id, self.dispatcher.trigger.name, download, started, self.clock(), report, notes
            )
            self.log(f"run summary: {self.summaries.save(summary)}")
        except Exception as error:  # noqa: BLE001 - Drive or the manifests failing must alert, never only crash
            self._post(DRIVE_REFUSED.format(job=self.job, error=f"{type(error).__name__}: {error}", fix=SIGN_IN_FIX))
            return 1
        self._post(summary.line())
        for failure in report.failures:
            p = failure.pointer
            self._post(
                FAILURE_LINE.format(
                    job=self.job, dataset=p.dataset, batch=p.batch, outcome=failure.outcome, detail=failure.detail
                )
            )
        return 0 if download == DOWNLOAD_OK and not report.failures else 1

    def _post(self, line: str) -> None:
        self.log(line)
        self.log(self.alerts.send(line))
