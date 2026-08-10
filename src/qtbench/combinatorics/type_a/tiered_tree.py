"""Zero-rooted tiered trees and their inversion statistic.

Following D'Adderio, Iraci, Le Borgne, Romero and Vanden Wyngaerd (see the
problem statement for references), a tiered tree has a positive level and a
positive label on every non-root vertex. Edges join compatible vertices: their
labels and levels increase in the same direction.

The family ``RTT_0(alpha)`` has an additional root at level and label ``0``.
The root is therefore compatible with every non-root vertex. Standard objects
use each non-root label in ``[n]`` exactly once, where ``n = |alpha|``.

The public statistic ``inv`` counts pairs ``(i, j)`` of non-root vertices such
that ``j`` is a descendant of ``i``, ``j`` is compatible with the parent of
``i``, and ``j < i``.

The root is fixed and carries no information, so the canonical encoding stores
only labels ``1, ..., n``:

    levels_of_1_through_n | parents_of_1_through_n

A parent value of ``0`` denotes the implicit root.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import cache, cached_property
from typing import Iterator

SEPARATOR = "|"

TieredTreeWord = str


def _parse(encoding: str) -> tuple[tuple[int, ...], tuple[int, ...]]:
    level_text, parent_text = encoding.split(SEPARATOR)
    levels = tuple(int(piece) for piece in level_text.split(",")) if level_text else ()
    parents = tuple(int(piece) for piece in parent_text.split(",")) if parent_text else ()
    return levels, parents


def _encode(levels, parents) -> str:
    return (
        ",".join(str(value) for value in levels)
        + SEPARATOR
        + ",".join(str(value) for value in parents)
    )


def _compatible(levels: tuple[int, ...], i: int, j: int) -> bool:
    if i == j:
        return False
    if i == 0 or j == 0:
        return True
    low, high = (i, j) if i < j else (j, i)
    return levels[low - 1] < levels[high - 1]


def is_zero_rooted_tiered_tree(encoding: str) -> bool:
    """Whether ``encoding`` is a standard element of ``RTT_0(alpha)``."""
    if not isinstance(encoding, str) or encoding.count(SEPARATOR) != 1:
        return False
    try:
        levels, parents = _parse(encoding)
    except ValueError:
        return False
    n = len(levels)
    if n < 1 or len(parents) != n:
        return False
    if min(levels) < 1 or set(levels) != set(range(1, max(levels) + 1)):
        return False
    for vertex, parent in enumerate(parents, start=1):
        if not 0 <= parent <= n or parent == vertex:
            return False
        if not _compatible(levels, vertex, parent):
            return False

    state = [0] * (n + 1)
    state[0] = 2
    for vertex in range(1, n + 1):
        current = vertex
        trail = []
        while state[current] == 0:
            state[current] = 1
            trail.append(current)
            current = parents[current - 1]
        if state[current] == 1:
            return False
        for node in trail:
            state[node] = 2
    return True


@dataclass(frozen=True, init=False)
class ZeroRootedTieredTree:
    """A standard tiered tree with an implicit root of label and level ``0``."""

    encoding: str
    n: int

    def __init__(self, encoding: str, *, validate: bool = True) -> None:
        if validate and not is_zero_rooted_tiered_tree(encoding):
            raise ValueError(f"not a standard zero-rooted tiered tree: {encoding!r}")
        levels, _parents = _parse(encoding)
        object.__setattr__(self, "encoding", encoding)
        object.__setattr__(self, "n", len(levels))

    @property
    def size(self) -> int:
        """Number ``n`` of non-root vertices."""
        return self.n

    @property
    def vertex_count(self) -> int:
        """Total number of vertices, including the fixed root."""
        return self.n + 1

    @property
    def root(self) -> int:
        """The fixed root label."""
        return 0

    @cached_property
    def _parsed(self):
        return _parse(self.encoding)

    @cached_property
    def levels(self) -> tuple[int, ...]:
        """``levels[i - 1]`` is the level of the vertex labelled ``i``."""
        return self._parsed[0]

    @cached_property
    def parents(self) -> tuple[int, ...]:
        """``parents[i - 1]`` is the parent of ``i``; ``0`` denotes the root."""
        return self._parsed[1]

    @cached_property
    def tiers(self) -> tuple[int, ...]:
        """The composition ``alpha`` of positive-level tier sizes."""
        return tuple(self.levels.count(level) for level in range(1, max(self.levels) + 1))

    @cached_property
    def children(self) -> dict[int, tuple[int, ...]]:
        """Children of every vertex, including root ``0``."""
        out: dict[int, list[int]] = {i: [] for i in range(self.n + 1)}
        for vertex, parent in enumerate(self.parents, start=1):
            out[parent].append(vertex)
        return {vertex: tuple(children) for vertex, children in out.items()}

    @cached_property
    def ancestors(self) -> dict[int, frozenset[int]]:
        """Proper ancestors of each non-root vertex, including root ``0``."""
        out: dict[int, frozenset[int]] = {}
        for vertex in range(1, self.n + 1):
            chain: list[int] = []
            current = self.parents[vertex - 1]
            while current:
                chain.append(current)
                current = self.parents[current - 1]
            chain.append(0)
            out[vertex] = frozenset(chain)
        return out

    @cached_property
    def height(self) -> dict[int, int]:
        """Distance from each vertex to root ``0``."""
        return {vertex: len(ancestors) for vertex, ancestors in self.ancestors.items()}

    def compatible(self, i: int, j: int) -> bool:
        """Whether labels ``i`` and ``j`` are compatible."""
        return _compatible(self.levels, i, j)

    def inv(self) -> int:
        """The tiered-tree inversion number, using constant auxiliary space.

        Walk upward from each possible descendant instead of materializing the
        quadratic dictionary of all ancestor sets.
        """
        parents = self.parents
        levels = self.levels
        total = 0
        for descendant in range(1, self.n + 1):
            ancestor = parents[descendant - 1]
            while ancestor:
                parent = parents[ancestor - 1]
                if descendant < ancestor and _compatible(
                    levels, descendant, parent
                ):
                    total += 1
                ancestor = parent
        return total

    def to_jsonable(self) -> str:
        return self.encoding


def tiered_tree_inv(encoding: str) -> int:
    """``inv`` of the encoded zero-rooted tiered tree."""
    return ZeroRootedTieredTree(encoding, validate=False).inv()


def tiered_tree_size(encoding_or_object) -> int:
    """Number of non-root vertices."""
    if isinstance(encoding_or_object, ZeroRootedTieredTree):
        return encoding_or_object.n
    level_text = encoding_or_object.split(SEPARATOR)[0]
    return level_text.count(",") + 1


def _iter_level_functions(mu: tuple[int, ...]) -> Iterator[tuple[int, ...]]:
    """Assign the tier sizes ``mu`` to labels ``1, ..., |mu|``."""
    n = sum(mu)
    levels = [0] * n

    def rec(label: int, remaining: tuple[int, ...]) -> Iterator[tuple[int, ...]]:
        if label > n:
            yield tuple(levels)
            return
        for index, left in enumerate(remaining):
            if left:
                levels[label - 1] = index + 1
                yield from rec(
                    label + 1,
                    (*remaining[:index], left - 1, *remaining[index + 1 :]),
                )

    yield from rec(1, mu)


def _iter_spanning_trees(levels: tuple[int, ...]) -> Iterator[tuple[int, ...]]:
    """Yield parent vectors of spanning trees of the compatibility graph."""
    n = len(levels)
    parents = [0] * n
    neighbours = {
        vertex: [
            other
            for other in range(n + 1)
            if other != vertex and _compatible(levels, vertex, other)
        ]
        for vertex in range(1, n + 1)
    }

    def closes_cycle(vertex: int) -> bool:
        current = parents[vertex - 1]
        for _ in range(n):
            if current == 0:
                return False
            if current == vertex:
                return True
            current = parents[current - 1]
        return True

    def rec(vertex: int) -> Iterator[tuple[int, ...]]:
        if vertex > n:
            yield tuple(parents)
            return
        for parent in neighbours[vertex]:
            parents[vertex - 1] = parent
            if not closes_cycle(vertex):
                yield from rec(vertex + 1)
        parents[vertex - 1] = 0

    yield from rec(1)


def iter_zero_rooted_tiered_trees(mu) -> Iterator[ZeroRootedTieredTree]:
    """Yield every standard element of ``RTT_0(mu)`` once."""
    mu = tuple(int(part) for part in mu)
    if not mu or any(part < 1 for part in mu):
        raise ValueError("tier sizes must be a nonempty sequence of positive integers")
    for levels in _iter_level_functions(mu):
        for parents in _iter_spanning_trees(levels):
            yield ZeroRootedTieredTree(_encode(levels, parents), validate=False)


@cache
def enumerate_zero_rooted_tiered_trees(mu) -> tuple[ZeroRootedTieredTree, ...]:
    """All standard elements of ``RTT_0(mu)``."""
    return tuple(iter_zero_rooted_tiered_trees(mu))


def zero_rooted_tiered_tree_count(mu) -> int:
    """Number of standard elements of ``RTT_0(mu)``."""
    return sum(1 for _ in iter_zero_rooted_tiered_trees(mu))


def canonical_zero_rooted_tiered_tree(mu) -> ZeroRootedTieredTree:
    """A canonical zero-rooted tree: every non-root vertex joins root ``0``."""
    mu = tuple(int(part) for part in mu)
    if not mu or any(part < 1 for part in mu):
        raise ValueError("tier sizes must be a nonempty sequence of positive integers")
    levels = tuple(
        level
        for level, tier_size in enumerate(mu, start=1)
        for _ in range(tier_size)
    )
    return ZeroRootedTieredTree(_encode(levels, [0] * sum(mu)), validate=False)
