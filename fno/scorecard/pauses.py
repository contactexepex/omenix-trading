"""Automatic pauses (story E6, criterion 1; design 12.8): the only switch-offs allowed before a review date.

- **Catastrophic loss:** a completed or unwound trade of an approved version, in any **book**, closed on or after the
  version's latest change to paper, whose C1 net loss reaches the plan's `catastrophic_loss_rs` (judge 73: a loss
  before an owner's re-approval, or in the version's earlier shadow test, never pauses it).
- **Cumulative loss (owner, 14 Oct 2026; protocol `catastrophic_loss_strategy`):** the version's realised C1 net over
  the same counting trades reaches minus `CUMULATIVE_CAPS` times its `catastrophic_loss_rs` (Rs 30,000 at Rs 10,000),
  so a run of losses each below the cap still pauses it. A shadow is alerted on a day one of its trades closes.
- **Live-feature drift (judge 67):** an approved version whose live feature no longer passes its use rule.

Either pauses that version at once (`paper -> paused`, approved by `hard_loss_rule`, through D1's status change, so no
book can trade it) and sends one #fno-desk line. A shadow version (status research) is only alerted: research cannot be
paused, and its result is evidence for the owner, who decides. Commit the registry and playbook file the change writes.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace
from datetime import date

from ..alerts.sender import AlertSender
from ..constants import APPROVER_HARD_LOSS_RULE, SHADOW_PREFIX, PlaybookStatus
from ..desk.trade_counts import version_key
from ..playbook.lifecycle import StatusChanger
from ..playbook.loader import Playbook
from ..playbook.measurement import is_measurement
from .measurement_alerts import cumulative_text, single_loss_text
from .strategy_record import StrategyRecord

ALERT = "F&O paper desk: {version} {action} ({reason})"
PAUSED_NOW, SHADOW_ONLY = "paused in every book", "shadow test, not paused: the owner decides"
CUMULATIVE_CAPS = 3  # the owner's rule: realised net at or below -3 x catastrophic_loss_rs


@dataclass(frozen=True)
class PauseTrigger:
    name: str
    version: int
    reason: str
    text: str = ""  # story R3: a measurement's own alert wording; empty for E6's ALERT

    @property
    def label(self) -> str:
        return f"{self.name}-v{self.version}"


def _counts(
    record: StrategyRecord, status: PlaybookStatus, approved_on: date | None, closed_on: date, on: date
) -> bool:
    """Whether a trade closed on `closed_on` in this record can trigger: an approved version only on its book trades
    since its latest approval; a research version (shadow) only on the day the trade closed (it is never paused, so an
    older loss would alert again on every run)."""
    shadow_account = record.account.startswith(SHADOW_PREFIX)
    if status == PlaybookStatus.PAPER:
        return not shadow_account and approved_on is not None and closed_on >= approved_on
    return status == PlaybookStatus.RESEARCH and closed_on == on


def catastrophic_losses(
    records: Iterable[StrategyRecord], playbook: Playbook, on: date, approved_on: Mapping[tuple[str, int], date]
) -> list[PauseTrigger]:
    """Every counting loss at or beyond its version's cap. `approved_on`: each version's latest change to paper."""
    triggers = []
    for record in records:
        name, version = version_key(record.strategy)
        found = [s for s in playbook.strategies if s.key == (name, version)]
        if not found:
            continue
        cap, status = found[0].evaluation_plan["catastrophic_loss_rs"], found[0].status
        losses = [t for t in record.closed if t.line.net <= -cap]
        measured = is_measurement(found[0]) and status == PlaybookStatus.RESEARCH
        for trade in losses:
            if _counts(record, status, approved_on.get((name, version)), trade.line.closed_on, on):
                reason = f"trade {trade.trade_id} in {record.account} lost Rs {-trade.line.net:,.2f}, cap Rs {cap:,.2f}"
                trigger = PauseTrigger(name, version, f"catastrophic loss: {reason}")
                # by close day, so two losses closing the same day both carry the escalation E6's one alert keeps
                count = sum(t.line.closed_on <= trade.line.closed_on for t in losses)
                triggers.append(
                    replace(trigger, text=single_loss_text(trigger.label, cap, reason, count) if measured else "")
                )
    return triggers


def cumulative_losses(
    records: Iterable[StrategyRecord], playbook: Playbook, on: date, approved_on: Mapping[tuple[str, int], date]
) -> list[PauseTrigger]:
    """Every version whose counting trades' realised net reaches -CUMULATIVE_CAPS x its cap: an approved version's book
    trades since its latest approval, in every book together; a shadow's own trades, when one closed on `on`."""
    totals: dict[tuple[str, int], float] = {}
    closed_today: set[tuple[str, int]] = set()
    caps = {s.key: (s.evaluation_plan["catastrophic_loss_rs"], s.status) for s in playbook.strategies}
    for record in records:
        key = version_key(record.strategy)
        if key not in caps:
            continue
        status, shadow = caps[key][1], record.account.startswith(SHADOW_PREFIX)
        since = approved_on.get(key)
        if status == PlaybookStatus.PAPER and not shadow and since is not None:
            lines = [t.line for t in record.closed if t.line.closed_on >= since]
        elif status == PlaybookStatus.RESEARCH and shadow:
            lines = [t.line for t in record.closed]
        else:
            continue
        totals[key] = totals.get(key, 0.0) + sum(line.net for line in lines)
        closed_today |= {key} if any(line.closed_on == on for line in lines) else set()
    measured = {s.key for s in playbook.strategies if is_measurement(s) and s.status == PlaybookStatus.RESEARCH}
    triggers = [
        PauseTrigger(
            *key, f"cumulative loss: realised Rs {-total:,.2f}, {CUMULATIVE_CAPS} x cap Rs {caps[key][0]:,.2f}"
        )
        for key, total in sorted(totals.items())
        if total <= -CUMULATIVE_CAPS * caps[key][0] and (caps[key][1] == PlaybookStatus.PAPER or key in closed_today)
    ]
    return [
        replace(t, text=cumulative_text(t.label, t.reason)) if (t.name, t.version) in measured else t for t in triggers
    ]


def drifts(playbook: Playbook) -> list[PauseTrigger]:
    return [PauseTrigger(*d.strategy.key, f"live feature drift: {d.reason}") for d in playbook.drifted]


class AutoPauser:
    def __init__(self, changer: StatusChanger, alerts: AlertSender):
        self.changer, self.alerts = changer, alerts

    def apply(self, triggers: Iterable[PauseTrigger], playbook: Playbook, on: date) -> list[str]:
        """Pause each approved version once, alert each shadow once; returns one line per action taken."""
        status = {s.key: s.status for s in playbook.strategies}
        lines, done = [], set()
        for trigger in triggers:
            key = (trigger.name, trigger.version)
            if key in done or status.get(key) not in (PlaybookStatus.PAPER, PlaybookStatus.RESEARCH):
                continue
            done.add(key)
            action = SHADOW_ONLY
            if status[key] == PlaybookStatus.PAPER:
                self.changer.change(trigger.name, trigger.version, PlaybookStatus.PAUSED, APPROVER_HARD_LOSS_RULE, on)
                action = PAUSED_NOW
            text = trigger.text or ALERT.format(version=trigger.label, action=action, reason=trigger.reason)
            lines.append(f"{text} [{self.alerts.send(text)}]")
        return lines
