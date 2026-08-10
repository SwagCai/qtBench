"""Standard multi-labelled ``k^n`` Dyck paths and their area.

Following Bergeron, Haglund, Iraci and Romero (see the problem statement for
references), a *multi-labelled* ``k^n`` Dyck path is a pair ``(pi, w)`` where

* ``pi`` is a ``kn x n`` Dyck path: a lattice path of ``n`` North and ``kn`` East
  unit steps from ``(0, 0)`` to ``(kn, n)`` staying weakly above the main
  diagonal ``ky = x``, and
* ``w = (w_1, ..., w_n)`` is a word of ``(k+1)``-tuples of positive integers such
  that the number of weak descents at position ``i`` is at most the number of
  East steps between the ``i``-th and the ``(i+1)``-th North step:

      #{ j : w_{i,j} >= w_{i+1,j} } <= col(i+1) - col(i),

  where ``col(i)`` is the ``x``-coordinate of the ``i``-th North step.

``LD_{k^n}`` denotes this set. A **standard** multi-labelling has each of the
``k + 1`` label rows ``w_{*,j} = (w_{1,j}, ..., w_{n,j})`` a permutation of
``[n]``; those are the objects selected by pairing the symmetric function with
``e_{1^n}`` in each of the ``k + 1`` sets of variables. Distinct labels turn the
weak descents into strict ones.

The public statistic is the ``area``: the number of whole lattice cells between
``pi`` and the main diagonal,

    area(pi) = sum_i ( k (i - 1) - col(i) ).

The joint distribution of ``area`` and the unknown partner is the Hilbert series
``<nabla_*^k e_n, e_{1^n} tensor ... tensor e_{1^n}>``; ``area`` is public and the
``t``-partner is the object of the discovery task.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import cache, cached_property
from itertools import permutations, product
from typing import Iterator

SEPARATOR = "|"

MultiLabelledDyckWord = str


def _columns_from_path(path: str) -> tuple[int, ...]:
    """``x``-coordinate of each North step, in step order."""
    columns = []
    x = 0
    for step in path:
        if step == "N":
            columns.append(x)
        else:
            x += 1
    return tuple(columns)


def _path_from_columns(columns, total_east: int) -> str:
    pieces = []
    previous = 0
    for column in columns:
        pieces.append("E" * (column - previous))
        pieces.append("N")
        previous = column
    pieces.append("E" * (total_east - previous))
    return "".join(pieces)


def _parse(encoding: str):
    fields = encoding.split(SEPARATOR)
    path = fields[0]
    rows = tuple(
        tuple(int(piece) for piece in field.split(",")) if field else ()
        for field in fields[1:]
    )
    return path, rows


def _encode(path: str, rows) -> str:
    body = SEPARATOR.join(",".join(str(value) for value in row) for row in rows)
    return f"{path}{SEPARATOR}{body}"


def is_multi_labelled_dyck_path(encoding: str) -> bool:
    """Whether ``encoding`` is a valid ``path|row_0|...|row_k`` standard object."""
    if not isinstance(encoding, str) or SEPARATOR not in encoding:
        return False
    try:
        path, rows = _parse(encoding)
    except ValueError:
        return False
    if set(path) - {"N", "E"}:
        return False
    n = path.count("N")
    east = path.count("E")
    if n < 1 or east % n:
        return False
    k = east // n
    if k < 1 or len(rows) != k + 1:
        return False
    columns = _columns_from_path(path)
    if any(columns[i - 1] > k * (i - 1) for i in range(1, n + 1)):
        return False
    if any(sorted(row) != list(range(1, n + 1)) for row in rows):
        return False
    for i in range(1, n):
        descents = sum(1 for row in rows if row[i - 1] >= row[i])
        if descents > columns[i] - columns[i - 1]:
            return False
    return True


@dataclass(frozen=True, init=False)
class MultiLabelledDyckPath:
    """A standard multi-labelled ``k^n`` Dyck path.

    Encoded as ``path + "|" + row_0 + "|" + ... + "|" + row_k`` where ``path`` is
    the North/East word and each ``row_j`` lists the ``j``-th label of every
    North step in step order (a permutation of ``[n]``). Public benchmark code
    exposes only structural data and the ``area`` statistic; the unknown
    ``t``-partner belongs to the discovery task.
    """

    encoding: str
    path: str
    n: int
    k: int

    def __init__(self, encoding: str, *, validate: bool = True) -> None:
        if validate and not is_multi_labelled_dyck_path(encoding):
            raise ValueError(f"not a standard multi-labelled Dyck path: {encoding!r}")
        path = encoding.split(SEPARATOR)[0]
        n = path.count("N")
        object.__setattr__(self, "encoding", encoding)
        object.__setattr__(self, "path", path)
        object.__setattr__(self, "n", n)
        object.__setattr__(self, "k", path.count("E") // n)

    @property
    def size(self) -> int:
        """Number of North steps, ``n``."""
        return self.n

    @cached_property
    def rows(self) -> tuple[tuple[int, ...], ...]:
        """The ``k + 1`` label rows, each a permutation of ``[n]``."""
        return _parse(self.encoding)[1]

    @cached_property
    def labels(self) -> tuple[tuple[int, ...], ...]:
        """``labels[i - 1]`` is the ``(k+1)``-tuple ``w_i`` of the ``i``-th North step."""
        return tuple(zip(*self.rows))

    @cached_property
    def columns(self) -> tuple[int, ...]:
        """``columns[i - 1]`` is ``col(i)``, the ``x``-coordinate of North step ``i``."""
        return _columns_from_path(self.path)

    @cached_property
    def gaps(self) -> tuple[int, ...]:
        """``gaps[i - 1] = col(i+1) - col(i)`` for ``1 <= i < n`` (East steps between)."""
        columns = self.columns
        return tuple(columns[i] - columns[i - 1] for i in range(1, self.n))

    @cached_property
    def area_word(self) -> tuple[int, ...]:
        """``area_word[i - 1] = k (i - 1) - col(i)``, the whole cells in row ``i``."""
        return tuple(self.k * (i - 1) - column for i, column in enumerate(self.columns, start=1))

    @cached_property
    def descents(self) -> tuple[int, ...]:
        """``descents[i - 1]`` is the number of rows descending at position ``i``."""
        rows = self.rows
        return tuple(
            sum(1 for row in rows if row[i - 1] >= row[i]) for i in range(1, self.n)
        )

    def area(self) -> int:
        """Whole cells between the path and the main diagonal ``ky = x``."""
        return sum(self.area_word)

    def to_jsonable(self) -> str:
        return self.encoding


def multi_labelled_dyck_area(encoding: str) -> int:
    """Area of the standard multi-labelled Dyck path given by ``encoding``."""
    return MultiLabelledDyckPath(encoding, validate=False).area()


def multi_labelled_dyck_size(encoding_or_object) -> int:
    """Number of North steps ``n`` (module-level, for the value/resource gate)."""
    if isinstance(encoding_or_object, MultiLabelledDyckPath):
        return encoding_or_object.n
    return encoding_or_object.split(SEPARATOR)[0].count("N")


# ---------------------------------------------------------------------------
# Enumeration of LD_{k^n} with standard labellings
# ---------------------------------------------------------------------------


def _iter_rectangular_dyck_columns(n: int, k: int) -> Iterator[tuple[int, ...]]:
    """Yield ``(col(1), ..., col(n))`` for every ``kn x n`` Dyck path."""
    columns: list[int] = []

    def rec(i: int) -> Iterator[tuple[int, ...]]:
        if i > n:
            yield tuple(columns)
            return
        low = columns[-1] if columns else 0
        for column in range(low, k * (i - 1) + 1):
            columns.append(column)
            yield from rec(i + 1)
            columns.pop()

    yield from rec(1)


@cache
def _permutations_by_descent_set(n: int) -> dict[frozenset[int], tuple[tuple[int, ...], ...]]:
    """Group the permutations of ``[n]`` by their descent set."""
    grouped: dict[frozenset[int], list[tuple[int, ...]]] = {}
    for perm in permutations(range(1, n + 1)):
        descents = frozenset(i for i in range(1, n) if perm[i - 1] > perm[i])
        grouped.setdefault(descents, []).append(perm)
    return {key: tuple(value) for key, value in grouped.items()}


def iter_multi_labelled_dyck_paths(n: int, k: int) -> Iterator[MultiLabelledDyckPath]:
    """Yield every standard element of ``LD_{k^n}`` once, streaming."""
    if n < 1 or k < 1:
        raise ValueError("size and label count must be positive")
    grouped = _permutations_by_descent_set(n)
    descent_sets = sorted(grouped, key=sorted)
    for columns in _iter_rectangular_dyck_columns(n, k):
        gaps = [columns[i] - columns[i - 1] for i in range(1, n)]
        path = _path_from_columns(columns, k * n)
        for choice in product(descent_sets, repeat=k + 1):
            if any(
                sum(1 for descents in choice if i in descents) > gaps[i - 1]
                for i in range(1, n)
            ):
                continue
            for rows in product(*(grouped[descents] for descents in choice)):
                yield MultiLabelledDyckPath(_encode(path, rows), validate=False)


@cache
def enumerate_multi_labelled_dyck_paths(n: int, k: int) -> tuple[MultiLabelledDyckPath, ...]:
    """All standard elements of ``LD_{k^n}`` (cached; use the iterator for large fibers)."""
    return tuple(iter_multi_labelled_dyck_paths(n, k))


def multi_labelled_dyck_count(n: int, k: int) -> int:
    """``|LD_{k^n}|`` restricted to standard labellings, by streaming enumeration."""
    return sum(1 for _ in iter_multi_labelled_dyck_paths(n, k))


def _permutation_with_descents(n: int, descents) -> tuple[int, ...]:
    """The permutation of ``[n]`` whose descent set is exactly ``descents``.

    Blocks cut at the descent positions receive consecutive decreasing ranges of
    values and increase inside each block.
    """
    cuts = [0, *sorted(descents), n]
    blocks = [(cuts[i], cuts[i + 1]) for i in range(len(cuts) - 1)]
    perm = [0] * n
    top = n
    for start, stop in blocks:
        width = stop - start
        for offset in range(width):
            perm[start + offset] = top - width + 1 + offset
        top -= width
    return tuple(perm)


def canonical_multi_labelled_dyck_path(path: str, k: int) -> MultiLabelledDyckPath:
    """A canonical standard multi-labelling of a fixed ``kn x n`` Dyck path.

    Row ``j < k`` gets the permutation whose descent set is exactly the positions
    with at least ``j + 1`` East steps and row ``k`` is the identity, so position
    ``i`` carries ``min(k, gap_i) <= gap_i`` descents. Used to build large valid
    objects for the resource and value gates without enumerating the
    (exponential) fiber.
    """
    n = path.count("N")
    if n < 1 or k < 1:
        raise ValueError("size and label count must be positive")
    columns = _columns_from_path(path)
    gaps = [columns[i] - columns[i - 1] for i in range(1, n)]
    rows = [
        _permutation_with_descents(n, {i for i in range(1, n) if gaps[i - 1] >= j + 1})
        for j in range(k)
    ]
    rows.append(tuple(range(1, n + 1)))
    return MultiLabelledDyckPath(_encode(path, rows))
