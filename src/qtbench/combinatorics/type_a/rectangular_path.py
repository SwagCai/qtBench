"""Standardly labelled rise-decorated rectangular paths and their area.

Following Iraci, Pagaria, Paolini and Vanden Wyngaerd (see the problem statement
for references), a *rectangular path* of size ``M x N`` is a lattice path of unit
North and East steps from ``(0, 0)`` to ``(M, N)`` that **ends with an East
step**. The *rises* are the rows whose North step immediately follows another
North step, and a *decorated rectangular path* carries a subset ``dr`` of them.

For a ``(m+k) x (n+k)`` decorated path with ``k`` decorated rises, the *broken
diagonal* starts at ``(0, 0)`` and advances by ``m/n`` horizontally per row,
except in decorated rows where it advances by ``1``; it therefore ends at
``(m+k, n+k)``. With ``col(i)`` the ``x``-coordinate of the ``i``-th North step and
``x_i`` the broken diagonal at height ``i - 1``, the *area word* is
``a_i = x_i - col(i)``, the *shift* is ``s = -min_i a_i >= 0`` (zero exactly for
the paths lying weakly above the broken diagonal), and

    area(pi) = sum_{i not in dr} floor(a_i + s).

A *labelling* assigns a positive integer to each North step, strictly increasing
along each maximal run of consecutive North steps; it is *standard* when the
labels are exactly ``[n + k]``. ``LRP(m+k, n+k)^{*k}`` is the set of labelled
decorated rectangular paths of that size with ``k`` decorated rises.

The joint distribution of ``area`` and the unknown partner is the Hilbert series
``<([m+k]_q / [gcd(m,n)]_q) Theta_{e_k} p_{m,n}, h_{1^{n+k}}>``; ``area`` is public
and the partner is the object of the discovery task.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from functools import cache, cached_property
from itertools import combinations
from typing import Iterator

SEPARATOR = "|"

RectangularPathWord = str


def _columns(path: str) -> tuple[int, ...]:
    """``x``-coordinate of each North step, in step order."""
    out = []
    x = 0
    for step in path:
        if step == "N":
            out.append(x)
        else:
            x += 1
    return tuple(out)


def _rises(path: str) -> tuple[int, ...]:
    """1-indexed rows whose North step directly follows another North step."""
    rows = []
    row = 0
    previous_was_north = False
    for step in path:
        if step == "N":
            row += 1
            if previous_was_north:
                rows.append(row)
            previous_was_north = True
        else:
            previous_was_north = False
    return tuple(rows)


def _runs(path: str) -> list[list[int]]:
    """Maximal runs of consecutive North steps, as lists of 1-indexed rows."""
    runs: list[list[int]] = []
    row = 0
    previous_was_north = False
    for step in path:
        if step == "N":
            row += 1
            if previous_was_north:
                runs[-1].append(row)
            else:
                runs.append([row])
            previous_was_north = True
        else:
            previous_was_north = False
    return runs


def _parse(encoding: str):
    """``(path, labels, drise)``; ``drise`` is kept as written, not deduplicated."""
    path, label_text, rise_text = encoding.split(SEPARATOR)
    labels = tuple(int(piece) for piece in label_text.split(",")) if label_text else ()
    drise = tuple(int(piece) for piece in rise_text.split(",")) if rise_text else ()
    return path, labels, drise


def _encode(path: str, labels, drise) -> str:
    label_text = ",".join(str(value) for value in labels)
    rise_text = ",".join(str(row) for row in sorted(drise))
    return f"{path}{SEPARATOR}{label_text}{SEPARATOR}{rise_text}"


def is_labelled_rectangular_path(encoding: str) -> bool:
    """Whether ``encoding`` is a valid ``path|labels|drise`` standard object."""
    if not isinstance(encoding, str) or encoding.count(SEPARATOR) != 2:
        return False
    try:
        path, labels, drise = _parse(encoding)
    except ValueError:
        return False
    if set(path) - {"N", "E"} or not path.endswith("E"):
        return False
    height = path.count("N")
    width = path.count("E")
    k = len(drise)
    if height - k < 1 or width - k < 1:
        return False
    if sorted(labels) != list(range(1, height + 1)):
        return False
    # the decorated rises are listed once each, in increasing order, so that every
    # object has exactly one encoding
    if list(drise) != sorted(set(drise)):
        return False
    if not set(drise) <= set(_rises(path)):
        return False
    return all(
        labels[run[i] - 1] < labels[run[i + 1] - 1]
        for run in _runs(path)
        for i in range(len(run) - 1)
    )


@dataclass(frozen=True, init=False)
class LabelledRectangularPath:
    """A standardly labelled rise-decorated rectangular path.

    Encoded as ``path + "|" + labels + "|" + drise`` where ``path`` is the
    North/East word (ending with an East step), ``labels`` lists the label of each
    North step in step order and ``drise`` lists the 1-indexed decorated rise
    rows. Public benchmark code exposes only structural data and the ``area``
    statistic; the unknown ``t``-partner belongs to the discovery task.
    """

    encoding: str
    path: str
    m: int
    n: int
    k: int

    def __init__(self, encoding: str, *, validate: bool = True) -> None:
        if validate and not is_labelled_rectangular_path(encoding):
            raise ValueError(f"not a standardly labelled rectangular path: {encoding!r}")
        path, _labels, drise = _parse(encoding)
        k = len(drise)
        object.__setattr__(self, "encoding", encoding)
        object.__setattr__(self, "path", path)
        object.__setattr__(self, "m", path.count("E") - k)
        object.__setattr__(self, "n", path.count("N") - k)
        object.__setattr__(self, "k", k)

    @property
    def width(self) -> int:
        """Number of East steps, ``m + k``."""
        return self.m + self.k

    @property
    def height(self) -> int:
        """Number of North steps (and of labels), ``n + k``."""
        return self.n + self.k

    @property
    def size(self) -> int:
        """Number of labels, ``n + k``."""
        return self.height

    @cached_property
    def labels(self) -> tuple[int, ...]:
        """Label of each North step in step order (bottom to top)."""
        return _parse(self.encoding)[1]

    @cached_property
    def decorated_rises(self) -> frozenset[int]:
        """1-indexed rows carrying a rise decoration."""
        return frozenset(_parse(self.encoding)[2])

    @cached_property
    def rises(self) -> frozenset[int]:
        """1-indexed rows whose North step directly follows another North step."""
        return frozenset(_rises(self.path))

    @cached_property
    def columns(self) -> tuple[int, ...]:
        """``columns[i - 1] = col(i)``, the ``x``-coordinate of North step ``i``."""
        return _columns(self.path)

    @cached_property
    def _scaled_area_word(self) -> tuple[int, ...]:
        """``n * a_i``: the area word cleared of its denominator ``n``."""
        drise = self.decorated_rises
        m, n = self.m, self.n
        out = []
        diagonal = 0
        for i, column in enumerate(self.columns, start=1):
            out.append(diagonal - n * column)
            diagonal += n if i in drise else m
        return tuple(out)

    @cached_property
    def shift(self) -> Fraction:
        """``s = -min_i a_i >= 0``; zero exactly above the broken diagonal."""
        return Fraction(-min(self._scaled_area_word), self.n)

    @cached_property
    def area_word(self) -> tuple[Fraction, ...]:
        """The (rational) area word ``a_i = x_i - col(i)``."""
        return tuple(Fraction(value, self.n) for value in self._scaled_area_word)

    def area(self) -> int:
        """Decorated area: ``sum_{i not in dr} floor(a_i + s)``."""
        drise = self.decorated_rises
        n = self.n
        scaled = self._scaled_area_word
        shift = -min(scaled)
        return sum(
            (value + shift) // n
            for i, value in enumerate(scaled, start=1)
            if i not in drise
        )

    def to_jsonable(self) -> str:
        return self.encoding


def labelled_rectangular_path_area(encoding: str) -> int:
    """Area of the standardly labelled decorated rectangular path ``encoding``."""
    return LabelledRectangularPath(encoding, validate=False).area()


def labelled_rectangular_path_size(encoding_or_object) -> int:
    """Semiperimeter ``m + n + 2k`` (module-level, for the value/resource gate)."""
    if isinstance(encoding_or_object, LabelledRectangularPath):
        return encoding_or_object.width + encoding_or_object.height
    return len(encoding_or_object.split(SEPARATOR)[0])


# ---------------------------------------------------------------------------
# Enumeration of LRP(m+k, n+k)^{*k}
# ---------------------------------------------------------------------------


def _iter_rectangular_paths(width: int, height: int) -> Iterator[str]:
    """Yield every ``width x height`` North/East word that ends with an East step."""
    word: list[str] = []

    def rec(north: int, east: int) -> Iterator[str]:
        if north == height and east == width:
            yield "".join(word)
            return
        if north < height:
            word.append("N")
            yield from rec(north + 1, east)
            word.pop()
        if east < width - 1 or (east == width - 1 and north == height):
            word.append("E")
            yield from rec(north, east + 1)
            word.pop()

    yield from rec(0, 0)


def _iter_standard_labellings(path: str) -> Iterator[tuple[int, ...]]:
    """Yield every labelling (as a row-ordered tuple) increasing along each run."""
    runs = _runs(path)
    height = path.count("N")
    pointers = [0] * len(runs)
    assigned: dict[int, int] = {}

    def rec(label: int) -> Iterator[tuple[int, ...]]:
        if label > height:
            yield tuple(assigned[row] for row in range(1, height + 1))
            return
        for j, run in enumerate(runs):
            if pointers[j] < len(run):
                row = run[pointers[j]]
                assigned[row] = label
                pointers[j] += 1
                yield from rec(label + 1)
                pointers[j] -= 1
                del assigned[row]

    yield from rec(1)


def iter_labelled_rectangular_paths(
    m: int, n: int, k: int
) -> Iterator[LabelledRectangularPath]:
    """Yield every standard element of ``LRP(m+k, n+k)^{*k}`` once, streaming."""
    if m < 1 or n < 1 or k < 0:
        raise ValueError("m, n must be positive and k nonnegative")
    for path in _iter_rectangular_paths(m + k, n + k):
        rises = _rises(path)
        if len(rises) < k:
            continue
        for drise in combinations(rises, k):
            for labels in _iter_standard_labellings(path):
                yield LabelledRectangularPath(
                    _encode(path, labels, frozenset(drise)), validate=False
                )


@cache
def enumerate_labelled_rectangular_paths(
    m: int, n: int, k: int
) -> tuple[LabelledRectangularPath, ...]:
    """All of ``LRP(m+k, n+k)^{*k}`` (cached; use the iterator for large fibers)."""
    return tuple(iter_labelled_rectangular_paths(m, n, k))


def labelled_rectangular_path_count(m: int, n: int, k: int) -> int:
    """``|LRP(m+k, n+k)^{*k}|`` computed by streaming enumeration."""
    return sum(1 for _ in iter_labelled_rectangular_paths(m, n, k))


def canonical_labelled_rectangular_path(
    path: str, k: int
) -> LabelledRectangularPath:
    """A canonical standard object on ``path`` with ``k`` decorated rises.

    The labelling assigns ``1, ..., n+k`` to the North steps in step order (which
    increases along every run) and the first ``k`` rises are decorated. Used to
    build large valid objects for the resource and value gates without
    enumerating the (exponential) fiber.
    """
    if k < 0:
        raise ValueError("decoration count must be nonnegative")
    height = path.count("N")
    rises = _rises(path)
    if len(rises) < k:
        raise ValueError(f"shape {path!r} has fewer than {k} rises")
    labels = tuple(range(1, height + 1))
    return LabelledRectangularPath(
        _encode(path, labels, frozenset(rises[:k]))
    )
