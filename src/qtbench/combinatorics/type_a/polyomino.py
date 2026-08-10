"""Parallelogram polyominoes and their area/bounce statistics.

A parallelogram polyomino with an ``m x n`` bounding box is a pair of lattice
paths from the Southwest corner ``(0, 0)`` to the Northeast corner ``(m, n)``,
each taking ``m`` East (``E``) and ``n`` North (``N``) steps, that touch only at
those two endpoints. The upper (Northwest) path starts with ``N`` and the lower
(Southeast) path starts with ``E``; the cells between them form the polyomino.
Such polyominoes are counted by the Narayana number ``N(m + n - 1, m)``.

The polyomino is encoded as the string ``upper + "|" + lower`` where ``upper``
and ``lower`` are the two ``N``/``E`` words, for example ``"NE|EN"`` for the
single-cell ``1 x 1`` polyomino.

The joint distribution of ``area`` and ``bounce`` is the q,t-Narayana polynomial
of Aval, D'Adderio, Dukes, Hicks, and Le Borgne (see the problem statement for
references); both statistics are public here -- the task is a bijection that
exchanges them, not discovering a statistic.
"""
from __future__ import annotations

from collections import Counter
from functools import cache
from math import comb
from typing import Iterator

PolyominoWord = str

SEPARATOR = "|"


def polyomino_count(m: int, n: int) -> int:
    """Number of parallelogram polyominoes with an ``m x n`` bounding box.

    This is the Narayana number ``N(m + n - 1, m)``.
    """
    if m < 1 or n < 1:
        return 0
    a = m + n - 1
    return comb(a, m) * comb(a, m - 1) // a


def _lattice_points(path: str) -> list[tuple[int, int]]:
    points = [(0, 0)]
    x = y = 0
    for step in path:
        if step == "N":
            y += 1
        else:
            x += 1
        points.append((x, y))
    return points


def is_parallelogram_polyomino(encoding: str) -> bool:
    """Whether ``encoding`` is a valid ``upper|lower`` parallelogram polyomino."""
    if not isinstance(encoding, str) or encoding.count(SEPARATOR) != 1:
        return False
    upper, lower = encoding.split(SEPARATOR)
    if len(upper) != len(lower) or not upper:
        return False
    if any(step not in "NE" for step in upper) or any(step not in "NE" for step in lower):
        return False
    if upper.count("N") != lower.count("N") or upper.count("E") != lower.count("E"):
        return False
    m = upper.count("E")
    n = upper.count("N")
    if m < 1 or n < 1:
        return False
    # The upper path leaves the Southwest corner going North and enters the
    # Northeast corner going East; the lower path does the opposite.
    if upper[0] != "N" or upper[-1] != "E" or lower[0] != "E" or lower[-1] != "N":
        return False
    # Two monotone paths that meet only at the two corners bound a parallelogram
    # polyomino; the upper path (starting North) then stays weakly above.
    upper_points = _lattice_points(upper)
    lower_points = _lattice_points(lower)
    shared = set(upper_points) & set(lower_points)
    return shared == {(0, 0), (m, n)}


def _paths(encoding: str) -> tuple[str, str]:
    upper, lower = encoding.split(SEPARATOR)
    return upper, lower


def polyomino_dimensions(encoding: str) -> tuple[int, int]:
    """The bounding box ``(m, n)`` (columns, rows) of the polyomino."""
    upper, _lower = _paths(encoding)
    return upper.count("E"), upper.count("N")


def polyomino_size(encoding: str) -> int:
    """Semiperimeter ``m + n``; the number of steps of each boundary path."""
    upper, _lower = _paths(encoding)
    return len(upper)


def _area_below(path: str) -> int:
    """Cells below a monotone ``N``/``E`` path: the sum of its East-step heights."""
    y = 0
    total = 0
    for step in path:
        if step == "N":
            y += 1
        else:
            total += y
    return total


def polyomino_area(encoding: str) -> int:
    """Area: the number of cells enclosed between the two boundary paths."""
    upper, lower = _paths(encoding)
    return _area_below(upper) - _area_below(lower)


def polyomino_bounce(encoding: str) -> int:
    """Bounce statistic, read off the polyomino's bounce path.

    The bounce path leaves the Southwest corner with a single East step, then
    alternately travels North until it meets the East endpoint of an East step
    of the upper path and East until it meets the North endpoint of a North step
    of the lower path, until it reaches the Northeast corner. The k-th maximal
    run of North steps is labelled ``k`` and the k-th maximal run of East steps
    is labelled ``k - 1``; bounce is the sum of the labels.
    """
    upper, lower = _paths(encoding)
    m = upper.count("E")
    n = upper.count("N")

    upper_east_ends: set[tuple[int, int]] = set()
    x = y = 0
    for step in upper:
        if step == "E":
            x += 1
            upper_east_ends.add((x, y))
        else:
            y += 1

    lower_north_ends: set[tuple[int, int]] = set()
    x = y = 0
    for step in lower:
        if step == "N":
            y += 1
            lower_north_ends.add((x, y))
        else:
            x += 1

    bounce = 0
    x, y = 1, 0            # initial single East step (first East run, label 0)
    vertical_run = 0
    horizontal_run = 1    # the initial East step is the first East run
    moving_north = True
    while (x, y) != (m, n):
        if moving_north:
            vertical_run += 1
            while (x, y) not in upper_east_ends:
                y += 1
                bounce += vertical_run
            moving_north = False
        else:
            horizontal_run += 1
            while (x, y) not in lower_north_ends:
                x += 1
                bounce += horizontal_run - 1
            moving_north = True
    return bounce


# ---------------------------------------------------------------------------
# Enumeration via area words (Corollary 3.2 of arXiv:1301.4803)
# ---------------------------------------------------------------------------
#
# An area word is a word in the alphabet 0-bar < 1 < 1-bar < 2 < 2-bar < ...,
# encoded here by the integer rank of each letter (0-bar -> 0, 1 -> 1,
# 1-bar -> 2, 2 -> 3, ...). Odd ranks are unbarred (East steps of the lower
# path), even ranks are barred (North steps of the upper path). A word is the
# area word of a polyomino in Polyo_{m,n} iff it starts with the unique 0-bar,
# has exactly m unbarred and n barred letters, and every letter has rank at most
# one more than its predecessor.


def _iter_area_word_ranks(m: int, n: int) -> Iterator[list[int]]:
    total = m + n

    def extend(ranks: list[int], unbarred_left: int, barred_left: int) -> Iterator[list[int]]:
        if len(ranks) == total:
            yield ranks
            return
        previous = ranks[-1]
        for rank in range(1, previous + 2):
            if rank % 2 == 0:  # barred letter
                if barred_left:
                    yield from extend(ranks + [rank], unbarred_left, barred_left - 1)
            else:  # unbarred letter
                if unbarred_left:
                    yield from extend(ranks + [rank], unbarred_left - 1, barred_left)

    yield from extend([0], m, n - 1)


def _paths_from_ranks(ranks: list[int]) -> tuple[str, str]:
    """Reconstruct the ``(upper, lower)`` paths from an area word's ranks.

    Each rank is the height of a rise of the Dyck path ``ptd(P)``; inserting the
    intervening falls rebuilds the Dyck path, whose odd-position steps are the
    upper path (rise -> N, fall -> E) and even-position steps the lower path
    (rise -> E, fall -> N).
    """
    steps: list[int] = []  # +1 rise, -1 fall
    height = 0
    for rank in ranks:
        steps.extend([-1] * (height - rank))
        steps.append(1)
        height = rank + 1
    steps.extend([-1] * height)

    upper: list[str] = []
    lower: list[str] = []
    for position, step in enumerate(steps, start=1):
        if position % 2 == 1:
            upper.append("N" if step == 1 else "E")
        else:
            lower.append("E" if step == 1 else "N")
    return "".join(upper), "".join(lower)


def polyomino_from_ranks(ranks: list[int]) -> str:
    """Encode the polyomino whose area word has the given letter ranks.

    ``ranks`` must be a valid area word (start at ``0``; every rank at most one
    more than its predecessor). This is the inverse of reading an area word off
    the reconstructed boundary paths and is a convenient way to build a valid
    polyomino directly, without enumeration.
    """
    ranks = list(ranks)
    if (
        not ranks
        or ranks[0] != 0
        or any(type(rank) is not int or rank < 0 for rank in ranks)
        or 0 in ranks[1:]
        or not any(rank % 2 for rank in ranks)
        or any(rank > previous + 1 for previous, rank in zip(ranks, ranks[1:]))
    ):
        raise ValueError("ranks must be a valid polyomino area word")
    upper, lower = _paths_from_ranks(ranks)
    return f"{upper}{SEPARATOR}{lower}"


def iter_parallelogram_polyominoes(m: int, n: int) -> Iterator[str]:
    """Yield every ``m x n`` parallelogram polyomino once, streaming."""
    if m < 1 or n < 1:
        raise ValueError("both bounding-box dimensions must be positive")
    for ranks in _iter_area_word_ranks(m, n):
        upper, lower = _paths_from_ranks(ranks)
        yield f"{upper}{SEPARATOR}{lower}"


@cache
def enumerate_parallelogram_polyominoes(m: int, n: int) -> tuple[str, ...]:
    """All ``m x n`` parallelogram polyominoes (cached; use the iterator for size)."""
    return tuple(iter_parallelogram_polyominoes(m, n))


def polyomino_area_bounce_distribution(m: int, n: int) -> Counter[tuple[int, int]]:
    """Joint ``(area, bounce)`` distribution over ``Polyo_{m,n}`` (the q,t-Narayana)."""
    distribution: Counter[tuple[int, int]] = Counter()
    for encoding in iter_parallelogram_polyominoes(m, n):
        distribution[(polyomino_area(encoding), polyomino_bounce(encoding))] += 1
    return distribution
