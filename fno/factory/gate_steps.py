"""G1-G3 run by code (story R1b), under the shared gate order (`gate_order.py`). Changing a card's inputs after its
numbers are seen makes a new idea (FACTORY_RULES section 2), so no gate re-runs."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date

from .card import IdeaCard
from .constants import Gate, Outcome
from .cost_wall import Screen, screen
from .data_spend import SpendVerdict, data_spend, parse_register
from .gate_log import figures
from .gate_numbers import plan_numbers, screen_numbers, spend_numbers
from .gate_order import GateOrder
from .inputs import plan_inputs, screen_inputs, spend_inputs
from .sample_plan import SamplePlan, sample_plan


class GateSteps:
    def __init__(self, order: GateOrder, charges: dict, register_text: Callable[[], str]):
        self.order, self.charges, self.register_text = order, charges, register_text

    def screen(self, card: IdeaCard, today: date) -> Screen:
        self.order.ready(card, Gate.IDEA_CARD, (Outcome.IDEA,))
        result = screen(screen_inputs(card, self.charges))
        self.order.log(card, Gate.SCREEN, result.outcome, today, screen_numbers(result))
        return result

    def spend(self, card: IdeaCard, today: date) -> SpendVerdict:
        self.order.ready(card, Gate.SCREEN, (Outcome.PASSED,))
        data_sets, _ = spend_inputs(card)
        verdict = data_spend(parse_register(self.register_text()), data_sets, card.trial_id, card.path)
        self.order.log(card, Gate.DATA_SPEND, verdict.outcome, today, spend_numbers(verdict))
        return verdict

    def plan(self, card: IdeaCard, today: date) -> SamplePlan:
        self.order.ready(card, Gate.DATA_SPEND, (Outcome.FRESH, Outcome.EXPLORATORY))
        inputs = plan_inputs(card)
        net = float(figures(self.order.row(card.trial_id, Gate.SCREEN))["net"])
        plan = sample_plan(inputs.sd_per_trade, net, inputs.frequency_per_year, inputs.pass_level)
        self.order.log(card, Gate.SAMPLE_PLAN, plan.outcome, today, plan_numbers(plan))
        return plan
