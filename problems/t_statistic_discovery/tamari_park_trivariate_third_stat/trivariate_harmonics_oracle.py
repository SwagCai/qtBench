"""Public oracle: the target polynomials H_n(q1,q2,q3) of problem 12.

This public oracle is used only to
regenerate the public polynomial targets; the scored evaluator never loads it.

``H_n`` is the trigraded Hilbert series of the space of trivariate diagonal
harmonics of Bergeron and Preville-Ratelle (arXiv:1105.3738),

    H_n(q1, q2, q3) = sum_{d in N^3} dim(Harm_{n, d}) q1^{d1} q2^{d2} q3^{d3},

whose proposed missing-statistic expansion is Equation (49), the
``(q1, q2, q3)``-enumerator of the
pairs ``(f, alpha)`` with ``f`` a parking function of length ``n`` and ``alpha``
below its shape in the Tamari lattice, graded by ``d(alpha, beta(f))``,
``dinv(f)`` and a missing third statistic.

There is no known formula for ``Harm_n``: the source of this data is the
*published* graded Frobenius characteristic ``Harm_n(w; q)``, tabulated there for
``n <= 5``, transcribed below. Replacing each ``S_lambda(w)`` by the number
``f^lambda`` of standard Young tableaux of that shape turns the Frobenius
characteristic into the Hilbert series (the paper does exactly this to obtain its
own ``Harm_n(q)`` table, which the ``n <= 4`` entries here reproduce), and each
``s_mu`` is the Schur polynomial in the three variables ``q1, q2, q3``.
"""
from __future__ import annotations

from collections import Counter
from functools import lru_cache
from math import factorial

PROBLEM_ID = 12
PROBLEM_NAME = "tamari_park_trivariate_third_stat"


# ---------------------------------------------------------------------------
# The published graded Frobenius characteristics, Harm_n(w; q), for n <= 5
#
# Each entry maps an S_n irreducible lambda to the list of (mu, multiplicity)
# giving its coefficient sum_mu multiplicity * s_mu(q1, q2, q3).
# Transcribed from Equation (valeurs_Frob) of arXiv:1105.3738.
# ---------------------------------------------------------------------------

FROBENIUS: dict[int, dict[tuple[int, ...], list[tuple[tuple[int, ...], int]]]] = {
    1: {
        (1,): [((), 1)],
    },
    2: {
        (2,): [((), 1)],
        (1, 1): [((1,), 1)],
    },
    3: {
        (3,): [((), 1)],
        (2, 1): [((1,), 1), ((2,), 1)],
        (1, 1, 1): [((1, 1), 1), ((3,), 1)],
    },
    4: {
        (4,): [((), 1)],
        (3, 1): [((1,), 1), ((2,), 1), ((3,), 1)],
        (2, 2): [((2,), 1), ((2, 1), 1), ((4,), 1)],
        (2, 1, 1): [((1, 1), 1), ((3,), 1), ((2, 1), 1), ((4,), 1), ((3, 1), 1), ((5,), 1)],
        (1, 1, 1, 1): [((1, 1, 1), 1), ((3, 1), 1), ((4, 1), 1), ((6,), 1)],
    },
    5: {
        (5,): [((), 1)],
        (4, 1): [((1,), 1), ((2,), 1), ((3,), 1), ((4,), 1)],
        (3, 2): [
            ((2,), 1), ((3,), 1), ((2, 1), 1), ((4,), 1), ((3, 1), 1), ((2, 2), 1),
            ((5,), 1), ((4, 1), 1), ((6,), 1),
        ],
        (3, 1, 1): [
            ((1, 1), 1), ((3,), 1), ((2, 1), 1), ((4,), 1), ((3, 1), 2), ((5,), 2),
            ((4, 1), 1), ((3, 2), 1), ((6,), 1), ((5, 1), 1), ((7,), 1),
        ],
        (2, 2, 1): [
            ((2, 1), 1), ((4,), 1), ((3, 1), 1), ((2, 2), 1), ((2, 1, 1), 1), ((5,), 1),
            ((4, 1), 2), ((3, 2), 1), ((3, 1, 1), 1), ((6,), 1), ((5, 1), 2), ((4, 2), 1),
            ((7,), 1), ((6, 1), 1), ((8,), 1),
        ],
        (2, 1, 1, 1): [
            ((1, 1, 1), 1), ((3, 1), 1), ((2, 1, 1), 1), ((4, 1), 2), ((3, 2), 1),
            ((3, 1, 1), 1), ((6,), 1), ((5, 1), 2), ((4, 2), 1), ((4, 1, 1), 1),
            ((3, 3), 1), ((7,), 1), ((6, 1), 2), ((5, 2), 1), ((8,), 1), ((7, 1), 1),
            ((9,), 1),
        ],
        (1, 1, 1, 1, 1): [
            ((3, 1, 1), 1), ((4, 2), 1), ((4, 1, 1), 1), ((6, 1), 1), ((5, 1, 1), 1),
            ((4, 3), 1), ((7, 1), 1), ((6, 2), 1), ((8, 1), 1), ((10,), 1),
        ],
    },
}

PUBLIC_MAX_N = max(FROBENIUS)


# ---------------------------------------------------------------------------
# Standard Young tableaux and Schur polynomials in three variables
# ---------------------------------------------------------------------------


def conjugate(lam: tuple[int, ...]) -> tuple[int, ...]:
    if not lam:
        return ()
    return tuple(sum(1 for part in lam if part >= i) for i in range(1, lam[0] + 1))


def standard_tableaux_count(lam: tuple[int, ...]) -> int:
    """``f^lambda``, by the hook length formula."""
    n = sum(lam)
    conj = conjugate(lam)
    hooks = 1
    for row, part in enumerate(lam):
        for column in range(part):
            hooks *= part - column + conj[column] - row - 1
    return factorial(n) // hooks


@lru_cache(maxsize=None)
def schur_three(mu: tuple[int, ...]) -> tuple[tuple[tuple[int, int, int], int], ...]:
    """``s_mu(q1, q2, q3)`` as a list of ``(exponent triple, coefficient)``.

    Semistandard Young tableaux of shape ``mu`` with entries in ``{1, 2, 3}``
    are enumerated directly; a shape with more than three rows contributes zero.
    """
    if len(mu) > 3:
        return ()
    if not mu:
        return (((0, 0, 0), 1),)
    cells = [(row, column) for row, part in enumerate(mu) for column in range(part)]
    counter: Counter[tuple[int, int, int]] = Counter()
    filling: dict[tuple[int, int], int] = {}

    def rec(index: int) -> None:
        if index == len(cells):
            content = [0, 0, 0]
            for value in filling.values():
                content[value - 1] += 1
            counter[tuple(content)] += 1
            return
        row, column = cells[index]
        low = 1
        if column:
            low = max(low, filling[(row, column - 1)])       # weakly increasing rows
        if row:
            low = max(low, filling[(row - 1, column)] + 1)   # strictly increasing columns
        for value in range(low, 4):
            filling[(row, column)] = value
            rec(index + 1)
        filling.pop((row, column), None)

    rec(0)
    return tuple(sorted(counter.items()))


def H_poly(n: int) -> dict[tuple[int, int, int], int]:
    """Return ``{(d1, d2, d3): dim}`` of the trigraded Hilbert series ``H_n``."""
    if n not in FROBENIUS:
        raise ValueError(f"no published Frobenius characteristic for n = {n}")
    counter: Counter[tuple[int, int, int]] = Counter()
    for lam, terms in FROBENIUS[n].items():
        dimension = standard_tableaux_count(lam)
        for mu, multiplicity in terms:
            for exponents, coefficient in schur_three(mu):
                counter[exponents] += dimension * multiplicity * coefficient
    return {key: value for key, value in counter.items() if value}


def frobenius_dimension(n: int) -> int:
    """``H_n(1, 1, 1)``, which should be ``2^n (n+1)^{n-2}``."""
    return sum(H_poly(n).values())


def is_symmetric(poly: dict[tuple[int, int, int], int]) -> bool:
    """Whether the Hilbert series is symmetric in ``q1, q2, q3``."""
    return all(
        poly.get(tuple(permuted), 0) == value
        for exponents, value in poly.items()
        for permuted in _permutations_of(exponents)
    )


def _permutations_of(exponents):
    a, b, c = exponents
    return ((a, b, c), (a, c, b), (b, a, c), (b, c, a), (c, a, b), (c, b, a))


def bivariate_slice(
    poly: dict[tuple[int, int, int], int], third: int
) -> dict[tuple[int, int], int]:
    """Specialize ``q3`` to ``0`` (``third = 0``) or to ``1`` (``third = 1``)."""
    counter: Counter[tuple[int, int]] = Counter()
    for (d1, d2, d3), value in poly.items():
        if third == 0 and d3:
            continue
        counter[(d1, d2)] += value
    return {key: value for key, value in counter.items() if value}
