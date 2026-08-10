"""Standard Young tableaux indexed by a second partition, for the (q,t)-Kostka task.

The modified Macdonald polynomial ``H~_mu(X; q, t)`` expands in the Schur basis
as ``H~_mu = sum_{lambda |- n} K~_{lambda mu}(q, t) s_lambda``, and its
coefficients, the **modified (q,t)-Kostka polynomials**, satisfy
``K~_{lambda mu}(1, 1) = f^lambda = |SYT(lambda)|``. Macdonald's combinatorial
problem asks for two statistics on ``SYT(lambda)``, depending on ``mu``, whose
joint distribution is ``K~_{lambda mu}(q, t)``.

An object of this family is therefore a pair ``(mu, T)`` with ``mu |- n`` and
``T`` a standard Young tableau with ``n`` cells; the partition ``lambda`` is the
shape of ``T``. Tableaux use English notation: ``rows[0]`` is the longest row,
entries increase left to right along rows and top to bottom down columns.

The canonical encoding is ``mu + "|" + rows``, with ``mu`` comma-separated and
the rows of ``T`` separated by ``"/"``. For example ::

    2,1|1,2/3

is the pair ``mu = (2, 1)``, ``T`` the tableau of shape ``lambda = (2, 1)`` with
first row ``1 2`` and second row ``3``.

No statistic on this family is public: the task is to discover **both** the
``q``-statistic and the ``t``-statistic. The classical descent set and its major
index are exposed here because they are the ``mu``-independent anchors that the
answer has to recover at the two extreme shapes ``mu = (n)`` and ``mu = (1^n)``.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from functools import cache, cached_property
from typing import Iterator

SEPARATOR = "|"
ROW_SEPARATOR = "/"

KostkaTableauWord = str


# ---------------------------------------------------------------------------
# Partitions
# ---------------------------------------------------------------------------


@cache
def iter_partitions(n: int) -> tuple[tuple[int, ...], ...]:
    """Every partition of ``n``, weakly decreasing, in reverse lexicographic order."""
    if n < 1:
        raise ValueError("size must be positive")
    out: list[tuple[int, ...]] = []
    current: list[int] = []

    def rec(remaining: int, largest: int) -> None:
        if remaining == 0:
            out.append(tuple(current))
            return
        for part in range(min(remaining, largest), 0, -1):
            current.append(part)
            rec(remaining - part, part)
            current.pop()

    rec(n, n)
    return tuple(out)


def conjugate_partition(mu: tuple[int, ...]) -> tuple[int, ...]:
    """The transpose ``mu'`` of a partition."""
    return tuple(sum(1 for part in mu if part > column) for column in range(mu[0] if mu else 0))


def _partition_text(mu) -> str:
    """``(2, 1)`` -> ``"2,1"``."""
    return ",".join(str(part) for part in mu)


# ---------------------------------------------------------------------------
# Objects
# ---------------------------------------------------------------------------


def _parse(encoding: str):
    mu_text, rows_text = encoding.split(SEPARATOR)
    mu = tuple(int(piece) for piece in mu_text.split(","))
    rows = tuple(
        tuple(int(piece) for piece in field.split(","))
        for field in rows_text.split(ROW_SEPARATOR)
    )
    return mu, rows


def _encode(mu, rows) -> str:
    body = ROW_SEPARATOR.join(",".join(str(value) for value in row) for row in rows)
    return f"{_partition_text(mu)}{SEPARATOR}{body}"


def is_partition(mu) -> bool:
    """Whether ``mu`` is a nonempty weakly decreasing sequence of positive parts."""
    if not isinstance(mu, Sequence) or isinstance(mu, (str, bytes, bytearray)):
        return False
    parts = tuple(mu)
    return (
        bool(parts)
        and all(type(part) is int and part >= 1 for part in parts)
        and all(parts[i - 1] >= parts[i] for i in range(1, len(parts)))
    )


def is_kostka_standard_tableau(encoding: str) -> bool:
    """Whether ``encoding`` is a valid ``mu|rows`` pair with ``|mu| = |T|``."""
    if not isinstance(encoding, str) or encoding.count(SEPARATOR) != 1:
        return False
    try:
        mu, rows = _parse(encoding)
    except ValueError:
        return False
    shape = tuple(len(row) for row in rows)
    if not is_partition(mu) or not is_partition(shape):
        return False
    if sum(mu) != sum(shape):
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
class KostkaStandardTableau:
    """A partition ``mu`` paired with a standard Young tableau ``T``.

    Encoded as ``mu + "|" + rows``; ``mu`` is comma-separated and the rows of
    ``T`` are separated by ``"/"``. Public benchmark code exposes only structural
    data and the classical descent statistics; both graded statistics of the
    target belong to the discovery task.
    """

    encoding: str
    mu: tuple[int, ...]
    rows: tuple[tuple[int, ...], ...]
    n: int

    def __init__(self, encoding: str, *, validate: bool = True) -> None:
        if validate and not is_kostka_standard_tableau(encoding):
            raise ValueError(f"not a mu-indexed standard Young tableau: {encoding!r}")
        mu, rows = _parse(encoding)
        object.__setattr__(self, "encoding", encoding)
        object.__setattr__(self, "mu", mu)
        object.__setattr__(self, "rows", rows)
        object.__setattr__(self, "n", sum(mu))

    @property
    def size(self) -> int:
        """Number of cells, ``n = |mu| = |lambda|``."""
        return self.n

    @cached_property
    def shape(self) -> tuple[int, ...]:
        """The partition ``lambda``, the shape of ``T``."""
        return tuple(len(row) for row in self.rows)

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


def kostka_tableau_maj(encoding: str) -> int:
    """Major index of the tableau given by ``encoding``."""
    return KostkaStandardTableau(encoding, validate=False).maj()


def kostka_tableau_size(encoding_or_object) -> int:
    """Number of cells ``n`` (module-level, for the value and resource gates)."""
    if isinstance(encoding_or_object, KostkaStandardTableau):
        return encoding_or_object.n
    return sum(
        int(piece) for piece in encoding_or_object.split(SEPARATOR)[0].split(",")
    )


# ---------------------------------------------------------------------------
# Enumeration of SYT(lambda) x {mu}
# ---------------------------------------------------------------------------


def iter_standard_tableau_rows(lam: tuple[int, ...]) -> Iterator[tuple[tuple[int, ...], ...]]:
    """Yield the rows of every standard Young tableau of shape ``lam``.

    Entries are placed in increasing order; ``value`` goes into the first free
    cell of some row whose predecessor row is already longer, which is exactly
    the condition keeping every intermediate shape a partition.
    """
    n = sum(lam)
    height = len(lam)
    filled = [0] * height
    rows: list[list[int]] = [[] for _ in range(height)]

    def rec(value: int) -> Iterator[tuple[tuple[int, ...], ...]]:
        if value > n:
            yield tuple(tuple(row) for row in rows)
            return
        for r in range(height):
            if filled[r] == lam[r]:
                continue
            if r and filled[r] == filled[r - 1]:
                continue
            rows[r].append(value)
            filled[r] += 1
            yield from rec(value + 1)
            filled[r] -= 1
            rows[r].pop()

    yield from rec(1)


def iter_kostka_standard_tableaux(
    lam: tuple[int, ...], mu: tuple[int, ...]
) -> Iterator[KostkaStandardTableau]:
    """Yield every ``(mu, T)`` with ``T`` a standard Young tableau of shape ``lam``."""
    if not is_partition(lam) or not is_partition(mu):
        raise ValueError("shape and index must be partitions")
    if sum(lam) != sum(mu):
        raise ValueError("shape and index must be partitions of the same integer")
    for rows in iter_standard_tableau_rows(lam):
        yield KostkaStandardTableau(_encode(mu, rows), validate=False)


@cache
def enumerate_kostka_standard_tableaux(
    lam: tuple[int, ...], mu: tuple[int, ...]
) -> tuple[KostkaStandardTableau, ...]:
    """All ``(mu, T)`` with ``T`` of shape ``lam`` (cached; stream for large fibers)."""
    return tuple(iter_kostka_standard_tableaux(lam, mu))


def kostka_standard_tableau_count(lam: tuple[int, ...]) -> int:
    """``f^lambda``, by the hook length formula."""
    n = sum(lam)
    conjugate = conjugate_partition(lam)
    product = 1
    for r, part in enumerate(lam):
        for c in range(part):
            product *= part - c + conjugate[c] - r - 1
    numerator = 1
    for value in range(2, n + 1):
        numerator *= value
    return numerator // product


def canonical_kostka_standard_tableau(
    lam: tuple[int, ...], mu: tuple[int, ...], *, by_columns: bool = False
) -> KostkaStandardTableau:
    """A single valid ``(mu, T)`` built without enumerating ``SYT(lambda)``.

    The row-superstandard tableau numbers the rows left to right, top to bottom;
    ``by_columns`` numbers the columns instead. Both are standard, and the two
    have very different descent sets, so the resource and value gates can probe
    large shapes cheaply.
    """
    if not is_partition(lam) or not is_partition(mu):
        raise ValueError("shape and index must be partitions")
    if sum(lam) != sum(mu):
        raise ValueError("shape and index must be partitions of the same integer")
    rows: list[list[int]] = [[0] * part for part in lam]
    if by_columns:
        value = 1
        for c in range(lam[0]):
            for r, part in enumerate(lam):
                if part > c:
                    rows[r][c] = value
                    value += 1
    else:
        value = 1
        for r, part in enumerate(lam):
            for c in range(part):
                rows[r][c] = value
                value += 1
    return KostkaStandardTableau(_encode(mu, rows), validate=False)
