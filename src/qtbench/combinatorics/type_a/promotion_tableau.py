"""Standard Young tableaux of rectangular or staircase shape, for the promotion task.

Schuetzenberger promotion ``d`` acts on ``SYT(lambda)``. For a rectangle
``lambda = c^r`` it has order ``N = rc``, and for a staircase
``sc_k = (k, k-1, ..., 1)`` the relevant cyclic group is ``Z/N`` with
``N = k(k+1) = 2|sc_k|``, the order of promotion on the rectangle
``SYT(k^{k+1})`` that ``SYT(sc_k)`` embeds into promotion-equivariantly
(Pon--Wang). Grouping ``SYT(lambda)`` into ``<d>``-orbits gives the least-degree
cyclic sieving polynomial

    C_lambda(q) = sum_{orbits O} (1 + q^{N/|O|} + ... + q^{(|O|-1)N/|O|}),

and the discovery task is a statistic on ``SYT(lambda)`` whose generating function
is ``C_lambda(q)``. On rectangles that statistic is known -- ``(maj - n(lambda))``
reduced mod ``N``, by Rhoades' theorem -- and on staircases it is open.

An object of this family is one such tableau; the fiber it is graded in is its
shape, read off the object. Tableaux use English notation (``rows[0]`` is the
longest row), entries increase left to right along rows and top to bottom down
columns, and the canonical encoding is the rows separated by ``"/"``::

    1,2,3/4,5/6

is the tableau of staircase shape ``sc_3 = (3, 2, 1)`` with first row ``1 2 3``.

Promotion itself is deliberately not exposed here. The task asks for an *intrinsic*
statistic -- one built from descents, diagonals or local patterns -- and a
construction that walks the promotion orbit to read off a position in it is not that.
Not exposing promotion makes such a construction conspicuous in a submission's source;
it does not prevent it, and `problem.md` says so.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
from typing import Iterator

from .kostka_tableau import is_partition, iter_standard_tableau_rows

ROW_SEPARATOR = "/"

PromotionTableauWord = str


def _parse(encoding: str) -> tuple[tuple[int, ...], ...]:
    return tuple(
        tuple(int(piece) for piece in field.split(","))
        for field in encoding.split(ROW_SEPARATOR)
    )


def _encode(rows) -> str:
    return ROW_SEPARATOR.join(",".join(str(value) for value in row) for row in rows)


def is_promotion_shape(shape) -> bool:
    """Whether ``shape`` is a rectangle ``c^r`` or a staircase ``sc_k``, both nontrivial.

    Single rows and single columns are excluded: their tableau set is a singleton,
    so they carry no information. The two families are disjoint once ``k >= 2``.
    """
    if not is_partition(shape) or len(shape) < 2 or shape[0] < 2:
        return False
    rectangle = len(set(shape)) == 1
    staircase = tuple(shape) == tuple(range(len(shape), 0, -1))
    return rectangle or staircase


def promotion_modulus(shape) -> int:
    """``N``: the order of the cyclic group acting by promotion on ``SYT(shape)``.

    ``rc`` for a rectangle ``c^r`` (Haiman: ``d^{rc} = id``), and ``k(k+1)``, twice
    the number of cells, for a staircase ``sc_k``.
    """
    if not is_promotion_shape(shape):
        raise ValueError(f"not a rectangular or staircase shape: {tuple(shape)!r}")
    if len(set(shape)) == 1:
        return shape[0] * len(shape)
    return len(shape) * (len(shape) + 1)


def is_promotion_tableau(encoding: str) -> bool:
    """Whether ``encoding`` is a standard Young tableau of a valid shape."""
    if not isinstance(encoding, str) or not encoding:
        return False
    try:
        rows = _parse(encoding)
    except ValueError:
        return False
    shape = tuple(len(row) for row in rows)
    if not is_promotion_shape(shape):
        return False
    cells = sum(shape)
    if sorted(value for row in rows for value in row) != list(range(1, cells + 1)):
        return False
    if any(row[c - 1] >= row[c] for row in rows for c in range(1, len(row))):
        return False
    return all(
        rows[r - 1][c] < rows[r][c]
        for r in range(1, len(rows))
        for c in range(len(rows[r]))
    )


@dataclass(frozen=True, init=False)
class PromotionTableau:
    """A standard Young tableau of rectangular or staircase shape.

    Encoded as the rows separated by ``"/"``. Public benchmark code exposes the
    tableau, its shape and modulus, and the classical descent statistics; the
    graded statistic of the target belongs to the discovery task.
    """

    encoding: str
    rows: tuple[tuple[int, ...], ...]
    n: int

    def __init__(self, encoding: str, *, validate: bool = True) -> None:
        if validate and not is_promotion_tableau(encoding):
            raise ValueError(f"not a promotion-task standard Young tableau: {encoding!r}")
        rows = _parse(encoding)
        object.__setattr__(self, "encoding", encoding)
        object.__setattr__(self, "rows", rows)
        object.__setattr__(self, "n", sum(len(row) for row in rows))

    @property
    def size(self) -> int:
        """Number of cells, ``n``."""
        return self.n

    @cached_property
    def shape(self) -> tuple[int, ...]:
        """The partition ``lambda``, the fiber index."""
        return tuple(len(row) for row in self.rows)

    @cached_property
    def is_rectangle(self) -> bool:
        """Whether the shape is a rectangle ``c^r``, the solved family."""
        return len(set(self.shape)) == 1

    @cached_property
    def is_staircase(self) -> bool:
        """Whether the shape is a staircase ``sc_k``, the open family."""
        return self.shape == tuple(range(len(self.shape), 0, -1))

    @cached_property
    def modulus(self) -> int:
        """``N``, the order of the promotion group: values below it suffice."""
        return promotion_modulus(self.shape)

    @cached_property
    def cells(self) -> tuple[tuple[int, int], ...]:
        """``cells[v - 1] = (row, column)`` of the entry ``v``, both 1-based."""
        positions = [(0, 0)] * self.n
        for r, row in enumerate(self.rows, start=1):
            for c, value in enumerate(row, start=1):
                positions[value - 1] = (r, c)
        return tuple(positions)

    def descent_set(self) -> tuple[int, ...]:
        """``{i : i + 1 lies strictly below i}``, increasing."""
        cells = self.cells
        return tuple(i for i in range(1, self.n) if cells[i][0] > cells[i - 1][0])

    def maj(self) -> int:
        """The major index ``sum_{i in Des(T)} i``."""
        return sum(self.descent_set())

    def comaj(self) -> int:
        """The comajor index ``sum_{i in Des(T)} (n - i)``."""
        return sum(self.n - i for i in self.descent_set())

    def shape_charge(self) -> int:
        """``n(lambda) = sum_i (i - 1) lambda_i``, the shift in the rectangular answer."""
        return sum(index * part for index, part in enumerate(self.shape))

    def to_jsonable(self) -> str:
        return self.encoding


def promotion_tableau(rows, *, validate: bool = True) -> PromotionTableau:
    """Build the object from its rows."""
    return PromotionTableau(_encode(rows), validate=validate)


def promotion_tableau_size(encoding_or_object) -> int:
    """Number of cells (module-level, for the value and resource gates)."""
    if isinstance(encoding_or_object, PromotionTableau):
        return encoding_or_object.n
    return sum(
        len(field.split(",")) for field in encoding_or_object.split(ROW_SEPARATOR)
    )


# ---------------------------------------------------------------------------
# Enumeration
# ---------------------------------------------------------------------------


def iter_promotion_tableaux_for_shape(shape) -> Iterator[PromotionTableau]:
    """Yield every standard Young tableau of the given rectangular or staircase shape."""
    shape = tuple(shape)
    if not is_promotion_shape(shape):
        raise ValueError(f"not a rectangular or staircase shape: {shape!r}")
    for rows in iter_standard_tableau_rows(shape):
        yield PromotionTableau(_encode(rows), validate=False)


def staircase_shape(k: int) -> tuple[int, ...]:
    """``sc_k = (k, k - 1, ..., 1)``."""
    if k < 2:
        raise ValueError("staircase shapes start at k = 2")
    return tuple(range(k, 0, -1))


def rectangle_shape(columns: int, rows: int) -> tuple[int, ...]:
    """The rectangle ``columns^rows``, with both sides at least ``2``."""
    if columns < 2 or rows < 2:
        raise ValueError("rectangular shapes need both sides at least 2")
    return tuple([columns] * rows)


def canonical_promotion_tableau(shape, *, by_columns: bool = False) -> PromotionTableau:
    """A single tableau of the shape, built without enumerating ``SYT(shape)``.

    The row-superstandard tableau numbers the rows left to right, top to bottom;
    ``by_columns`` numbers the columns instead. Both are standard and their descent
    sets are the two extremes, so the resource and value gates can probe large
    shapes cheaply.
    """
    shape = tuple(shape)
    if not is_promotion_shape(shape):
        raise ValueError(f"not a rectangular or staircase shape: {shape!r}")
    rows: list[list[int]] = [[0] * part for part in shape]
    value = 1
    if by_columns:
        for c in range(shape[0]):
            for r, part in enumerate(shape):
                if part > c:
                    rows[r][c] = value
                    value += 1
    else:
        for r, part in enumerate(shape):
            for c in range(part):
                rows[r][c] = value
                value += 1
    return PromotionTableau(_encode(rows), validate=False)
