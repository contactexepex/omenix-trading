"""What a playbook file may name: the features of the feature library (B1) with the kind of value each gives and the
live 15:00 version (B7) the desk computes for it, and the structure codes B2 can build (STR1 added six). A condition
names the research feature it was tested on; the desk evaluates its live version, which must pass the gate (B7)."""

from __future__ import annotations

from dataclasses import dataclass

from ..constants import (
    FEATURE_ATM_IV_MINUS_RV20,
    FEATURE_ATM_IV_MINUS_RV20_LIVE,
    FEATURE_EVENT_IN_WINDOW,
    FEATURE_EVENT_IN_WINDOW_LIVE,
    FEATURE_VIX_ABOVE_MEDIAN,
    FEATURE_VIX_ABOVE_MEDIAN_LIVE,
    STRUCTURES,
    STRUCTURES_ONE_SIDE,
)

NUMBER, FLAG = "number", "flag"


@dataclass(frozen=True)
class FeatureEntry:
    kind: str  # NUMBER or FLAG
    live_version: str


FEATURES = {
    FEATURE_ATM_IV_MINUS_RV20: FeatureEntry(NUMBER, FEATURE_ATM_IV_MINUS_RV20_LIVE),
    FEATURE_VIX_ABOVE_MEDIAN: FeatureEntry(FLAG, FEATURE_VIX_ABOVE_MEDIAN_LIVE),
    FEATURE_EVENT_IN_WINDOW: FeatureEntry(FLAG, FEATURE_EVENT_IN_WINDOW_LIVE),
}
STRUCTURE_CODES = (*STRUCTURES, *STRUCTURES_ONE_SIDE)  # B2's four-leg codes and STR1's one- and two-leg ones
