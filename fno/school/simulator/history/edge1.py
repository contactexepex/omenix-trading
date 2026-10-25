"""The one place the simulator reads EDGE1's frozen study (orchestrator, 22 Oct 2026: read-only, one adapter, never
copied or edited): NSE's circular lot schedule, the dated STT rates and, for tests, its day-file reader.

`research/edge1/edge1study` is not an installed package. It is loaded by file path under its own unique package name, so
its folder never joins `sys.path` and none of its neighbours (`cards.py`, `study.py`) can shadow another import."""

import importlib
import importlib.util
import sys
from collections.abc import Callable, Mapping
from datetime import date
from pathlib import Path
from types import ModuleType

PACKAGE = "ms_sim_edge1study"
STUDY = Path(__file__).resolve().parents[4] / "research" / "edge1" / "edge1study"


def _load_package() -> ModuleType:
    if PACKAGE in sys.modules:
        return sys.modules[PACKAGE]
    spec = importlib.util.spec_from_file_location(
        PACKAGE, STUDY / "__init__.py", submodule_search_locations=[str(STUDY)]
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[PACKAGE] = module
    spec.loader.exec_module(module)
    return module


def module(name: str) -> ModuleType:
    """One of EDGE1's modules (`lots`, `stt_history`, `day_files`), imported inside the unique package."""
    _load_package()
    return importlib.import_module(f"{PACKAGE}.{name}")


def circular_lot_or_none(underlying: str, expiry: date) -> int | None:
    """NSE's circular lot for an index EDGE1 has a schedule for (NIFTY, BANKNIFTY); None for any other. The schedule
    ends with the legacy files (29 Dec 2023): the caller asks it for legacy-format days only."""
    lots = module("lots")
    return lots.circular_lot(underlying, expiry) if underlying in lots.SCHEDULE else None


def dated_charges(charges: Mapping[str, float]) -> Callable[[date], dict]:
    """C1's charges with the two STT rates of a trade date (EDGE1's `stt_history`); every other charge as decided."""
    return module("stt_history").charges_on(charges)
