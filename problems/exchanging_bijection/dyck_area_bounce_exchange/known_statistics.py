"""Reference implementations of the two public statistics, area and bounce.

A Dyck path of semilength n is a string of n 'N' (north) and n 'E' (east) steps
that never goes below the diagonal. Both statistics are public; the task is to
find a bijection that exchanges them, not to discover a statistic.
"""
from __future__ import annotations


def area(path: str) -> int:
    """Number of full lattice squares between the path and the diagonal."""
    x = 0
    y = 0
    total = 0
    for step in path:
        if step == "N":
            total += y - x
            y += 1
        else:
            x += 1
    return total


def bounce(path: str) -> int:
    """Haglund's bounce statistic, from the bounce path's returns to the diagonal."""
    height = 0
    east_heights: list[int] = []
    for step in path:
        if step == "N":
            height += 1
        else:
            east_heights.append(height)
    n = len(east_heights)
    point = 0
    total = 0
    while point < n:
        point = east_heights[point]
        total += n - point
    return total
