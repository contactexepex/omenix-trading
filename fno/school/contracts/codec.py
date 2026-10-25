"""Canonical JSON for the school's records (story 3.4): sorted keys, no spaces, no NaN, ISO dates and enum values,
so equal records give equal bytes (replay twice, identical) and a record reads back to an equal object."""

import json
import types
from collections.abc import Mapping
from dataclasses import fields, is_dataclass
from datetime import date, datetime
from enum import Enum
from typing import Any, Union, get_args, get_origin, get_type_hints

_PLAIN = (bool, int, float, str)


def to_plain(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        hints = get_type_hints(type(value))
        return {f.name: to_plain(_as_declared(hints[f.name], getattr(value, f.name))) for f in fields(value)}
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise TypeError("record mappings take string keys only")
        return {key: to_plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [to_plain(item) for item in value]
    if isinstance(value, float):
        return 0.0 if value == 0 else value  # -0.0 and 0.0 are equal records: one spelling
    if value is None or isinstance(value, (bool, int, str)):
        return value
    raise TypeError(f"cannot write {type(value).__name__} into a record")


def _as_declared(hint: Any, value: Any) -> Any:
    """An int given to a field declared float (alone or with None) is written as a float, as it reads back."""
    if isinstance(value, int) and not isinstance(value, bool):
        members = get_args(hint) if get_origin(hint) in (Union, types.UnionType) else (hint,)
        if float in members and int not in members:
            return float(value)
    return value


def canonical_bytes(record: Any) -> bytes:
    text = json.dumps(to_plain(record), sort_keys=True, separators=(",", ":"), allow_nan=False, ensure_ascii=True)
    return text.encode("ascii")


def from_bytes(cls: type, data: bytes) -> Any:
    return from_plain(cls, json.loads(data))


def from_plain(kind: Any, value: Any) -> Any:
    origin, args = get_origin(kind), get_args(kind)
    if origin in (Union, types.UnionType):
        if value is None and type(None) in args:
            return None
        if type(value) in _PLAIN and type(value) in args:
            return value  # a plain value of a member type reads as itself (3 stays an int in `float | int | str`)
        return _first_fitting([arg for arg in args if arg is not type(None)], value)
    if origin is tuple:
        return tuple(from_plain(args[0], item) for item in value)
    if origin is Mapping or origin is dict:
        return {key: from_plain(args[1], item) for key, item in value.items()}
    if is_dataclass(kind):
        hints = get_type_hints(kind)
        return kind(**{f.name: from_plain(hints[f.name], value[f.name]) for f in fields(kind)})
    if isinstance(kind, type) and issubclass(kind, Enum):
        return kind(value)
    if kind is datetime:
        return datetime.fromisoformat(value)
    if kind is date:
        return date.fromisoformat(value)
    if kind is float and isinstance(value, int) and not isinstance(value, bool):
        return float(value)
    return value


def _first_fitting(kinds: list, value: Any) -> Any:
    """A union's value: the first member that reads it (enum members before plain strings, as declared)."""
    for kind in kinds:
        try:
            return from_plain(kind, value)
        except (TypeError, ValueError, KeyError):
            continue
    raise ValueError(f"no member of the union reads {value!r}")


class CanonicalRecord:
    """Gives a frozen record dataclass its canonical bytes and the reader back."""

    def to_bytes(self) -> bytes:
        return canonical_bytes(self)

    @classmethod
    def from_bytes(cls, data: bytes):
        return from_bytes(cls, data)
