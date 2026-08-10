"""Reference implementation of the public first statistic: type B area.

A type B Catalan path is a word of ``2n`` north (``N``) and east (``E``) steps
from ``(0, 0)`` that stays weakly above the diagonal ``y = x``. The area is the
number of boxes under the path in the type B (diamond) region: for the north
step out of ``(x, y)`` the row capacity is ``y`` while ``y < n`` and ``2n - y``
afterwards, and the step contributes ``capacity - x``.
"""
from __future__ import annotations


def area_from_steps(steps: str) -> int:
    n = len(steps) // 2
    x = y = 0
    total = 0
    for step in steps:
        if step == "N":
            capacity = y if y < n else 2 * n - y
            total += capacity - x
            y += 1
        else:
            x += 1
    return total


def statistic(path) -> int:
    return area_from_steps(path.steps)
