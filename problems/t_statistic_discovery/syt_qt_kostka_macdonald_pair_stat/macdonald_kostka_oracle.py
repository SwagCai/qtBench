"""Public oracle: modified (q,t)-Kostka polynomials from the HHL formula.

MAINTAINER ONLY. The scored evaluator never loads this module; it exists so the
public target data in ``problems/t_statistic_discovery/
syt_qt_kostka_macdonald_pair_stat/data`` is reproducible.

The modified Macdonald polynomial is computed from the Haglund-Haiman-Loehr
formula (arXiv:math/0409538, Theorem 2.2),

    H~_mu(X; q, t) = sum_{sigma : dg(mu) -> Z_{>0}} q^{inv(sigma)} t^{maj(sigma)} x^sigma,

where the diagram ``dg(mu)`` is drawn in French notation (row ``1`` is the
longest, at the bottom) and, for a filling ``sigma``,

    Des(sigma) = { u : sigma(u) > sigma(south(u)) },
    maj(sigma) = sum_{u in Des(sigma)} (leg(u) + 1),
    inv(sigma) = |Inv(sigma)| - sum_{u in Des(sigma)} arm(u),

with ``Inv(sigma)`` the set of attacking pairs ``(u, v)``, ``u`` before ``v`` in
reading order (top row first, left to right inside a row), with
``sigma(u) > sigma(v)``. Two cells attack each other if they lie in the same row,
or in consecutive rows with the cell in the upper row strictly to the right of
the cell in the lower row.

Since ``H~_mu`` is symmetric it is determined by the coefficients of ``x^alpha``
for partitions ``alpha``, so only fillings whose content is a partition are
enumerated. The monomial expansion is then converted to the Schur basis by
back-substitution against the Kostka matrix ``s_lambda = sum_alpha K_{lambda
alpha} m_alpha``, which is unitriangular for the dominance order.
"""
from __future__ import annotations

from collections import Counter
from functools import lru_cache

PROBLEM_ID = 13
PROBLEM_NAME = "syt_qt_kostka_macdonald_pair_stat"


# ---------------------------------------------------------------------------
# Partitions
# ---------------------------------------------------------------------------


@lru_cache(maxsize=None)
def partitions(n: int) -> tuple[tuple[int, ...], ...]:
    """Every partition of ``n``, weakly decreasing, in reverse lexicographic order."""
    out: list[tuple[int, ...]] = []
    current: list[int] = []

    def rec(remaining: int, largest: int) -> None:
        if remaining == 0:
            out.append(tuple(current))
            return
        for part in range(min(remaining, largest), 0, -1):
            current.append(part)
            rec(remaining - part, part)
            current.pop()

    rec(n, n)
    return tuple(out)


def conjugate(mu: tuple[int, ...]) -> tuple[int, ...]:
    return tuple(sum(1 for part in mu if part > column) for column in range(mu[0]))


# ---------------------------------------------------------------------------
# Kostka numbers K_{lambda alpha} = #SSYT(lambda, alpha)
# ---------------------------------------------------------------------------


@lru_cache(maxsize=None)
def kostka_number(lam: tuple[int, ...], alpha: tuple[int, ...]) -> int:
    """Number of semistandard Young tableaux of shape ``lam`` and content ``alpha``."""
    lam = tuple(part for part in lam if part)
    if not alpha:
        return 1 if not lam else 0
    if sum(lam) != sum(alpha):
        return 0
    last = alpha[-1]
    total = 0
    for nu in _horizontal_strip_removals(lam, last):
        total += kostka_number(nu, alpha[:-1])
    return total


def _horizontal_strip_removals(lam: tuple[int, ...], size: int):
    """Every ``nu <= lam`` with ``lam / nu`` a horizontal strip of ``size`` cells."""
    height = len(lam)
    nu: list[int] = []

    def rec(index: int, remaining: int):
        if index == height:
            if remaining == 0:
                yield tuple(part for part in nu if part)
            return
        # nu_i must satisfy lam_{i+1} <= nu_i <= lam_i (no two removed cells in a column).
        low = lam[index + 1] if index + 1 < height else 0
        for value in range(low, lam[index] + 1):
            taken = lam[index] - value
            if taken > remaining:
                continue
            nu.append(value)
            yield from rec(index + 1, remaining - taken)
            nu.pop()

    yield from rec(0, size)


# ---------------------------------------------------------------------------
# The HHL statistics on fillings of dg(mu)
# ---------------------------------------------------------------------------


@lru_cache(maxsize=None)
def _diagram_data(mu: tuple[int, ...]):
    """Reading-order cell data of ``dg(mu)``: south index, arm, leg, attacking pairs.

    Rows are numbered from the bottom (row ``1`` is the longest); the reading
    order runs from the top row down, left to right inside each row.
    """
    mu_conjugate = conjugate(mu)
    cells = [
        (row, column)
        for row in range(len(mu), 0, -1)
        for column in range(1, mu[row - 1] + 1)
    ]
    index_of = {cell: index for index, cell in enumerate(cells)}
    south = [index_of[(row - 1, column)] if row > 1 else -1 for row, column in cells]
    arm = [mu[row - 1] - column for row, column in cells]
    leg = [mu_conjugate[column - 1] - row for row, column in cells]
    attacking = [
        (i, j)
        for i, (row_i, column_i) in enumerate(cells)
        for j, (row_j, column_j) in enumerate(cells)
        if i < j
        and (
            row_i == row_j
            or (row_i == row_j + 1 and column_i > column_j)
        )
    ]
    return tuple(south), tuple(arm), tuple(leg), tuple(attacking)


def _filling_statistics(values, south, arm, leg, attacking) -> tuple[int, int]:
    """``(inv, maj)`` of one filling, given in reading order."""
    maj = 0
    arm_correction = 0
    for index, below in enumerate(south):
        if below >= 0 and values[index] > values[below]:
            maj += leg[index] + 1
            arm_correction += arm[index]
    inversions = sum(1 for i, j in attacking if values[i] > values[j])
    return inversions - arm_correction, maj


def _multiset_permutations(content: tuple[int, ...]):
    """Distinct rearrangements of the word with ``content[i]`` copies of ``i + 1``.

    Generated directly, one letter at a time, so the cost is the multinomial
    ``n! / prod_i content_i!`` rather than ``n!``.
    """
    remaining = list(content)
    word: list[int] = []
    total = sum(content)

    def rec(placed: int):
        if placed == total:
            yield tuple(word)
            return
        for index, count in enumerate(remaining):
            if not count:
                continue
            remaining[index] = count - 1
            word.append(index + 1)
            yield from rec(placed + 1)
            word.pop()
            remaining[index] = count

    yield from rec(0)


def modified_macdonald_monomial(mu: tuple[int, ...]) -> dict[tuple[int, ...], Counter]:
    """``H~_mu`` in the monomial basis: ``alpha -> Counter[(i, j)] = [q^i t^j] c_alpha``."""
    south, arm, leg, attacking = _diagram_data(mu)
    expansion: dict[tuple[int, ...], Counter] = {}
    for alpha in partitions(sum(mu)):
        coefficients: Counter[tuple[int, int]] = Counter()
        for word in _multiset_permutations(alpha):
            inv, maj = _filling_statistics(word, south, arm, leg, attacking)
            coefficients[(inv, maj)] += 1
        expansion[alpha] = coefficients
    return expansion


def modified_macdonald_schur(mu: tuple[int, ...]) -> dict[tuple[int, ...], Counter]:
    """``H~_mu`` in the Schur basis: ``lambda -> Counter[(i, j)] = [q^i t^j] K~_{lambda mu}``."""
    n = sum(mu)
    monomial = modified_macdonald_monomial(mu)
    ordered = sorted(partitions(n), key=lambda part: tuple(-value for value in part))
    schur: dict[tuple[int, ...], Counter] = {}
    for alpha in ordered:
        coefficients = Counter(monomial[alpha])
        for lam in ordered:
            if lam == alpha:
                break
            multiplicity = kostka_number(lam, alpha)
            if multiplicity:
                for exponents, value in schur[lam].items():
                    coefficients[exponents] -= multiplicity * value
        schur[alpha] = Counter({key: value for key, value in coefficients.items() if value})
    return schur


def kostka_polynomials(n: int) -> dict[tuple[tuple[int, ...], tuple[int, ...]], Counter]:
    """``(lambda, mu) -> Counter[(i, j)] = [q^i t^j] K~_{lambda mu}(q, t)`` for all pairs."""
    out: dict[tuple[tuple[int, ...], tuple[int, ...]], Counter] = {}
    for mu in partitions(n):
        for lam, coefficients in modified_macdonald_schur(mu).items():
            out[(lam, mu)] = coefficients
    return out
