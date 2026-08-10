"""Reference implementations of the two public statistics, area and bounce.

A parallelogram polyomino with an m x n bounding box is encoded as the string
``upper + "|" + lower`` where ``upper`` and ``lower`` are the two boundary paths
as words of ``m`` East (``E``) and ``n`` North (``N``) steps from ``(0, 0)`` to
``(m, n)``, touching only at those corners. The upper path starts North, the
lower path starts East. Both statistics are public; the task is to find a
bijection between the transposed boxes that preserves them, not to discover a
statistic.
"""
from __future__ import annotations


def _paths(polyomino: str) -> tuple[str, str]:
    upper, lower = polyomino.split("|")
    return upper, lower


def _area_below(path: str) -> int:
    """Cells below a monotone N/E path: the sum of its East-step heights."""
    y = 0
    total = 0
    for step in path:
        if step == "N":
            y += 1
        else:
            total += y
    return total


def area(polyomino: str) -> int:
    """Area: the number of cells enclosed between the two boundary paths."""
    upper, lower = _paths(polyomino)
    return _area_below(upper) - _area_below(lower)


def bounce(polyomino: str) -> int:
    """Bounce statistic, read off the polyomino's bounce path.

    The bounce path leaves the Southwest corner with a single East step, then
    alternately travels North until it meets the East endpoint of an East step
    of the upper path and East until it meets the North endpoint of a North step
    of the lower path, until it reaches the Northeast corner. The k-th maximal
    run of North steps is labelled k and the k-th maximal run of East steps is
    labelled k - 1; bounce is the sum of the labels.
    """
    upper, lower = _paths(polyomino)
    m = upper.count("E")
    n = upper.count("N")

    upper_east_ends = set()
    x = y = 0
    for step in upper:
        if step == "E":
            x += 1
            upper_east_ends.add((x, y))
        else:
            y += 1

    lower_north_ends = set()
    x = y = 0
    for step in lower:
        if step == "N":
            y += 1
            lower_north_ends.add((x, y))
        else:
            x += 1

    total = 0
    x, y = 1, 0            # initial single East step (first East run, label 0)
    vertical_run = 0
    horizontal_run = 1
    moving_north = True
    while (x, y) != (m, n):
        if moving_north:
            vertical_run += 1
            while (x, y) not in upper_east_ends:
                y += 1
                total += vertical_run
            moving_north = False
        else:
            horizontal_run += 1
            while (x, y) not in lower_north_ends:
                x += 1
                total += horizontal_run - 1
            moving_north = True
    return total
