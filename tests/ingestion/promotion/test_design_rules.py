"""The Record is written by the gate only, enforced structurally (docs/PIPELINE_DESIGN.md): inside the promotion
package only the staging area and the gate may reference `.put`, so a fetcher module cannot write anything else."""

from __future__ import annotations

import ast
from pathlib import Path

PACKAGE = Path(__file__).parents[3] / "fno" / "ingestion" / "promotion"
MAY_WRITE = {"staging.py", "gate.py"}


def put_references(path: Path) -> int:
    """Every `.put` attribute access, called or aliased (`w = store.put`)."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return sum(isinstance(n, ast.Attribute) and n.attr == "put" for n in ast.walk(tree))


def test_only_the_staging_area_and_the_gate_reference_put():
    files = sorted(PACKAGE.glob("*.py"))
    assert len(files) >= 7
    writers = {p.name for p in files if put_references(p)}
    assert writers == MAY_WRITE


def test_the_stager_can_only_be_given_a_staging_area_never_a_store_or_a_gate():
    import inspect

    from fno.ingestion.promotion.runs import Stager

    parameters = inspect.signature(Stager.__init__).parameters
    assert "record" not in parameters and "gate" not in parameters
    assert str(parameters["staging"].annotation) == "StagingArea"
