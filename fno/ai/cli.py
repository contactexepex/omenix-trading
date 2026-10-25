"""`python -m fno ai <action>`: the GitHub Actions side of the AI books' forecasts (stories F1 and G5). Research only.

- `fire`: after the day's v2 pack is committed, fires each AI book's routine once (one #fno-desk line per failure);
  `fire --protocol v4 --day <d>` fires them on the released v4 pack instead (G11, run by v4-fire.yml);
  `collect --protocol v4` judges the v4 day, then writes the rows of every settled day (G11);
- `reveals-ready`: exit 0 once every fired book's reveal is in the checkout (or nothing was fired); `--protocol v4`
  for the v4 fire's books (forecast-capture waits for both before its collect: an audit is written once);
- `collect`: after 15:15 IST, turns the books' sealed submissions into records and audit files (written once), then
  records every book run's own timing in BG1's usage ledger and alerts each run of the day not captured (F8c);
- `coverage`: per book, the pack days with a counted forecast (story G5 criterion 3);
- `audits-due`: records any new weekly draw (with its seed inputs), then lists the selected sessions not audited yet,
  for v2's runs and v4's apart (each protocol drawn from its own fire logs, G11 round 2c);
- `audit-record`: records one session's transcript audit (clean, or the breach kinds found), written once;
  `--protocol v4` for a v4 run;
- `register-v4-slots`: appends the AI books' 10 v4 slot registrations after the freeze (`--print`: only print them,
  for the freeze commit; G11 C13). Exit 1 when refused;
- `fire-probe`: fires Book 3's routine once with a harmless text the size of a v4 pointer, to prove the routine API
  takes it (run only by hand, by routine-fire-probe.yml; writes nothing). Exit 1 when not fired;
- `observe-remote`: reads the remote branch's head at each deadline into an observation file (story F1t's receipts).
The routine side is `python -m fno.ai` (standard library only).
"""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

from ..constants import AI_BOOKS, BOOK3_AI
from .run_terms import FORECAST_PROTOCOL_V2, FORECAST_PROTOCOL_V4
from .transcript_audit import BREACH_KINDS


def add_ai_parser(subparsers) -> None:
    ai = subparsers.add_parser("ai", help="the AI books' daily forecasts: fire, collect, coverage (F1, G5)")
    actions = ai.add_subparsers(dest="ai_cmd", required=True)
    for name, text in (("fire", "fire each AI book's routine once for the day"),
                       ("reveals-ready", "exit 0 once every fired book's reveal is in"),
                       ("collect", "record the AI books' forecasts for the day (after 15:15 IST)")):  # fmt: skip
        action = actions.add_parser(name, help=text)
        action.add_argument("--day", type=date.fromisoformat, help="YYYY-MM-DD (default: today in IST)")
        if name in ("fire", "collect", "reveals-ready"):
            protocols = (FORECAST_PROTOCOL_V2, FORECAST_PROTOCOL_V4)
            action.add_argument("--protocol", choices=protocols, default=FORECAST_PROTOCOL_V2,
                                help="v4: the books' run on the released v4 pack")  # fmt: skip
    actions.add_parser("coverage", help="pack days with a counted forecast, per AI book")
    actions.add_parser("audits-due", help="routine sessions selected for a transcript audit and not yet audited")
    register = actions.add_parser("register-v4-slots", help="the AI books' 10 v4 slot registrations, after the freeze")
    register.add_argument("--print", action="store_true", dest="print_only", help="print the rows, write nothing")
    actions.add_parser("fire-probe", help="fire Book 3's routine once with a harmless v4-sized text (writes nothing)")
    record = actions.add_parser("audit-record", help="record one routine session's transcript audit (written once)")
    record.add_argument("--day", type=date.fromisoformat, required=True, help="YYYY-MM-DD")
    record.add_argument("--book", required=True, choices=AI_BOOKS)
    record.add_argument("--breach", action="append", default=[], choices=BREACH_KINDS, help="a breach kind found")
    record.add_argument("--evidence", required=True, help="what was read and seen (tool calls, files), never a secret")
    record.add_argument("--auditor", required=True, help="who read the transcript")
    record.add_argument("--session", default="", help="the session, when the fire log has no link")
    protocols = (FORECAST_PROTOCOL_V2, FORECAST_PROTOCOL_V4)
    record.add_argument("--protocol", choices=protocols, default=FORECAST_PROTOCOL_V2, help="v4: a run of the v4 fire")
    observe = actions.add_parser("observe-remote", help="read the remote's head at each deadline (F1t receipts)")
    observe.add_argument("--out", type=Path, required=True, help="the observation file (git-ignored)")
    observe.add_argument("--deadline", type=datetime.fromisoformat, action="append", required=True)
    ai.set_defaults(func=cmd_ai)


def cmd_ai(args) -> int:
    from ..models import now_ist

    day = getattr(args, "day", None) or now_ist().date()
    if args.ai_cmd == "audit-record":
        return _audit_record(args)
    if args.ai_cmd == "observe-remote":
        return _observe_remote(args)
    if args.ai_cmd == "register-v4-slots":
        return _register_v4_slots(args)
    if args.ai_cmd == "fire-probe":
        return _fire_probe()
    if args.ai_cmd in ("fire", "collect") and args.protocol == FORECAST_PROTOCOL_V4:
        return _fire_v4(day) if args.ai_cmd == "fire" else _collect_v4(day)
    if args.ai_cmd == "reveals-ready":
        return _reveals_ready(day, args.protocol)
    commands = {"fire": _fire, "collect": _collect, "coverage": _coverage, "audits-due": _audits_due}
    return commands[args.ai_cmd](day)


def _fire_probe() -> int:
    from .fire_probe import fire_probe
    from .wiring import build_book_trigger

    fired, line = fire_probe(build_book_trigger(BOOK3_AI))
    print(line)
    return 0 if fired else 1


def _fire(day: date) -> int:
    from .wiring import build_ai_firer

    print("\n".join(build_ai_firer().fire(day)))
    return 0


def _fire_v4(day: date) -> int:
    from .wiring import build_v4_firer

    print("\n".join(build_v4_firer().fire(day)))
    return 0


def _collect_v4(day: date) -> int:
    """Judges the day, writes the rows of every settled day, counts those awaiting audit, then prints the runs' cost."""
    from .wiring import build_v4_collector, build_v4_cost_report, build_v4_settler

    collected = build_v4_collector().collect(day) + build_v4_settler().settle()
    print("\n".join(collected + build_v4_cost_report().lines()))
    return 0


def _reveals_ready(day: date, protocol: str) -> int:
    from ..config import ROOT
    from .run_terms import V2_TERMS, V4_TERMS

    terms = V4_TERMS if protocol == FORECAST_PROTOCOL_V4 else V2_TERMS
    log = ROOT / terms.fired_path(day)
    books = terms.fired_books(json.loads(log.read_text(encoding="utf-8"))) if log.is_file() else {}
    fired = [book for book, entry in books.items() if entry["fired"]]
    return 0 if all((ROOT / terms.reveal_path(day, book)).is_file() for book in fired) else 1


def _collect(day: date) -> int:
    from .wiring import build_ai_collector, record_book_usage

    print("\n".join(build_ai_collector().collect(day) + record_book_usage(day)))
    return 0


def _coverage(day: date) -> int:
    from ..config import ROOT
    from .coverage import coverage_lines

    print("\n".join(coverage_lines(ROOT)))
    return 0


def _audits_due(day: date) -> int:
    from ..composition import build_alert_sender
    from ..config import ROOT
    from .audit_plan import audits_due, record_draws
    from .run_terms import V2_TERMS, V4_TERMS
    from .wiring import build_audit_seeds

    seeds, refused = build_audit_seeds()
    for line in refused:  # a close the archive does not confirm: that week is not drawn, and the desk is told
        print(line, "|", build_alert_sender().send(line))
    for terms in (V2_TERMS, V4_TERMS):
        drawn = record_draws(ROOT, seeds, terms)
        due = audits_due(ROOT, seeds, terms)
        print(
            f"Omenix F&O AI transcript audits due ({terms.protocol}): {len(due)}"
            + (f"; new weekly draws: {', '.join(drawn)}" if drawn else "")
        )
        for session in due:
            print(f"  {session.day} {session.book} {session.entry.get('session', '(no link)')}")
    return 0


def _audit_record(args) -> int:
    from ..config import ROOT
    from ..models import now_ist
    from .run_terms import V2_TERMS, V4_TERMS
    from .transcript_audit import AuditRefused, TranscriptAudits, new_audit

    terms = V4_TERMS if args.protocol == FORECAST_PROTOCOL_V4 else V2_TERMS
    log = ROOT / terms.fired_path(args.day)
    books = terms.fired_books(json.loads(log.read_text(encoding="utf-8"))) if log.is_file() else {}
    try:
        audit = new_audit(args.day, args.book, books.get(args.book, {}), args.breach, args.evidence, args.auditor,
                          now_ist(), args.session)  # fmt: skip
        print(f"recorded {audit.result}: {TranscriptAudits(ROOT, terms).record(args.day, audit)}")
    except AuditRefused as refused:
        print(f"refused: {refused}")
        return 1
    return 0


def _register_v4_slots(args) -> int:
    from .wiring import build_slot_registrar

    lines = build_slot_registrar().register(write=not args.print_only)
    print("\n".join(lines))
    return 1 if any("refused" in line for line in lines) else 0


def _observe_remote(args) -> int:
    import time

    from ..config import ROOT
    from ..models import now_ist
    from .observed_receipts import ObservationFile
    from .remote_observer import GitLsRemote, RemoteObserver

    if any(deadline.tzinfo is None for deadline in args.deadline):
        print("refused: every deadline needs its time zone")
        return 1
    RemoteObserver(GitLsRemote(ROOT), ObservationFile(args.out), now_ist, time.sleep).run(args.deadline)
    print(f"observed the remote at {len(args.deadline)} deadline(s): {args.out}")
    return 0
