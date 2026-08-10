from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from itertools import product
import re

PartitionMatrixWord = str
_MATRIX_ENCODING = re.compile(
    r"M;([1-9][0-9]*(?:,[1-9][0-9]*)*);([1-9][0-9]*(?:,[1-9][0-9]*)*)"
)
_INVERSION_ENCODING = re.compile(
    r"I;((?:0|[1-9][0-9]*)(?:,(?:0|[1-9][0-9]*))*)"
)


def _encode_partition_matrix(rows: tuple[int, ...], columns: tuple[int, ...]) -> str:
    return f"M;{','.join(map(str, rows))};{','.join(map(str, columns))}"


def _encode_inversion_sequence(entries: tuple[int, ...]) -> str:
    return f"I;{','.join(map(str, entries))}"


def canonical_improper_partition_matrix(
    rows: tuple[int, ...], columns: tuple[int, ...]
) -> str:
    rows = tuple(rows)
    columns = tuple(columns)
    if (
        any(type(value) is not int for value in (*rows, *columns))
        or not _is_partition_matrix(rows, columns)
        or not _is_improper(rows, columns)
        or not _matrix_minus(rows, columns)
    ):
        raise ValueError("invalid improper partition matrix")
    return _encode_partition_matrix(rows, columns)


def canonical_restricted_inversion_sequence(entries: tuple[int, ...]) -> str:
    entries = tuple(entries)
    if (
        any(type(value) is not int for value in entries)
        or not _is_restricted_inversion_sequence(entries)
    ):
        raise ValueError("invalid restricted inversion sequence")
    return _encode_inversion_sequence(entries)


def _is_partition_matrix(rows: tuple[int, ...], columns: tuple[int, ...]) -> bool:
    if len(rows) != len(columns) or not rows:
        return False
    dimension = max(columns)
    return (
        max(rows) == dimension
        and set(rows) == set(range(1, dimension + 1))
        and set(columns) == set(range(1, dimension + 1))
        and all(left <= right for left, right in zip(rows, columns))
        and all(left <= right for left, right in zip(columns, columns[1:]))
    )


def _is_improper(rows: tuple[int, ...], columns: tuple[int, ...]) -> bool:
    for index in range(1, len(rows) - 1):
        if columns[index] != columns[index + 1] or rows[index] == rows[index + 1]:
            continue
        column = columns[index]
        minimum = next(position + 1 for position, value in enumerate(columns) if value == column)
        if (index + 1) % 2 == minimum % 2:
            return False
    return True


def _matrix_minus(rows: tuple[int, ...], columns: tuple[int, ...]) -> bool:
    last = len(rows) - 1
    return sum(
        row == rows[last] and column == columns[last]
        for row, column in zip(rows, columns)
    ) % 2 == 1


def _is_restricted_inversion_sequence(entries: tuple[int, ...]) -> bool:
    if len(entries) < 2 or entries[-2] == entries[-1]:
        return False
    positions: dict[int, list[int]] = {}
    for index, value in enumerate(entries):
        if not 0 <= value <= index:
            return False
        positions.setdefault(value, []).append(index)
    return all(len(found) == 1 or (len(found) == 2 and found[1] == found[0] + 1) for found in positions.values())


def is_partition_matrix_inversion_encoding(value: object) -> bool:
    if not isinstance(value, str):
        return False
    matrix_match = _MATRIX_ENCODING.fullmatch(value)
    if matrix_match is not None:
        rows = tuple(int(piece) for piece in matrix_match.group(1).split(","))
        columns = tuple(int(piece) for piece in matrix_match.group(2).split(","))
        return (
            _is_partition_matrix(rows, columns)
            and _is_improper(rows, columns)
            and _matrix_minus(rows, columns)
            and value == canonical_improper_partition_matrix(rows, columns)
        )
    inversion_match = _INVERSION_ENCODING.fullmatch(value)
    if inversion_match is None:
        return False
    entries = tuple(int(piece) for piece in inversion_match.group(1).split(","))
    return (
        _is_restricted_inversion_sequence(entries)
        and value == canonical_restricted_inversion_sequence(entries)
    )


@dataclass(frozen=True, init=False)
class PartitionMatrixInversion:
    """One side of Chern--Fu Question 5.5."""

    encoding: PartitionMatrixWord
    side: str
    rows: tuple[int, ...]
    columns: tuple[int, ...]
    entries: tuple[int, ...]

    def __init__(self, encoding: str, *, validate: bool = True) -> None:
        if validate and not is_partition_matrix_inversion_encoding(encoding):
            raise ValueError("invalid canonical partition-matrix/inversion encoding")
        matrix_match = _MATRIX_ENCODING.fullmatch(encoding)
        inversion_match = _INVERSION_ENCODING.fullmatch(encoding)
        if matrix_match is not None:
            rows = tuple(int(piece) for piece in matrix_match.group(1).split(","))
            columns = tuple(int(piece) for piece in matrix_match.group(2).split(","))
            entries: tuple[int, ...] = ()
            side = "source"
        elif inversion_match is not None:
            rows, columns = (), ()
            entries = tuple(int(piece) for piece in inversion_match.group(1).split(","))
            side = "target"
        else:
            raise ValueError("invalid partition-matrix/inversion encoding")
        object.__setattr__(self, "encoding", encoding)
        object.__setattr__(self, "side", side)
        object.__setattr__(self, "rows", rows)
        object.__setattr__(self, "columns", columns)
        object.__setattr__(self, "entries", entries)

    @property
    def n(self) -> int:
        return len(self.rows) if self.side == "source" else len(self.entries)

    @property
    def size(self) -> int:
        return self.n

    @property
    def grading(self) -> int:
        if self.side == "target":
            return len(set(self.entries))
        counts = [self.columns.count(column) for column in range(1, max(self.columns) + 1)]
        return sum((count + 1) // 2 for count in counts)

    def feature_dict(self) -> dict[str, object]:
        return {
            "side": self.side,
            "n": self.n,
            "rows": list(self.rows),
            "columns": list(self.columns),
            "entries": list(self.entries),
            "grading": self.grading,
        }


def _matrix_from_inversion_sequence(entries: tuple[int, ...]) -> PartitionMatrixInversion:
    values = sorted(set(entries))
    row_for_value = {value: index + 1 for index, value in enumerate(values)}
    rows = tuple(row_for_value[value] for value in entries)
    boundaries = (*values, len(entries))
    columns = tuple(
        next(index for index in range(1, len(boundaries)) if label <= boundaries[index])
        for label in range(1, len(entries) + 1)
    )
    return PartitionMatrixInversion(
        _encode_partition_matrix(rows, columns), validate=False
    )


@cache
def iter_improper_partition_matrices(n: int) -> tuple[PartitionMatrixInversion, ...]:
    if n < 2:
        raise ValueError("public fibers start at size two")
    result = []
    for suffix in product(*(range(index) for index in range(2, n + 1))):
        matrix = _matrix_from_inversion_sequence((0, *suffix))
        if _is_improper(matrix.rows, matrix.columns) and _matrix_minus(matrix.rows, matrix.columns):
            result.append(matrix)
    return tuple(result)


@cache
def iter_restricted_inversion_sequences(n: int) -> tuple[PartitionMatrixInversion, ...]:
    if n < 2:
        raise ValueError("public fibers start at size two")
    return tuple(
        PartitionMatrixInversion(canonical_restricted_inversion_sequence((0, *suffix)), validate=False)
        for suffix in product(*(range(index) for index in range(2, n + 1)))
        if _is_restricted_inversion_sequence((0, *suffix))
    )


def partition_matrix_inversion_size(value) -> int:
    if isinstance(value, PartitionMatrixInversion):
        return value.n
    return PartitionMatrixInversion(value).n
