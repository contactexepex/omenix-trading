"""The circulars cron is paused (owner, 27 Oct 2026) until the receipts of `data/circulars/list` are rebuilt from Drive. This
pins the state, so a paused workflow is never mistaken for a scheduled one and a re-enable is a deliberate change: whoever
restores the schedule updates this test in the same commit (see the comment in the workflow)."""

from __future__ import annotations

from pathlib import Path

import yaml

WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "circulars.yml"


def test_circulars_has_no_schedule_and_can_still_be_dispatched_by_hand():
    flow = yaml.safe_load(WORKFLOW.read_text())
    triggers = flow.get("on", flow.get(True))
    assert list(triggers) == ["workflow_dispatch"]


def test_the_paused_workflow_says_why_and_how_to_re_enable_it():
    text = WORKFLOW.read_text()
    assert "PAUSED on 27 Oct 2026" in text and "#     - cron:" in text and "restoring the schedule block" in text
