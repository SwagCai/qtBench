"""Classical parking functions with the area and dinv statistics."""
from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
from typing import Iterator

from .tamari_parking import (
    _iter_parking_functions,
    dyck_area,
    is_parking_function,
    parking_dinv,
    parking_shape,
)

ParkingFunctionWord = str


def _parse(encoding: str) -> tuple[int, ...]:
    return tuple(int(piece) for piece in encoding.split(","))


def _encode(values) -> str:
    return ",".join(str(value) for value in values)


def is_parking_function_word(encoding: str) -> bool:
    if not isinstance(encoding, str) or not encoding:
        return False
    try:
        values = _parse(encoding)
    except ValueError:
        return False
    return bool(values) and _encode(values) == encoding and is_parking_function(values)


@dataclass(frozen=True, init=False)
class ParkingFunction:
    encoding: str
    values: tuple[int, ...]
    n: int

    def __init__(self, encoding: str, *, validate: bool = True) -> None:
        if validate and not is_parking_function_word(encoding):
            raise ValueError(f"not a parking function: {encoding!r}")
        values = _parse(encoding)
        object.__setattr__(self, "encoding", encoding)
        object.__setattr__(self, "values", values)
        object.__setattr__(self, "n", len(values))

    @property
    def size(self) -> int:
        return self.n

    @cached_property
    def shape(self) -> tuple[int, ...]:
        return parking_shape(self.values)

    def area(self) -> int:
        return dyck_area(self.shape)

    def dinv(self) -> int:
        return parking_dinv(self.values)

    def to_jsonable(self) -> str:
        return self.encoding


def parking_function(values, *, validate: bool = True) -> ParkingFunction:
    return ParkingFunction(_encode(values), validate=validate)


def parking_function_size(encoding_or_object) -> int:
    if isinstance(encoding_or_object, ParkingFunction):
        return encoding_or_object.n
    return encoding_or_object.count(",") + 1


def iter_parking_functions(n: int) -> Iterator[ParkingFunction]:
    if n < 1:
        raise ValueError("size must be positive")
    for values in _iter_parking_functions(n):
        yield ParkingFunction(_encode(values), validate=False)


def canonical_parking_function(n: int, *, reverse: bool = False) -> ParkingFunction:
    if n < 1:
        raise ValueError("size must be positive")
    values = list(range(n))
    if reverse:
        values.reverse()
    return parking_function(values, validate=False)
