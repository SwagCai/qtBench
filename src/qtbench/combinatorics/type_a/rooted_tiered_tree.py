"""Standard rooted tiered trees ``stRTT(mu)`` and their inversion statistic.

Following D'Adderio, Iraci, Le Borgne, Romero and Vanden Wyngaerd (see the
problem statement for references), a tiered tree carries a level and a positive
label on every vertex; an edge may join two vertices only when their labels and
levels increase in the same direction. A *rooted* ``alpha``-tree has one extra
vertex, the root, alone at level ``0``, with ``alpha_i`` of the remaining
vertices at level ``i``. A standard object on ``n = |alpha|`` non-root vertices
labels all ``n + 1`` vertices bijectively with ``1, ..., n + 1``.

Unlike the zero-rooted family of ``tiered_tree``, here the root carries an
ordinary label and therefore takes part in the compatibility relation: since
its level is ``0``, the root is compatible exactly with the vertices whose
label exceeds its own.

The public statistic ``inv`` counts pairs ``(i, j)`` of non-root vertices such
that ``j`` is a descendant of ``i``, ``j`` is compatible with the parent of
``i``, and ``j < i``.

The canonical encoding stores both vectors over the labels ``1, ..., n + 1``:

    levels_of_1_through_n_plus_1 | parents_of_1_through_n_plus_1

The root is the unique vertex of level ``0``, and it is the unique vertex whose
parent entry is ``0``. For example the unique ``mu = (1)`` object is ::

    0,1|0,1
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
from itertools import permutations
from typing import Iterator

SEPARATOR = "|"

RootedTieredTreeWord = str


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
    low, high = (i, j) if i < j else (j, i)
    return levels[low - 1] < levels[high - 1]


def is_rooted_tiered_tree(encoding: str) -> bool:
    """Whether ``encoding`` is a standard element of some ``stRTT(alpha)``."""
    if not isinstance(encoding, str) or encoding.count(SEPARATOR) != 1:
        return False
    try:
        levels, parents = _parse(encoding)
    except ValueError:
        return False
    size = len(levels)
    if size < 2 or len(parents) != size:
        return False
    if levels.count(0) != 1:
        return False
    if set(levels) != set(range(max(levels) + 1)):
        return False
    root = levels.index(0) + 1
    if parents.count(0) != 1 or parents[root - 1] != 0:
        return False
    for vertex, parent in enumerate(parents, start=1):
        if vertex == root:
            continue
        if not 1 <= parent <= size or not _compatible(levels, vertex, parent):
            return False

    state = [0] * (size + 1)
    state[root] = 2
    for vertex in range(1, size + 1):
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
class RootedTieredTree:
    """A standard rooted tiered tree with an ordinary root label."""

    encoding: str
    n: int

    def __init__(self, encoding: str, *, validate: bool = True) -> None:
        if validate and not is_rooted_tiered_tree(encoding):
            raise ValueError(f"not a standard rooted tiered tree: {encoding!r}")
        levels, _parents = _parse(encoding)
        object.__setattr__(self, "encoding", encoding)
        object.__setattr__(self, "n", len(levels) - 1)

    @property
    def size(self) -> int:
        """Number ``n`` of non-root vertices."""
        return self.n

    @property
    def vertex_count(self) -> int:
        """Total number of vertices, ``n + 1``."""
        return self.n + 1

    @cached_property
    def _parsed(self):
        return _parse(self.encoding)

    @cached_property
    def levels(self) -> tuple[int, ...]:
        """``levels[i - 1]`` is the level of the vertex labelled ``i``."""
        return self._parsed[0]

    @cached_property
    def parents(self) -> tuple[int, ...]:
        """``parents[i - 1]`` is the parent of ``i``; the root's entry is ``0``."""
        return self._parsed[1]

    @cached_property
    def root(self) -> int:
        """The label of the root, the unique vertex at level ``0``."""
        return self.levels.index(0) + 1

    @cached_property
    def tiers(self) -> tuple[int, ...]:
        """The composition ``alpha`` of positive-level tier sizes."""
        return tuple(
            self.levels.count(level) for level in range(1, max(self.levels) + 1)
        )

    @cached_property
    def children(self) -> dict[int, tuple[int, ...]]:
        """Children of every vertex."""
        out: dict[int, list[int]] = {i: [] for i in range(1, self.n + 2)}
        for vertex, parent in enumerate(self.parents, start=1):
            if parent:
                out[parent].append(vertex)
        return {vertex: tuple(items) for vertex, items in out.items()}

    @cached_property
    def ancestors(self) -> dict[int, frozenset[int]]:
        """Proper ancestors of each vertex; the root has none."""
        out: dict[int, frozenset[int]] = {}
        for vertex in range(1, self.n + 2):
            chain: list[int] = []
            current = self.parents[vertex - 1]
            while current:
                chain.append(current)
                current = self.parents[current - 1]
            out[vertex] = frozenset(chain)
        return out

    @cached_property
    def height(self) -> dict[int, int]:
        """Distance from each vertex to the root."""
        return {vertex: len(ancestors) for vertex, ancestors in self.ancestors.items()}

    def compatible(self, i: int, j: int) -> bool:
        """Whether labels ``i`` and ``j`` are compatible."""
        return _compatible(self.levels, i, j)

    def inv(self) -> int:
        """The tiered-tree inversion number, using constant auxiliary space.

        Walk upward from each possible descendant instead of materializing the
        quadratic dictionary of all ancestor sets.
        """
        root = self.root
        parents = self.parents
        levels = self.levels
        total = 0
        for descendant in range(1, self.n + 2):
            if descendant == root:
                continue
            ancestor = parents[descendant - 1]
            while ancestor != root:
                parent = parents[ancestor - 1]
                if descendant < ancestor and _compatible(
                    levels, descendant, parent
                ):
                    total += 1
                ancestor = parent
        return total

    def to_jsonable(self) -> str:
        return self.encoding


def rooted_tiered_tree_size(encoding_or_object) -> int:
    """Number of non-root vertices."""
    if isinstance(encoding_or_object, RootedTieredTree):
        return encoding_or_object.n
    level_text = encoding_or_object.split(SEPARATOR)[0]
    return level_text.count(",")


def _iter_level_functions(mu: tuple[int, ...]) -> Iterator[tuple[int, ...]]:
    """Assign one level ``0`` and the tier sizes ``mu`` to labels ``1, ..., n+1``."""
    multiset = [0] + [
        level for level, size in enumerate(mu, start=1) for _ in range(size)
    ]
    seen = set()
    for arrangement in permutations(multiset):
        if arrangement in seen:
            continue
        seen.add(arrangement)
        yield arrangement


def _iter_spanning_trees(levels: tuple[int, ...]) -> Iterator[tuple[int, ...]]:
    """Yield parent vectors of spanning trees of the compatibility graph."""
    size = len(levels)
    root = levels.index(0) + 1
    parents = [0] * size
    order = [vertex for vertex in range(1, size + 1) if vertex != root]
    neighbours = {
        vertex: [
            other
            for other in range(1, size + 1)
            if _compatible(levels, vertex, other)
        ]
        for vertex in order
    }

    def closes_cycle(vertex: int) -> bool:
        current = parents[vertex - 1]
        for _ in range(size):
            # An unassigned parent reads as the root here; any cycle it hides is
            # caught once the last vertex of that cycle is assigned.
            if current == root or current == 0:
                return False
            current = parents[current - 1]
        return True

    def rec(index: int) -> Iterator[tuple[int, ...]]:
        if index == len(order):
            yield tuple(parents)
            return
        vertex = order[index]
        for parent in neighbours[vertex]:
            parents[vertex - 1] = parent
            if not closes_cycle(vertex):
                yield from rec(index + 1)
        parents[vertex - 1] = 0

    yield from rec(0)


def iter_rooted_tiered_trees(mu) -> Iterator[RootedTieredTree]:
    """Yield every standard element of ``stRTT(mu)`` once."""
    mu = tuple(int(part) for part in mu)
    if not mu or any(part < 1 for part in mu):
        raise ValueError("tier sizes must be a nonempty sequence of positive integers")
    for levels in _iter_level_functions(mu):
        for parents in _iter_spanning_trees(levels):
            yield RootedTieredTree(_encode(levels, parents), validate=False)


def rooted_tiered_tree_count(mu) -> int:
    """Number of standard elements of ``stRTT(mu)``."""
    return sum(1 for _ in iter_rooted_tiered_trees(mu))


def canonical_rooted_tiered_tree(mu) -> RootedTieredTree:
    """The root-star of ``stRTT(mu)``: label ``1`` roots every other vertex.

    Label ``1`` sits alone at level ``0``, so it is compatible with every other
    label, and the levels increase with the labels. This is a valid object for
    every ``mu``, obtained without enumerating the fiber.
    """
    mu = tuple(int(part) for part in mu)
    if not mu or any(part < 1 for part in mu):
        raise ValueError("tier sizes must be a nonempty sequence of positive integers")
    levels = (0,) + tuple(
        level for level, size in enumerate(mu, start=1) for _ in range(size)
    )
    parents = (0,) + (1,) * sum(mu)
    return RootedTieredTree(_encode(levels, parents), validate=False)
