"""Standard Young-diagram fillings for the Macdonald q,t-symmetry task.

Rows use French notation: ``rows[0]`` is the bottom (longest) row.  A standard
filling of shape ``mu`` contains ``1, ..., |mu|`` once each, with no monotonicity
condition.  The canonical encoding includes the shape so a submission can emit
a filling of the conjugate diagram::

    3,2,1|1,5,2/4,3/6

The rows after ``|`` are again listed bottom to top.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
from itertools import permutations
from typing import Iterator

from .kostka_tableau import conjugate_partition, is_partition

MacdonaldFillingWord = str


def _encode(shape, rows) -> str:
    shape_text = ",".join(str(part) for part in shape)
    rows_text = "/".join(",".join(str(value) for value in row) for row in rows)
    return f"{shape_text}|{rows_text}"


def _parse(encoding: str) -> tuple[tuple[int, ...], tuple[tuple[int, ...], ...]]:
    shape_text, rows_text = encoding.split("|", 1)
    shape = tuple(int(piece) for piece in shape_text.split(","))
    rows = tuple(
        tuple(int(piece) for piece in row.split(","))
        for row in rows_text.split("/")
    )
    return shape, rows


def is_standard_macdonald_filling(encoding: str) -> bool:
    if not isinstance(encoding, str) or not encoding:
        return False
    try:
        shape, rows = _parse(encoding)
    except (ValueError, TypeError):
        return False
    if _encode(shape, rows) != encoding:
        return False
    if not is_partition(shape) or tuple(len(row) for row in rows) != shape:
        return False
    n = sum(shape)
    return sorted(value for row in rows for value in row) == list(range(1, n + 1))


@dataclass(frozen=True, init=False)
class StandardMacdonaldFilling:
    """A bijectively labelled Young diagram with HHL ``inv`` and ``maj``."""

    encoding: str
    shape: tuple[int, ...]
    rows: tuple[tuple[int, ...], ...]
    n: int

    def __init__(self, encoding: str, *, validate: bool = True) -> None:
        if validate and not is_standard_macdonald_filling(encoding):
            raise ValueError(f"not a standard Macdonald filling: {encoding!r}")
        shape, rows = _parse(encoding)
        object.__setattr__(self, "encoding", encoding)
        object.__setattr__(self, "shape", shape)
        object.__setattr__(self, "rows", rows)
        object.__setattr__(self, "n", sum(shape))

    @property
    def size(self) -> int:
        return self.n

    @cached_property
    def conjugate_shape(self) -> tuple[int, ...]:
        return conjugate_partition(self.shape)

    def maj(self) -> int:
        """HHL major index: sum of column-word descent positions."""
        total = 0
        for row_index in range(1, len(self.rows)):
            lower = self.rows[row_index - 1]
            upper = self.rows[row_index]
            for column, value in enumerate(upper):
                if value > lower[column]:
                    column_height = sum(width > column for width in self.shape)
                    total += column_height - row_index
        return total

    def inv(self) -> int:
        """HHL inversion number (attacks minus descent arms)."""
        attacks = 0
        for row in self.rows:
            for left in range(len(row)):
                attacks += sum(row[left] > row[right] for right in range(left + 1, len(row)))
        for row_index in range(1, len(self.rows)):
            lower = self.rows[row_index - 1]
            upper = self.rows[row_index]
            for upper_column, upper_value in enumerate(upper):
                attacks += sum(
                    upper_value > lower[lower_column]
                    for lower_column in range(upper_column)
                )
        descent_arms = 0
        for row_index in range(1, len(self.rows)):
            lower = self.rows[row_index - 1]
            upper = self.rows[row_index]
            for column, value in enumerate(upper):
                if value > lower[column]:
                    descent_arms += len(upper) - column - 1
        return attacks - descent_arms

    def to_jsonable(self) -> str:
        return self.encoding


def standard_macdonald_filling(shape, rows, *, validate: bool = True) -> StandardMacdonaldFilling:
    shape = tuple(shape)
    return StandardMacdonaldFilling(_encode(shape, rows), validate=validate)


def standard_macdonald_filling_size(encoding_or_object) -> int:
    if isinstance(encoding_or_object, StandardMacdonaldFilling):
        return encoding_or_object.n
    shape_text = encoding_or_object.split("|", 1)[0]
    return sum(int(piece) for piece in shape_text.split(","))


def iter_standard_macdonald_fillings(shape) -> Iterator[StandardMacdonaldFilling]:
    shape = tuple(shape)
    if not is_partition(shape):
        raise ValueError(f"not a partition: {shape!r}")
    n = sum(shape)
    for values in permutations(range(1, n + 1)):
        rows = []
        offset = 0
        for width in shape:
            rows.append(values[offset : offset + width])
            offset += width
        yield StandardMacdonaldFilling(_encode(shape, rows), validate=False)


def canonical_standard_macdonald_filling(shape, *, reverse: bool = False) -> StandardMacdonaldFilling:
    shape = tuple(shape)
    if not is_partition(shape):
        raise ValueError(f"not a partition: {shape!r}")
    values = list(range(1, sum(shape) + 1))
    if reverse:
        values.reverse()
    rows = []
    offset = 0
    for width in shape:
        rows.append(values[offset : offset + width])
        offset += width
    return StandardMacdonaldFilling(_encode(shape, rows), validate=False)
