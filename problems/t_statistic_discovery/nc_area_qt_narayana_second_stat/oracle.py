from __future__ import annotations

PROBLEM_ID = 1
PROBLEM_NAME = "nc_area_qt_narayana_second_stat"


def statistic(partition) -> int:
    """Public target-generation oracle for the first problem.

    Scoring never loads this module.
    """

    repeated_maxima: list[int] = []
    nonmaximal_elements: list[int] = []
    for block in partition.blocks_by_max:
        repeated_maxima.extend([block[-1]] * (len(block) - 1))
        nonmaximal_elements.extend(block[:-1])

    if not repeated_maxima:
        return 0

    nonmaximal_elements.sort()
    total = 0
    index = 0
    fuel = len(repeated_maxima) + 1
    while index < len(repeated_maxima):
        if fuel <= 0:
            raise RuntimeError(f"oracle recursion did not terminate for {partition.blocks}")
        fuel -= 1
        current = repeated_maxima[index]
        total += partition.n - current
        index = sum(1 for value in nonmaximal_elements if value < current)
    return total
