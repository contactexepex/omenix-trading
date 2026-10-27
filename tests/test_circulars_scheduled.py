"""The circulars cron runs again (owner, 27 Oct 2026) after its receipts were rebuilt from Drive. This pins the
schedule, so a silent loss of the cron (which would stop the 14-day NSE window being captured) fails here first."""

from __future__ import annotations

from pathlib import Path

import yaml

WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "circulars.yml"
CRON = "30 2-16 * * *"  # hourly, 08:00-22:00 IST


def test_circulars_is_scheduled_hourly_through_the_ist_day_and_can_still_be_dispatched_by_hand():
    flow = yaml.safe_load(WORKFLOW.read_text())
    triggers = flow.get("on", flow.get(True))
    assert triggers["schedule"] == [{"cron": CRON}] and "workflow_dispatch" in triggers
