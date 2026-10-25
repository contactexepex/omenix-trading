"""A routine's rehearsal (story REH1): `python -m fno daily run --rehearse --day D` and `python -m fno rehearse
<routine> --day D`. The rehearsal's own checkout is made, the replay clock starts at the routine's time on the day,
the guard checks every outside service, the routine's own commands run in the checkout as children with the mode set,
its receipts are committed as its session commits them, and at the end its branch is the one push to GitHub."""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Callable
from datetime import date, datetime
from functools import partial
from pathlib import Path

from ..constants import ENV_FNO_REHEARSAL
from ..models import IST
from .checkout import RehearsalCheckout, RehearsalCheckoutError, run_git
from .clock import ReplayClock
from .exercised_line import not_live_result, report_exercised
from .git_dates import install_git_shim
from .mode import Rehearsal, in_this_process
from .routines import ROUTINES, Command, Routine

HOME = Path("~/.fno/rehearsals").expanduser()
STARTED = "rehearsal {routine} {day} {run_id}: data as of {at}, checkout {checkout}"
NOT_A_SESSION = "rehearsal refused: {day} is not a session day (NSE's calendar)"
GUARD_STOPPED = "rehearsal STOPPED before any step: {problem}"
ENDED = "rehearsal {routine} {day} {run_id} ended: {line}; branch {ref}; Drive dryrun/{run_id}/"
RECEIPTS_MESSAGE = "Rehearsal {routine} {day}: the routine's receipts"
CONFIG_FILE = "config.yaml"
REPLAY_CLOCK = "replay clock not checked (by design)"  # REH1l: said once per rehearsal, never a capture's problem
NO_EXERCISED = "run_routine: commands set apart (not live, or not yet in their routine) need an `exercised` record"
EXERCISED_UNREAD = "rehearsal: the exercised steps could not be read from the run's full log: {problem}"


def rehearse_daily(day: date, source: Path, out: Callable[[str], None] = print, home: Path = HOME, **seams) -> int:
    return rehearse(ROUTINES["daily"], day, source, out, home, **seams)


def rehearse(routine: Routine, day: date, source: Path, out: Callable[[str], None] = print, home: Path = HOME,
             is_session: Callable[[date], bool] | None = None, run_child=None, guard=None,
             alerts=None) -> int:  # fmt: skip
    if not (is_session or _is_session)(day):
        out(NOT_A_SESSION.format(day=day))
        return 1
    mode = Rehearsal.new(day, home, source)
    with in_this_process(mode):  # REH1e: the checkout's own commit and its hook are labelled too
        return _rehearse(routine, day, source, out, home, mode, run_child, guard, alerts)


def _rehearse(routine: Routine, day: date, source: Path, out: Callable[[str], None], home: Path, mode: Rehearsal,
              run_child, guard, alerts) -> int:  # fmt: skip
    start = datetime.combine(day, routine.start, IST)
    checkout = RehearsalCheckout(source, mode, home)
    ReplayClock(mode.state).start(start)  # first: the origin's push log reads it from the first push on
    try:
        checkout.create(start)
    except RehearsalCheckoutError as failed:
        out(str(failed))
        return 1
    fields = {"routine": routine.name, "day": day, "run_id": mode.run_id}
    out(STARTED.format(**fields, at=start.isoformat(), checkout=checkout.clone))
    path = install_git_shim(checkout.root / "bin", mode.state)  # every commit dated by the replay clock
    env = {**os.environ, ENV_FNO_REHEARSAL: mode.to_env(), "PATH": path}
    for problem in (guard or _guard)(env, checkout.clone):
        out(GUARD_STOPPED.format(problem=problem))
        return 1
    exercised: dict[str, dict] = {}  # REH1k: the routine's commands not live in real runs on the day
    run = run_child or partial(run_routine, not_live=_not_live_editions(day, checkout.clone), exercised=exercised)
    code, line = run(checkout.clone, routine, day, env, out)
    try:  # REH1j: after the day's last line; never in the way of the receipts and the publish
        report_exercised(checkout.clone, day, out, alerts or _alerts(out), exercised, (REPLAY_CLOCK,))
    except (OSError, ValueError, KeyError) as unreadable:
        out(EXERCISED_UNREAD.format(problem=f"{type(unreadable).__name__}: {unreadable}"))
    if routine.receipts:
        commit_receipts(checkout.clone, routine.receipts, RECEIPTS_MESSAGE.format(routine=routine.name, day=day), env)
    ref = checkout.publish(run_git(source, "remote", "get-url", "origin").strip())
    out(ENDED.format(**fields, line=line, ref=ref))
    return code


def _alerts(out: Callable[[str], None]):
    """#fno-desk, labelled by the mode this process carries; a post Slack did not take prints "alert NOT sent"."""
    from ..composition import build_alert_sender
    from ..daily.alerts import ReportedAlerts

    return ReportedAlerts(build_alert_sender(), out)


def _is_session(day: date) -> bool:
    from ..storage.trading_days import is_trading_day
    from ..storage.wiring import build_session_calendar

    return is_trading_day(build_session_calendar(), day)


GUARD_COMMAND = (sys.executable, "-m", "fno", "rehearse", "check")
GUARD_CRASHED = "the guard did not finish cleanly (exit {code}): {last}"


def _guard(env: dict, cwd: Path, command: tuple[str, ...] = GUARD_COMMAND) -> list[str]:
    """`rehearse check` in a child started as every step is (`python -m fno`, the mode set, in the checkout): its own
    clock and HTTP guard, and every builder's rehearsal form. Only a clean exit with nothing printed is safe: a guard
    that crashes or exits non-zero stops the rehearsal, whatever it printed (judge 560 F3)."""
    done = subprocess.run(list(command), cwd=cwd, env=env, capture_output=True, text=True, check=False)
    found = [line for line in done.stdout.splitlines() if line]
    if done.returncode != 0:
        last = (done.stderr or "").strip().splitlines()[-1:] or ["no error output"]
        found.append(GUARD_CRASHED.format(code=done.returncode, last=last[0]))
    return found


def run_routine(checkout: Path, routine: Routine, day: date, env: dict, out: Callable[[str], None],
                not_live: frozenset[str] = frozenset(), exercised: dict | None = None) -> tuple[int, str]:  # fmt: skip
    """The routine's own commands in the rehearsal's checkout, each relayed line by line: the background ones first,
    then the rest in order, then the background ones waited for. One command's failure never stops the next, as in
    the routine; the last line is the daily run's own, or which commands failed. A command whose live key is in
    `not_live`, or that was not yet in its routine on `day` (REH1r), runs as on the day, but its outcome goes into
    `exercised` (REH1j's shape), never into "failed"."""

    def start(command: Command) -> subprocess.Popen:
        return subprocess.Popen([sys.executable, "-m", "fno", *command.for_day(day)], cwd=checkout, env=env,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)  # fmt: skip

    apart = {c for c in routine.commands if c.exercised_on(day, not_live)}
    if apart and exercised is None:
        raise ValueError(NO_EXERCISED)  # a set-apart command's outcome must be reported somewhere, never dropped
    background = [(c, start(c)) for c in routine.commands if c.background]
    results = [(c, _relayed(start(c), out)) for c in routine.commands if not c.background]
    results += [(c, _relayed(child, out)) for c, child in background]
    for c, (code, last) in results:
        if c in apart:
            since = None if c.live_key in not_live else c.since
            exercised[" ".join(c.args)] = {"result": not_live_result(code, last, since)}
    failed = [" ".join(c.args) for c, (code, _) in results if code != 0 and c not in apart]
    if len(results) == 1 and results[0][0] not in apart:  # the daily run: its own last line
        return results[0][1]
    return (1 if failed else 0), (f"failed: {', '.join(failed)}" if failed else f"{len(results)} commands done")


def _not_live_editions(day: date, checkout: Path) -> frozenset[str]:
    """The lab editions not live in real runs on the replayed day, by the checkout's own `config.yaml` (the one the
    routine's children read)."""
    from ..config import load_app_config
    from ..forecast_lab.wiring import live_from

    live = live_from(load_app_config(Path(checkout) / CONFIG_FILE))
    return frozenset(e for e, real in live.items() if real is None or day < real)


def _relayed(child: subprocess.Popen, out: Callable[[str], None]) -> tuple[int, str]:
    last = ""
    for line in child.stdout:
        out(line.rstrip("\n"))
        last = line.strip() or last
    return child.wait(), last


def commit_receipts(checkout: Path, pathspecs: tuple[str, ...], message: str, env: dict) -> None:
    """The routine's own `git add` paths, committed and pushed to the rehearsal's origin as its session does: through
    the rehearsal's git (dated by the replay clock), with the record scan's hook (never --no-verify)."""
    present = [p for p in pathspecs if (checkout / p).exists()]
    if not present:
        return
    git = lambda *args: subprocess.run(["git", *args], cwd=checkout, env=env, check=True, capture_output=True)  # noqa: E731
    git("add", "--", *present)
    if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=checkout, env=env, check=False).returncode:
        git("commit", "-q", "-m", message)
        git("push", "-q", "origin", "HEAD:main")
