"""Natural unit interval graphs (``Dyck graphs``) with ``G``-nondescent permutations.

Following the reformulation of the Shareshian--Wachs conjecture (see the problem
statement for references), a **Dyck graph** ``G = ([n], E)`` is a natural unit
interval graph: ``E`` is a set of edges ``(i, j)`` with ``1 <= i < j <= n`` such
that whenever ``(i, j) in E`` also ``(k, j) in E`` for ``i <= k < j`` and
``(i, h) in E`` for ``i < h <= j``. Such graphs are parametrised by their
right-endpoint vector ``b = (b_1, ..., b_n)`` with ``i <= b_i <= n`` and ``b``
weakly increasing, where ``(i, j) in E`` (for ``i < j``) exactly when ``j <= b_i``.
There are ``C_n`` (Catalan) of them, one per Dyck path of size ``n``.

For a permutation ``sigma = sigma_1 ... sigma_n`` in one-line notation, put

    DesTilde_G(sigma) = { i in [n-1] : sigma_i > sigma_{i+1} and (sigma_{i+1}, sigma_i) not in E },
    D_G^0            = { sigma in S_n : DesTilde_G(sigma) = empty },
    invTilde_G(sigma) = #{ (i, j) : i < j, sigma_i > sigma_j, (sigma_j, sigma_i) in E }.

The benchmark object is a pair ``(G, sigma)`` with ``sigma in D_G^0``; the public
statistic is ``ginv = invTilde_G`` and the discovery task is the (partition-valued)
``theta`` partner realising the Shareshian--Wachs ``e``-expansion. Public code
exposes only the graph structure, the permutation, and ``ginv``.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from functools import cached_property
from itertools import permutations
from typing import Iterator

SEPARATOR = "|"

UnitIntervalGraphWord = str


def edges_from_b(b: tuple[int, ...]) -> frozenset[tuple[int, int]]:
    """Edge set ``{(i, j) : i < j, j <= b_i}`` of the graph with right-ends ``b``."""
    n = len(b)
    return frozenset(
        (i, j) for i in range(1, n + 1) for j in range(i + 1, b[i - 1] + 1)
    )


def is_dyck_graph_vector(b: tuple[int, ...]) -> bool:
    """Whether ``b`` is a valid right-endpoint vector: ``i <= b_i <= n``, weakly up."""
    if not isinstance(b, Sequence) or isinstance(b, (str, bytes, bytearray)):
        return False
    n = len(b)
    if n == 0:
        return False
    previous = 0
    for i in range(1, n + 1):
        bi = b[i - 1]
        if type(bi) is not int or bi < i or bi > n or bi < previous:
            return False
        previous = bi
    return True


def _g_descents_empty(perm: tuple[int, ...], b: tuple[int, ...]) -> bool:
    """True iff ``DesTilde_G(perm)`` is empty (``perm`` lies in ``D_G^0``).

    A ``G``-descent is a position ``i`` with ``perm_i > perm_{i+1}`` and no edge
    between ``perm_{i+1} < perm_i`` (i.e. ``perm_i > b_{perm_{i+1}}``).
    """
    for i in range(len(perm) - 1):
        higher, lower = perm[i], perm[i + 1]
        if higher > lower and higher > b[lower - 1]:
            return False
    return True


def _ginv(perm: tuple[int, ...], b: tuple[int, ...]) -> int:
    """``invTilde_G(perm)``: inversions ``perm_i > perm_j`` (``i < j``) whose values are adjacent."""
    n = len(perm)
    count = 0
    for i in range(n):
        higher = perm[i]
        for j in range(i + 1, n):
            lower = perm[j]
            if higher > lower and higher <= b[lower - 1]:
                count += 1
    return count


def _parse(encoding: str) -> tuple[tuple[int, ...], tuple[int, ...]]:
    b_text, perm_text = encoding.split(SEPARATOR)
    b = tuple(int(piece) for piece in b_text.split(",")) if b_text else ()
    perm = tuple(int(piece) for piece in perm_text.split(",")) if perm_text else ()
    return b, perm


def is_unit_interval_graph_permutation(encoding: str) -> bool:
    """Whether ``encoding`` is a valid ``b|perm`` object with ``perm in D_G^0``."""
    if not isinstance(encoding, str) or encoding.count(SEPARATOR) != 1:
        return False
    b_text, perm_text = encoding.split(SEPARATOR)
    try:
        b = tuple(int(piece) for piece in b_text.split(",")) if b_text else ()
        perm = tuple(int(piece) for piece in perm_text.split(",")) if perm_text else ()
    except ValueError:
        return False
    if len(b) != len(perm) or not is_dyck_graph_vector(b):
        return False
    if sorted(perm) != list(range(1, len(perm) + 1)):
        return False
    return _g_descents_empty(perm, b)


def _encode(b: tuple[int, ...], perm: tuple[int, ...]) -> str:
    b_text = ",".join(str(v) for v in b)
    perm_text = ",".join(str(v) for v in perm)
    return f"{b_text}{SEPARATOR}{perm_text}"


@dataclass(frozen=True, init=False)
class UnitIntervalGraphPermutation:
    """A Dyck graph ``G`` together with a ``G``-nondescent permutation ``sigma``.

    Encoded as ``b + "|" + perm`` where ``b`` is the comma-separated right-endpoint
    vector of ``G`` (edge ``(i, j)`` with ``i < j`` present iff ``j <= b_i``) and
    ``perm`` is the comma-separated one-line notation of ``sigma`` (a permutation of
    ``1..n`` with ``DesTilde_G(sigma)`` empty). Public benchmark code exposes the
    graph, the permutation, and the ``ginv`` statistic; the partition-valued
    ``theta`` partner belongs to the discovery task.
    """

    encoding: str
    n: int

    def __init__(self, encoding: str, *, validate: bool = True) -> None:
        if validate and not is_unit_interval_graph_permutation(encoding):
            raise ValueError(f"not a Dyck graph / G-nondescent permutation: {encoding!r}")
        b_text = encoding.split(SEPARATOR)[0]
        object.__setattr__(self, "encoding", encoding)
        object.__setattr__(self, "n", len(b_text.split(",")) if b_text else 0)

    @property
    def size(self) -> int:
        """Number of vertices ``n``."""
        return self.n

    @cached_property
    def _parsed(self) -> tuple[tuple[int, ...], tuple[int, ...]]:
        return _parse(self.encoding)

    @cached_property
    def b(self) -> tuple[int, ...]:
        """Right-endpoint vector of ``G``: ``b_i = max{ j : (i, j) in E }`` (or ``i``)."""
        return self._parsed[0]

    @cached_property
    def perm(self) -> tuple[int, ...]:
        """One-line notation ``(sigma_1, ..., sigma_n)`` (values ``1..n``)."""
        return self._parsed[1]

    @cached_property
    def edges(self) -> frozenset[tuple[int, int]]:
        """Edge set of ``G`` as pairs ``(i, j)`` with ``i < j``."""
        return edges_from_b(self.b)

    def ginv(self) -> int:
        """``invTilde_G(sigma)``: adjacent inversions of ``sigma`` under ``G`` (the known statistic)."""
        return _ginv(self.perm, self.b)

    def to_jsonable(self) -> str:
        return self.encoding


def unit_interval_graph_permutation(
    b: tuple[int, ...], perm: tuple[int, ...], *, validate: bool = True
) -> UnitIntervalGraphPermutation:
    """Build the object ``(G, sigma)`` from a graph vector ``b`` and permutation ``perm``."""
    return UnitIntervalGraphPermutation(_encode(b, perm), validate=validate)


def unit_interval_graph_permutation_ginv(encoding: str) -> int:
    """``ginv`` of the object given by ``encoding``."""
    b, perm = _parse(encoding)
    return _ginv(perm, b)


def unit_interval_graph_permutation_size(encoding_or_object) -> int:
    """Size ``n`` (module-level, for the value/resource gate)."""
    if isinstance(encoding_or_object, UnitIntervalGraphPermutation):
        return encoding_or_object.n
    b_text = encoding_or_object.split(SEPARATOR)[0]
    return len(b_text.split(",")) if b_text else 0


# ---------------------------------------------------------------------------
# Enumeration
# ---------------------------------------------------------------------------


def iter_dyck_graph_vectors(n: int) -> Iterator[tuple[int, ...]]:
    """Yield the right-endpoint vector of every Dyck graph on ``[n]`` (``C_n`` of them)."""
    if n < 1:
        raise ValueError("size must be positive")

    def rec(i: int, previous: int, acc: list[int]) -> Iterator[tuple[int, ...]]:
        if i > n:
            yield tuple(acc)
            return
        for bi in range(max(i, previous), n + 1):
            acc.append(bi)
            yield from rec(i + 1, bi, acc)
            acc.pop()

    yield from rec(1, 1, [])


def iter_uig_permutations_for_vector(b: tuple[int, ...]) -> Iterator[UnitIntervalGraphPermutation]:
    """Yield ``(G, sigma)`` for every ``sigma in D_G^0`` of the graph with vector ``b``."""
    n = len(b)
    for perm in permutations(range(1, n + 1)):
        if _g_descents_empty(perm, b):
            yield UnitIntervalGraphPermutation(_encode(b, perm), validate=False)


def iter_unit_interval_graph_permutations(n: int) -> Iterator[UnitIntervalGraphPermutation]:
    """Yield every size-``n`` object ``(G, sigma)`` (all Dyck graphs, all of ``D_G^0``)."""
    if n < 1:
        raise ValueError("size must be positive")
    for b in iter_dyck_graph_vectors(n):
        yield from iter_uig_permutations_for_vector(b)


def unit_interval_graph_permutation_count(n: int) -> int:
    """Total number of size-``n`` objects; equals the double factorial ``(2n-1)!!``."""
    return sum(1 for _ in iter_unit_interval_graph_permutations(n))


def canonical_unit_interval_graph_permutation(b: tuple[int, ...]) -> UnitIntervalGraphPermutation:
    """The object ``(G, identity)`` for the graph with vector ``b``.

    The identity permutation has no descents at all, so it lies in ``D_G^0`` for
    every ``G``; this builds a single valid large object for the resource and
    value gates without enumerating the (exponential) fiber ``D_G^0``.
    """
    if not is_dyck_graph_vector(b):
        raise ValueError(f"not a Dyck graph vector: {b!r}")
    identity = tuple(range(1, len(b) + 1))
    return UnitIntervalGraphPermutation(_encode(b, identity), validate=False)
