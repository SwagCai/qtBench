# Known-good submission for problem 1, the solved calibration problem.
# This file is self-contained and should pass every stage of the scored evaluator.


def statistic(partition):
    repeated_maxima = []
    nonmaximal_elements = []
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
            raise RuntimeError("calibration statistic did not terminate")
        fuel -= 1
        current = repeated_maxima[index]
        total += partition.n - current
        index = sum(1 for value in nonmaximal_elements if value < current)
    return total
