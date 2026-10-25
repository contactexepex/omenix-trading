"""Commands of story G8 (protocol v4 scoring):

python -m fno forecast-v4-scores report [--as-of YYYY-MM-DD]    # write research/forecasts/v4_scores/<as-of>.{md,json}
python -m fno forecast-v4-scores look --look stop_rule_review   # the family decision and Test A (recorded once)

Before `research/forecasts/FREEZE_v4.md` exists every output starts with the EXPLORATORY line and `look` writes nothing.
After it, the report's first lines say whether the freeze holds (and which recorded files changed since), and a look
records nothing unless the freeze holds (story G6 freeze, criteria 4 and 12).
"""

from __future__ import annotations

import json
from datetime import date

from ...forecast_v4.terms import LOOK_ERROR_RATE


def add_forecast_v4_scores_parser(subparsers) -> None:
    parser = subparsers.add_parser(
        "forecast-v4-scores", help="protocol v4 scores, comparisons and the two looks (story G8)"
    )
    actions = parser.add_subparsers(dest="v4_cmd", required=True)
    report = actions.add_parser("report", help="score every v4 forecast and write the descriptive report")
    report.add_argument("--as-of", type=date.fromisoformat, help="YYYY-MM-DD (default: today in IST)")
    look = actions.add_parser("look", help="run a confirmatory look (minutes: thresholds are computed at the look)")
    look.add_argument("--look", choices=sorted(LOOK_ERROR_RATE), required=True)
    parser.set_defaults(func=cmd_forecast_v4)


def cmd_forecast_v4(args) -> int:
    from .outcomes import VixCloseMissing

    try:
        return _run(args)
    except VixCloseMissing as fault:  # one named line, never a traceback (orchestrator, 16 Oct 2026)
        print(fault)
        return 1


def _run(args) -> int:
    from ...models import now_ist
    from .wiring import (
        build_ai_slot_days,
        build_day_counts,
        build_diagnostic_lines,
        build_freeze_check,
        build_look_records,
        build_scoring,
        build_thresholds,
        build_unchecked_days,
    )

    scoring, records = build_scoring(), build_look_records()
    if args.v4_cmd == "report":
        as_of = args.as_of or now_ist().date()
        days, diagnostics = build_day_counts(as_of), build_diagnostic_lines()
        return _report(scoring, records, as_of.isoformat(), days, diagnostics, freeze=build_freeze_check())
    return _look(scoring, records, build_thresholds(), build_ai_slot_days(), args.look, now_ist(), build_unchecked_days,
                 freeze=build_freeze_check)  # fmt: skip


def _report(scoring, records, as_of: str, days, diagnostics=(), *, freeze) -> int:
    from .render import report_json, report_lines
    from .scoring import QUESTIONS

    reports = [scoring.question_report(q) for q in QUESTIONS]
    frozen = records.frozen()
    lines = (freeze.lines() if frozen else []) + report_lines(reports, frozen, as_of, days, diagnostics)
    records.folder.mkdir(parents=True, exist_ok=True)
    (records.folder / f"{as_of}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    payload = report_json(reports, frozen, as_of, days, diagnostics) | ({"freeze": freeze.lines()} if frozen else {})
    (records.folder / f"{as_of}.json").write_text(json.dumps(payload, indent=1, default=str) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0


def _look(scoring, records, thresholds, slot_days, look: str, decided_at, unchecked=list, *, freeze) -> int:
    """A recorded look runs only when the freeze holds (`freeze()`: a `FreezeCheck`; story G6 freeze, criterion 4),
    every scheduled AI slot-day up to its day is settled (`slot_days`) and every live row up to it has its 15:10
    deadline verdict (`unchecked()`: the days without one; G10 completion, criterion 8)."""
    from dataclasses import asdict

    from .deadlines import require_checked
    from .look import run_look
    from .reconcile import LookBlocked, require_reconciled
    from .records import EXPLORATORY

    counted_after = records.frozen_on() if records.frozen() else None
    if counted_after is not None:
        found = freeze()
        if not found.holds():
            print("\n".join([f"look NOT run, nothing recorded: {found.lines()[0]}", *found.lines()[1:]]))
            return 1
        print("\n".join(found.lines()))
        try:
            require_reconciled(slot_days.unsettled(counted_after, decided_at.date()), decided_at.date())
            require_checked(unchecked(), counted_after, decided_at.date())
        except LookBlocked as refusal:
            print(f"look NOT run, nothing recorded: {refusal}")
            return 1
    result = run_look(look, decided_at, scoring.member_comparisons(counted_after), thresholds, records.closed(look))
    if counted_after is None:
        print("\n".join([EXPLORATORY, *result.lines()]))
        return 0
    payload = {"lines": result.lines(), "test_a": result.test_a, "regimes": [list(k) + [v] for k, v in
               result.regimes.items()], "misses": [list(k) + [v] for k, v in result.misses.items()],
               "members": [asdict(m) for m in result.decision.members], "freeze": found.lines()}  # fmt: skip
    print("\n".join([*result.lines(), f"recorded: {records.write(look, payload)}"]))
    return 0
