"""A measurement version (story R3): shadowed to measure premium, costs and the fill path at real quotes, never a
candidate. Its one source is the version file's existing `edge_family` field; every output that shows such a version
labels it through this predicate. A measurement is never promoted and never counted as a positive candidate."""

from __future__ import annotations

from .schema import Strategy

MEASUREMENT = "measurement"  # the `edge_family` value that marks a measurement version


def is_measurement(strategy: Strategy | None) -> bool:
    return strategy is not None and strategy.edge_family == MEASUREMENT
