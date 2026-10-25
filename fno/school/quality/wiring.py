"""Composition root of `fno/school/quality/` (story MS-P1b): the quality gate and the capture-gate report over the
recorded captures of `fno/school/roads/wiring.py`."""

from ..roads.wiring import build_road_services
from .band import DEFAULT_BAND_STEPS
from .capture_gate import CaptureGateReport
from .gate import RoadQualityGate
from .ports import ListedContracts


def build_quality_gate(listing: ListedContracts, band_steps: int = DEFAULT_BAND_STEPS) -> RoadQualityGate:
    return RoadQualityGate(listing, band_steps)


def build_capture_gate_report(band_steps: int = DEFAULT_BAND_STEPS) -> CaptureGateReport:
    services = build_road_services()
    gate = build_quality_gate(services.listing, band_steps)
    return CaptureGateReport(services.calendar, services.catalogue, services.snapshots, gate)
