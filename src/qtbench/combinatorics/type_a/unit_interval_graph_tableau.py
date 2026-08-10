"""Dyck graphs paired with standard Young tableaux, for the unicellular LLT task.

For a Dyck graph (natural unit interval graph) ``G = ([n], E)`` the unicellular
LLT polynomial is

    LLT_G(X; q) = sum_{kappa : [n] -> Z_{>0}} q^{asc_G(kappa)} x_kappa,

the sum over *all* colourings (no properness condition), with
``asc_G(kappa) = #{ (i, j) in E : i < j, kappa(i) < kappa(j) }``. It is a
symmetric function and is Schur positive, so

    LLT_G(X; q) = sum_{lambda |- n} c_lambda^G(q) s_lambda(X),

and at ``q = 1`` it degenerates to ``p_1^n``, whence
``c_lambda^G(1) = f^lambda = |SYT(lambda)|``. The discovery task is a statistic
``lltstat_G`` on ``SYT(lambda)`` whose generating function is ``c_lambda^G(q)``.

An object of this family is therefore a pair ``(G, T)`` with ``T`` a standard
Young tableau with ``n`` cells; the partition ``lambda`` is the shape of ``T``.
Tableaux use English notation: ``rows[0]`` is the longest row, entries increase
left to right along rows and top to bottom down columns.

The canonical encoding is ``b + "|" + rows``, with ``b`` the comma-separated
right-endpoint vector of ``G`` (edge ``(i, j)`` with ``i < j`` present iff
``j <= b_i``) and the rows of ``T`` separated by ``"/"``. For example ::

    2,4,4,4|1,2,3/4

is the graph ``G = ([4], {(1,2),(2,3),(2,4),(3,4)})`` paired with the tableau of
shape ``lambda = (3, 1)`` whose first row is ``1 2 3`` and second row is ``4``.

No statistic on this family is public: the single graded statistic is the whole
task. The classical descent set and its major index are exposed here because
they are the answer at the two extreme graphs (``maj`` for the complete graph,
``0`` for the empty one).
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
from typing import Iterator

from .kostka_tableau import (
    is_partition,
    iter_partitions,
    iter_standard_tableau_rows,
    kostka_standard_tableau_count,
)
from .unit_interval_graph import edges_from_b, is_dyck_graph_vector, iter_dyck_graph_vectors

SEPARATOR = "|"
ROW_SEPARATOR = "/"

UnitIntervalGraphTableauWord = str


def _parse(encoding: str):
    b_text, rows_text = encoding.split(SEPARATOR)
    b = tuple(int(piece) for piece in b_text.split(","))
    rows = tuple(
        tuple(int(piece) for piece in field.split(","))
        for field in rows_text.split(ROW_SEPARATOR)
    )
    return b, rows


def _encode(b, rows) -> str:
    head = ",".join(str(value) for value in b)
    body = ROW_SEPARATOR.join(",".join(str(value) for value in row) for row in rows)
    return f"{head}{SEPARATOR}{body}"


def is_unit_interval_graph_tableau(encoding: str) -> bool:
    """Whether ``encoding`` is a valid ``b|rows`` pair with ``|b| = |T|``."""
    if not isinstance(encoding, str) or encoding.count(SEPARATOR) != 1:
        return False
    try:
        b, rows = _parse(encoding)
    except ValueError:
        return False
    shape = tuple(len(row) for row in rows)
    if not is_dyck_graph_vector(b) or not is_partition(shape):
        return False
    if len(b) != sum(shape):
        return False
    if sorted(value for row in rows for value in row) != list(range(1, sum(shape) + 1)):
        return False
    if any(row[c - 1] >= row[c] for row in rows for c in range(1, len(row))):
        return False
    return all(
        rows[r - 1][c] < rows[r][c]
        for r in range(1, len(rows))
        for c in range(len(rows[r]))
    )


@dataclass(frozen=True, init=False)
class UnitIntervalGraphTableau:
    """A Dyck graph ``G`` paired with a standard Young tableau ``T`` of ``n`` cells.

    Encoded as ``b + "|" + rows``; ``b`` is the comma-separated right-endpoint
    vector of ``G`` and the rows of ``T`` are separated by ``"/"``. Public
    benchmark code exposes the graph, the tableau and the classical descent
    statistics; the graded statistic of the target belongs to the discovery task.
    """

    encoding: str
    b: tuple[int, ...]
    rows: tuple[tuple[int, ...], ...]
    n: int

    def __init__(self, encoding: str, *, validate: bool = True) -> None:
        if validate and not is_unit_interval_graph_tableau(encoding):
            raise ValueError(f"not a Dyck graph / standard Young tableau pair: {encoding!r}")
        b, rows = _parse(encoding)
        object.__setattr__(self, "encoding", encoding)
        object.__setattr__(self, "b", b)
        object.__setattr__(self, "rows", rows)
        object.__setattr__(self, "n", len(b))

    @property
    def size(self) -> int:
        """Number of vertices and of cells, ``n``."""
        return self.n

    @cached_property
    def shape(self) -> tuple[int, ...]:
        """The partition ``lambda``, the shape of ``T``."""
        return tuple(len(row) for row in self.rows)

    @cached_property
    def edges(self) -> frozenset[tuple[int, int]]:
        """Edge set of ``G`` as pairs ``(i, j)`` with ``i < j``."""
        return edges_from_b(self.b)

    @cached_property
    def cells(self) -> tuple[tuple[int, int], ...]:
        """``cells[v - 1] = (row, column)`` of the entry ``v``, both 1-based."""
        positions = [(0, 0)] * self.n
        for r, row in enumerate(self.rows, start=1):
            for c, value in enumerate(row, start=1):
                positions[value - 1] = (r, c)
        return tuple(positions)

    def descent_set(self) -> tuple[int, ...]:
        """``{i : i + 1 lies strictly below i in T}``, increasing."""
        cells = self.cells
        return tuple(i for i in range(1, self.n) if cells[i][0] > cells[i - 1][0])

    def maj(self) -> int:
        """The major index ``sum_{i in Des(T)} i``."""
        return sum(self.descent_set())

    def comaj(self) -> int:
        """The comajor index ``sum_{i in Des(T)} (n - i)``."""
        return sum(self.n - i for i in self.descent_set())

    def to_jsonable(self) -> str:
        return self.encoding


def unit_interval_graph_tableau(
    b: tuple[int, ...], rows, *, validate: bool = True
) -> UnitIntervalGraphTableau:
    """Build the object ``(G, T)`` from a graph vector ``b`` and the rows of ``T``."""
    return UnitIntervalGraphTableau(_encode(b, rows), validate=validate)


def unit_interval_graph_tableau_size(encoding_or_object) -> int:
    """Size ``n`` (module-level, for the value and resource gates)."""
    if isinstance(encoding_or_object, UnitIntervalGraphTableau):
        return encoding_or_object.n
    return len(encoding_or_object.split(SEPARATOR)[0].split(","))


# ---------------------------------------------------------------------------
# Enumeration
# ---------------------------------------------------------------------------


def iter_uig_tableaux_for_vector(b: tuple[int, ...]) -> Iterator[UnitIntervalGraphTableau]:
    """Yield ``(G, T)`` for every standard Young tableau ``T`` with ``n = |b|`` cells."""
    if not is_dyck_graph_vector(b):
        raise ValueError(f"not a Dyck graph vector: {b!r}")
    for lam in iter_partitions(len(b)):
        for rows in iter_standard_tableau_rows(lam):
            yield UnitIntervalGraphTableau(_encode(b, rows), validate=False)


def iter_unit_interval_graph_tableaux(n: int) -> Iterator[UnitIntervalGraphTableau]:
    """Yield every size-``n`` object ``(G, T)`` (all Dyck graphs, all tableaux)."""
    if n < 1:
        raise ValueError("size must be positive")
    for b in iter_dyck_graph_vectors(n):
        yield from iter_uig_tableaux_for_vector(b)


def unit_interval_graph_tableau_count(n: int) -> int:
    """Total number of size-``n`` objects: ``C_n`` times the number of involutions."""
    tableaux = sum(kostka_standard_tableau_count(lam) for lam in iter_partitions(n))
    return sum(1 for _ in iter_dyck_graph_vectors(n)) * tableaux


def canonical_unit_interval_graph_tableau(
    b: tuple[int, ...], lam: tuple[int, ...], *, by_columns: bool = False
) -> UnitIntervalGraphTableau:
    """A single valid ``(G, T)`` built without enumerating ``SYT(lambda)``.

    The row-superstandard tableau numbers the rows left to right, top to bottom;
    ``by_columns`` numbers the columns instead. Both are standard, and the two
    have opposite extreme descent sets, so the resource and value gates can probe
    large graphs and shapes cheaply.
    """
    if not is_dyck_graph_vector(b):
        raise ValueError(f"not a Dyck graph vector: {b!r}")
    if not is_partition(lam) or sum(lam) != len(b):
        raise ValueError("shape must be a partition of the number of vertices")
    rows: list[list[int]] = [[0] * part for part in lam]
    value = 1
    if by_columns:
        for c in range(lam[0]):
            for r, part in enumerate(lam):
                if part > c:
                    rows[r][c] = value
                    value += 1
    else:
        for r, part in enumerate(lam):
            for c in range(part):
                rows[r][c] = value
                value += 1
    return UnitIntervalGraphTableau(_encode(b, rows), validate=False)
