"""`python -m fno ai-trading <action>`: the transcript audit of the AI books' decision sessions (story F1t), by the
forecasts' rule and with their code: every session of the first 10 fired days, then 2 a week drawn with the verified
weekly seed; a breach makes that book-day unscored, and two in 20 decision days stop that book's decision fires.

- `audits-due`: records any new weekly draw of decision sessions, then lists the selected sessions not audited yet;
- `audit-record`: records one decision session's transcript audit (clean, or the breach kinds found), written once;
- `model-audit`: records whether the session's copied model fields equal its session tool's answer (criterion 3c).
"""

from __future__ import annotations

import json
from datetime import date

from ..ai.fire_once import FIRE_UNKNOWN
from ..ai.transcript_audit import BREACH_KINDS
from ..constants import AI_BOOKS
from .model_audit import RESULTS


def add_ai_trading_parser(subparsers) -> None:
    parser = subparsers.add_parser("ai-trading", help="the AI books' decision sessions: transcript audits (F1t)")
    actions = parser.add_subparsers(dest="ai_trading_cmd", required=True)
    actions.add_parser("audits-due", help="decision sessions selected for a transcript audit and not yet audited")
    record = actions.add_parser("audit-record", help="record one decision session's transcript audit (written once)")
    record.add_argument("--day", type=date.fromisoformat, required=True, help="YYYY-MM-DD")
    record.add_argument("--book", required=True, choices=AI_BOOKS)
    record.add_argument("--breach", action="append", default=[], choices=BREACH_KINDS, help="a breach kind found")
    record.add_argument("--evidence", required=True, help="what was read and seen (tool calls, files), never a secret")
    record.add_argument("--auditor", required=True, help="who read the transcript")
    record.add_argument("--session", default="", help="the session, when the fire log has no link")
    model = actions.add_parser("model-audit", help="record whether a decision's model fields match its transcript")
    model.add_argument("--day", type=date.fromisoformat, required=True, help="YYYY-MM-DD")
    model.add_argument("--book", required=True, choices=AI_BOOKS)
    model.add_argument("--result", required=True, choices=RESULTS)
    model.add_argument("--evidence", required=True, help="the tool call's fields as seen, never a secret")
    model.add_argument("--auditor", required=True, help="who read the transcript")
    parser.set_defaults(func=cmd_ai_trading)


def cmd_ai_trading(args) -> int:
    commands = {"audit-record": _audit_record, "model-audit": _model_audit}
    return commands[args.ai_trading_cmd](args) if args.ai_trading_cmd in commands else _audits_due()


def _model_audit(args) -> int:
    from ..config import ROOT
    from ..models import now_ist
    from .model_audit import ModelAuditRefused, ModelAudits
    from .paths import fired_path

    log = ROOT / fired_path(args.day)
    version = json.loads(log.read_text(encoding="utf-8")).get(args.book, {}).get("version", "") if log.is_file() else ""
    try:
        path = ModelAudits(ROOT).record(
            args.day, args.book, version, args.result, args.evidence, args.auditor, now_ist()
        )
    except ModelAuditRefused as refused:
        print(f"refused: {refused}")
        return 1
    print(f"recorded {args.result}: {path}")
    return 0


def _audits_due() -> int:
    from ..ai.audit_plan import audits_due, record_draws
    from ..ai.wiring import build_audit_seeds
    from ..composition import build_alert_sender
    from ..config import ROOT

    terms = _terms()
    seeds, refused = build_audit_seeds(ROOT, more=(terms,))
    for line in refused:  # a close the archive does not confirm: that week is not drawn, and the desk is told
        print(line, "|", build_alert_sender().send(line))
    drawn, due = record_draws(ROOT, seeds, terms), audits_due(ROOT, seeds, terms)
    print(
        f"Omenix F&O AI decision transcript audits due: {len(due)}"
        + (f"; new weekly draws: {', '.join(drawn)}" if drawn else "")
    )
    for session in due:
        print(f"  {session.day} {session.book} {session.entry.get('session', '(no link)')}")
    return 0


def _terms():
    """The decision run's terms (its folder decides every path read here), from the same config the run reads."""
    from ..config import load_app_config
    from ..desk.timetable import timetable_from_config
    from .terms import decision_terms
    from .timing import decision_timing_from_config

    cfg = load_app_config()
    return decision_terms(decision_timing_from_config(cfg, timetable_from_config(cfg)))


def _audit_record(args) -> int:
    from ..ai.transcript_audit import AuditRefused, TranscriptAudits, new_audit
    from ..config import ROOT
    from ..models import now_ist
    from .paths import fired_path

    log = ROOT / fired_path(args.day)
    fired = json.loads(log.read_text(encoding="utf-8")).get(args.book, {}) if log.is_file() else {}
    if fired.get("state") == FIRE_UNKNOWN and args.session:  # it may have run: its transcript is auditable by link
        fired = fired | {"fired": True}
    try:
        audit = new_audit(args.day, args.book, fired, args.breach, args.evidence, args.auditor, now_ist(), args.session)
        print(f"recorded {audit.result}: {TranscriptAudits(ROOT, _terms()).record(args.day, audit)}")
    except AuditRefused as refused:
        print(f"refused: {refused}")
        return 1
    return 0
