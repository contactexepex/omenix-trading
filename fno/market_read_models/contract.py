"""The dashboard's contract, pinned (story P6; P1 adds the F&O screens' data catalog): byte copies of omenix-dashboard's
api/openapi.yaml, schemas and the 33-34, 32, frame and F&O screen examples, with the contract version, the source commit
and each file's SHA-256 in pin.json. Every block is validated against these schemas before it may be published;
`contract-check` compares the pin with the dashboard."""

from __future__ import annotations

import hashlib
import json
from abc import ABC, abstractmethod
from functools import cached_property
from pathlib import Path

import requests
import yaml
from jsonschema import Draft202012Validator
from jsonschema.exceptions import best_match

PIN_FILE = "pin.json"
OPENAPI_FILE = "api/openapi.yaml"
SCHEMA_FOLDER = "api/schemas"
# Screener and Markets; chain (P9); the frame, whose India session example states hours (2.6); P1's F&O screens
EXAMPLES_FILES = (
    "api/examples/blocks-33-34.json",
    "api/examples/blocks-32.json",
    "api/examples/blocks.json",
    "api/examples/fno-screens.json",
)
GITHUB_RAW = "https://raw.githubusercontent.com/{repository}/{branch}/"
DRIFT_TIMEOUT_SECONDS = 30
NOT_FOUND = 404


class ContractBroken(ValueError):
    """A payload does not match its pinned schema, or the pinned copy does not match its pin."""


class PinnedContract:
    def __init__(self, folder: Path):
        self.folder = Path(folder)
        self.pin = json.loads((self.folder / PIN_FILE).read_text(encoding="utf-8"))

    @property
    def version(self) -> str:
        return self.pin["contract_version"]

    def changed_files(self) -> list[str]:
        """Pinned files whose bytes no longer match their recorded SHA-256 (empty: the copy is intact)."""
        return [name for name, sha in self.pin["files"].items() if self.sha256(name) != sha]

    def sha256(self, name: str) -> str | None:
        path = self.folder / name
        return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None

    @cached_property
    def schemas(self) -> dict:
        """Every schema of the bundled document: openapi.yaml's components and each schemas/*.yaml file."""
        merged = dict(yaml.safe_load((self.folder / OPENAPI_FILE).read_text(encoding="utf-8"))["components"]["schemas"])
        for path in sorted((self.folder / SCHEMA_FOLDER).glob("*.yaml")):
            merged.update(yaml.safe_load(path.read_text(encoding="utf-8")))
        return merged

    def examples(self) -> dict:
        """Every pinned example by name (the files share no name)."""
        return {k: v for f in EXAMPLES_FILES for k, v in json.loads((self.folder / f).read_text("utf-8")).items()}

    def validate(self, schema_name: str, instance) -> None:
        """ContractBroken listing every violation of `instance` against the named schema by its path and the rule it
        breaks, never the value: the message reaches the public Actions log (story P2, privacy rule 3)."""
        root = {"$ref": f"#/components/schemas/{schema_name}", "components": {"schemas": self.schemas}}
        errors = sorted(Draft202012Validator(root).iter_errors(instance), key=lambda e: list(e.absolute_path))
        if errors:
            lines = [_violation(e) for e in errors[:10]]
            raise ContractBroken(f"{schema_name}: {len(errors)} violation(s): " + "; ".join(lines))


def _violation(error) -> str:
    """A violation's path and rule; for a missing or unexpected field, the field names (keys, never values). Under
    anyOf or oneOf, the alternative of the right type that came closest names it (a nullable object's failure is in
    its object branch, not in "is not null")."""
    while error.context:
        error = best_match([e for e in error.context if e.validator != "type"] or error.context)
    where = "/".join(map(str, error.absolute_path)) or "."
    names = _field_names(error)
    return f"{where}: breaks '{error.validator}'" + (f" ({', '.join(names)})" if names else "")


def _field_names(error) -> list[str]:
    if not isinstance(error.instance, dict):
        return []
    if error.validator == "required":
        return [k for k in error.validator_value if k not in error.instance]
    if error.validator == "additionalProperties" and error.validator_value is False:
        allowed = set(error.schema.get("properties", {}))
        return sorted(k for k in error.instance if k not in allowed)
    return []


class PublishedContract(ABC):
    """Where the dashboard publishes its contract files (today: its repository's main branch on GitHub)."""

    @abstractmethod
    def read(self, name: str) -> bytes | None:
        """The published bytes of a pinned file (its path in the pin); None if it is no longer published."""


class GitHubRawContract(PublishedContract):
    def __init__(self, repository: str, branch: str = "main", session: requests.Session | None = None):
        self.base = GITHUB_RAW.format(repository=repository, branch=branch)
        self.session = session or requests.Session()

    def read(self, name: str) -> bytes | None:
        response = self.session.get(self.base + name, timeout=DRIFT_TIMEOUT_SECONDS)
        if response.status_code == NOT_FOUND:
            return None
        response.raise_for_status()
        return response.content


def drift(contract: PinnedContract, published: PublishedContract) -> list[str]:
    """Pinned files whose published bytes now differ, or are no longer published (a new contract to adopt)."""
    return [
        name for name, sha in contract.pin["files"].items()
        if (data := published.read(name)) is None or hashlib.sha256(data).hexdigest() != sha
    ]  # fmt: skip
