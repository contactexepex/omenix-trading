"""Runs one period of a registered experiment (story B3): the guard first (before any data is read), then the
period's opportunities, every policy and control on them, and the results document."""

from __future__ import annotations

from collections.abc import Callable, Sequence

from ..research_data.panel_reader import NiftyPanel
from .cycles import Cycle
from .experiments import Experiment, Period
from .features import Feature, ResearchData
from .opportunities import build_opportunities
from .period_report import period_document, score
from .simulator import CycleSimulator
from .structures import Structure
from .trial_guard import TrialGuard


class ExperimentRunner:
    def __init__(
        self,
        guard: TrialGuard,
        load_data: Callable[[Period], ResearchData],
        build_cycles: Callable[[NiftyPanel], list[Cycle]],
        features: Sequence[Feature],
        structures: Sequence[Structure],
        build_simulator: Callable[[NiftyPanel], CycleSimulator],
        ledger_count: Callable[[str], dict],
        inputs: Callable[[], dict],
    ):
        self.guard, self.load_data, self.build_cycles = guard, load_data, build_cycles
        self.features, self.structures, self.build_simulator = tuple(features), tuple(structures), build_simulator
        self.ledger_count, self.inputs = ledger_count, inputs

    def run(self, experiment: Experiment, period_name: str) -> dict:
        period = experiment.period(period_name)
        self.guard.check(experiment.trial_ids, experiment.protocol_path, period.decisive)
        data = self.load_data(period)
        cycles = [c for c in self.build_cycles(data.panel) if period.start <= c.decision_day <= period.end]
        simulator = self.build_simulator(data.panel)
        opportunities = build_opportunities(cycles, data, self.features, self.structures, simulator)
        scored = score(experiment, opportunities, tuple(s.code for s in self.structures))
        document = period_document(experiment, period, scored, self.ledger_count(experiment.ledger_name))
        document["inputs"] = self.inputs()
        return document
