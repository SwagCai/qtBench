from __future__ import annotations

from collections import Counter
from functools import cache


DyckPath = str


def is_dyck_path(path: str) -> bool:
    if not isinstance(path, str):
        return False
    height = 0
    north = 0
    east = 0
    for step in path:
        if step == "N":
            height += 1
            north += 1
        elif step == "E":
            height -= 1
            east += 1
        else:
            return False
        if height < 0:
            return False
    return height == 0 and north == east


def dyck_size(path: str) -> int:
    if not is_dyck_path(path):
        raise ValueError(f"not a Dyck path: {path!r}")
    return len(path) // 2


def dyck_area(path: str) -> int:
    if not is_dyck_path(path):
        raise ValueError(f"not a Dyck path: {path!r}")
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


def dyck_bounce(path: str) -> int:
    if not is_dyck_path(path):
        raise ValueError(f"not a Dyck path: {path!r}")
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


def first_return(path: str) -> tuple[str, str]:
    if not is_dyck_path(path) or not path:
        raise ValueError("first_return requires a nonempty Dyck path")
    height = 0
    for index, step in enumerate(path):
        height += 1 if step == "N" else -1
        if height == 0:
            return path[1:index], path[index + 1 :]
    raise RuntimeError("unreachable")


@cache
def enumerate_dyck_paths(n: int) -> tuple[DyckPath, ...]:
    if n < 0:
        raise ValueError("n must be nonnegative")
    if n == 0:
        return ("",)
    paths: list[str] = []
    for left_size in range(n):
        right_size = n - 1 - left_size
        for left in enumerate_dyck_paths(left_size):
            for right in enumerate_dyck_paths(right_size):
                paths.append(f"N{left}E{right}")
    return tuple(paths)


def area_bounce_distribution(n: int) -> Counter[tuple[int, int]]:
    return Counter((dyck_area(path), dyck_bounce(path)) for path in enumerate_dyck_paths(n))
