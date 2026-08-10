from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
from itertools import permutations
import re
from typing import Iterable, Sequence

GraphWord = str
_ENCODING = re.compile(r"([1-9][0-9]*):([0-9a-f]+)")


def _edge_pairs(n: int):
    for high in range(1, n):
        for low in range(high):
            yield low, high


def _adjacency_from_bits(n: int, bits: int) -> tuple[int, ...]:
    adjacency = [0] * n
    edge_count = n * (n - 1) // 2
    for index, (left, right) in enumerate(_edge_pairs(n)):
        if bits & (1 << (edge_count - index - 1)):
            adjacency[left] |= 1 << right
            adjacency[right] |= 1 << left
    return tuple(adjacency)


def _bits_for_order(adjacency: Sequence[int], order: Sequence[int]) -> int:
    bits = 0
    for left, right in _edge_pairs(len(order)):
        bits = (bits << 1) | ((adjacency[order[left]] >> order[right]) & 1)
    return bits


def _encoding(n: int, bits: int) -> str:
    width = max(1, (n * (n - 1) // 2 + 3) // 4)
    return f"{n}:{bits:0{width}x}"


def _is_connected(adjacency: Sequence[int]) -> bool:
    if not adjacency:
        return False
    seen = 1
    frontier = 1
    while frontier:
        vertex_bit = frontier & -frontier
        frontier ^= vertex_bit
        vertex = vertex_bit.bit_length() - 1
        new = adjacency[vertex] & ~seen
        seen |= new
        frontier |= new
    return seen == (1 << len(adjacency)) - 1


def canonical_connected_graph(
    n: int,
    edges: Iterable[tuple[int, int]],
    *,
    validate: bool = True,
) -> GraphWord:
    if n <= 0:
        raise ValueError("a connected graph must have at least one vertex")
    adjacency = [0] * n
    for left, right in edges:
        if not (0 <= left < n and 0 <= right < n) or left == right:
            raise ValueError("edges must join distinct vertices in range(n)")
        adjacency[left] |= 1 << right
        adjacency[right] |= 1 << left
    if validate and not _is_connected(adjacency):
        raise ValueError("graph must be connected")
    bits = min(_bits_for_order(adjacency, order) for order in permutations(range(n)))
    return _encoding(n, bits)


def is_connected_graph_encoding(value: object, *, canonical: bool = True) -> bool:
    if not isinstance(value, str):
        return False
    match = _ENCODING.fullmatch(value)
    if match is None:
        return False
    n = int(match.group(1))
    bits_text = match.group(2)
    width = max(1, (n * (n - 1) // 2 + 3) // 4)
    bits = int(bits_text, 16)
    if len(bits_text) != width or bits >= 1 << (n * (n - 1) // 2):
        return False
    adjacency = _adjacency_from_bits(n, bits)
    if not _is_connected(adjacency):
        return False
    if not canonical:
        return True
    return value == canonical_connected_graph(
        n,
        ((left, right) for left, right in _edge_pairs(n) if adjacency[left] & (1 << right)),
        validate=False,
    )


@dataclass(frozen=True, init=False)
class ConnectedGraph:
    """An unlabeled simple connected graph in canonical adjacency encoding."""

    encoding: GraphWord
    n: int
    adjacency: tuple[int, ...]

    def __init__(self, encoding: str, *, validate: bool = True) -> None:
        if validate and not is_connected_graph_encoding(encoding):
            raise ValueError("invalid canonical connected-graph encoding")
        match = _ENCODING.fullmatch(encoding)
        if match is None:
            raise ValueError("invalid connected-graph encoding")
        n = int(match.group(1))
        adjacency = _adjacency_from_bits(n, int(match.group(2), 16))
        object.__setattr__(self, "encoding", encoding)
        object.__setattr__(self, "n", n)
        object.__setattr__(self, "adjacency", adjacency)

    @property
    def size(self) -> int:
        return self.n

    @cached_property
    def degrees(self) -> tuple[int, ...]:
        return tuple(neighbors.bit_count() for neighbors in self.adjacency)

    def sibling_number(self) -> int:
        multiplicities: dict[int, int] = {}
        for vertex, neighbors in enumerate(self.adjacency):
            closed = neighbors | (1 << vertex)
            multiplicities[closed] = multiplicities.get(closed, 0) + 1
        return max(multiplicities.values()) - 1

    def tuft_number(self) -> int:
        leaves = sum(1 << vertex for vertex, degree in enumerate(self.degrees) if degree == 1)
        return max((neighbors & leaves).bit_count() for neighbors in self.adjacency)

    def _reduction_step(self) -> ConnectedGraph:
        keep = [vertex for vertex, degree in enumerate(self.degrees) if degree != 1]
        if not keep:
            return self
        restricted = []
        for vertex in keep:
            restricted.append(
                sum(1 << new for new, other in enumerate(keep) if self.adjacency[vertex] & (1 << other))
            )
        classes: dict[int, list[int]] = {}
        for vertex, neighbors in enumerate(restricted):
            classes.setdefault(neighbors | (1 << vertex), []).append(vertex)
        groups = tuple(classes.values())
        edges = []
        for left in range(len(groups)):
            for right in range(left + 1, len(groups)):
                if restricted[groups[left][0]] & (1 << groups[right][0]):
                    edges.append((left, right))
        return ConnectedGraph(canonical_connected_graph(len(groups), edges), validate=False)

    @cached_property
    def reduction(self) -> GraphWord:
        if self.n == 2:
            return self.encoding
        current = self
        while True:
            reduced = current._reduction_step()
            if reduced.n == current.n:
                return current.encoding
            current = reduced

    def feature_dict(self) -> dict[str, object]:
        return {
            "n": self.n,
            "degrees": list(self.degrees),
            "adjacency": [
                [other for other in range(self.n) if neighbors & (1 << other)]
                for neighbors in self.adjacency
            ],
            "reduction": self.reduction,
        }


def connected_graph_size(encoding_or_object) -> int:
    if isinstance(encoding_or_object, ConnectedGraph):
        return encoding_or_object.n
    match = _ENCODING.fullmatch(encoding_or_object)
    if match is None:
        raise ValueError("invalid connected-graph encoding")
    return int(match.group(1))
