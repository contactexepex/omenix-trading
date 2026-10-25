"""C4's modes (story C4, design 12.4). `PlaybookMode` checks the trade against the version it claims: the version's
fingerprint, that the version may trade on the day, its structure code, wing widths and lots, and that the legs have
that structure's shape (`validity_shapes.py`). Book 2's mode (`EnvelopeMode`, story D4) reuses it with "at most the
version's lots" and adds the authority envelope; Book 3's (`ConstitutionMode`, story D5) checks its registered
strategy and constitution. A book without a mode has no trade path."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Mapping

from .validity_evidence import Evidence
from .validity_proposal import CheckResult, ValidityProposal
from .validity_shapes import Shape, shape_problem


class ValidityMode(ABC):
    name: str

    @abstractmethod
    def checks(self, proposal: ValidityProposal, evidence: Evidence | None) -> list[CheckResult]:
        """The mode's own checks, each with its result; `evidence` is the committed snapshot (None if untrusted)."""


def exact_lots(lots: int, version_lots: int) -> bool:
    return lots == version_lots


class PlaybookMode(ValidityMode):
    name = "playbook"

    def __init__(self, shapes: Mapping[str, Shape], lots_rule: Callable[[int, int], bool] = exact_lots):
        self.shapes = dict(shapes)  # structure code -> its shape rule (validity_shapes.py)
        self.lots_rule = lots_rule  # Book 1: exactly the version's lots; Book 2's envelope: at most (story D4)

    def checks(self, proposal: ValidityProposal, evidence: Evidence | None) -> list[CheckResult]:
        strategy = proposal.strategy
        if strategy is None:
            return [CheckResult("version", False, "no playbook version named for the trade")]
        spec, key = strategy.structure, (strategy.name, strategy.version)
        fingerprint = strategy.parameters_sha256 == proposal.rule_sha256
        atm = evidence.atm_strike(proposal.expiry) if evidence is not None else None
        legs = [leg.leg for leg in proposal.legs]
        shape = shape_problem(self.shapes, proposal.structure, legs, proposal.width, atm)
        version = f"rule {proposal.rule_sha256[:12]} vs the version's {strategy.parameters_sha256[:12]}"
        return [
            CheckResult("version", fingerprint, version),
            CheckResult(
                "permitted", key in proposal.approved, f"{strategy.name} v{strategy.version} on {proposal.day}"
            ),
            CheckResult("structure", proposal.structure == spec.code, f"{proposal.structure} vs {spec.code}"),
            CheckResult("width", proposal.width in spec.widths, f"{proposal.width:g} in {list(spec.widths)}"),
            CheckResult(
                "lots", self.lots_rule(proposal.lots, spec.lots), f"{proposal.lots} vs the version's {spec.lots}"
            ),
            CheckResult("shape", not shape, shape or "legs have the structure's shape"),
        ]
