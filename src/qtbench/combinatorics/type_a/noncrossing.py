from __future__ import annotations

from dataclasses import dataclass
from functools import cache, cached_property
from itertools import combinations, product
from math import comb
from typing import Iterable, Iterator

Block = tuple[int, ...]
PartitionBlocks = tuple[Block, ...]


def _normalize_block(block: Iterable[int]) -> Block:
    values = tuple(block)
    if any(type(value) is not int for value in values):
        raise ValueError("block elements must be integers")
    normalized = tuple(sorted(values))
    if not normalized:
        raise ValueError("blocks must be nonempty")
    if len(set(normalized)) != len(normalized):
        raise ValueError(f"block repeats an element: {normalized}")
    return normalized


def canonicalize_blocks(blocks: Iterable[Iterable[int]]) -> PartitionBlocks:
    normalized = tuple(_normalize_block(block) for block in blocks)
    return tuple(sorted(normalized, key=lambda block: (block[0], len(block), block)))


def _validate_partition_of_interval(blocks: PartitionBlocks, n: int) -> None:
    universe = [value for block in blocks for value in block]
    expected = list(range(1, n + 1))
    if sorted(universe) != expected:
        raise ValueError(f"blocks must partition [1, {n}] exactly")


def _validate_noncrossing(blocks: PartitionBlocks) -> None:
    for first, second in combinations(blocks, 2):
        for a, c in combinations(first, 2):
            for b, d in combinations(second, 2):
                if a < b < c < d or b < a < d < c:
                    raise ValueError(f"crossing blocks detected: {first} and {second}")


def narayana_number(n: int, k: int) -> int:
    if n <= 0 or k <= 0 or k > n:
        return 0
    return comb(n, k) * comb(n, k - 1) // n


@dataclass(frozen=True, init=False)
class NoncrossingPartition:
    """A noncrossing partition of [n], encoded as sorted integer blocks.

    Public benchmark code intentionally exposes only structural data and the
    statistics named in each problem statement. Generation or calibration
    oracles live beside their corresponding public problem when available.
    """

    n: int
    blocks: PartitionBlocks

    def __init__(
        self,
        blocks: Iterable[Iterable[int]],
        *,
        n: int | None = None,
        validate: bool = True,
    ) -> None:
        canonical = canonicalize_blocks(blocks)
        inferred_n = max((value for block in canonical for value in block), default=0)
        size = inferred_n if n is None else n
        if type(size) is not int or size < 0:
            raise ValueError("n must be a nonnegative integer")
        if validate:
            _validate_partition_of_interval(canonical, size)
            _validate_noncrossing(canonical)
        object.__setattr__(self, "n", size)
        object.__setattr__(self, "blocks", canonical)

    @classmethod
    def _from_canonical_blocks(
        cls,
        blocks: PartitionBlocks,
        *,
        n: int,
    ) -> NoncrossingPartition:
        """Build an internally enumerated partition without copying its blocks."""

        partition = cls.__new__(cls)
        object.__setattr__(partition, "n", n)
        object.__setattr__(partition, "blocks", blocks)
        return partition

    def __iter__(self):
        return iter(self.blocks)

    def __len__(self) -> int:
        return self.block_count

    @property
    def block_count(self) -> int:
        return len(self.blocks)

    @property
    def narayana_k(self) -> int:
        return self.n - self.block_count + 1

    @cached_property
    def blocks_by_max(self) -> PartitionBlocks:
        return tuple(sorted(self.blocks, key=lambda block: (block[-1], block[0], len(block), block)))

    @cached_property
    def block_maxima(self) -> tuple[int, ...]:
        return tuple(block[-1] for block in self.blocks_by_max)

    @cached_property
    def block_type(self) -> tuple[int, ...]:
        """The multiset of block sizes as a partition of ``n``, weakly decreasing.

        Kreweras' refinement of the Catalan number: the number of noncrossing
        partitions of a given block type is the Kreweras number of that partition.
        """
        return tuple(sorted((len(block) for block in self.blocks), reverse=True))

    @cached_property
    def block_sizes_by_max(self) -> tuple[int, ...]:
        return tuple(len(block) for block in self.blocks_by_max)

    @cached_property
    def preceding_block_sizes(self) -> tuple[int, ...]:
        values: list[int] = []
        total = 0
        for block in self.blocks_by_max:
            values.append(total)
            total += len(block)
        return tuple(values)

    @cached_property
    def nonmaximal_elements(self) -> tuple[int, ...]:
        return tuple(sorted(value for block in self.blocks_by_max for value in block[:-1]))

    @cached_property
    def parent_indices_by_max(self) -> tuple[int | None, ...]:
        parents: list[int | None] = []
        for index, block in enumerate(self.blocks_by_max):
            left = block[0]
            right = block[-1]
            candidates = [
                other_index
                for other_index, other in enumerate(self.blocks_by_max)
                if other_index != index and other[0] < left and right < other[-1]
            ]
            if not candidates:
                parents.append(None)
                continue
            parent = min(
                candidates,
                key=lambda item: self.blocks_by_max[item][-1] - self.blocks_by_max[item][0],
            )
            parents.append(parent)
        return tuple(parents)

    def area(self) -> int:
        """Area statistic used as the public first statistic for q,t-Narayana."""

        return sum(
            maximum - previous_size
            for maximum, previous_size in zip(self.block_maxima, self.preceding_block_sizes)
        ) - self.n

    def skip(self) -> int:
        return sum(block[-1] - block[0] - len(block) + 1 for block in self.blocks)

    def to_jsonable(self) -> list[list[int]]:
        return [list(block) for block in self.blocks]

    def to_rgf(self) -> list[int]:
        word = [0 for _ in range(self.n)]
        for block_index, block in enumerate(self.blocks, start=1):
            for value in block:
                word[value - 1] = block_index
        return word

    def feature_dict(self) -> dict[str, object]:
        return {
            "n": self.n,
            "k": self.narayana_k,
            "block_count": self.block_count,
            "blocks_by_max": [list(block) for block in self.blocks_by_max],
            "block_maxima": list(self.block_maxima),
            "block_sizes_by_max": list(self.block_sizes_by_max),
            "preceding_block_sizes": list(self.preceding_block_sizes),
            "nonmaximal_elements": list(self.nonmaximal_elements),
            "rgf": self.to_rgf(),
        }


def _weak_compositions(total: int, parts: int):
    if parts == 1:
        yield (total,)
        return
    for first in range(total + 1):
        for rest in _weak_compositions(total - first, parts - 1):
            yield (first, *rest)


def _bounded_weak_compositions(total: int, capacities: tuple[int, ...]):
    if not capacities:
        if total == 0:
            yield ()
        return
    first_capacity = capacities[0]
    for first in range(min(total, first_capacity) + 1):
        for rest in _bounded_weak_compositions(total - first, capacities[1:]):
            yield (first, *rest)


def _shift_blocks(blocks: PartitionBlocks, offset: int) -> PartitionBlocks:
    return tuple(tuple(value + offset for value in block) for block in blocks)


@cache
def _enumerate_blocks(size: int, block_count: int) -> tuple[PartitionBlocks, ...]:
    if size == 0:
        return ((),) if block_count == 0 else ()
    if block_count <= 0 or block_count > size:
        return ()

    results: list[PartitionBlocks] = []
    for root_size in range(1, size + 1):
        interval_count = root_size
        remaining = size - root_size
        for gaps in _weak_compositions(remaining, interval_count):
            capacities = gaps
            for child_counts in _bounded_weak_compositions(block_count - 1, capacities):
                child_options = [
                    _enumerate_blocks(gap, child_count)
                    for gap, child_count in zip(gaps, child_counts)
                ]
                if any(not choices for choices in child_options):
                    continue

                current = 1
                root_block = [1]
                interval_starts: list[int] = []
                for gap in gaps[:-1]:
                    interval_starts.append(current + 1)
                    current = current + gap + 1
                    root_block.append(current)
                interval_starts.append(current + 1)

                for children in product(*child_options):
                    merged: list[Block] = []
                    for start, child in zip(interval_starts, children):
                        merged.extend(_shift_blocks(child, start - 1))
                    merged.append(tuple(root_block))
                    results.append(tuple(sorted(merged, key=lambda block: (block[0], len(block), block))))
    return tuple(results)


def iter_noncrossing_partitions(
    n: int,
    *,
    block_count: int | None = None,
) -> Iterator[NoncrossingPartition]:
    """Yield partitions while retaining at most one memoized Narayana fiber."""

    try:
        if n < 0:
            raise ValueError("n must be nonnegative")
        if n == 0:
            return
        counts = [block_count] if block_count is not None else range(1, n + 1)
        for count in counts:
            if count is None:
                continue
            try:
                for blocks in _enumerate_blocks(n, count):
                    yield NoncrossingPartition._from_canonical_blocks(blocks, n=n)
            finally:
                # Do not retain one complete Narayana fiber while constructing
                # the next one.
                _enumerate_blocks.cache_clear()
    finally:
        # Memoization avoids repeated recursive work within one fiber, but
        # retaining intermediate families across calls grows quickly with n.
        _enumerate_blocks.cache_clear()


def enumerate_noncrossing_partitions(
    n: int,
    *,
    block_count: int | None = None,
) -> list[NoncrossingPartition]:
    return list(iter_noncrossing_partitions(n, block_count=block_count))


def enumerate_narayana_partitions(n: int, k: int) -> list[NoncrossingPartition]:
    if k <= 0 or k > n:
        return []
    return enumerate_noncrossing_partitions(n, block_count=n - k + 1)


def partition_to_text(blocks: PartitionBlocks) -> str:
    pieces = ["{" + ",".join(str(value) for value in block) + "}" for block in blocks]
    return "{" + ",".join(pieces) + "}"
