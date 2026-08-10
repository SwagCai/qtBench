from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
import re
from typing import Iterator, Sequence

ShiftedTableauWord = str
_PARTITION = re.compile(r"[1-9][0-9]*(?:,[1-9][0-9]*)*")
_CELL = re.compile(r"[1-9][0-9]*(?:\.[1-9][0-9]*)*")


def _strict_partition(text: str) -> tuple[int, ...]:
    if _PARTITION.fullmatch(text) is None:
        raise ValueError("invalid strict partition")
    parts = tuple(int(value) for value in text.split(","))
    if any(left <= right for left, right in zip(parts, parts[1:])):
        raise ValueError("partition is not strict")
    return parts


def shifted_shape_cells(shape: Sequence[int]) -> tuple[tuple[int, int], ...]:
    return tuple(
        (row, column)
        for row, length in enumerate(shape, 1)
        for column in range(row, row + length)
    )


def shifted_extensions(mu: Sequence[int]) -> tuple[tuple[tuple[int, ...], int], ...]:
    mu = tuple(mu)
    result = []
    for mask in range(1 << len(mu)):
        shape = tuple(mu[i] + ((mask >> i) & 1) for i in range(len(mu)))
        if any(left <= right for left, right in zip(shape, shape[1:])):
            continue
        added_columns = [
            row + mu[row - 1]
            for row in range(1, len(mu) + 1)
            if (mask >> (row - 1)) & 1
        ]
        parity = (len(set(added_columns)) + len(added_columns)) % 2
        result.append((shape, -1 if parity else 1))
    return tuple(result)


def _validate_tableau(
    family: str,
    mu: tuple[int, ...],
    shape: tuple[int, ...],
    cells: tuple[tuple[int, ...], ...],
) -> None:
    extensions = dict(shifted_extensions(mu))
    if shape not in extensions or (family == "Q" and shape != mu):
        raise ValueError("shape is not an allowed extension")
    positions = shifted_shape_cells(shape)
    if len(cells) != len(positions):
        raise ValueError("cell count does not match the shifted shape")
    by_position = dict(zip(positions, cells, strict=True))
    row_primes: set[tuple[int, int]] = set()
    column_unprimes: set[tuple[int, int]] = set()
    for (row, column), entry in by_position.items():
        if not entry or any(rank < 1 for rank in entry) or tuple(sorted(set(entry))) != entry:
            raise ValueError("tableau cells must be nonempty sets of positive ranks")
        left = by_position.get((row, column - 1))
        below = by_position.get((row - 1, column))
        if left is not None and left[-1] > entry[0]:
            raise ValueError("tableau row is not weakly increasing")
        if below is not None and below[-1] > entry[0]:
            raise ValueError("tableau column is not weakly increasing")
        for rank in entry:
            label = (rank + 1) // 2
            key = (row, label) if rank % 2 else (column, label)
            seen = row_primes if rank % 2 else column_unprimes
            if key in seen:
                raise ValueError("tableau repeats a restricted letter")
            seen.add(key)
        if family == "P" and row == column:
            primes = [rank for rank in entry if rank % 2]
            if shape[row - 1] > mu[row - 1]:
                if primes:
                    raise ValueError("extended diagonal cell contains a prime")
            elif len(primes) > 1 or (primes and primes[0] != entry[-1]):
                raise ValueError("fixed diagonal cell violates unprime-max")


def canonical_shifted_setvalued_tableau(
    family: str,
    mu: Sequence[int],
    shape: Sequence[int],
    cells: Sequence[Sequence[int]],
) -> ShiftedTableauWord:
    mu = tuple(int(value) for value in mu)
    shape = tuple(int(value) for value in shape)
    cells = tuple(tuple(int(rank) for rank in entry) for entry in cells)
    if family not in {"P", "Q"} or not mu or len(shape) != len(mu):
        raise ValueError("invalid shifted-tableau family or shape")
    if any(left <= right for left, right in zip(mu, mu[1:])):
        raise ValueError("mu must be a strict partition")
    _validate_tableau(family, mu, shape, cells)
    return ";".join(
        (
            family,
            ",".join(map(str, mu)),
            ",".join(map(str, shape)),
            "|".join(".".join(map(str, entry)) for entry in cells),
        )
    )


def is_shifted_setvalued_tableau_encoding(value: object) -> bool:
    if not isinstance(value, str):
        return False
    fields = value.split(";")
    if len(fields) != 4 or fields[0] not in {"P", "Q"}:
        return False
    try:
        mu = _strict_partition(fields[1])
        shape = _strict_partition(fields[2])
        encoded_cells = fields[3].split("|")
        if any(_CELL.fullmatch(entry) is None for entry in encoded_cells):
            return False
        cells = tuple(tuple(int(rank) for rank in entry.split(".")) for entry in encoded_cells)
        return value == canonical_shifted_setvalued_tableau(fields[0], mu, shape, cells)
    except ValueError:
        return False


@dataclass(frozen=True, init=False)
class ShiftedSetValuedTableau:
    encoding: ShiftedTableauWord
    family: str
    mu: tuple[int, ...]
    shape: tuple[int, ...]
    cells: tuple[tuple[int, ...], ...]

    def __init__(self, encoding: str, *, validate: bool = True) -> None:
        if validate and not is_shifted_setvalued_tableau_encoding(encoding):
            raise ValueError("invalid shifted set-valued tableau encoding")
        fields = encoding.split(";")
        if len(fields) != 4:
            raise ValueError("invalid shifted set-valued tableau encoding")
        object.__setattr__(self, "encoding", encoding)
        object.__setattr__(self, "family", fields[0])
        object.__setattr__(self, "mu", tuple(map(int, fields[1].split(","))))
        object.__setattr__(self, "shape", tuple(map(int, fields[2].split(","))))
        object.__setattr__(
            self,
            "cells",
            tuple(tuple(map(int, entry.split("."))) for entry in fields[3].split("|")),
        )

    @property
    def entry_count(self) -> int:
        return sum(map(len, self.cells))

    @property
    def size(self) -> int:
        return self.entry_count

    @property
    def content(self) -> tuple[int, ...]:
        counts = [0] * max((rank + 1) // 2 for cell in self.cells for rank in cell)
        for cell in self.cells:
            for rank in cell:
                counts[(rank - 1) // 2] += 1
        return tuple(counts)

    @property
    def side(self) -> str:
        if self.family == "Q":
            return "source"
        sign = dict(shifted_extensions(self.mu))[self.shape]
        return "source" if sign < 0 else "target"

    def feature_dict(self) -> dict[str, object]:
        return {
            "family": self.family,
            "mu": list(self.mu),
            "shape": list(self.shape),
            "cells": [list(cell) for cell in self.cells],
            "content": list(self.content),
            "entry_count": self.entry_count,
            "side": self.side,
        }


def iter_shifted_setvalued_tableaux(
    family: str,
    mu: Sequence[int],
    shape: Sequence[int],
    content: Sequence[int],
) -> Iterator[ShiftedSetValuedTableau]:
    mu = tuple(mu)
    shape = tuple(shape)
    content = tuple(content)
    positions = shifted_shape_cells(shape)
    if not content or content[-1] < 1 or any(value < 0 for value in content):
        raise ValueError("content must be a canonically trimmed nonnegative vector")
    if sum(content) < len(positions):
        return
    remaining = list(content)
    assigned: dict[tuple[int, int], tuple[int, ...]] = {}
    row_primes = {row: set() for row in range(1, len(shape) + 1)}
    column_unprimes = {column: set() for _, column in positions}
    ranks = tuple(range(1, 2 * len(content) + 1))

    def extend(index: int) -> Iterator[ShiftedSetValuedTableau]:
        if index == len(positions):
            if not any(remaining):
                cells = tuple(assigned[position] for position in positions)
                encoding = canonical_shifted_setvalued_tableau(family, mu, shape, cells)
                yield ShiftedSetValuedTableau(encoding, validate=False)
            return
        row, column = positions[index]
        left = assigned.get((row, column - 1), ())
        below = assigned.get((row - 1, column), ())
        floor = max(left[-1] if left else 0, below[-1] if below else 0)
        eligible = []
        for rank in ranks:
            label = (rank + 1) // 2
            if not remaining[label - 1] or rank < floor:
                continue
            if rank % 2 and label in row_primes[row]:
                continue
            if not rank % 2 and label in column_unprimes[column]:
                continue
            if family == "P" and row == column and shape[row - 1] > mu[row - 1] and rank % 2:
                continue
            eligible.append(rank)
        room = sum(remaining) - (len(positions) - index - 1)
        for width in range(1, min(len(eligible), room) + 1):
            for entry in combinations(eligible, width):
                labels = [(rank + 1) // 2 for rank in entry]
                if any(labels.count(label) > remaining[label - 1] for label in set(labels)):
                    continue
                if family == "P" and row == column and shape[row - 1] == mu[row - 1]:
                    primes = [rank for rank in entry if rank % 2]
                    if len(primes) > 1 or (primes and primes[0] != entry[-1]):
                        continue
                assigned[(row, column)] = entry
                for rank in entry:
                    label = (rank + 1) // 2
                    remaining[label - 1] -= 1
                    (row_primes[row] if rank % 2 else column_unprimes[column]).add(label)
                yield from extend(index + 1)
                for rank in entry:
                    label = (rank + 1) // 2
                    remaining[label - 1] += 1
                    (row_primes[row] if rank % 2 else column_unprimes[column]).remove(label)
                del assigned[(row, column)]

    yield from extend(0)


def shifted_tableau_size(value) -> int:
    if isinstance(value, ShiftedSetValuedTableau):
        return value.entry_count
    if not is_shifted_setvalued_tableau_encoding(value):
        raise ValueError("invalid shifted set-valued tableau encoding")
    return ShiftedSetValuedTableau(value, validate=False).entry_count
