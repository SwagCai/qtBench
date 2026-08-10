from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Iterable

from .type_a.noncrossing import NoncrossingPartition

Term2D = tuple[int, int, int]
PairCounter = Counter[tuple[int, int]]


def canonical_terms(counter: Counter[tuple[int, int]] | dict[tuple[int, int], int]) -> list[list[int]]:
    terms: list[list[int]] = []
    for (q_exp, t_exp), coeff in sorted(counter.items()):
        if coeff:
            terms.append([int(q_exp), int(t_exp), int(coeff)])
    return terms


def terms_to_counter(terms: Iterable[Iterable[int]]) -> Counter[tuple[int, int]]:
    counter: Counter[tuple[int, int]] = Counter()
    for term in terms:
        q_exp, t_exp, coeff = [int(value) for value in term]
        if coeff:
            counter[(q_exp, t_exp)] += coeff
    return counter


def joint_distribution(
    partitions: Iterable[NoncrossingPartition],
    left_statistic: Callable[[NoncrossingPartition], int],
    right_statistic: Callable[[NoncrossingPartition], int],
) -> Counter[tuple[int, int]]:
    counter: Counter[tuple[int, int]] = Counter()
    for partition in partitions:
        q_exp = int(left_statistic(partition))
        t_exp = int(right_statistic(partition))
        if q_exp < 0 or t_exp < 0:
            raise ValueError(f"statistics must be nonnegative, got {(q_exp, t_exp)} for {partition.blocks}")
        counter[(q_exp, t_exp)] += 1
    return counter
