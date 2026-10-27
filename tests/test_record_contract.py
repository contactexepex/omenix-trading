"""docs/RECORD_CONTRACT.md and docs/NEWS_RECORD_CONTRACT.md stay honest (story P5): every test they name exists, every
row names a test, the plant list (`tools/contract_plants.json`) and the two documents describe the same claims with the
same tests, and each document stays under 500 lines. It does not re-run the plants
(`python tools/contract_plants.py` does)."""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ("RECORD_CONTRACT.md", "NEWS_RECORD_CONTRACT.md")  # one owning document per area (DEL1 follow-up split)
TEXTS = {name: (ROOT / "docs" / name).read_text() for name in DOCS}
DOC = "\n".join(TEXTS.values())
PLANTS = json.loads((ROOT / "tools" / "contract_plants.json").read_text())
ROW = re.compile(r"^\| ([A-Z]\d+[a-z]?) \|.*\|$", re.M)
TEST_ID = re.compile(r"`(tests/[\w/.]+\.py(?:::\w+)?)`")


def cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def rows() -> dict[str, list[str]]:
    """Row id -> the tests in its "Pinned by" column (the fourth); other columns may name files that pin nothing."""
    return {cells(line)[0]: TEST_ID.findall(cells(line)[3]) for line in DOC.splitlines() if ROW.match(line)}


def exists(test_id: str) -> bool:
    path, _, name = test_id.partition("::")
    file = ROOT / path
    if not file.is_file():
        return False
    if not name:
        return True
    return any(
        isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name
        for n in ast.walk(ast.parse(file.read_text()))
    )


def test_every_test_the_document_names_exists():
    missing = [t for tests in rows().values() for t in tests if not exists(t)]
    assert missing == []


def test_every_row_names_at_least_one_test_and_the_document_has_rows():
    found = rows()
    assert len(found) >= 25 and [row_id for row_id, tests in found.items() if not tests] == []


def test_the_document_and_the_plant_list_describe_the_same_claims_and_tests():
    found = rows()
    assert sorted(found) == sorted(p["id"] for p in PLANTS)
    assert {p["id"]: sorted(p["tests"]) for p in PLANTS} == {row_id: sorted(tests) for row_id, tests in found.items()}


def test_every_plant_names_a_real_file_and_text():
    for plant in PLANTS:
        assert plant["old"] in (ROOT / plant["file"]).read_text(), plant["id"]


def test_each_document_stays_under_500_lines():
    assert all(len(text.splitlines()) < 500 for text in TEXTS.values())


def stated_only_rows() -> set[str]:
    return {cells(line)[0] for line in DOC.splitlines() if ROW.match(line) and "**stated only**" in cells(line)[5]}


def test_the_tool_expects_exactly_the_rows_the_document_calls_stated_only():
    import importlib.util

    spec = importlib.util.spec_from_file_location("contract_plants", ROOT / "tools" / "contract_plants.py")
    tool = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tool)
    assert set(tool.EXPECT_SURVIVE) == stated_only_rows()
