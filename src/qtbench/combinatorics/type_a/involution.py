"""Involutions of ``S_n`` graded by their number of fixed points.

The locus of problem 15 is

    M_{n,a} = { pi in S_n : pi^2 = id, fix(pi) = a },

the set of ``n x n`` permutation matrices of involutions with exactly ``a``
fixed points. Applying orbit harmonics to that locus produces a graded quotient
``R(M_{n,a})`` of ``C[x_{11}, ..., x_{nn}]`` whose Hilbert series is a positive
polynomial ``H_{n,a}(q)`` with ``H_{n,a}(1) = |M_{n,a}|``, and the discovery task
is a statistic on ``M_{n,a}`` whose generating function is ``H_{n,a}(q)``.

An object of this family is a single involution; the fiber it belongs to is
``(n, a) = (pi.n, pi.fix)``, both read off the object. The canonical encoding is
one-line notation, the comma-separated images ``pi(1), ..., pi(n)``, so ::

    2,1,3,5,4

is the involution ``(1 2)(4 5)`` of ``S_5``, with ``fix = 1``.

No statistic on this family is public. The RSK shape and the longest
increasing/decreasing subsequence lengths are exposed because they are the answer
in the one solved fiber: on fixed-point-free involutions
``H_{n,0}(q) = sum_pi q^{(n - lds(pi))/2}``, where ``lds(pi)`` is the length of a
longest decreasing subsequence, i.e. the number of rows of the RSK shape.
"""
from __future__ import annotations

from bisect import bisect_left, bisect_right
from dataclasses import dataclass
from functools import cached_property
from math import comb
from typing import Iterator

InvolutionWord = str


def _parse(encoding: str) -> tuple[int, ...]:
    return tuple(int(piece) for piece in encoding.split(","))


def _encode(images) -> str:
    return ",".join(str(value) for value in images)


def is_involution(encoding: str) -> bool:
    """Whether ``encoding`` is the one-line notation of an involution of some ``S_n``."""
    if not isinstance(encoding, str) or not encoding:
        return False
    try:
        images = _parse(encoding)
    except ValueError:
        return False
    n = len(images)
    if sorted(images) != list(range(1, n + 1)):
        return False
    return all(images[images[i - 1] - 1] == i for i in range(1, n + 1))


@dataclass(frozen=True, init=False)
class Involution:
    """An involution ``pi in S_n``, encoded in one-line notation.

    Public benchmark code exposes the permutation, its fixed points and 2-cycles,
    and the RSK shape with the two longest-subsequence lengths derived from it.
    The graded statistic of the target belongs to the discovery task.
    """

    encoding: str
    images: tuple[int, ...]
    n: int

    def __init__(self, encoding: str, *, validate: bool = True) -> None:
        if validate and not is_involution(encoding):
            raise ValueError(f"not an involution in one-line notation: {encoding!r}")
        object.__setattr__(self, "encoding", encoding)
        object.__setattr__(self, "images", _parse(encoding))
        object.__setattr__(self, "n", len(self.images))

    @property
    def size(self) -> int:
        """Number of letters, ``n``."""
        return self.n

    def __call__(self, i: int) -> int:
        """The image ``pi(i)``, with ``i`` 1-based."""
        return self.images[i - 1]

    @cached_property
    def fixed_points(self) -> tuple[int, ...]:
        """The fixed points ``{ i : pi(i) = i }``, increasing."""
        return tuple(i for i, image in enumerate(self.images, start=1) if image == i)

    @cached_property
    def fix(self) -> int:
        """``fix(pi) = a``, the number of fixed points: the fiber index."""
        return len(self.fixed_points)

    @cached_property
    def pairs(self) -> tuple[tuple[int, int], ...]:
        """The 2-cycles as pairs ``(i, pi(i))`` with ``i < pi(i)``, increasing in ``i``."""
        return tuple(
            (i, image) for i, image in enumerate(self.images, start=1) if image > i
        )

    @cached_property
    def rsk_shape(self) -> tuple[int, ...]:
        """The common shape of the two equal RSK tableaux of ``pi``.

        Schensted row insertion of the one-line word; only the row lengths are
        kept. Under RSK an involution with ``a`` fixed points has exactly ``a``
        columns of odd length.
        """
        rows: list[list[int]] = []
        for value in self.images:
            carried = value
            for row in rows:
                position = bisect_right(row, carried)
                if position == len(row):
                    row.append(carried)
                    carried = 0
                    break
                carried, row[position] = row[position], carried
            if carried:
                rows.append([carried])
        return tuple(len(row) for row in rows)

    def longest_increasing(self) -> int:
        """Length of a longest increasing subsequence, the first row of the RSK shape."""
        piles: list[int] = []
        for value in self.images:
            position = bisect_left(piles, value)
            if position == len(piles):
                piles.append(value)
            else:
                piles[position] = value
        return len(piles)

    def longest_decreasing(self) -> int:
        """Length of a longest decreasing subsequence, the number of RSK rows."""
        piles: list[int] = []
        for value in self.images:
            position = bisect_left(piles, -value)
            if position == len(piles):
                piles.append(-value)
            else:
                piles[position] = -value
        return len(piles)

    def to_jsonable(self) -> str:
        return self.encoding


def involution(images, *, validate: bool = True) -> Involution:
    """Build an involution from its sequence of images ``pi(1), ..., pi(n)``."""
    return Involution(_encode(images), validate=validate)


def involution_size(encoding_or_object) -> int:
    """Size ``n`` (module-level, for the value and resource gates)."""
    if isinstance(encoding_or_object, Involution):
        return encoding_or_object.n
    return len(encoding_or_object.split(","))


# ---------------------------------------------------------------------------
# Enumeration
# ---------------------------------------------------------------------------


def _iter_matchings(free: tuple[int, ...], fixed_left: int) -> Iterator[tuple[tuple[int, int], ...]]:
    """Yield the cycles of every involution of ``free`` with ``fixed_left`` fixed points."""
    if not 0 <= fixed_left <= len(free) or (len(free) - fixed_left) % 2:
        return
    if not free:
        yield ()
        return
    smallest, rest = free[0], free[1:]
    if fixed_left:
        for tail in _iter_matchings(rest, fixed_left - 1):
            yield ((smallest, smallest), *tail)
    for index, partner in enumerate(rest):
        remaining = rest[:index] + rest[index + 1:]
        for tail in _iter_matchings(remaining, fixed_left):
            yield ((smallest, partner), *tail)


def iter_involutions_with_fixed_points(n: int, a: int) -> Iterator[Involution]:
    """Yield every involution in ``M_{n,a}``, one at a time."""
    if n < 1:
        raise ValueError("size must be positive")
    if not 0 <= a <= n or (n - a) % 2:
        raise ValueError(f"M_{{{n},{a}}} is empty: need 0 <= a <= n and a = n mod 2")
    for cycles in _iter_matchings(tuple(range(1, n + 1)), a):
        images = [0] * n
        for i, j in cycles:
            images[i - 1] = j
            images[j - 1] = i
        yield Involution(_encode(images), validate=False)


def iter_involutions(n: int) -> Iterator[Involution]:
    """Yield every involution of ``S_n``, fiber by fiber in increasing ``a``."""
    if n < 1:
        raise ValueError("size must be positive")
    for a in range(n % 2, n + 1, 2):
        yield from iter_involutions_with_fixed_points(n, a)


def involution_count(n: int, a: int) -> int:
    """``|M_{n,a}| = C(n, a) (n - a - 1)!!``, the size of one fiber."""
    if not 0 <= a <= n or (n - a) % 2:
        raise ValueError(f"M_{{{n},{a}}} is empty: need 0 <= a <= n and a = n mod 2")
    matchings = 1
    for size in range(1, n - a, 2):
        matchings *= size
    return comb(n, a) * matchings


def canonical_involution(n: int, a: int, *, nested: bool = False) -> Involution:
    """A single involution in ``M_{n,a}`` built without enumerating the fiber.

    The ``n - a`` non-fixed letters are matched either consecutively
    (``(1 2)(3 4) ...``, longest decreasing subsequence 2) or by nesting
    (``i <-> n - a + 1 - i``, longest decreasing subsequence ``n - a``), so the
    two extremes of the one solved fiber are both cheap to probe. The fixed
    points are the largest ``a`` letters.
    """
    if not 0 <= a <= n or (n - a) % 2:
        raise ValueError(f"M_{{{n},{a}}} is empty: need 0 <= a <= n and a = n mod 2")
    images = list(range(1, n + 1))
    moved = n - a
    if nested:
        for i in range(1, moved // 2 + 1):
            images[i - 1] = moved + 1 - i
            images[moved - i] = i
    else:
        for i in range(1, moved, 2):
            images[i - 1] = i + 1
            images[i] = i
    return Involution(_encode(images), validate=False)
