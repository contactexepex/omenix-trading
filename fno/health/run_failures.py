"""A capture workflow's run that did not succeed, read from GitHub's Actions API (story O10). `RunSource` is the
interface; `GitHubRuns` reads `GET /repos/{repository}/actions/runs/{id}` and its jobs with the run's own token.

The error names the run's conclusion (`failure`, `cancelled`, `timed_out`) and the first step that did not succeed in
the first job that did not succeed. Only names and conclusions are read, never a log, so nothing secret is copied."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import datetime

import requests

from ..models import IST
from .capture_errors import CaptureError

RUN_URL = "https://api.github.com/repos/{repository}/actions/runs/{run_id}"
API_HEADERS = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
TIMEOUT_SECONDS = 30
NOT_FAILED = ("success", "skipped", "neutral")
FAILURE = "failure"  # the only conclusion after which a job's own alert step can have run
ALERT_STEP_PREFIXES = ("Alert", "One line to")  # every workflow's alert step (YAML drops the text after " #")
RAN = ("success", "failure")
# Workflows where a newer run takes over from a cancelled pending one (A19's poller: its kick dispatches the next run;
# O9b's data-checks: each run checks the current committed state); such a run cancelled before any step ran was
# replaced, not lost. Any other workflow's cancelled slot is lost. data-checks stays here only while it records
# nothing per push or per day that a cancelled run would have had to write (O10 builder's condition, 23 Oct 2026).
REPLACEABLE = ("news-capture", "data-checks")
BEFORE_ANY_STEP = "before any step"
ALERT = "Omenix F&O {job}: the GitHub Actions run was {kind} at '{step}' and posted nothing itself; see {url}"


class RunSourceError(RuntimeError):
    """GitHub's run or jobs could not be read; the message says why (never a credential)."""


class RunSource(ABC):
    @abstractmethod
    def run(self, run_id: int) -> tuple[dict, list[dict]]:
        """The run's JSON and its jobs' JSON (latest attempt)."""


class GitHubRuns(RunSource):
    def __init__(self, repository: str, token: str, get: Callable | None = None):
        self._repository, self._token, self._get = repository, token, get or requests.get

    def run(self, run_id: int) -> tuple[dict, list[dict]]:
        url = RUN_URL.format(repository=self._repository, run_id=run_id)
        return self._json(url), self._json(f"{url}/jobs", {"per_page": 100}).get("jobs", [])

    def _json(self, url: str, params: dict | None = None) -> dict:
        headers = {**API_HEADERS, "Authorization": f"Bearer {self._token}"}
        try:
            response = self._get(url, params=params, headers=headers, timeout=TIMEOUT_SECONDS)
        except requests.RequestException as error:
            raise RunSourceError(f"GitHub's Actions API not reached ({type(error).__name__})") from None
        if not response.ok:
            raise RunSourceError(f"HTTP {response.status_code} from GitHub's Actions API")
        return response.json()


def capture_error(run: dict, jobs: list[dict]) -> CaptureError | None:
    """The run's error row, or None when the run succeeded (or was skipped)."""
    kind = run.get("conclusion") or "unfinished"
    if kind in NOT_FAILED or _replaced(run, kind, jobs):
        return None
    step, conclusion = _first_bad_step(jobs)
    started = datetime.fromisoformat(run["run_started_at"].replace("Z", "+00:00")).astimezone(IST)
    return CaptureError(started.date(), run["name"], step, kind, f"{step}: {conclusion}", run_url(run))


def run_url(run: dict) -> str:
    """The run's link, naming the attempt after the first, so a re-run attempt gets its own row and line."""
    attempt = run.get("run_attempt") or 1
    return run["html_url"] if attempt == 1 else f"{run['html_url']}/attempts/{attempt}"


def _replaced(run: dict, kind: str, jobs: list[dict]) -> bool:
    started = any(s.get("conclusion") in RAN for job in jobs for s in job.get("steps") or [])
    return run.get("name") in REPLACEABLE and kind == "cancelled" and not started


def needs_alert(error: CaptureError, jobs: list[dict]) -> bool:
    """True unless the run failed and every failed job ran its own alert step (judge 350 SF1: a failed job with no
    alert step, such as forecast-capture's gate, posted nothing). Cancelled, timed-out, startup failures and the rest
    never ran a `failure()` step."""
    failed = [job for job in jobs if job.get("conclusion") == FAILURE]
    return error.kind != FAILURE or not failed or not all(_ran_alert(job) for job in failed)


def _ran_alert(job: dict) -> bool:
    steps = job.get("steps") or []
    return any(s.get("conclusion") in RAN and str(s.get("name", "")).startswith(ALERT_STEP_PREFIXES) for s in steps)


def alert_text(error: CaptureError) -> str:
    return ALERT.format(job=error.job, kind=error.kind, step=error.step, url=error.run_url)


def _first_bad_step(jobs: list[dict]) -> tuple[str, str]:
    for job in jobs:
        if job.get("conclusion") in NOT_FAILED:
            continue
        for step in job.get("steps") or []:
            if step.get("conclusion") not in (*NOT_FAILED, None):
                return f"{job['name']} / {step['name']}", step["conclusion"]
        return f"{job['name']} / {BEFORE_ANY_STEP}", job.get("conclusion") or "unfinished"
    return BEFORE_ANY_STEP, "no job ran"
