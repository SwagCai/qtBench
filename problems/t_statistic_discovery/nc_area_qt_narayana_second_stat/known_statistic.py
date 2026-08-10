from __future__ import annotations

from collections.abc import Iterable

Block = tuple[int, ...]


def _as_blocks(partition) -> tuple[Block, ...]:
    if hasattr(partition, "blocks"):
        blocks = partition.blocks
    else:
        blocks = partition
    return tuple(tuple(sorted(int(value) for value in block)) for block in blocks)


def _size(partition, blocks: tuple[Block, ...]) -> int:
    if hasattr(partition, "n"):
        return int(partition.n)
    return max((value for block in blocks for value in block), default=0)


def area_from_blocks(blocks: Iterable[Iterable[int]], *, n: int | None = None) -> int:
    normalized = tuple(tuple(sorted(int(value) for value in block)) for block in blocks)
    size = max((value for block in normalized for value in block), default=0) if n is None else int(n)
    blocks_by_max = sorted(normalized, key=lambda block: (block[-1], block[0], len(block), block))

    total = 0
    preceding_size = 0
    for block in blocks_by_max:
        total += block[-1] - preceding_size
        preceding_size += len(block)
    return total - size


def area(partition) -> int:
    blocks = _as_blocks(partition)
    return area_from_blocks(blocks, n=_size(partition, blocks))


def statistic(partition) -> int:
    return area(partition)
