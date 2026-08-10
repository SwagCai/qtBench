from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
import random
import re
from typing import Iterable, Iterator, Sequence

ASMWord = str
_ENCODING = re.compile(r"([1-9][0-9]*):([+0-]+(?:/[+0-]+)*)")
_SYMBOL = {-1: "-", 0: "0", 1: "+"}
_VALUE = {symbol: value for value, symbol in _SYMBOL.items()}


def _is_alternating_line(line: Sequence[int]) -> bool:
    partial = 0
    for value in line:
        if value not in (-1, 0, 1):
            return False
        partial += value
        if partial not in (0, 1):
            return False
    return partial == 1


def canonical_alternating_sign_matrix(rows: Iterable[Iterable[int]]) -> ASMWord:
    matrix = tuple(tuple(int(value) for value in row) for row in rows)
    n = len(matrix)
    if n < 1 or any(len(row) != n for row in matrix):
        raise ValueError("an alternating sign matrix must be nonempty and square")
    if not all(_is_alternating_line(row) for row in matrix) or not all(
        _is_alternating_line(tuple(matrix[row][column] for row in range(n)))
        for column in range(n)
    ):
        raise ValueError("rows and columns must alternate and sum to one")
    return f"{n}:" + "/".join("".join(_SYMBOL[value] for value in row) for row in matrix)


def is_alternating_sign_matrix_encoding(value: object) -> bool:
    if not isinstance(value, str):
        return False
    match = _ENCODING.fullmatch(value)
    if match is None:
        return False
    n = int(match.group(1))
    encoded_rows = match.group(2).split("/")
    if len(encoded_rows) != n or any(len(row) != n for row in encoded_rows):
        return False
    rows = tuple(tuple(_VALUE[symbol] for symbol in row) for row in encoded_rows)
    try:
        return value == canonical_alternating_sign_matrix(rows)
    except ValueError:
        return False


@dataclass(frozen=True, init=False)
class AlternatingSignMatrix:
    """A square alternating sign matrix in its canonical row encoding."""

    encoding: ASMWord
    n: int
    rows: tuple[tuple[int, ...], ...]

    def __init__(self, encoding: str, *, validate: bool = True) -> None:
        if validate and not is_alternating_sign_matrix_encoding(encoding):
            raise ValueError("invalid alternating-sign-matrix encoding")
        match = _ENCODING.fullmatch(encoding)
        if match is None:
            raise ValueError("invalid alternating-sign-matrix encoding")
        encoded_rows = match.group(2).split("/")
        object.__setattr__(self, "encoding", encoding)
        object.__setattr__(self, "n", int(match.group(1)))
        object.__setattr__(
            self,
            "rows",
            tuple(tuple(_VALUE[symbol] for symbol in row) for row in encoded_rows),
        )

    @property
    def size(self) -> int:
        return self.n

    @cached_property
    def negative_count(self) -> int:
        return sum(value == -1 for row in self.rows for value in row)

    @cached_property
    def inversion_number(self) -> int:
        below = [0] * self.n
        total = 0
        for row in reversed(self.rows):
            prefix = 0
            for column, value in enumerate(row):
                total += value * prefix
                prefix += below[column]
            for column, value in enumerate(row):
                below[column] += value
        return total

    def feature_dict(self) -> dict[str, object]:
        return {
            "n": self.n,
            "rows": [list(row) for row in self.rows],
            "negative_count": self.negative_count,
            "inversion_number": self.inversion_number,
        }


def _interlacing_rows(lower: tuple[int, ...]) -> Iterator[tuple[int, ...]]:
    row: list[int] = []

    def extend(index: int) -> Iterator[tuple[int, ...]]:
        if index == len(lower) - 1:
            yield tuple(row)
            return
        minimum = lower[index]
        maximum = lower[index + 1]
        if row:
            minimum = max(minimum, row[-1] + 1)
        for value in range(minimum, maximum + 1):
            row.append(value)
            yield from extend(index + 1)
            row.pop()

    yield from extend(0)


def _matrix_from_triangle(triangle: Sequence[Sequence[int]]) -> AlternatingSignMatrix:
    n = len(triangle)
    previous: set[int] = set()
    rows = []
    for triangle_row in triangle:
        current = set(triangle_row)
        rows.append(
            tuple(
                int(column in current) - int(column in previous)
                for column in range(1, n + 1)
            )
        )
        previous = current
    return AlternatingSignMatrix(canonical_alternating_sign_matrix(rows), validate=False)


def enumerate_alternating_sign_matrices(n: int) -> Iterator[AlternatingSignMatrix]:
    if n < 1:
        raise ValueError("alternating-sign-matrix size must be positive")
    reversed_triangle: list[tuple[int, ...]] = [tuple(range(1, n + 1))]

    def extend() -> Iterator[AlternatingSignMatrix]:
        lower = reversed_triangle[-1]
        if len(lower) == 1:
            yield _matrix_from_triangle(tuple(reversed(reversed_triangle)))
            return
        for upper in _interlacing_rows(lower):
            reversed_triangle.append(upper)
            yield from extend()
            reversed_triangle.pop()

    yield from extend()


def alternating_sign_matrix_from_permutation(permutation: Sequence[int]) -> AlternatingSignMatrix:
    n = len(permutation)
    if sorted(permutation) != list(range(n)):
        raise ValueError("permutation must contain range(n)")
    rows = [tuple(int(column == image) for column in range(n)) for image in permutation]
    return AlternatingSignMatrix(canonical_alternating_sign_matrix(rows), validate=False)


def adversarial_alternating_sign_matrices(
    size: int, *, seed: int | None = None
) -> list[AlternatingSignMatrix]:
    if size < 1:
        raise ValueError("alternating-sign-matrix probe size must be positive")
    n = min(size, 256)
    generator = random.Random(seed)
    random_permutation = list(range(n))
    generator.shuffle(random_permutation)
    objects = [
        alternating_sign_matrix_from_permutation(tuple(range(n))),
        alternating_sign_matrix_from_permutation(tuple(reversed(range(n)))),
        alternating_sign_matrix_from_permutation(random_permutation),
    ]
    if n >= 3:
        rows = [[int(row == column) for column in range(n)] for row in range(n)]
        rows[0][:3] = [0, 1, 0]
        rows[1][:3] = [1, -1, 1]
        rows[2][:3] = [0, 1, 0]
        objects.append(
            AlternatingSignMatrix(canonical_alternating_sign_matrix(rows), validate=False)
        )
    return list({obj.encoding: obj for obj in objects}.values())


def alternating_sign_matrix_size(encoding_or_object) -> int:
    if isinstance(encoding_or_object, AlternatingSignMatrix):
        return encoding_or_object.n
    if not isinstance(encoding_or_object, str):
        raise ValueError("invalid alternating-sign-matrix encoding")
    match = _ENCODING.fullmatch(encoding_or_object)
    if match is None:
        raise ValueError("invalid alternating-sign-matrix encoding")
    return int(match.group(1))
