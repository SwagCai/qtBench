"""Spanning trees of connected threshold graphs, with their inversion statistic.

Following Liu, Meszaros and Morales (see the problem statement for
references), a **threshold graph** is built from one vertex by repeatedly adding
either a dominating vertex or an isolated one. Labelled by reverse degree
sequence on ``{0, 1, ..., n}``, such a graph satisfies the staircase property:
if ``i`` and ``j`` are adjacent then so are ``i'`` and ``j'`` for all
``i' <= i``, ``j' <= j`` with ``i' != j'``. A connected one is therefore
determined by its **up-degrees** ``u``, where vertex ``i`` is adjacent to
``j > i`` exactly when ``j <= i + u_i``:

    u_0 = n > u_1 > ... > u_{k-1} >= 1,   u_i = 0 for i >= k.

There are ``2^(n-1)`` of them on ``n + 1`` vertices, one per subset of
``{1, ..., n-1}``; ``u = (n, n-1, ..., 1)`` is the complete graph ``K_{n+1}``
and ``u = (n, 0, ..., 0)`` is the star.

An object of this family is a spanning tree ``T`` of such a graph, rooted at
vertex ``0`` (which dominates, so the root is always adjacent to everything).
The public statistic is the number of inversions

    inv(T) = #{ (i, j) : i > j, j a descendant of i in T }.

For a threshold graph every inversion is a ``kappa``-inversion, so this is also
Gessel's inversion enumerator statistic.

The canonical encoding is ``up_degrees + "|" + parents``, both comma separated,
with ``parents[j - 1]`` the parent of vertex ``j`` for ``j = 1, ..., n``. The
graph is part of the object because the missing statistic provably depends on
it. For example ::

    3,2,1|0,0,0

is the star-rooted spanning tree of ``K_4``.

The graph side is kept lazy: ``adjacent`` is O(1) and ``degrees`` is O(n), so a
large dense fiber index costs no quadratic memory. Only ``edges`` materialises
the edge set, which is quadratic by nature.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from functools import cached_property
from itertools import combinations
from typing import Iterator

SEPARATOR = "|"

ThresholdTreeWord = str


def _parse(encoding: str) -> tuple[tuple[int, ...], tuple[int, ...]]:
    up_text, parent_text = encoding.split(SEPARATOR)
    up_degrees = tuple(int(piece) for piece in up_text.split(",")) if up_text else ()
    parents = tuple(int(piece) for piece in parent_text.split(",")) if parent_text else ()
    return up_degrees, parents


def _encode(up_degrees, parents) -> str:
    return (
        ",".join(str(value) for value in up_degrees)
        + SEPARATOR
        + ",".join(str(value) for value in parents)
    )


def is_threshold_up_degrees(up_degrees) -> bool:
    """Whether ``up_degrees`` describes a connected threshold graph."""
    if not isinstance(up_degrees, Sequence) or isinstance(
        up_degrees, (str, bytes, bytearray)
    ):
        return False
    n = len(up_degrees)
    if n < 1 or type(up_degrees[0]) is not int or up_degrees[0] != n:
        return False
    positive = True
    for index in range(1, n):
        value = up_degrees[index]
        if type(value) is not int or value < 0:
            return False
        if value == 0:
            positive = False
        elif not positive or value >= up_degrees[index - 1]:
            return False
    return True


def _adjacent(up_degrees, i: int, j: int) -> bool:
    if i == j:
        return False
    low, high = (i, j) if i < j else (j, i)
    return high <= low + up_degrees[low]


def is_threshold_spanning_tree(encoding: str) -> bool:
    """Whether ``encoding`` is a spanning tree of a connected threshold graph."""
    if not isinstance(encoding, str) or encoding.count(SEPARATOR) != 1:
        return False
    try:
        up_degrees, parents = _parse(encoding)
    except ValueError:
        return False
    n = len(up_degrees)
    if len(parents) != n or not is_threshold_up_degrees(up_degrees):
        return False
    for vertex, parent in enumerate(parents, start=1):
        if not 0 <= parent <= n or not _adjacent(up_degrees, vertex, parent):
            return False

    # Resolve every parent chain once.  Walking from every vertex all the way
    # to the root makes a valid path-shaped tree quadratic in its vertex count.
    # States are unvisited, active in this traversal, and known to reach root.
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
class ThresholdSpanningTree:
    """A spanning tree of a connected threshold graph, rooted at vertex ``0``."""

    encoding: str
    n: int

    def __init__(self, encoding: str, *, validate: bool = True) -> None:
        if validate and not is_threshold_spanning_tree(encoding):
            raise ValueError(f"not a threshold-graph spanning tree: {encoding!r}")
        up_degrees, _parents = _parse(encoding)
        object.__setattr__(self, "encoding", encoding)
        object.__setattr__(self, "n", len(up_degrees))

    @cached_property
    def _parsed(self):
        return _parse(self.encoding)

    @property
    def size(self) -> int:
        """Number ``n`` of non-root vertices."""
        return self.n

    @property
    def vertex_count(self) -> int:
        """Total number of vertices, ``n + 1``."""
        return self.n + 1

    @property
    def root(self) -> int:
        """The root, which is the dominating vertex ``0``."""
        return 0

    @cached_property
    def up_degrees(self) -> tuple[int, ...]:
        """``up_degrees[i]`` is the number of neighbours of ``i`` above ``i``."""
        return self._parsed[0]

    @cached_property
    def parents(self) -> tuple[int, ...]:
        """``parents[j - 1]`` is the parent of ``j`` in the tree."""
        return self._parsed[1]

    @cached_property
    def degrees(self) -> tuple[int, ...]:
        """Degrees in the graph, weakly decreasing (reverse degree labelling)."""
        n = self.n
        up = self.up_degrees
        difference = [0] * (n + 2)
        for vertex in range(n):
            if up[vertex]:
                difference[vertex + 1] += 1
                difference[vertex + up[vertex] + 1] -= 1
        out = []
        running = 0
        for vertex in range(n + 1):
            running += difference[vertex]
            out.append(running + (up[vertex] if vertex < n else 0))
        return tuple(out)

    def adjacent(self, i: int, j: int) -> bool:
        """Whether ``i`` and ``j`` are adjacent in the graph."""
        return _adjacent(self.up_degrees, i, j)

    def neighbours(self, i: int) -> tuple[int, ...]:
        """The neighbours of ``i`` in the graph, increasing."""
        up = self.up_degrees
        below = [j for j in range(i) if i <= j + up[j]]
        above = list(range(i + 1, i + up[i] + 1)) if i < self.n else []
        return tuple(below + above)

    @cached_property
    def edges(self) -> tuple[tuple[int, int], ...]:
        """Every edge ``(i, j)`` with ``i < j``; quadratic in ``n`` when dense."""
        up = self.up_degrees
        return tuple(
            (i, j) for i in range(self.n) for j in range(i + 1, i + up[i] + 1)
        )

    @cached_property
    def children(self) -> dict[int, tuple[int, ...]]:
        """Children of every vertex in the tree."""
        out: dict[int, list[int]] = {i: [] for i in range(self.n + 1)}
        for vertex, parent in enumerate(self.parents, start=1):
            out[parent].append(vertex)
        return {vertex: tuple(items) for vertex, items in out.items()}

    def ancestors(self, vertex: int) -> tuple[int, ...]:
        """The proper ancestors of ``vertex``, nearest first, ending at ``0``."""
        chain = []
        current = self.parents[vertex - 1] if vertex else 0
        while current:
            chain.append(current)
            current = self.parents[current - 1]
        if vertex:
            chain.append(0)
        return tuple(chain)

    @cached_property
    def height(self) -> dict[int, int]:
        """Distance from each vertex to the root."""
        out = {0: 0}
        for vertex in range(1, self.n + 1):
            chain = []
            current = vertex
            while current not in out:
                chain.append(current)
                current = self.parents[current - 1]
            for step, node in enumerate(reversed(chain), start=1):
                out[node] = out[current] + step
        return out

    @cached_property
    def subtree_sizes(self) -> dict[int, int]:
        """Number of descendants of each vertex, including itself."""
        out = {vertex: 1 for vertex in range(self.n + 1)}
        for vertex in sorted(range(1, self.n + 1), key=lambda v: -self.height[v]):
            out[self.parents[vertex - 1]] += out[vertex]
        return out

    def is_increasing(self) -> bool:
        """Whether the tree has no inversions."""
        return all(
            self.parents[vertex - 1] < vertex for vertex in range(1, self.n + 1)
        )

    def inv(self) -> int:
        """The number of inversions, in ``O(n log n)`` time.

        A Fenwick tree stores the labels on the current root-to-vertex path.
        For each vertex, its contribution is the number of active ancestors
        whose labels are larger than its own.
        """
        children: list[list[int]] = [[] for _ in range(self.n + 1)]
        for vertex, parent in enumerate(self.parents, start=1):
            children[parent].append(vertex)

        frequencies = [0] * (self.n + 2)

        def update(label: int, delta: int) -> None:
            index = label + 1
            while index < len(frequencies):
                frequencies[index] += delta
                index += index & -index

        def prefix_count(label: int) -> int:
            count = 0
            index = label + 1
            while index:
                count += frequencies[index]
                index -= index & -index
            return count

        total = 0
        stack = [(0, 0, False)]
        while stack:
            vertex, depth, exiting = stack.pop()
            if exiting:
                update(vertex, -1)
                continue
            total += depth - prefix_count(vertex)
            update(vertex, 1)
            stack.append((vertex, depth, True))
            stack.extend(
                (child, depth + 1, False)
                for child in reversed(children[vertex])
            )
        return total

    def to_jsonable(self) -> str:
        return self.encoding


def threshold_tree_size(encoding_or_object) -> int:
    """Number of non-root vertices."""
    if isinstance(encoding_or_object, ThresholdSpanningTree):
        return encoding_or_object.n
    up_text = encoding_or_object.split(SEPARATOR)[0]
    return up_text.count(",") + 1


def threshold_up_degrees(n: int, subset) -> tuple[int, ...]:
    """Up-degrees of the connected threshold graph indexed by ``subset``.

    ``subset`` is any subset of ``{1, ..., n-1}``; together with the forced
    ``u_0 = n`` its elements are the positive up-degrees in decreasing order.
    """
    if type(n) is not int or n < 1:
        raise ValueError("a threshold graph fiber needs n >= 1")
    subset = tuple(subset)
    if (
        any(type(value) is not int or not 1 <= value < n for value in subset)
        or len(set(subset)) != len(subset)
    ):
        raise ValueError("subset must contain distinct integers from 1 through n - 1")
    values = [n, *sorted(subset, reverse=True)]
    return tuple(values + [0] * (n - len(values)))


def iter_threshold_graphs(n: int) -> Iterator[tuple[int, ...]]:
    """Every connected threshold graph on ``{0, ..., n}``, as up-degrees."""
    if n < 1:
        raise ValueError("a threshold graph fiber needs n >= 1")
    pool = range(1, n)
    for size in range(len(pool) + 1):
        for subset in combinations(pool, size):
            yield threshold_up_degrees(n, subset)


def iter_threshold_spanning_trees(up_degrees) -> Iterator[ThresholdSpanningTree]:
    """Yield every spanning tree of the graph, rooted at ``0``."""
    up_degrees = tuple(int(value) for value in up_degrees)
    if not is_threshold_up_degrees(up_degrees):
        raise ValueError(f"not a connected threshold graph: {up_degrees}")
    n = len(up_degrees)
    parents = [0] * (n + 1)
    options = {
        vertex: [other for other in range(n + 1) if _adjacent(up_degrees, vertex, other)]
        for vertex in range(1, n + 1)
    }

    def closes_cycle(vertex: int) -> bool:
        current = parents[vertex]
        for _ in range(n + 1):
            if current == 0:
                return False
            current = parents[current]
        return True

    def rec(vertex: int) -> Iterator[ThresholdSpanningTree]:
        if vertex > n:
            yield ThresholdSpanningTree(
                _encode(up_degrees, parents[1:]), validate=False
            )
            return
        for parent in options[vertex]:
            parents[vertex] = parent
            if not closes_cycle(vertex):
                yield from rec(vertex + 1)
        parents[vertex] = 0

    yield from rec(1)


def threshold_spanning_tree_count(up_degrees) -> int:
    """Number of spanning trees of the graph."""
    return sum(1 for _ in iter_threshold_spanning_trees(up_degrees))


def canonical_threshold_spanning_tree(up_degrees) -> ThresholdSpanningTree:
    """The star rooted at ``0``, valid for every connected threshold graph.

    Vertex ``0`` dominates, so attaching every other vertex directly to it is
    always a spanning tree, obtained without enumerating the fiber.
    """
    up_degrees = tuple(int(value) for value in up_degrees)
    if not is_threshold_up_degrees(up_degrees):
        raise ValueError(f"not a connected threshold graph: {up_degrees}")
    return ThresholdSpanningTree(
        _encode(up_degrees, [0] * len(up_degrees)), validate=False
    )
